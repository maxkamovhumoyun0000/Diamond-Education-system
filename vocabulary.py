import io
import random
from typing import List, Dict, Any, Tuple
from openpyxl import load_workbook
from db import get_conn
from openpyxl import Workbook
import io

EXPECTED_VOCAB_HEADERS = ['Level', 'Word', 'translation_uz', 'translation_ru', 'Example Sentence 1', 'Example Sentence 2']


def get_available_vocabulary_levels(user_level: str) -> list:
    """User levelidan past va teng leveldagi darajalarni qaytaradi"""
    level_order = ['A1', 'A2', 'B1', 'B2', 'C1']
    try:
        idx = level_order.index(user_level.upper())
        return level_order[:idx+1]  # o'zi va pastdagilar
    except ValueError:
        return level_order  # agar level noto'g'ri bo'lsa hammasi


def parse_excel_bytes(file_bytes: bytes) -> List[Dict[str, Any]]:
    wb = load_workbook(io.BytesIO(file_bytes), read_only=True)
    sheet = wb.active
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        return []

    raw_headers = [str(h).strip().lower() if h is not None else '' for h in rows[0]]
    results = []
    for row in rows[1:]:
        if all(c is None for c in row):
            continue
        entry = {}
        example_parts = []

        for i, cell in enumerate(row):
            if i >= len(raw_headers):
                continue
            key = raw_headers[i]
            if 'example sentence' in key or key == 'example':
                if cell:
                    example_parts.append(str(cell))
            else:
                mapped = {
                    'level': 'level',
                    'word': 'word',
                    'translation_uz': 'translation_uz',
                    'translation_ru': 'translation_ru',
                    'definition': 'definition'
                }.get(key, key)
                entry[mapped] = cell

        entry['example'] = '\n'.join(example_parts) if example_parts else ''
        results.append(entry)

    return results


def import_words_from_excel(file_bytes: bytes, file_name: str, added_by: int, subject: str, language: str):
    parsed = parse_excel_bytes(file_bytes)
    conn = get_conn()
    cur = conn.cursor()

    cur.execute('INSERT INTO vocabulary_imports (file_name, added_by, subject, language) VALUES (?,?,?,?)',
                (file_name, added_by, subject, language))
    import_id = cur.lastrowid

    inserted = 0
    skipped = 0
    duplicate_words = []

    for entry in parsed:
        word = (entry.get('word') or '').strip()
        if not word:
            continue

        cur.execute("""
            SELECT id FROM words 
            WHERE LOWER(word) = LOWER(?) 
              AND subject = ? 
              AND language = ?
        """, (word, subject, language))

        if cur.fetchone():
            skipped += 1
            duplicate_words.append(word)
            continue

        level = entry.get('level') or ''
        translation_uz = entry.get('translation_uz') or ''
        translation_ru = entry.get('translation_ru') or ''
        definition = entry.get('definition') or ''
        example = entry.get('example') or ''

        cur.execute('''
            INSERT INTO words 
            (word, subject, language, level, translation_uz, translation_ru, definition, example, added_by)
            VALUES (?,?,?,?,?,?,?,?,?)
        ''', (word, subject, language, level, translation_uz, translation_ru, definition, example, added_by))

        inserted += 1

    conn.commit()
    conn.close()

    return {
        'import_id': import_id,
        'inserted': inserted,
        'skipped': skipped,
        'duplicates': duplicate_words,
        'total': len(parsed)
    }


def search_words(subject: str, query: str) -> List[Dict[str, Any]]:
    if not subject or not query:
        return []
    
    conn = get_conn()
    try:
        cur = conn.cursor()
        q = f"%{query.strip().lower()}%"
        cur.execute('''SELECT * FROM words WHERE subject=? AND (LOWER(word) LIKE ? OR LOWER(translation_uz) LIKE ? OR LOWER(translation_ru) LIKE ?) LIMIT 50''',
                    (subject, q, q, q))
        rows = cur.fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"Error in search_words: {e}")
        return []
    finally:
        conn.close()


def get_words_by_subject_level(subject: str, level: str) -> List[Dict[str, Any]]:
    """Get words by subject and level from the database"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('''SELECT * FROM words WHERE subject=? AND level=? ORDER BY RANDOM() LIMIT 50''',
                (subject, level))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_student_preference(user_id: int, preferred_translation: str):
    conn = get_conn()
    cur = conn.cursor()
    # Upsert style: delete existing then insert
    cur.execute('DELETE FROM student_preferences WHERE user_id=?', (user_id,))
    cur.execute('INSERT INTO student_preferences (user_id, preferred_translation) VALUES (?,?)', (user_id, preferred_translation))
    conn.commit()
    conn.close()


def get_student_preference(user_id: int) -> str:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT preferred_translation FROM student_preferences WHERE user_id=?', (user_id,))
    row = cur.fetchone()
    conn.close()
    return row['preferred_translation'] if row else None


def _get_random_distractors(cur, subject, language, column, correct_value, count=3):
    cur.execute(f'SELECT DISTINCT {column} FROM words WHERE subject=? AND language=? AND {column} IS NOT NULL AND LOWER({column})!=? ORDER BY RANDOM() LIMIT ?',
                (subject, language, (correct_value or '').lower(), count))
    rows = cur.fetchall()
    return [r[0] for r in rows if r[0]]

def _ensure_four_options(cur, subject: str, language: str, column: str, options: List[str]) -> List[str]:
    """Pad options to 4 unique items (best effort) using random values from DB."""
    seen = []
    for o in options:
        if o and o not in seen:
            seen.append(o)
    # pull extra candidates until we reach 4 or exhaust tries
    tries = 0
    while len(seen) < 4 and tries < 5:
        need = 4 - len(seen)
        cur.execute(
            f"SELECT DISTINCT {column} FROM words WHERE subject=? AND language=? AND {column} IS NOT NULL ORDER BY RANDOM() LIMIT ?",
            (subject, language, need),
        )
        for r in cur.fetchall():
            val = r[0]
            if val and val not in seen:
                seen.append(val)
        tries += 1
    return seen[:4]


def generate_quiz(user_id: int, subject: str, level: str, count: int, qtype: str, preferred_translation: str) -> List[Dict[str, Any]]:
    """
    qtype: 'multiple_choice', 'gap_filling', 'definition'
    preferred_translation: 'uz' or 'ru' — which translation language to use when presenting translations
    Returns list of questions with options and correct answer index/value
    """
    conn = get_conn()
    cur = conn.cursor()
    params = [subject]
    sql = 'SELECT * FROM words WHERE subject=?'
    if level:
        sql += ' AND level=?'
        params.append(level)
    sql += ' ORDER BY RANDOM() LIMIT ?'
    params.append(count)
    cur.execute(sql, tuple(params))
    rows = cur.fetchall()
    words = [dict(r) for r in rows]

    questions = []
    for w in words:
        if qtype == 'multiple_choice':
            # Decide whether to ask for translation or the word itself randomly
            ask_translation = random.choice([True, False])
            if ask_translation:
                correct = w['translation_uz'] if preferred_translation == 'uz' else w['translation_ru']
                if not correct:
                    # fallback to other
                    correct = w['translation_uz'] or w['translation_ru'] or w['word']
                distractors = _get_random_distractors(cur, subject, w['language'], 'translation_uz' if preferred_translation == 'uz' else 'translation_ru', correct, 3)
                options = _ensure_four_options(cur, subject, w['language'], 'translation_uz' if preferred_translation == 'uz' else 'translation_ru', [correct] + distractors)
                random.shuffle(options)
                questions.append({'type': 'multiple_choice', 'prompt': w['word'], 'options': options, 'correct': correct, 'ask': 'translation'})
            else:
                # Ask to choose the correct word given a translation
                correct = w['word']
                col = 'translation_uz' if preferred_translation == 'uz' else 'translation_ru'
                prompt = w[col] or w['translation_uz'] or w['translation_ru'] or ''
                distractors = _get_random_distractors(cur, subject, w['language'], 'word', correct, 3)
                options = _ensure_four_options(cur, subject, w['language'], 'word', [correct] + distractors)
                random.shuffle(options)
                questions.append({'type': 'multiple_choice', 'prompt': prompt, 'options': options, 'correct': correct, 'ask': 'word'})

        elif qtype == 'gap_filling':
            example = w.get('example') or ''
            if not example or w['word'] == '':
                # fallback to multiple choice
                questions.append({'type': 'multiple_choice', 'prompt': w['word'], 'options': [w['word']], 'correct': w['word'], 'ask': 'word'})
                continue
            # replace first occurrence of the word (case-insensitive)
            import re
            pattern = re.compile(re.escape(w['word']), re.IGNORECASE)
            blanked = pattern.sub('_____', example, count=1)
            # options: correct word + distractors
            distractors = _get_random_distractors(cur, subject, w['language'], 'word', w['word'], 3)
            options = _ensure_four_options(cur, subject, w['language'], 'word', [w['word']] + distractors)
            random.shuffle(options)
            questions.append({'type': 'gap_filling', 'prompt': blanked, 'options': options, 'correct': w['word']})

        elif qtype == 'definition':
            correct = w.get('definition') or ''
            if not correct:
                # fallback to multiple choice on word
                distractors = _get_random_distractors(cur, subject, w['language'], 'word', w['word'], 3)
                options = [w['word']] + distractors
                random.shuffle(options)
                questions.append({'type': 'multiple_choice', 'prompt': w['word'], 'options': options, 'correct': w['word'], 'ask': 'word'})
                continue
            distractors = _get_random_distractors(cur, subject, w['language'], 'definition', correct, 3)
            options = _ensure_four_options(cur, subject, w['language'], 'definition', [correct] + distractors)
            random.shuffle(options)
            questions.append({'type': 'definition', 'prompt': w['word'], 'options': options, 'correct': correct})

    conn.close()
    return questions


def export_words_to_xlsx(subject: str) -> Tuple[io.BytesIO, str]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT * FROM words WHERE subject=? ORDER BY word', (subject,))
    rows = cur.fetchall()
    conn.close()

    wb = Workbook()
    ws = wb.active
    ws.title = f"{subject} Vocabulary"
    
    # Use the same headers as import format
    headers = ['word', 'level', 'translation_uz', 'translation_ru', 'definition', 'example']
    ws.append(headers)
    
    for r in rows:
        row_dict = dict(r)
        ws.append([
            row_dict['word'], row_dict.get('level') or '', row_dict.get('translation_uz') or '', row_dict.get('translation_ru') or '',
            row_dict.get('definition') or '', row_dict.get('example') or ''
        ])

    # Auto-adjust column widths for better readability
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 30)
        ws.column_dimensions[column_letter].width = adjusted_width

    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    
    # Use the same naming convention as import
    filename = f"Vocabulary_importing_List_for_{subject}.xlsx"
    return bio, filename


def export_all_groups_to_xlsx() -> Tuple[io.BytesIO, str]:
    from db import get_all_groups, get_group_users
    groups = get_all_groups()
    wb = Workbook()
    ws = wb.active
    ws.append(['group_id', 'group_name', 'level', 'teacher_id', 'teacher_name', 'student_id', 'student_login', 'student_name', 'student_subject', 'student_level'])
    for g in groups:
        users = get_group_users(g['id'])
        teacher_name = ''
        if g.get('teacher_id'):
            from db import get_user_by_id
            t = get_user_by_id(g['teacher_id'])
            if t:
                teacher_name = f"{t.get('first_name','')} {t.get('last_name','')}"
        if not users:
            ws.append([g['id'], g['name'], g.get('level') or '', g.get('teacher_id'), teacher_name, '', '', '', '', ''])
        else:
            for u in users:
                ws.append([g['id'], g['name'], g.get('level') or '', g.get('teacher_id'), teacher_name, u['id'], u.get('login_id'), f"{u.get('first_name','')} {u.get('last_name','')}", u.get('subject'), u.get('level')])

    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    return bio, 'groups_with_students.xlsx'


def export_groups_for_teacher_to_xlsx(teacher_id: int) -> Tuple[io.BytesIO, str]:
    from db import get_groups_by_teacher, get_group_users, get_user_by_id
    groups = get_groups_by_teacher(teacher_id)
    wb = Workbook()
    ws = wb.active
    ws.append(['group_id', 'group_name', 'level', 'teacher_id', 'teacher_name', 'student_id', 'student_login', 'student_name', 'student_subject', 'student_level'])
    for g in groups:
        users = get_group_users(g['id'])
        teacher_name = ''
        if g.get('teacher_id'):
            t = get_user_by_id(g['teacher_id'])
            if t:
                teacher_name = f"{t.get('first_name','')} {t.get('last_name','')}"
        if not users:
            ws.append([g['id'], g['name'], g.get('level') or '', g.get('teacher_id'), teacher_name, '', '', '', '', ''])
        else:
            for u in users:
                ws.append([g['id'], g['name'], g.get('level') or '', g.get('teacher_id'), teacher_name, u['id'], u.get('login_id'), f"{u.get('first_name','')} {u.get('last_name','')}", u.get('subject'), u.get('level')])

    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    return bio, f'teacher_{teacher_id}_groups.xlsx'


def export_students_to_xlsx() -> Tuple[io.BytesIO, str]:
    from db import get_all_users
    users = get_all_users()
    wb = Workbook()
    ws = wb.active
    ws.append(['id', 'login_id', 'first_name', 'last_name', 'phone', 'subject', 'level', 'telegram_id', 'group_id', 'access_enabled'])
    for u in users:
        ws.append([u.get('id'), u.get('login_id'), u.get('first_name'), u.get('last_name'), u.get('phone'), u.get('subject'), u.get('level'), u.get('telegram_id'), u.get('group_id'), u.get('access_enabled')])

    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    return bio, 'all_students.xlsx'


def export_full_system_to_xlsx() -> Tuple[io.BytesIO, str]:
    """
    Export all sqlite tables into a single XLSX workbook.
    Each table becomes a separate worksheet.
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]

    wb = Workbook()
    # Replace default sheet with a small info sheet
    ws_info = wb.active
    ws_info.title = 'meta'
    from datetime import datetime
    ws_info.append(['exported_at_utc', datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')])
    ws_info.append(['tables', ', '.join(tables)])

    for table in tables:
        # Excel sheet title max length is 31
        sheet_name = table[:31]
        ws = wb.create_sheet(title=sheet_name)
        cur.execute(f'SELECT * FROM "{table}"')
        rows = cur.fetchall()
        headers = [d[0] for d in (cur.description or [])]
        if headers:
            ws.append(headers)
        for r in rows:
            # sqlite3.Row supports dict/sequence access
            ws.append([r[h] for h in headers])

    conn.close()
    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    return bio, 'diamond_full_export.xlsx'


def export_all_attendance_to_xlsx() -> Tuple[io.BytesIO, str]:
    """Export all attendance data to Excel"""
    from db import get_conn, get_all_groups, get_group_users
    
    conn = get_conn()
    cur = conn.cursor()
    
    # Get all attendance records
    cur.execute("""
        SELECT a.user_id, a.group_id, a.date, a.status, 
               u.first_name, u.last_name, u.login_id, u.telegram_id,
               g.name as group_name, g.level as group_level
        FROM attendance a
        JOIN users u ON a.user_id = u.id
        JOIN groups g ON a.group_id = g.id
        ORDER BY a.date DESC, g.name, u.first_name
    """)
    
    attendance_data = cur.fetchall()
    conn.close()
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Attendance"
    
    # Headers
    headers = ['Date', 'Group', 'Group Level', 'Student ID', 'First Name', 'Last Name', 'Telegram ID', 'Status']
    ws.append(headers)
    
    # Data
    for row in attendance_data:
        ws.append([
            row['date'],
            row['group_name'],
            row['group_level'],
            row['login_id'],
            row['first_name'],
            row['last_name'],
            row['telegram_id'] or '-',
            row['status']
        ])
    
    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    return bio, 'attendance_all_export.xlsx'


def export_group_attendance_to_xlsx(group_id: int) -> Tuple[io.BytesIO, str]:
    """Export attendance data for a specific group to Excel"""
    from db import get_conn, get_group
    
    group = get_group(group_id)
    if not group:
        raise ValueError("Group not found")
    
    conn = get_conn()
    cur = conn.cursor()
    
    # Get attendance for this group
    cur.execute("""
        SELECT a.user_id, a.date, a.status, 
               u.first_name, u.last_name, u.login_id, u.telegram_id
        FROM attendance a
        JOIN users u ON a.user_id = u.id
        WHERE a.group_id = ?
        ORDER BY a.date DESC, u.first_name
    """, (group_id,))
    
    attendance_data = cur.fetchall()
    conn.close()
    
    wb = Workbook()
    ws = wb.active
    ws.title = f"Attendance - {group['name']}"
    
    # Headers
    headers = ['Date', 'Student ID', 'First Name', 'Last Name', 'Telegram ID', 'Status']
    ws.append(headers)
    
    # Data
    for row in attendance_data:
        ws.append([
            row['date'],
            row['login_id'],
            row['first_name'],
            row['last_name'],
            row['telegram_id'] or '-',
            row['status']
        ])
    
    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    return bio, f'attendance_{group["name"]}_export.xlsx'
