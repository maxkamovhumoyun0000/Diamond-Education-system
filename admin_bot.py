import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types.input_file import BufferedInputFile
from aiogram.filters import Command
import unicodedata
import re
import asyncio
from datetime import datetime
import pytz
from openpyxl import Workbook
from openpyxl.styles import Font

from config import ADMIN_BOT_TOKEN, STUDENT_BOT_TOKEN, SUBJECTS, ADMIN_CHAT_IDS
from db import (
    create_user,
    get_recent_results,
    get_recent_users,
    get_all_users,
    get_all_teachers,
    enable_access,
    disable_access,
    get_user_by_id,
    get_user_by_telegram,
    update_user_subjects,
    get_user_subjects,
    prepare_user_for_new_test,
    is_access_active,
    update_user_subject,
    create_group,
    get_all_groups,
    get_groups_by_teacher,
    get_group_users,
    add_user_to_group,
    remove_user_from_group,
    update_group_name,
    update_group_level,
    update_group_teacher,
    update_group_schedule,
    update_group_subject,
    delete_group,
    add_attendance,
    get_attendance_by_group,
    get_group,
    get_user_groups,
    get_conn,
    set_pending_approval,
    set_user_language_by_telegram,
    get_teacher_groups_count,
    get_teacher_students_count,
    get_teacher_total_students,
    get_student_subjects,
)
from auth import create_user_sync, restore_sessions_on_startup
from utils import admin_main_keyboard, cancel_keyboard, create_user_type_keyboard, create_subject_keyboard, create_dual_choice_keyboard, create_group_action_keyboard, create_group_list_keyboard, create_teacher_selection_keyboard, create_user_selection_keyboard, create_user_selection_keyboard_by_type, create_language_selection_keyboard_for_user, create_group_teacher_selection_keyboard, create_language_selection_keyboard_for_self
from i18n import t, t_from_update, detect_lang_from_user
from payment import set_month_paid, is_month_paid, was_notified_on_day, mark_notified_day
from attendance_manager import attendance_scheduler, send_attendance_panel, build_attendance_keyboard, get_session, set_session_closed, set_session_opened
from broadcast_system import setup_broadcast_handlers
from logging_config import get_logger

# Setup logger
logger = get_logger(__name__)

bot: Bot | None = None
student_notify_bot: Bot | None = None
dp = Dispatcher()

# Keep transient admin state between steps in-memory.
admin_state = {}


def get_admin_state(chat_id: int):
    return admin_state.setdefault(chat_id, {'step': None, 'data': {}, 'list_page': 0, 'list_users': []})


def reset_admin_state(chat_id: int):
    admin_state.pop(chat_id, None)


def _normalize_hhmm(s: str) -> str | None:
    s = (s or "").strip()
    # allow both 14:00 and 14.00, normalize to HH:MM
    s = s.replace(".", ":")
    # Accept formats like 9, 9:0, 9:00, 09:00, 14:00, 14.00
    m = re.match(r"^([0-1]?\d|2[0-3])(?::([0-5]?\d))?$", s)
    if not m:
        return None
    hh = int(m.group(1))
    mm = int(m.group(2)) if m.group(2) else 0
    return f"{hh:02d}:{mm:02d}"


def _parse_time_range(s: str) -> tuple[str | None, str | None]:
    """
    Parse strings like '14.00-15.30' or '14:00-15:30' into (HH:MM, HH:MM).
    """
    s = (s or "").strip()
    # remove spaces to be tolerant of '14.00 - 15.30'
    s = s.replace(" ", "")
    if "-" not in s:
        return None, None
    start_raw, end_raw = s.split("-", 1)
    start = _normalize_hhmm(start_raw)
    end = _normalize_hhmm(end_raw)
    return start, end


def _lesson_days_label(lesson_date: str | None) -> str:
    if not lesson_date:
        return '-'
    if lesson_date.upper() in ('MWF', 'MON/WED/FRI', 'MON,WED,FRI'):
        return 'Mon, Wed, Fri'
    if lesson_date.upper() in ('TTS', 'TUE/THU/SAT', 'TUE,THU,SAT'):
        return 'Tue, Thu, Sat'
    return lesson_date


def _to_lesson_days_key(days: str) -> str:
    if not days:
        return ''
    days = days.strip().lower()
    if days in ('mwf', 'mon/wed/fri', 'mon,wed,fri', 'mon,wednesday,fri'):
        return 'MWF'
    if days in ('tts', 'tue/thu/sat', 'tue,thu,sat', 'tuesday,thursday,saturday'):
        return 'TTS'
    # Fallback: keep uppercase text
    return days.upper()


def _to_lesson_days_text(days: str) -> str:
    d = _to_lesson_days_key(days)
    if d == 'MWF':
        return 'Mon/Wed/Fri'
    if d == 'TTS':
        return 'Tue/Thu/Sat'
    return days


def _to_minutes(t: str | None) -> int | None:
    if not t:
        return None
    parts = t.split(':')
    if len(parts) != 2:
        return None
    try:
        h = int(parts[0])
        m = int(parts[1])
        return h * 60 + m
    except ValueError:
        return None


def _times_conflict(start1: str, end1: str, start2: str, end2: str) -> bool:
    m1 = _to_minutes(start1)
    m2 = _to_minutes(end1)
    n1 = _to_minutes(start2)
    n2 = _to_minutes(end2)
    if None in (m1, m2, n1, n2):
        return False
    # Overlap if start1 < end2 and start2 < end1
    return m1 < n2 and n1 < m2


def _teacher_conflicts(teacher_id: int, lesson_date: str, start: str, end: str, exclude_group_id: int | None = None) -> bool:
    if not lesson_date or not start or not end:
        return False
    groups = get_groups_by_teacher(teacher_id)
    for g in groups:
        if exclude_group_id and g.get('id') == exclude_group_id:
            continue
        if not g.get('lesson_date') or not g.get('lesson_start') or not g.get('lesson_end'):
            continue
        if _to_lesson_days_key(g.get('lesson_date')) != _to_lesson_days_key(lesson_date):
            continue
        if _times_conflict(start, end, g.get('lesson_start'), g.get('lesson_end')):
            return True
    return False


def _format_group_line(idx: int, g: dict) -> str:
    subject = (g.get("subject") or g.get("level") or "-")
    name = g.get("name") or "-"
    level = g.get("level") or "-"
    start = (g.get("lesson_start") or "-")[:5]
    end = (g.get("lesson_end") or "-")[:5]
    raw_date = g.get("lesson_date") or "-"
    if raw_date.upper() in ('MWF', 'MON/WED/FRI', 'MON,WED,FRI'):
        date = 'Mon, Wed, Fri'
    elif raw_date.upper() in ('TTS', 'TUE/THU/SAT', 'TUE,THU,SAT'):
        date = 'Tue, Thu, Sat'
    else:
        date = raw_date
    return (
        f"{idx}. Fan: {subject}\n"
        f"   Nomi: {name}\n"
        f"   Level: {level}\n"
        f"   Dars: {date} | {start}-{end}\n"
    )


def _groups_page(groups: list[dict], page: int, page_size: int = 10) -> list[dict]:
    start = max(0, page) * page_size
    return groups[start:start + page_size]


def _group_list_keyboard(page_groups: list[dict], page: int, total_pages: int, base: str, lang: str):
    # base examples: "group_list", "rec_groups:<user_id>", "assign_group:<user_id>"
    rows = []
    nums = []
    for i, g in enumerate(page_groups, start=1):
        nums.append(InlineKeyboardButton(text=str(i), callback_data=f"{base}:pick:{g['id']}"))
    if nums:
        rows.append(nums[:5])
        if len(nums) > 5:
            rows.append(nums[5:10])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text=t(lang, "btn_back"), callback_data=f"{base}:page:{page-1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text=t(lang, "btn_next"), callback_data=f"{base}:page:{page+1}"))
    if nav:
        rows.append(nav)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _student_list_keyboard(page_users: list[dict], page: int, total_pages: int, base: str, lang: str):
    rows = []
    nums = []
    for i, u in enumerate(page_users, start=1):
        label = f"{i}. {u.get('first_name','')} {u.get('last_name','')}".strip()
        nums.append(InlineKeyboardButton(text=label, callback_data=f"{base}:pick:{u['id']}"))
    if nums:
        rows.append(nums[:5])
        if len(nums) > 5:
            rows.append(nums[5:10])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text=t(lang, "btn_back"), callback_data=f"{base}:page:{page-1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text=t(lang, "btn_next"), callback_data=f"{base}:page:{page+1}"))
    if nav:
        rows.append(nav)
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def monthly_payment_scheduler(student_bot: Bot):
    """Send monthly payment reminders on 1/5/15/25 to unpaid students."""
    tz = pytz.timezone("Asia/Tashkent")
    remind_days = {1, 5, 15, 25}
    while True:
        try:
            now = datetime.now(tz)
            day = now.day
            # Run only on target days
            if day in remind_days:
                # Month key must follow Uzbekistan time
                ym = now.strftime("%Y-%m")
                users = [u for u in get_all_users() if u.get('login_type') in (1, 2)]
                for u in users:
                    if u.get('blocked'):
                        continue
                    tg = u.get('telegram_id')
                    if not tg:
                        continue
                    groups = get_user_groups(u['id'])
                    if not groups:
                        continue
                    # Notify only if any group is unpaid
                    unpaid = [g for g in groups if not is_month_paid(u['id'], ym=ym, group_id=g['id'])]
                    if not unpaid:
                        continue
                    if was_notified_on_day(u['id'], day, ym):
                        continue
                    try:
                        await student_bot.send_message(int(tg), t(detect_lang_from_user(u), "payment_reminder"))
                        mark_notified_day(u['id'], day, ym)
                    except Exception:
                        logger.exception("Monthly payment notify failed user_id=%s", u['id'])
        except Exception:
            logger.exception("monthly_payment_scheduler loop error")

        # Sleep 1 hour; notifications are day-based and deduped
        await asyncio.sleep(3600)


async def _show_group_details(callback: CallbackQuery, group_id: int):
    group = get_group(group_id)
    lang = detect_lang_from_user(callback.from_user)
    if not group:
        await callback.message.answer(t(lang, 'group_not_found'))
        await callback.answer()
        return
    teacher = get_user_by_id(group.get('teacher_id')) if group.get('teacher_id') else None
    teacher_name = f"{teacher.get('first_name','')} {teacher.get('last_name','')}".strip() if teacher else "-"
    students = get_group_users(group_id)
    subject = group.get('subject') or '-'
    start = (group.get('lesson_start') or '-')[:5]
    end = (group.get('lesson_end') or '-')[:5]
    raw_date = (group.get('lesson_date') or '-').strip()
    if raw_date.upper() in ('MWF', 'MON/WED/FRI', 'MON,WED,FRI'):
        date = 'Mon, Wed, Fri'
    elif raw_date.upper() in ('TTS', 'TUE/THU/SAT', 'TUE,THU,SAT'):
        date = 'Tue, Thu, Sat'
    else:
        date = raw_date or '-'

    text = (
        f"📌 Guruh: {group.get('name')}\n"
        f"1) Fan: {subject}\n"
        f"2) Level: {group.get('level') or '-'}\n"
        f"3) Teacher: {teacher_name}\n"
        f"4) Dars vaqti: {date} | {start}-{end} ({group.get('tz') or 'Asia/Tashkent'})\n"
        f"5) O‘quvchilar soni: {len(students)}"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "btn_grp_time"), callback_data=f"grp_set:{group_id}:time")],
        [InlineKeyboardButton(text='📅 Dars kunlari', callback_data=f"grp_set:{group_id}:days")],
        
        # ← BU YERNI O'ZGARTIRAMIZ
        [InlineKeyboardButton(text=t(lang, "btn_grp_teacher"), callback_data=f"group_edit_teacher_{group_id}")],
        
        [InlineKeyboardButton(text=t(lang, "btn_grp_name"), callback_data=f"grp_set:{group_id}:name")],
        [InlineKeyboardButton(text=t(lang, "btn_grp_level"), callback_data=f"grp_set:{group_id}:level")],
        
        # ← BU YERNI O'ZGARTIRAMIZ
        [InlineKeyboardButton(text=t(lang, "btn_grp_add_student"), callback_data=f"group_add_student_{group_id}")],
        [InlineKeyboardButton(text=t(lang, "btn_grp_remove_student"), callback_data=f"group_remove_student_{group_id}")],
        
        [InlineKeyboardButton(text=t(lang, "btn_grp_delete"), callback_data=f"grp_set:{group_id}:delete")],
    ])
    await callback.message.answer(text, reply_markup=kb)
    await callback.answer()


@dp.message(Command('main'))
async def cmd_main(message: Message):
    """Return to main menu"""
    if message.from_user.id not in ADMIN_CHAT_IDS:
        await message.answer(t_from_update(message, 'admin_only'))
        return
    
    reset_admin_state(message.chat.id)
    lang = detect_lang_from_user(message.from_user)
    await message.answer(t(lang, 'admin_panel'), reply_markup=admin_main_keyboard(lang))


@dp.message(Command('start'))
async def cmd_start(message: Message):
    if message.from_user.id not in ADMIN_CHAT_IDS:
        await message.answer(t_from_update(message, 'admin_only'))
        return
    lang = detect_lang_from_user(message.from_user)
    await message.answer(t(lang, 'welcome_admin'), reply_markup=admin_main_keyboard(lang))


@dp.message(Command('admin'))
async def cmd_admin(message: Message):
    if message.from_user.id not in ADMIN_CHAT_IDS:
        await message.answer(t_from_update(message, 'admin_only'))
        return
    lang = detect_lang_from_user(message.from_user)
    await message.answer(t(lang, 'admin_panel'), reply_markup=admin_main_keyboard(lang))


@dp.message()
async def handle_admin_text(message: Message):
    if message.from_user.id not in ADMIN_CHAT_IDS:
        await message.answer(t_from_update(message, 'admin_only'))
        return
    text = message.text.strip() if message.text else ''
    state = get_admin_state(message.chat.id)
    lang = detect_lang_from_user(message.from_user)
    
    # Safety check: if state seems invalid, reset to main menu
    if state and not isinstance(state, dict) or 'step' not in state:
        logger.warning(f"Invalid state detected, resetting: {state}")
        reset_admin_state(message.chat.id)
        state = get_admin_state(message.chat.id)
    
    logger.info(f"Admin message received: text='{text}', step='{state.get('step')}', chat_id={message.chat.id}")

    # Cancel current flow
    cancel_text = t(lang, 'cancel').lower()
    if (text.lower() in ('/cancel', '/bekor', '/stop') or 
        text.startswith('❌') or 
        text.lower().startswith(cancel_text) or
        cancel_text in text.lower()):
        logger.info(f"Cancel triggered: text='{text}', step='{state.get('step')}', chat_id={message.chat.id}")
        reset_admin_state(message.chat.id)
        await message.answer(t(lang, 'admin_panel'), reply_markup=admin_main_keyboard(lang))
        return

    # Normalize incoming text to handle emoji variants, smart quotes and other
    # minor differences between clients so button presses map correctly.
    try:
        norm = unicodedata.normalize('NFKC', text)
    except Exception:
        norm = text
    norm = norm.replace('‘', "'").replace('’', "'").replace('`', "'")
    tl = norm.lower()

    # Helper to match translated labels across supported languages
    langs = ('uz', 'ru', 'en')
    def matches_label(key: str):
        for L in langs:
            try:
                if t(L, key).lower() in tl:
                    return True
            except Exception:
                continue
        return False

    # === STUDENTS LIST ===
    if matches_label('students_list_title') or any(k in tl for k in ("oquvchilar", "o'quvchilar", "o'quvchi", "oquvchi", 'student', 'students')):
        await show_students_list(message, page=0)
        return

    if any(k in text.lower() for k in ["o'qituvchilar", "oqituvchilar", "teachers", "teacher list"]):
        await show_teachers_list(message)
        return

    if matches_label('groups_menu') or 'guruh' in tl or 'group' in tl:
        await show_group_menu(message)
        return


    if 'tolov' in tl or 'tolov' in tl or "to'lov" in tl or 'payment' in tl:
        await show_payment_menu(message)
        return

    if "davomat" in tl or "attendance" in tl:
        await show_attendance_menu(message)
        return
    # Show language selection keyboard when admin presses the language button
    if matches_label('choose_lang') or 'til' in tl or 'language' in tl:
        await message.answer(t(lang, 'choose_lang'), reply_markup=create_language_selection_keyboard_for_self())
        return

    if state['step'] == 'ask_first_name':
        state['data']['first_name'] = text
        state['step'] = 'ask_last_name'
        await message.answer(t(lang, 'ask_last_name'), reply_markup=cancel_keyboard(lang))
        return
    if state['step'] == 'ask_last_name':
        state['data']['last_name'] = text
        state['step'] = 'ask_phone'
        await message.answer(t(lang, 'ask_phone'), reply_markup=cancel_keyboard(lang))
        return
    if state['step'] == 'ask_phone':
        state['data']['phone'] = text
        state['step'] = 'ask_subject'
        await message.answer(t(lang, 'ask_subject'), reply_markup=create_subject_keyboard())
        return

    if state['step'] == 'ask_subject':
        subject = text.title()
        if subject not in SUBJECTS:
            await message.answer(t(lang, 'ask_subject'), reply_markup=create_subject_keyboard())
            return
        state['data']['subject'] = subject

        login_type = state['data'].get('login_type', 1)
        user = create_user_sync(
            first_name=state['data']['first_name'],
            last_name=state['data']['last_name'],
            phone=state['data']['phone'],
            subject=state['data']['subject'],
            login_type=login_type,
        )

        msg = t(lang, 'new_user_created', login_id=f'<code>{user["login_id"]}</code>', password=f'<code>{user["password"]}</code>')
        await message.answer(msg, parse_mode='HTML')
        
        # Handle different user types
        if login_type == 1:
            # New student - prepare for placement test
            from db import prepare_user_for_new_test
            prepare_user_for_new_test(user['id'], state['data']['subject'])
            
            # Send test to student if they have telegram_id
            if user.get('telegram_id'):
                try:
                    from student_bot import start_placement_test
                    await start_placement_test(int(user['telegram_id']), state['data']['subject'])
                    await message.answer(f"✅ Test yuborildi: {user['first_name']} {user['last_name']}")
                except Exception as e:
                    await message.answer(f"⚠️ Test yuborishda xato: {e}")
                
                # Reset to main menu after sending test
                reset_admin_state(message.chat.id)
            else:
                await message.answer("⚠️ Student telegram ID'si mavjud emas. Keyinroq test yuborishingiz mumkin.")
                
        elif login_type == 2:
            # Existing student - ask which group to attach
            groups = get_all_groups()
            if not groups:
                await message.answer(t(lang, "no_groups"))
                reset_admin_state(message.chat.id)
                return
            await message.answer(t(lang, "select_group_to_add_user"), reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text=t(lang, "btn_choose_group"), callback_data=f"assign_new:{user['id']}:page:0")]]
            ))
            reset_admin_state(message.chat.id)
            return
        reset_admin_state(message.chat.id)
        return

    # Payment search (text input)
    if state.get('step') == 'pay_search_login':
        q = text.strip().upper()
        # Use a safe token in callback (no spaces)
        await _render_payment_search_results(message, mode="login", query=q, page=0)
        state['step'] = None
        return

    if state.get('step') == 'pay_search_name':
        q = re.sub(r"\s+", " ", text.strip())
        q_token = q.replace(" ", "_")
        await _render_payment_search_results(message, mode="name", query=q_token, page=0)
        state['step'] = None
        return

    if state['step'] == 'teach_edit_first':
        teacher_id = state['data'].get('teacher_id')
        if teacher_id:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute('UPDATE users SET first_name=? WHERE id=?', (text.strip(), teacher_id))
            conn.commit()
            conn.close()
            await message.answer('👤 Ism yangilandi')
        state['step'] = None
        state['data'] = {}
        return

    if state['step'] == 'teach_edit_last':
        teacher_id = state['data'].get('teacher_id')
        if teacher_id:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute('UPDATE users SET last_name=? WHERE id=?', (text.strip(), teacher_id))
            conn.commit()
            conn.close()
            await message.answer('👤 Familya yangilandi')
        state['step'] = None
        state['data'] = {}
        return

    # Edit selected user (student) first name
    if state['step'] == 'user_edit_first':
        user_id = state['data'].get('change_user_id')
        if user_id:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute('UPDATE users SET first_name=? WHERE id=?', (text.strip(), user_id))
            conn.commit()
            conn.close()
            await message.answer('👤 Ism yangilandi')
        state['step'] = None
        state['data'] = {}
        return

    # Edit selected user (student) last name
    if state['step'] == 'user_edit_last':
        user_id = state['data'].get('change_user_id')
        if user_id:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute('UPDATE users SET last_name=? WHERE id=?', (text.strip(), user_id))
            conn.commit()
            conn.close()
            await message.answer('👤 Familya yangilandi')
        state['step'] = None
        state['data'] = {}
        return

    if state['step'] == 'teach_edit_phone':
        teacher_id = state['data'].get('teacher_id')
        if teacher_id:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute('UPDATE users SET phone=? WHERE id=?', (text.strip(), teacher_id))
            conn.commit()
            conn.close()
            await message.answer('📱 Telefon yangilandi')
        state['step'] = None
        state['data'] = {}
        return

    if state['step'] == 'teach_edit_subject':
        teacher_id = state['data'].get('teacher_id')
        if teacher_id:
            update_user_subject(teacher_id, text.strip())
        else:
            subjects = [s.strip() for s in (u.get('subject') or '').split(',') if s.strip()]
            new = text.strip()
            if not new:
                await callback.answer(t(lang, 'empty_subject_not_allowed'))
            elif new in subjects:
                await message.answer(t(lang, 'subject_already_exists'))
            elif len(subjects) >= 2:
                await message.answer(t(lang, 'max_subjects_reached'))
            else:
                subjects.append(new)
                update_user_subjects(user_id, subjects)
                await message.answer(t(lang, 'subjects_updated', subjects=', '.join(subjects)))
        state['step'] = None
        state['data'] = {}
        return

    if state['step'] == 'add_subject':
        user_id = state['data'].get('change_user_id')
        if user_id:
            # This step should be handled by callback query, not text input
            # But if admin types, show the buttons again
            await message.answer(
                "❌ Iltimos, subjectni tugmalardan tanlang!\n\n"
                "📚 Quyidagi fanlardan birini tanlang:",
                reply_markup=create_subject_keyboard()
            )
        return

    if state['step'] == 'delete_subject':
        user_id = state['data'].get('change_user_id')
        if user_id:
            u = get_user_by_id(user_id)
            if not u:
                await message.answer(t(lang, 'user_not_found'))
            else:
                subjects = [s.strip() for s in (u.get('subject') or '').split(',') if s.strip()]
                rem = text.strip()
                if rem not in subjects:
                    await message.answer(t(lang, 'subject_not_assigned_to_user'))
                else:
                    subjects = [s for s in subjects if s != rem]
                    update_user_subjects(user_id, subjects)
        state['step'] = 'ask_group_level'
        await message.answer(t(lang, 'ask_group_level'))
        return

    if state.get('step') == 'ask_group_name':
        name = message.text.strip()
        if not name:
            await message.answer(t(lang, 'group_name_empty'))
            return
        state['data']['name'] = name
        state['step'] = 'ask_group_level'
        await message.answer(t(lang, 'ask_group_level'))
        return

    if state.get('step') == 'ask_group_level':
        level = message.text.strip().upper()
        if not level or not re.match(r'^[A-C][1-2]$', level):
            await message.answer(t(lang, 'group_level_invalid'))
            return
        state['data']['level'] = level
        state['step'] = 'ask_group_days'
        
        # Show day selection buttons (no text input allowed)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='Mon, Wed, Fri', callback_data="group_days:MWF")],
            [InlineKeyboardButton(text='Tue, Thu, Sat', callback_data="group_days:TTS")],
            [InlineKeyboardButton(text='❌ Cancel', callback_data="cancel_group_creation")],
        ])
        await message.answer(t(lang, 'ask_group_days'), reply_markup=kb)
        return

    # Note: ask_group_days step is handled by callback queries only
    # Admin must use buttons (Mon,Wed,Fri or Tue,Thu,Sat) to select days
    
    if state.get('step') == 'ask_group_days':
        # Admin is trying to type days instead of using buttons
        await message.answer(
            "❌ Iltimos, kunlarni tugmalardan tanlang!\n\n"
            "📅 Faqat quyidagi variantlar mavjud:\n"
            "• Mon, Wed, Fri (Dushanba, Chorshanba, Juma)\n"
            "• Tue, Thu, Sat (Seshanba, Payshanba, Shanba)\n\n"
            "⚠️ Matn kiritish o'rniga tugmalardan foydalaning!",
            reply_markup=kb
        )
        return

    if state.get('step') == 'ask_group_time':
        time_str = message.text.strip()
        start, end = _parse_time_range(time_str)   # bu funksiya mavjud deb hisoblaymiz
        
        if not start or not end:
            await message.answer(t(lang, 'format_wrong_time', example=t(lang, 'time_example')))
            return
        
        state['data']['lesson_start'] = start
        state['data']['lesson_end']   = end
        
        # ─── GURUHNI YARATISH ───────────────────────
        await create_group_from_state(message, state)
        return

    # Teacher selection handler
    if state.get('step') == 'ask_teacher_for_group':
        # This will be handled by callback query, but we can add text input handling
        await message.answer(
            "Iltimos, o'qituvchini tugmalardan tanlang yoki \"O'qituvchisiz yaratish\" tugmasini bosing."
        )
        return

    if state.get('step') == 'edit_group_name':
        group_id = state['data'].get('edit_group_id')
        if not group_id:
            reset_admin_state(message.chat.id)
            return
        update_group_name(int(group_id), text.strip())
        await message.answer(t(lang, "group_name_updated"))
        reset_admin_state(message.chat.id)
        return

    if state.get('step') == 'edit_group_level':
        group_id = state['data'].get('edit_group_id')
        if not group_id:
            reset_admin_state(message.chat.id)
            return
        update_group_level(int(group_id), text.strip().upper(), sync_students=True)
        await message.answer(t(lang, "group_level_updated"))
        reset_admin_state(message.chat.id)
        return

    if state.get('step') == 'edit_group_time':
        await message.answer(t(lang, "ask_new_start"))
        return

    if state.get('step') == 'edit_group_start':
        group_id = state['data'].get('edit_group_id')
        start_t = _normalize_hhmm(text)
        if not start_t:
            await message.answer(t(lang, "format_wrong_time", example="14:00"))
            return
        state['data']['new_lesson_start'] = start_t
        state['step'] = 'edit_group_end'
        await message.answer(t(lang, "ask_new_end"))
        return

    if state.get('step') == 'edit_group_end':
        group_id = state['data'].get('edit_group_id')
        end_t = _normalize_hhmm(text)
        if not end_t:
            await message.answer(t(lang, "format_wrong_time", example="15:30"))
            return
        lesson_date = state['data'].get('new_lesson_date')
        lesson_start = state['data'].get('new_lesson_start')
        update_group_schedule(int(group_id), lesson_date, lesson_start, end_t, tz='Asia/Tashkent')
        await message.answer(t(lang, "group_time_updated"))
        reset_admin_state(message.chat.id)
        return

    if matches_label('choose_user_type') or 'yangi foydalanuvchi' in tl or 'new user' in tl:
        state['step'] = 'choose_type'
        await message.answer(t(lang, 'new_user_type_prompt'), reply_markup=create_user_type_keyboard(lang))
        return

    if matches_label('recent_results_title') or 'natija' in tl or 'result' in tl:
        results = get_recent_results()
        if not results:
            await message.answer(t(lang, 'no_results'))
            return
        text = t(lang, 'recent_results_title') + '\n'
        for r in results:
            user = get_user_by_id(r['user_id'])
            name = f"{user['first_name']} {user['last_name']}" if user else f"UserID={r['user_id']}"
            # Calculate percentage and correct count
            percentage = r['score']  # score is percentage (0-100+)
            max_score = r.get('max_score', 100)
            correct_count = int((r['score'] / max_score) * 20) if max_score > 0 else 0  # Calculate correct answers for 20 questions
            text += f"{r['created_at'][:10]} | {name} | subj={r['subject']} | {percentage}% | {correct_count} tog'ri javob | {r['level']}\n"
        await message.answer(text)
        return

    if matches_label('students_list_title'):
        users = [u for u in get_all_users() if u.get('login_type') in (1, 2)]
        if not users:
            await message.answer(t(lang, 'no_students'))
            return
        state['list_page'] = 0
        state['list_users'] = users
        await send_user_list(message.chat.id, message, state)
        return

    if matches_label('teachers_list_title'):
        await show_teachers_list(message)
        return

    # Vocabulary import/export menu (admin)
    if ('sozlar import/export' in tl) or ('sozlar import' in tl and 'export' in tl) or ('import_vocab' in tl) or (text.strip().lower() == '/vocab'):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, 'vocab_import_btn'), callback_data='admin_vocab_action_import')],
            [InlineKeyboardButton(text=t(lang, 'vocab_export_btn'), callback_data='admin_vocab_action_export')],
        ])
        await message.answer(t(lang, 'choose'), reply_markup=kb)
        return

    # Export full system to XLSX
    if text.strip().lower() in ('/export_all', '/export') or ('export (xlsx)' in tl) or (tl.startswith('📤') and 'export' in tl):
        if message.from_user.id not in ADMIN_CHAT_IDS:
            await message.answer(t_from_update(message, 'admin_only'))
            return
        logger.info(f"📤 Export requested by admin user_id={message.from_user.id}")
        from vocabulary import export_full_system_to_xlsx
        bio, fname = export_full_system_to_xlsx()
        await bot.send_document(message.chat.id, BufferedInputFile(bio.getvalue(), filename=fname))
        return

    # Admin provided subject while in vocab import flow
    if state.get('step') == 'admin_await_vocab_subject':
        subject = text.strip().title()
        state['data']['subject'] = subject
        state['step'] = 'admin_await_vocab_file'
        await message.answer(t(lang, 'send_excel_file'))
        return

    # Admin sent file during import flow
    if state.get('step') == 'admin_await_vocab_file' and message.document:
        # Ensure xlsx only
        if not (message.document.file_name or '').lower().endswith('.xlsx'):
            await message.answer(t(lang, 'only_xlsx_allowed'))
            state['step'] = None
            state['data'] = {}
            return
        from vocabulary import import_words_from_excel
        import io

        doc = message.document
        bio = io.BytesIO()
        await message.bot.download(file=doc.file_id, destination=bio)
        bio.seek(0)
        subject = state['data'].get('subject')
        lang_code = 'en' if subject.lower().startswith('english') else ('ru' if subject.lower().startswith('russian') else 'en')
        # Admin ID may not be in users table; pass None
        try:
            report = import_words_from_excel(bio.read(), doc.file_name or 'upload.xlsx', None, subject, lang_code)
        except Exception as e:
            await message.answer(f"❌ XLSX xato: {e}")
            state['step'] = None
            state['data'] = {}
            return

        await message.answer(t(lang, 'vocab_import_result', inserted=report['inserted'], skipped=report['skipped'], total=report['total']))
        # Show duplicates to uploader (admin) as a compact list
        if report.get('duplicates'):
            words = report['duplicates'][:30]
            more = len(report['duplicates']) - len(words)
            msg = "⏭️ Oldin qo‘shilganligi sabab skip bo‘lgan so‘zlar:\n" + "\n".join([f"- {w}" for w in words])
            if more > 0:
                msg += f"\n… va yana {more} ta"
            await message.answer(msg)

        state['step'] = None
        state['data'] = {}
        return


@dp.callback_query(lambda c: c.data in ('admin_vocab_action_import', 'admin_vocab_action_export'))
async def handle_admin_vocab_action(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        await callback.message.answer(t_from_update(callback, 'admin_only'))
        return
    state = get_admin_state(callback.message.chat.id)
    lang = detect_lang_from_user(callback.from_user)
    action = callback.data.split('_')[-1]  # import/export
    if action == 'import':
        state['step'] = 'admin_await_vocab_subject'
        state['data'] = {}
        await callback.answer()
        await callback.message.answer(t(lang, 'send_vocab_subject'), reply_markup=create_subject_keyboard())
        return
    if action == 'export':
        state['step'] = 'admin_export_choose_subject'
        state['data'] = {}
        await callback.answer()
        await callback.message.answer(t(lang, 'choose_subject_export'), reply_markup=create_subject_keyboard())
        return


@dp.callback_query(lambda c: c.data.startswith('subject_') and get_admin_state(c.message.chat.id).get('step') in ('admin_export_choose_subject', 'admin_await_vocab_subject', 'ask_subject', 'ask_test_subject', 'add_subject'))
async def handle_subject_for_admin_vocab(callback: CallbackQuery):
    data = callback.data
    state = get_admin_state(callback.message.chat.id)
    lang = detect_lang_from_user(callback.from_user)
    subject = data.split('_', 1)[1]

    # Export vocab by subject
    if state.get('step') == 'admin_export_choose_subject':
        from vocabulary import export_words_to_xlsx
        bio, fname = export_words_to_xlsx(subject)
        await bot.send_document(callback.message.chat.id, BufferedInputFile(bio.getvalue(), filename=fname))
        state['step'] = None
        state['data'] = {}
        await callback.answer()
        return

    # Add subject to existing user
    if state.get('step') == 'add_subject':
        user_id = state['data'].get('change_user_id')
        if user_id:
            user = get_user_by_id(user_id)
            if user:
                subjects = [s.strip() for s in (user.get('subject') or '').split(',') if s.strip()]
                if subject not in subjects:
                    if len(subjects) < 2:
                        subjects.append(subject)
                        update_user_subjects(user_id, subjects)
                        await callback.message.answer(
                            f"✅ Subject '{subject}' qo'shildi.\n\n"
                            f"👤 {user.get('first_name', '')} {user.get('last_name', '')}\n"
                            f"📚 Subjectlar: {', '.join(subjects)}"
                        )
                    else:
                        await callback.message.answer(
                            f"❌ {user.get('first_name', '')} {user.get('last_name', '')} "
                            f"allaqachon 2 ta subjectga ega. Max 2 ta gacha."
                        )
                else:
                    await callback.message.answer(
                        f"❌ Subject '{subject}' allaqachon mavjud."
                    )
            else:
                await callback.message.answer("❌ O'quvchi topilmadi.")
        await callback.answer()
        return

    # New user creation subject selection
    if state.get('step') == 'ask_subject':
        state['data']['subject'] = subject
        state['step'] = None
        
        # Create user with collected data
        user_data = state['data']
        from auth import create_user_sync
        user = create_user_sync(
            first_name=user_data['first_name'],
            last_name=user_data['last_name'],
            phone=user_data['phone'],
            login_type=user_data['login_type'],
            subject=subject
        )
        
        await callback.message.answer(
            f"✅ User muvaffaqiyatli yaratildi!\n"
            f"🔑 Login ID: <code>{user['login_id']}</code>\n"
            f"🔐 Parol: <code>{user['password']}</code>\n\n"
            f"⚠️ Eslatma: Yangi studentlar avtomatik bloklangan.\n"
            f"Guruhga biriktirilgandan so'ng admin blokdan olishi kerak!",
            parse_mode='HTML'
        )
        
        state['step'] = None
        state['data'] = {}
        reset_admin_state(callback.message.chat.id)
        await callback.answer()
        return

    # Test subject selection
    if state.get('step') == 'ask_test_subject':
        user_id = state['data'].get('test_user_id')
        if not user_id:
            await callback.answer("❌ User not found")
            return
        
        user = get_user_by_id(user_id)
        if not user:
            await callback.answer("❌ User not found")
            return
        
        # Prepare user for test
        from db import prepare_user_for_new_test
        prepare_user_for_new_test(user_id, subject)
        
        # Send test to student
        student_chat_id = user.get('telegram_id')
        if student_chat_id:
            try:
                # Create inline keyboard with Start Test button
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🚀 Testni boshlash", callback_data="start_test")]
                ])
                
                await student_notify_bot.send_message(
                    student_chat_id,
                    f"📝 Sizga yangi test yuborildi!\n"
                    f"📚 Fan: {subject}\n"
                    f"🔑 Login ID: {user['login_id']}\n\n"
                    f"Testni boshlash uchun pastdagi tugmani bosing!",
                    reply_markup=keyboard,
                    parse_mode='HTML'
                )
                await callback.message.answer(f"✅ Test {subject} fani uchun yuborildi!\n👤 User: {user['first_name']} {user['last_name']}")
            except Exception as e:
                await callback.message.answer(f"❌ Test yuborishda xatolik: {e}")
        else:
            await callback.message.answer("❌ User telegram ID si topilmadi")
        
        state['step'] = None
        state['data'] = {}
        await callback.answer()
        return

    # Change subject for existing user
    if state.get('step') == 'change_subject':
        user_id = state['data'].get('change_user_id')
        if not user_id:
            await callback.answer("❌ User not found")
            return
        
        user = get_user_by_id(user_id)
        if not user:
            await callback.answer("❌ User not found")
            return
        
        update_user_subject(user_id, subject)
        await callback.message.answer(f"Foydalanuvchi {user['first_name']} {user['last_name']}ning fani {subject}ga o'zgartirildi.")
        state['step'] = None
        state['data'] = {}
        await callback.answer()
        return

    # Import vocab subject selection (only when admin chose import via inline)
    if state.get('step') == 'admin_await_vocab_subject':
        state['data']['subject'] = subject
        state['step'] = 'admin_await_vocab_file'
        await callback.answer()
        
        # Send example file
        await callback.message.answer(t(lang, 'send_excel_file'))
        
        # Create and send example file using user's actual template files
        try:
            # Load the actual example file based on subject
            if subject.lower() == 'english':
                example_file = os.path.join(os.path.dirname(__file__), 'Vocabulary_importing_list_for_english.xlsx')
            else:
                example_file = os.path.join(os.path.dirname(__file__), 'Vocabulary_importing_list_for_russian.xlsx')
            
            # Read the actual template file
            with open(example_file, 'rb') as f:
                file_data = f.read()
            
            # Send the actual template file
            await bot.send_document(
                callback.message.chat.id,
                BufferedInputFile(file_data, filename="Vocabulary_importing_list_template.xlsx"),
                caption=f"📝 <b>{subject} faniga namuna fayl</b>\n\n"
                        f"Ushbu faylni to'ldirib yuboring. "
                        f"File nomi muhim emas, istalgan nom bilan yuborishingiz mumkin.\n"
                        f"Import qilish uchun faqat ustunlar tuzilishi muhim.",
                parse_mode='HTML'
            )
            
            # Save example words to database
            try:
                from vocabulary import import_words_from_excel
                import_words_from_excel(file_data, example_file, None, subject, 'en')
            except Exception as e:
                logger.error(f"Error saving example words to DB: {e}")
                
        except FileNotFoundError:
            # Fallback to generated template if file not found
            await callback.message.answer("❌ Namuna fayl topilmadi, avtomatik yaratilmoqda...")
            
            # Generate fallback template
            wb = Workbook()
            ws = wb.active
            ws.title = "Template"
            
            # Headers based on subject
            if subject.lower() == 'english':
                headers = ['Level', 'Word', 'translation_uz', 'translation_ru', 'Example Sentence 1', 'Example Sentence 2']
            else:  # Russian
                headers = ['Level', 'Word', 'translation_uz', 'Definition', 'Example Sentence 1', 'Example Sentence 2']
            
            ws.append(headers)
            
            # Make headers bold
            for col in range(1, len(headers) + 1):
                ws.cell(row=1, column=col).font = Font(bold=True)
            
            # Save to BytesIO
            bio = io.BytesIO()
            wb.save(bio)
            bio.seek(0)
            
            await bot.send_document(
                callback.message.chat.id,
                BufferedInputFile(bio.getvalue(), filename="Vocabulary_importing_list_template.xlsx"),
                caption=f"📝 <b>{subject} faniga namuna fayl</b>\n\n"
                        f"Ushbu faylni to'ldirib yuboring. "
                        f"File nomi muhim emas, istalgan nom bilan yuborishingiz mumkin.",
                parse_mode='HTML'
            )
            
        except Exception as e:
            logger.error(f"Error sending example file: {e}")
            await callback.message.answer("❌ Namuna faylni yuborishda xatolik yuz berdi")
        
        return


@dp.message(Command('export_all'))
async def cmd_export_all_admin(message: Message):
    if message.from_user.id not in ADMIN_CHAT_IDS:
        await message.answer(t_from_update(message, 'admin_only'))
        return
    logger.info(f"📤 /export_all by admin user_id={message.from_user.id}")
    from vocabulary import export_full_system_to_xlsx
    bio, fname = export_full_system_to_xlsx()
    await bot.send_document(message.chat.id, BufferedInputFile(bio.getvalue(), filename=fname))

    if matches_label('groups_menu'):
        await show_group_menu(message)
        return

    # Teacher editing handlers
    if state['step'] == 'edit_teacher_first_name':
        if text.strip().lower() == '/skip':
            state['step'] = 'edit_teacher_last_name'
            teacher_id = state['data'].get('edit_teacher_id')
            teacher = get_user_by_id(teacher_id)
            await message.answer(f"{t(lang, 'ask_last_name')} {teacher['last_name']}\n\n{t(lang, 'ask_last_name')} (yoki /skip yozing):")
            return
        state['data']['new_first_name'] = text
        state['step'] = 'edit_teacher_last_name'
        teacher_id = state['data'].get('edit_teacher_id')
        teacher = get_user_by_id(teacher_id)
        await message.answer(t(lang, 'current_last_name', last_name=teacher['last_name']))
        return

    if state['step'] == 'edit_teacher_last_name':
        if text.strip().lower() == '/skip':
            state['step'] = 'edit_teacher_phone'
            teacher_id = state['data'].get('edit_teacher_id')
            teacher = get_user_by_id(teacher_id)
            await message.answer(t(lang, 'current_phone', phone=teacher.get('phone', '-')))
            return
        state['data']['new_last_name'] = text
        state['step'] = 'edit_teacher_phone'
        teacher_id = state['data'].get('edit_teacher_id')
        teacher = get_user_by_id(teacher_id)
        await message.answer(t(lang, 'current_phone', phone=teacher.get('phone', '-')))
        return

    if state['step'] == 'edit_teacher_phone':
        if text.strip().lower() != '/skip':
            state['data']['new_phone'] = text
        
        # Apply all changes
        teacher_id = state['data'].get('edit_teacher_id')
        teacher = get_user_by_id(teacher_id)
        
        changes = []
        
        # Use single database connection for all updates
        conn = get_conn()
        cur = conn.cursor()
        
        try:
            if 'new_first_name' in state['data']:
                cur.execute("UPDATE users SET first_name=? WHERE id=?", (state['data']['new_first_name'], teacher_id))
                changes.append(f"Ism o'zgartirildi: {teacher['first_name']} → {state['data']['new_first_name']}")
            
            if 'new_last_name' in state['data']:
                cur.execute("UPDATE users SET last_name=? WHERE id=?", (state['data']['new_last_name'], teacher_id))
                changes.append(f"Familya o'zgartirildi: {teacher['last_name']} → {state['data']['new_last_name']}")
            
            if 'new_phone' in state['data']:
                cur.execute("UPDATE users SET phone=? WHERE id=?", (state['data']['new_phone'], teacher_id))
                changes.append(f"Telefon o'zgartirildi: {teacher.get('phone', '-')} → {state['data']['new_phone']}")
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.exception("Failed to update teacher data")
            await message.answer("❌ Xatolik yuz berdi, qayta urinib ko'ring.")
            return
        finally:
            conn.close()
        
        if changes:
            await message.answer(t(lang, 'teacher_updated', changes='\n'.join(changes)))
        else:
            await message.answer(t(lang, 'no_changes'))
        
        reset_admin_state(message.chat.id)
        return

    await message.answer(t(lang, 'main_menu_prompt'), reply_markup=admin_main_keyboard(lang))

    # Xavfsizlik: agar step hali ham ochiq qolsa, tozalaymiz
    if state.get('step') and text.lower() in ('/cancel', '❌', 'bekor'):
        state['step'] = None


async def show_group_student_list(callback: CallbackQuery, group_id: int, remove_mode: bool = False, show_for_teacher_change: bool = False):
    """Show group students with pagination and search functionality"""
    state = get_admin_state(callback.message.chat.id)
    search_query = state['data'].get('search_query', '')
    page = state['data'].get('students_page', 0)
    
    # Get all students (login_type 1 and 2)
    all_users = get_all_users()
    students = [u for u in all_users if u.get('login_type') in [1, 2]]
    
    # Filter by search query
    if search_query:
        search_lower = search_query.lower()
        students = [u for u in students if 
                   search_lower in u.get('first_name', '').lower() or 
                   search_lower in u.get('last_name', '').lower()]
    
    # Get current group students
    group = get_group(group_id)
    current_group_students = []
    if group:
        current_group_students = get_group_users(group_id)
        current_group_student_ids = {s['id'] for s in current_group_students}
    else:
        current_group_student_ids = set()
    
    # Mark which students are already in group
    for student in students:
        student['in_group'] = student['id'] in current_group_student_ids
    
    # Pagination
    per_page = 10
    total = len(students)
    start = page * per_page
    end = start + per_page
    chunk = students[start:end]
    
    total_pages = (total - 1) // per_page + 1 if total else 1
    
    # Build message
    if show_for_teacher_change:
        title = f"👥 Guruh o'qituvchisini o'zgartirish — sahifa {page+1}/{total_pages}"
    elif remove_mode:
        title = f"➖ Guruhdan o'quvchini o'chirish — sahifa {page+1}/{total_pages}"
    else:
        title = f"➕ Guruhga o'quvchi qo'shish — sahifa {page+1}/{total_pages}"
    
    text = f"{title}\n\n"
    
    for i, student in enumerate(chunk, start=1):
        # Get student status
        if student.get('blocked'):
            status = '🔒'
        elif is_access_active(student):
            status = '✅'
        else:
            status = '❌'
        
        # Get student's current group info
        student_groups = get_user_groups(student['id'])
        group_count = len(student_groups)
        
        # Get teacher info
        teacher_name = "-"
        if student_groups:
            first_group = student_groups[0]
            if first_group.get('teacher_id'):
                teacher = get_user_by_id(first_group['teacher_id'])
                if teacher:
                    teacher_name = f"{teacher['first_name']} {teacher['last_name']}"
        
        # Get class time
        class_time = "-"
        if student_groups:
            first_group = student_groups[0]
            class_time = f"{first_group.get('start_time', '?')}-{first_group.get('end_time', '?')}"
        
        # Group student count
        group_student_count = 0
        if student_groups:
            first_group = student_groups[0]
            group_students = get_group_users(first_group['id'])
            group_student_count = len(group_students)
        
        # Add status indicator for group membership
        in_group_indicator = " ✅" if student['in_group'] else ""
        
        text += (
            f"{i}. {student['subject']}{in_group_indicator}\n"
            f"   {student['first_name']} {student['last_name']}\n"
            f"   🔑 {student['login_id']} | 📱 {student.get('phone', '—')} | 🎓 {student.get('level', '—')} | {status}\n"
            f"   👨‍🏫 {teacher_name} | ⏰ {class_time} | 👥 {group_student_count}\n\n"
        )
    
    # Create keyboard
    keyboard = []
    
    # Number buttons (1-10)
    number_buttons = []
    for i in range(1, min(6, len(chunk) + 1)):
        if remove_mode:
            if chunk[i-1]['in_group']:
                number_buttons.append(InlineKeyboardButton(
                    text=f"{i} ✅", 
                    callback_data=f"grp_remove:{group_id}:{chunk[i-1]['id']}"
                ))
            else:
                number_buttons.append(InlineKeyboardButton(text=f"{i}", callback_data="noop"))
        elif show_for_teacher_change:
            number_buttons.append(InlineKeyboardButton(
                text=f"{i}", 
                callback_data=f"teacher_select_{chunk[i-1]['id']}"
            ))
        else:  # add_student mode
            if chunk[i-1]['in_group']:
                number_buttons.append(InlineKeyboardButton(text=f"{i} ✅", callback_data="noop"))
            else:
                number_buttons.append(InlineKeyboardButton(
                    text=f"{i}", 
                    callback_data=f"grp_add_student:{group_id}:{chunk[i-1]['id']}"
                ))
    
    for i in range(6, min(11, len(chunk) + 1)):
        if remove_mode:
            if chunk[i-1]['in_group']:
                number_buttons.append(InlineKeyboardButton(
                    text=f"{i} ✅", 
                    callback_data=f"grp_remove:{group_id}:{chunk[i-1]['id']}"
                ))
            else:
                number_buttons.append(InlineKeyboardButton(text=f"{i}", callback_data="noop"))
        elif show_for_teacher_change:
            number_buttons.append(InlineKeyboardButton(
                text=f"{i}", 
                callback_data=f"teacher_select_{chunk[i-1]['id']}"
            ))
        else:  # add_student mode
            if chunk[i-1]['in_group']:
                number_buttons.append(InlineKeyboardButton(text=f"{i} ✅", callback_data="noop"))
            else:
                number_buttons.append(InlineKeyboardButton(
                    text=f"{i}", 
                    callback_data=f"grp_add_student:{group_id}:{chunk[i-1]['id']}"
                ))
    
    # Split number buttons into rows
    if number_buttons:
        keyboard.append(number_buttons[:5])
        if len(number_buttons) > 5:
            keyboard.append(number_buttons[5:])
    
    # Search and navigation buttons
    nav_buttons = []
    
    # Search buttons
    if show_for_teacher_change:
        nav_buttons.append(InlineKeyboardButton(text="🔍 Ism/Familya qidirish", callback_data=f"grp_search_students:{group_id}:name"))
    else:
        nav_buttons.append(InlineKeyboardButton(text="🔍 Ism/Familya qidirish", callback_data=f"grp_search_students:{group_id}:name"))
    
    # Pagination buttons
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"grp_students_page:{group_id}:{page-1}"))
    
    if end < total:
        nav_buttons.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"grp_students_page:{group_id}:{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Back button
    keyboard.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"group_detail_{group_id}")])
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")


@dp.callback_query(lambda c: c.data.startswith('grp_search_students:'))
async def handle_group_student_search(callback: CallbackQuery):
    """Handle student search in group management"""
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    
    parts = callback.data.split(':')
    group_id = int(parts[2])
    search_type = parts[3]
    
    state = get_admin_state(callback.message.chat.id)
    state['step'] = 'search_group_students'
    state['data']['group_id'] = group_id
    state['data']['search_type'] = search_type
    
    if search_type == 'name':
        await callback.message.answer("🔍 Ism yoki familyani kiriting:")
    
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('grp_students_page:'))
async def handle_group_students_pagination(callback: CallbackQuery):
    """Handle pagination for group student list"""
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    
    parts = callback.data.split(':')
    group_id = int(parts[2])
    page = int(parts[3])
    
    state = get_admin_state(callback.message.chat.id)
    state['data']['students_page'] = page
    
    # Determine the mode based on current step
    step = state.get('step')
    if step == 'remove_student_from_group':
        await show_group_student_list(callback, group_id, remove_mode=True)
    elif step == 'edit_group_teacher':
        await show_group_student_list(callback, group_id, show_for_teacher_change=True)
    else:  # add_student_to_group
        await show_group_student_list(callback, group_id)
    
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('students_page_'))
async def handle_students_pagination(callback: CallbackQuery):
    """Handle pagination for students list"""
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    
    page = int(callback.data.split('_')[-1])
    state = get_admin_state(callback.message.chat.id)
    state['list_page'] = page
    
    await send_user_list(callback.message.chat.id, callback.message, state)
    await callback.answer()


@dp.callback_query(lambda c: c.data == "students_search_start")
async def handle_students_search_start(callback: CallbackQuery):
    state = get_admin_state(callback.message.chat.id)
    state['step'] = 'students_search'
    await callback.message.answer("🔍 Ism, familya yoki Login ID kiriting:", 
                                 reply_markup=cancel_keyboard('uz'))
    await callback.answer()


# Qidiruv natijasi
@dp.message(lambda m: get_admin_state(m.chat.id).get('step') == 'students_search')
async def handle_students_search_input(message: Message):
    query = message.text.strip()
    await show_students_list(message, page=0, search_query=query)


# Pagination va detail callbacklar (fayl oxiriga qo'shing)
@dp.callback_query(lambda c: c.data.startswith("students_page_"))
async def handle_students_pagination(callback: CallbackQuery):
    """Handle pagination for students list"""
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    
    page = int(callback.data.split("_")[-1])
    state = get_admin_state(callback.message.chat.id)
    state['data']['students_page'] = page
    
    await show_students_list(callback.message, page=page)


@dp.callback_query(lambda c: c.data.startswith("student_detail_"))
async def handle_student_detail(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[-1])
    user = get_user_by_id(user_id)
    if not user:
        await callback.answer("Foydalanuvchi topilmadi")
        return
    
    # Bu yerda batafsil ma'lumot chiqarishimiz mumkin emas
    await callback.message.answer(f"🔍 Batafsil: {user['first_name']} {user['last_name']}\nLogin: {user['login_id']}")
    await callback.answer()


# Qidiruvni boshlash
@dp.callback_query(lambda c: c.data == "students_search_start")
async def handle_students_search_start(callback: CallbackQuery):
    state = get_admin_state(callback.message.chat.id)
    state['step'] = 'students_search'
    await callback.message.answer(
        "🔍 Ism, familya yoki Login ID kiriting:", 
        reply_markup=cancel_keyboard('uz')
    )
    state['step'] = None  # ← qidiruv rejimidan chiqish


@dp.callback_query(lambda c: c.data.startswith('grp_add_student:'))
async def handle_add_student_to_group(callback: CallbackQuery):
    """Handle adding student to group"""
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    
    try:
        _, group_id, user_id = callback.data.split(":")
        group_id = int(group_id)
        user_id = int(user_id)
        
        # Check if user already in group
        from db import get_group_users
        current_users = get_group_users(group_id)
        if any(u['id'] == user_id for u in current_users):
            await callback.answer("⚠️ O'quvchi allaqachon bu guruhda!")
            return
        
        # Add user to group
        from db import add_user_to_group
        add_user_to_group(user_id, group_id)
        
        # Get user name for display
        user = get_user_by_id(user_id)
        user_name = f"{user['first_name']} {user['last_name']}" if user else "O'quvchi"
        
        await callback.answer(f"✅ {user_name} guruhga qo'shildi!")
        await _show_group_details(callback, group_id)   # yangi detail sahifasiga qaytadi
        
    except Exception as e:
        logger.error(f"Error adding student to group: {e}")
        await callback.answer("❌ Xatolik yuz berdi")


@dp.callback_query(lambda c: c.data.startswith("grp_remove_student:"))
async def handle_remove_student(callback: CallbackQuery):
    _, group_id, user_id = callback.data.split(":")
    group_id = int(group_id)
    user_id = int(user_id)
    
    remove_user_from_group(user_id, group_id)
    await callback.answer("✅ O'quvchi guruhdan chiqarildi!")
    await _show_group_details(callback, group_id)   # yangi detail sahifasiga qaytadi


@dp.callback_query(lambda c: c.data == 'noop')
async def handle_noop(callback: CallbackQuery):
    """Handle no-operation callbacks"""
    await callback.answer("⚠️ Bu amal mumkin emas")


@dp.callback_query(lambda c: c.data.startswith("grp_set:"))
async def handle_grp_set(callback: CallbackQuery):
    try:
        _, group_id_str, action = callback.data.split(":")
        group_id = int(group_id_str)
        state = get_admin_state(callback.message.chat.id)
        state['data']['group_id'] = group_id

        if action == "teacher":
            teachers = get_all_teachers()
            if not teachers:
                await callback.message.edit_text("❌ Hech qanday o'qituvchi topilmadi.")
                await callback.answer()
                return
            
            kb = create_group_teacher_selection_keyboard(teachers)
            await callback.message.edit_text("👨‍🏫 Yangi o'qituvchini tanlang:", reply_markup=kb)

        elif action == "add_student":
            await show_group_student_list_for_add(callback.message, group_id)

        elif action == "remove_student":
            await show_group_student_list_for_remove(callback.message, group_id)

        elif action == 'time':
            state = get_admin_state(callback.message.chat.id)
            state['step'] = 'edit_group_time'
            state['data']['edit_group_id'] = group_id
            await callback.message.answer('Yangi dars vaqtini kiriting (masalan 14.00-15.30):')

        elif action == 'days':
            state = get_admin_state(callback.message.chat.id)
            state['step'] = 'edit_group_days'
            state['data']['edit_group_id'] = group_id
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text='Mon, Wed, Fri', callback_data="group_days:MWF")],
                [InlineKeyboardButton(text='Tue, Thu, Sat', callback_data="group_days:TTS")],
                [InlineKeyboardButton(text='❌ Cancel', callback_data="cancel_group_creation")],
            ])
            lang = detect_lang_from_user(callback.from_user)
            await callback.message.answer(t(lang, 'ask_group_days'), reply_markup=kb)

        elif action == 'name':
            state = get_admin_state(callback.message.chat.id)
            state['step'] = 'edit_group_name'
            state['data']['edit_group_id'] = group_id
            lang = detect_lang_from_user(callback.from_user)
            await callback.message.answer(t(lang, 'ask_group_name'))

        elif action == 'level':
            state = get_admin_state(callback.message.chat.id)
            state['step'] = 'edit_group_level'
            state['data']['edit_group_id'] = group_id
            lang = detect_lang_from_user(callback.from_user)
            await callback.message.answer(t(lang, 'ask_group_level'))

        elif action == 'delete':
            lang = detect_lang_from_user(callback.from_user)
            group = get_group(group_id)
            if not group:
                await callback.answer(t(lang, 'group_not_found'))
                return
            
            confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Ha", callback_data=f"grp_delete_yes:{group_id}")],
                [InlineKeyboardButton(text="❌ Yo'q", callback_data=f"grp_delete_no:{group_id}")]
            ])
            await callback.message.edit_text(
                f"📚 Guruh: {group.get('name')}\n"
                f"🎓 Level: {group.get('level')}\n\n"
                f"{t(lang, 'confirm_delete_group')}",
                reply_markup=confirm_kb
            )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in handle_grp_set: {e}")
        await callback.answer("❌ Xatolik yuz berdi")


@dp.callback_query(lambda c: c.data.startswith('grp_delete_yes:'))
async def handle_group_delete_yes(callback: CallbackQuery):
    """Handle group deletion confirmation"""
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    
    try:
        group_id = int(callback.data.split(':')[-1])
        from db import delete_group
        delete_group(group_id)
        lang = detect_lang_from_user(callback.from_user)
        await callback.message.answer(t(lang, "group_deleted"))
    except Exception as e:
        logger.error(f"Error deleting group: {e}")
        await callback.message.answer("Xatolik yuz berdi")
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('grp_delete_no:'))
async def handle_group_delete_no(callback: CallbackQuery):
    """Handle group deletion cancellation"""
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('grp_remove:'))
async def handle_group_remove_student(callback: CallbackQuery):
    """Handle removing student from group"""
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    
    parts = callback.data.split(':')
    try:
        group_id = int(parts[1])
        user_id = int(parts[2])
        from db import remove_user_from_group
        remove_user_from_group(user_id, group_id)
        lang = detect_lang_from_user(callback.from_user)
        await callback.message.answer(t(lang, "student_removed_from_group"))
    except Exception as e:
        logger.error(f"Error removing student from group: {e}")
        await callback.message.answer("Xatolik yuz berdi")
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('approve_access_yes:'))
async def handle_approve_access_yes(callback: CallbackQuery):
    """Handle access approval confirmation"""
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    
    try:
        user_id = int(callback.data.split(':')[-1])
        enable_access(user_id)
        lang = detect_lang_from_user(callback.from_user)
        await callback.message.answer(t(lang, "access_approved"))
    except Exception as e:
        logger.error(f"Error approving access: {e}")
        await callback.message.answer("Xatolik yuz berdi")
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('approve_access_no:'))
async def handle_approve_access_no(callback: CallbackQuery):
    """Handle access rejection"""
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    
    try:
        user_id = int(callback.data.split(':')[-1])
        disable_access(user_id)
        lang = detect_lang_from_user(callback.from_user)
        await callback.message.answer(t(lang, "access_rejected"))
    except Exception as e:
        logger.error(f"Error rejecting access: {e}")
        await callback.message.answer("Xatolik yuz berdi")
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('user_test_'))
async def handle_user_test(callback: CallbackQuery):
    """Handle sending test to user"""
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    
    user_id = int(callback.data.split('_')[-1])
    state = get_admin_state(callback.message.chat.id)
    state['step'] = 'ask_test_subject'
    state['data']['test_user_id'] = user_id
    lang = detect_lang_from_user(callback.from_user)
    await callback.message.answer(t(lang, "ask_test_subject"), reply_markup=create_subject_keyboard())
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('user_control_sub_'))
async def handle_user_control_subjects(callback: CallbackQuery):
    """Handle control subjects for a user"""
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    
    user_id = int(callback.data.split('_')[-1])
    user = get_user_by_id(user_id)
    if not user:
        await callback.answer("User not found")
        return
    
    lang = detect_lang_from_user(callback.from_user)
    await callback.message.answer(
        f"🔧 {user['first_name']} {user['last_name']} uchun fanlarni boshqarish",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Add Subject", callback_data=f'user_add_sub_{user_id}')],
            [InlineKeyboardButton(text="🔄 Change Subject", callback_data=f'user_change_sub_{user_id}')],
            [InlineKeyboardButton(text="➖ Delete Subject", callback_data=f'user_delete_sub_{user_id}')],
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data='back_to_menu')],
        ])
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('user_change_sub_'))
async def handle_user_change_subject(callback: CallbackQuery):
    """Handle changing user subject"""
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    
    user_id = int(callback.data.split('_')[-1])
    state = get_admin_state(callback.message.chat.id)
    state['step'] = 'change_subject'
    state['data']['change_user_id'] = user_id
    lang = detect_lang_from_user(callback.from_user)
    await callback.message.answer(t(lang, "ask_new_subject"), reply_markup=create_subject_keyboard())
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('user_add_sub_'))
async def handle_user_add_subject(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    user_id = int(callback.data.split('_')[-1])
    state = get_admin_state(callback.message.chat.id)
    state['step'] = 'add_subject'
    state['data']['change_user_id'] = user_id
    
    # Show subject selection buttons instead of text input
    await callback.message.answer('Yangi subjectni tanlang:', reply_markup=create_subject_keyboard())
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('user_delete_sub_'))
async def handle_user_delete_subject(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    user_id = int(callback.data.split('_')[-1])
    state = get_admin_state(callback.message.chat.id)
    state['step'] = 'delete_subject'
    state['data']['change_user_id'] = user_id
    
    # Show user's current subjects as buttons for deletion
    user = get_user_by_id(user_id)
    if user and user.get('subject'):
        subjects = [s.strip() for s in (user.get('subject') or '').split(',') if s.strip()]
        if subjects:
            # Create buttons for each subject
            buttons = []
            for subject in subjects:
                buttons.append([InlineKeyboardButton(
                    text=f"🗑️ {subject}", 
                    callback_data=f'delete_subject_confirm_{user_id}_{subject}'
                )])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            await callback.message.answer(
                f"👤 {user.get('first_name', '')} {user.get('last_name', '')}\n\n"
                f"O'chirish uchun subjectni tanlang:",
                reply_markup=keyboard
            )
        else:
            await callback.message.answer("❌ Ushbu o'quvchida subjectlar mavjud emas.")
    else:
        await callback.message.answer("❌ O'quvchi topilmadi.")
    await callback.answer()


# Handle subject deletion confirmation
@dp.callback_query(lambda c: c.data.startswith('delete_subject_confirm_'))
async def handle_delete_subject_confirm(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    
    parts = callback.data.split('_')
    if len(parts) < 4 or parts[2] == "confirm":
        await callback.answer("❌ Invalid callback data")
        return
    user_id = int(parts[2])
    subject = '_'.join(parts[3:])  # Handle subject names with underscores
    
    user = get_user_by_id(user_id)
    if user and user.get('subject'):
        subjects = [s.strip() for s in (user.get('subject') or '').split(',') if s.strip()]
        if subject in subjects:
            subjects.remove(subject)
            update_user_subjects(user_id, subjects)
            remaining_subjects = ', '.join(subjects) if subjects else "Yo'q"
            await callback.message.answer(
                f"✅ Subject '{subject}' o'chirildi.\n\nQolgan subjectlar: {remaining_subjects}"
            )
        else:
            await callback.message.answer(f"❌ Subject '{subject}' topilmadi.")
    else:
        await callback.message.answer("❌ O'quvchi topilmadi.")
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('user_block_'))
async def handle_user_block(callback: CallbackQuery):
    """Handle blocking a user"""
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    
    user_id = int(callback.data.split('_')[-1])
    from db import block_user
    block_user(user_id)
    
    lang = detect_lang_from_user(callback.from_user)
    await callback.message.answer("✅ User bloklandi", parse_mode='HTML')
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('user_unblock_'))
async def handle_user_unblock(callback: CallbackQuery):
    """Handle unblocking a user"""
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    
    user_id = int(callback.data.split('_')[-1])
    from db import unblock_user
    unblock_user(user_id)
    
    lang = detect_lang_from_user(callback.from_user)
    await callback.message.answer("✅ User blokdan olindi", parse_mode='HTML')
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('user_reset_'))
async def handle_user_reset_password(callback: CallbackQuery):
    """Handle user password reset"""
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    
    user_id = int(callback.data.split('_')[-1])
    from db import reset_user_password
    import random
    import string
    
    # Generate random password
    new_password = ''.join(random.choices(string.digits, k=6))
    reset_user_password(user_id, new_password)
    
    lang = detect_lang_from_user(callback.from_user)
    await callback.message.answer(f"🔑 Yangi parol: <code>{new_password}</code>", parse_mode='HTML')
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('back_to_menu'))
async def handle_back_to_menu(callback: CallbackQuery):
    """Handle back to main menu"""
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    
    lang = detect_lang_from_user(callback.from_user)
    await callback.message.answer(t(lang, 'main_menu_prompt'), reply_markup=admin_main_keyboard(lang))
    await callback.answer()


@dp.callback_query(lambda c: c.data in ('users_next', 'users_prev'))
async def handle_user_pagination(callback: CallbackQuery):
    """Handle user list pagination"""
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    
    data = callback.data
    state = get_admin_state(callback.message.chat.id)
    
    if data == 'users_next':
        state['list_page'] += 1
    elif data == 'users_prev':
        state['list_page'] = max(0, state.get('list_page', 0) - 1)
    
    await send_user_list(callback.message.chat.id, callback.message, state)
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('user_select_'))
async def handle_user_selection(callback: CallbackQuery):
    """Handle user selection from list"""
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    
    idx = int(callback.data.split('_')[-1])
    state = get_admin_state(callback.message.chat.id)
    users = state.get('list_users', [])
    
    if idx < 0 or idx >= len(users):
        await callback.answer(t(detect_lang_from_user(callback.from_user), 'err_invalid_choice'))
        return
    
    selected_user = users[idx]
    state['selected_user'] = selected_user
    
    if selected_user.get('blocked'):
        status = '🔒 Bloklangan'
    elif is_access_active(selected_user):
        status = '✅ Ochiq'
    else:
        status = '❌ Yopiq'

    lang = detect_lang_from_user(callback.from_user)
    # Build user control keyboard (add edit name, reset pw, block/unblock)
    kb_rows = [
        [InlineKeyboardButton(text=t(lang, 'btn_send_test'), callback_data=f'user_test_{selected_user["id"]}')],
        [InlineKeyboardButton(text="📚 Subject settings", callback_data=f'user_control_sub_{selected_user["id"]}')],
        [InlineKeyboardButton(text='✏️ Ism', callback_data=f'user_edit_first_{selected_user["id"]}'), InlineKeyboardButton(text='✏️ Familya', callback_data=f'user_edit_last_{selected_user["id"]}')],
        [InlineKeyboardButton(text='🔑 Parol reset', callback_data=f'user_reset_{selected_user["id"]}')],
    ]
    if selected_user.get('blocked'):
        kb_rows.append([InlineKeyboardButton(text='🔓 Unblock', callback_data=f'user_unblock_{selected_user["id"]}')])
    else:
        kb_rows.append([InlineKeyboardButton(text='🔒 Block', callback_data=f'user_block_{selected_user["id"]}')])
    kb_rows.append([InlineKeyboardButton(text=t(lang, 'btn_home_menu'), callback_data='back_to_menu')])

    await callback.message.answer(
        f"👤 {selected_user['first_name']} {selected_user['last_name']}\n"
        f"🔑 {selected_user['login_id']} | 🧩 {selected_user['subject']} | 🎓 {selected_user['level'] or '-'}\n"
        f"📌 Status: {status}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows)
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data in ('pay_search:login', 'pay_search:name'))
async def handle_payment_search(callback: CallbackQuery):
    """Handle payment search initialization"""
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    
    data = callback.data
    state = get_admin_state(callback.message.chat.id)
    lang = detect_lang_from_user(callback.from_user)
    
    if data == 'pay_search:login':
        state['step'] = 'pay_search_login'
        await callback.message.answer(t(lang, "enter_login_id_example"))
    elif data == 'pay_search:name':
        state['step'] = 'pay_search_name'
        await callback.message.answer(t(lang, "enter_name_or_fullname"))
    
    await callback.answer()


@dp.callback_query(lambda c: c.data == 'payment_export_history')
async def handle_payment_export_history(callback: CallbackQuery):
    """Handle payment history export"""
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    
    from payment import export_payment_history_to_xlsx, cleanup_old_payment_history
    lang = detect_lang_from_user(callback.from_user)
    
    try:
        cleanup_old_payment_history()
        bio, fname = export_payment_history_to_xlsx()
        await callback.bot.send_document(callback.message.chat.id, BufferedInputFile(bio.getvalue(), filename=fname))
        await callback.answer(t(lang, 'export_success'))
    except Exception as e:
        logger.exception("Failed to export payment history")
        await callback.answer(t(lang, 'export_error'))


@dp.callback_query(lambda c: c.data.startswith('admin_attendance_group:'))
async def handle_admin_attendance_group(callback: CallbackQuery):
    """Handle attendance group selection"""
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    
    group_id = int(callback.data.split(":")[1])
    group = get_group(group_id)
    if not group:
        await callback.answer()
        return
    
    from attendance_manager import get_group_sessions
    sessions = get_group_sessions(group_id)
    if not sessions:
        await callback.message.answer("Bu guruhda davomat sessiyalari topilmadi.")
        await callback.answer()
        return
    
    # Show recent sessions
    keyboard = []
    for session in sessions[:5]:  # Show last 5 sessions
        date = session['date']
        keyboard.append([InlineKeyboardButton(text=f"📅 {date}", callback_data=f"admin_take_attendance:{group_id}:{date}")])
    
    keyboard.append([InlineKeyboardButton(text="📥 Export Attendance (Excel)", callback_data=f"admin_export_group_attendance:{group_id}")])
    keyboard.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_attendance_back")])
    
    lang = detect_lang_from_user(callback.from_user)
    await callback.message.answer(
        f"📊 <b>{group['name']}</b> guruhining davomati\n\nOxirgi sessiyalar:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode='HTML'
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('admin_take_attendance:'))
async def handle_admin_take_attendance(callback: CallbackQuery):
    """Handle taking attendance for a group"""
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    
    parts = callback.data.split(":")
    group_id = int(parts[1])
    date = parts[2]
    
    from attendance_manager import ensure_session, send_attendance_panel
    session = ensure_session(group_id, date)
    if not session:
        await callback.answer("Davomat sessiyasi yaratilmadi")
        return
    
    await send_attendance_panel(callback.bot, callback.message.chat.id, session["id"], group_id, date, 0)
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('admin_export_group_attendance:'))
async def handle_admin_export_group_attendance(callback: CallbackQuery):
    """Handle exporting group attendance"""
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    
    group_id = int(callback.data.split(":")[1])
    from vocabulary import export_group_attendance_to_xlsx
    
    try:
        bio, fname = export_group_attendance_to_xlsx(group_id)
        await callback.bot.send_document(callback.message.chat.id, BufferedInputFile(bio.getvalue(), filename=fname))
        await callback.answer()
    except Exception as e:
        logger.exception("Failed to export group attendance")
        await callback.answer("Xatolik yuz berdi")


@dp.callback_query(lambda c: c.data == "admin_attendance_back")
async def handle_admin_attendance_back(callback: CallbackQuery):
    """Handle back to attendance menu"""
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    
    await show_attendance_menu(callback.message)
    await callback.answer()


@dp.callback_query(lambda c: c.data == "admin_back_to_main")
async def handle_admin_back_to_main(callback: CallbackQuery):
    """Handle back to main menu"""
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    
    lang = detect_lang_from_user(callback.from_user)
    await callback.message.answer(t(lang, 'main_menu_prompt'), reply_markup=admin_main_keyboard(lang))
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('assign_new:'))
async def handle_assign_new_user(callback: CallbackQuery):
    """Handle assigning new user to group"""
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    
    parts = callback.data.split(':')
    if len(parts) < 3:
        await callback.answer()
        return
    
    user_id = int(parts[1])
    page = int(parts[3]) if len(parts) > 3 else 0
    
    state = get_admin_state(callback.message.chat.id)
    state['step'] = 'assign_user_to_group'
    state['data']['assign_user_id'] = user_id
    
    lang = detect_lang_from_user(callback.from_user)
    groups = get_all_groups()
    if not groups:
        await callback.message.answer(t(lang, "no_groups_found"))
        await callback.answer()
        return
    
    # Paginate groups
    PAGE_SIZE = 10
    total_pages = (len(groups) + PAGE_SIZE - 1) // PAGE_SIZE
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_groups = groups[start:end]
    
    out = []
    out.append("👥 Guruhlar ro'yxati")
    out.append(f"(Sahifa {page+1}/{total_pages})\n")
    
    for idx, g in enumerate(page_groups, start=1):
        teacher = get_user_by_id(g.get('teacher_id')) if g.get('teacher_id') else None
        teacher_name = f"{teacher.get('first_name','')} {teacher.get('last_name','')}".strip() if teacher else "-"
        students = get_group_users(g['id'])
        out.append(f"{idx}. {g['name']} - {teacher_name} ({len(students)} o'quvchi)")
    
    kb = _group_list_keyboard(page_groups, page, total_pages, base=f"assign_select:{user_id}", lang=lang)
    await callback.message.answer("\n".join(out), reply_markup=kb)
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('assign_select:'))
async def handle_assign_select_group(callback: CallbackQuery):
    """Handle group selection for user assignment"""
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    
    parts = callback.data.split(':')
    if len(parts) < 3:
        await callback.answer()
        return
    
    user_id = int(parts[1])
    group_id = int(parts[2])
    
    from db import add_user_to_group
    add_user_to_group(user_id, group_id)
    
    lang = detect_lang_from_user(callback.from_user)
    user = get_user_by_id(user_id)
    group = get_group(group_id)
    
    await callback.message.answer(
        f"✅ {user['first_name']} {user['last_name']} {group['name']} guruhiga qo'shildi"
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('group_days:'))
async def handle_group_days(callback: CallbackQuery):
    """Handle group days selection"""
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    
    days = callback.data.split(':')[1]
    state = get_admin_state(callback.message.chat.id)
    state['data']['group_days'] = _to_lesson_days_key(days)
    state['data']['lesson_date'] = _to_lesson_days_key(days)
    state['step'] = 'ask_group_time'  # Set next step to time input
    lang = detect_lang_from_user(callback.from_user)
    label = 'Mon, Wed, Fri' if _to_lesson_days_key(days) == 'MWF' else 'Tue, Thu, Sat'
    await callback.message.answer(
        f'✅ Dars kunlari: {label} saqlandi.\n\n'
        '⏰ Endi dars vaqtini kiriting:\n\n'
        '📝 Format: 09.00-13.30 yoki 09:00-13:30\n'
        '📋 Masalan: 09.00-13.30'
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data == 'cancel_group_creation')
async def handle_cancel_group_creation(callback: CallbackQuery):
    """Handle group creation cancellation"""
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    
    reset_admin_state(callback.message.chat.id)
    lang = detect_lang_from_user(callback.from_user)
    await callback.message.edit_text(
        t(lang, 'operation_cancelled'),
        reply_markup=admin_main_keyboard(lang)
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('edit_group_days:'))
async def handle_edit_group_days(callback: CallbackQuery):
    """Handle edit group days selection"""
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    
    days = callback.data.split(':')[1]
    state = get_admin_state(callback.message.chat.id)
    group_id = state['data'].get('edit_group_id')
    if group_id:
        group = get_group(group_id)
        if not group:
            await callback.answer('Guruh topilmadi.')
            return
        teacher_id = group.get('teacher_id')
        if teacher_id and _teacher_conflicts(teacher_id, days, group.get('lesson_start') or '', group.get('lesson_end') or '', exclude_group_id=group_id):
            await callback.message.answer('❌ Ushbu o‘qituvchida yangi kunlar uchun o‘sha vaqt band. Amal bekor qilindi.')
            await callback.answer()
            return

        from db import update_group_days
        update_group_days(group_id, _to_lesson_days_key(days))

        lang = detect_lang_from_user(callback.from_user)
        label = 'Mon, Wed, Fri' if _to_lesson_days_key(days) == 'MWF' else 'Tue, Thu, Sat'
        await callback.message.answer(f'✅ Guruh dars kunlari {label} ga yangilandi.')
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('att_mark_'))
async def handle_attendance_mark(callback: CallbackQuery):
    """Handle attendance marking"""
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    
    parts = callback.data.split('_')
    session_id = int(parts[2])
    user_id = int(parts[3])
    status = parts[4]
    
    from attendance_manager import mark_attendance
    mark_attendance(session_id, user_id, status)
    
    page = int(parts[5]) if len(parts) > 5 else 0
    session = get_session(session_id)
    if session:
        kb = build_attendance_keyboard(session_id, session["group_id"], session["date"], page)
        await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('att_finish_'))
async def handle_attendance_finish(callback: CallbackQuery):
    """Handle attendance session finish"""
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    
    session_id = int(callback.data.split('_')[2])
    from attendance_manager import set_session_closed
    set_session_closed(session_id, True)
    await callback.answer("✅ Davomat yakunlandi")


@dp.callback_query(lambda c: c.data.startswith('att_reopen_'))
async def handle_attendance_reopen(callback: CallbackQuery):
    """Handle attendance session reopen"""
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    
    session_id = int(callback.data.split('_')[2])
    from attendance_manager import set_session_closed
    set_session_closed(session_id, False)
    
    session = get_session(session_id)
    if session:
        kb = build_attendance_keyboard(session_id, session["group_id"], session["date"], 0)
        await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer("🔄 Davomat qayta ochildi")


@dp.callback_query(lambda c: c.data.startswith(':pick:'))
async def handle_generic_pick(callback: CallbackQuery):
    """Handle generic pick callbacks for pagination"""
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    
    parts = callback.data.split(':')
    if len(parts) < 3:
        await callback.answer()
        return
    
    base = parts[0]
    item_id = int(parts[2])
    
    # Handle different base types
    if base.startswith('assign_select'):
        user_id = int(base.split('_')[1])
        group_id = item_id
        
        from db import add_user_to_group
        add_user_to_group(user_id, group_id)
        
        lang = detect_lang_from_user(callback.from_user)
        user = get_user_by_id(user_id)
        group = get_group(group_id)
        
        await callback.message.answer(
            f"✅ {user['first_name']} {user['last_name']} {group['name']} guruhiga qo'shildi"
        )
    
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith(':page:'))
async def handle_generic_page(callback: CallbackQuery):
    """Handle generic page callbacks"""
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    
    parts = callback.data.split(':')
    if len(parts) < 3:
        await callback.answer()
        return
    
    base = parts[0]
    page = int(parts[2])
    
    # Handle pagination for different base types
    if base.startswith('assign_select'):
        user_id = int(base.split('_')[1])
        # Show groups page
        groups = get_all_groups()
        PAGE_SIZE = 10
        total_pages = (len(groups) + PAGE_SIZE - 1) // PAGE_SIZE
        start = page * PAGE_SIZE
        end = start + PAGE_SIZE
        page_groups = groups[start:end]
        
        lang = detect_lang_from_user(callback.from_user)
        out = []
        out.append("👥 Guruhlar ro'yxati")
        out.append(f"(Sahifa {page+1}/{total_pages})\n")
        
        for idx, g in enumerate(page_groups, start=1):
            teacher = get_user_by_id(g.get('teacher_id')) if g.get('teacher_id') else None
            teacher_name = f"{teacher.get('first_name','')} {teacher.get('last_name','')}".strip() if teacher else "-"
            students = get_group_users(g['id'])
            out.append(f"{idx}. {g['name']} - {teacher_name} ({len(students)} o'quvchi)")
        
        kb = _group_list_keyboard(page_groups, page, total_pages, base=f"assign_select:{user_id}", lang=lang)
        await callback.message.edit_text("\n".join(out), reply_markup=kb)
    
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('user_detail_'))
async def handle_user_detail(callback: CallbackQuery):
    """Handle user detail view"""
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    
    try:
        user_id = int(callback.data.split('_')[-1])
        user = get_user_by_id(user_id)
        if not user:
            await callback.answer("User not found")
            return
        
        lang = detect_lang_from_user(callback.from_user)
        
        if user.get('blocked'):
            status = '🔒 Bloklangan'
        elif is_access_active(user):
            status = '✅ Ochiq'
        else:
            status = '❌ Yopiq'

        kb_rows = [
            [InlineKeyboardButton(text=t(lang, 'btn_send_test'), callback_data=f'user_test_{user["id"]}')],
            [InlineKeyboardButton(text='📚 Subject settings', callback_data=f'user_control_sub_{user["id"]}')],
            [InlineKeyboardButton(text='✏️ Ismni ozgartirish', callback_data=f'user_edit_first_{user["id"]}'), 
             InlineKeyboardButton(text='✏️ Familyani ozgartirish', callback_data=f'user_edit_last_{user["id"]}')],
            [InlineKeyboardButton(text='📱 Telefon raqamni ozgartirish', callback_data=f'user_edit_phone_{user["id"]}')],
            [InlineKeyboardButton(text='🔑 Parolni Reset qilish', callback_data=f'user_reset_{user["id"]}')],
        ]
        if user.get('blocked'):
            kb_rows.append([InlineKeyboardButton(text='🔓 Unblock', callback_data=f'user_unblock_{user["id"]}')])
        else:
            kb_rows.append([InlineKeyboardButton(text='🔒 Block', callback_data=f'user_block_{user["id"]}')])
        kb_rows.append([InlineKeyboardButton(text=t(lang, 'btn_home_menu'), callback_data='back_to_menu')])

        await callback.message.answer(
            f"👤 {user['first_name']} {user['last_name']}\n"
            f"🔑 {user['login_id']} | 🧩 {user['subject']} | 🎓 {user['level'] or '-'}\n"
            f"📱 Tel: {user.get('phone', '—')}\n"
            f"📌 Status: {status}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows)
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in user_detail handler: {e}")
        await callback.answer("❌ Xatolik yuz berdi")
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('teacher_select_'))
async def handle_teacher_selection(callback: CallbackQuery):
    """Handle teacher selection"""
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    
    teacher_id = int(callback.data.split('_')[-1])
    state = get_admin_state(callback.message.chat.id)
    
    lang = detect_lang_from_user(callback.from_user)
    
    # Handle different teacher selection contexts
    if state.get('step') == 'edit_group_teacher':
        state['data']['edit_group_teacher_id'] = teacher_id
        state['step'] = None
        group_id = state['data'].get('edit_group_id')
        
        if group_id:
            from db import update_group_teacher
            update_group_teacher(group_id, teacher_id)
            await callback.message.answer("✅ O'qituvchi guruhga tayinlandi")
        await callback.answer()
        return
    
    if state.get('step') == 'ask_teacher_for_group':
        group_id = state['data'].get('group_id')
        if group_id:
            from db import update_group_teacher
            update_group_teacher(group_id, teacher_id)
            await callback.message.answer("✅ O'qituvchi guruhga tayinlandi")
        state['step'] = None
        state['data'] = {}
        await callback.answer()
        return

    # Default teacher profile + edit menu
    teacher = get_user_by_id(teacher_id)
    if not teacher:
        await callback.answer(t(lang, 'teacher_not_found'))
        return

    if teacher.get('blocked'):
        status = '🔒 Bloklangan'
    elif is_access_active(teacher):
        status = '✅ Ochiq'
    else:
        status = '❌ Yopiq'

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='✏️ Ism', callback_data=f'teach_edit_first_{teacher_id}')],
        [InlineKeyboardButton(text='✏️ Familya', callback_data=f'teach_edit_last_{teacher_id}')],
        [InlineKeyboardButton(text='📱 Telefon', callback_data=f'teach_edit_phone_{teacher_id}')],
        [InlineKeyboardButton(text='📚 Fan', callback_data=f'teach_edit_subject_{teacher_id}')],
        [InlineKeyboardButton(text="🔄 Password Reset", callback_data=f'teacher_reset_{teacher_id}')]
    ])

    await callback.message.answer(
        f"👨‍🏫 {teacher['first_name']} {teacher['last_name']}\n"
        f"📱 {teacher.get('phone') or '-'}\n"
        f"📚 {teacher.get('subject') or '-'}\n"
        f"📌 Status: {status}",
        reply_markup=kb
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('teacher_reset_'))
async def handle_teacher_password_reset(callback: CallbackQuery):
    """Handle teacher password reset"""
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    
    teacher_id = int(callback.data.split('_')[-1])
    teacher = get_user_by_id(teacher_id)
    
    if not teacher:
        await callback.answer(t(lang, 'teacher_not_found'))
        return
    
    lang = detect_lang_from_user(callback.from_user)
    
    # Generate new password
    import random
    import string
    new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    
    # Update password in database
    from db import get_conn
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('UPDATE users SET password = ?, password_used = 0 WHERE id = ?', (new_password, teacher_id))
    conn.commit()
    conn.close()
    
    # Send confirmation to admin
    await callback.message.answer(
        f"✅ Teacher password reset successfully!\n"
        f"👨‍🏫 {teacher['first_name']} {teacher['last_name']}\n"
        f"🔑 New Password: <code>{new_password}</code>",
        parse_mode='HTML'
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('teach_edit_'))
async def handle_teacher_edit_field(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return

    parts = callback.data.split('_')
    field = parts[2]
    teacher_id = int(parts[-1])
    state = get_admin_state(callback.message.chat.id)
    
    if field == 'subject':
        # Show subject selection keyboard instead of text input
        state['step'] = f'teach_edit_{field}'
        state['data']['teacher_id'] = teacher_id
        await callback.message.answer(
            f"Yangi {field}ni tanlang:",
            reply_markup=create_subject_keyboard()
        )
        await callback.answer()
        return
    
    # For other fields, use text input as before
    state['step'] = f'teach_edit_{field}'
    state['data']['teacher_id'] = teacher_id

    prompt = {
        'first': 'Yangi ismni kiriting:',
        'last': 'Yangi familyani kiriting:',
        'phone': 'Yangi telefon raqamini kiriting:',
    }.get(field, 'Yangi qiymatni kiriting:')

    await callback.message.answer(prompt)
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('user_edit_first_'))
async def handle_user_edit_first(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    parts = callback.data.split('_')
    user_id = int(parts[-1])
    state = get_admin_state(callback.message.chat.id)
    state['step'] = 'user_edit_first'
    state['data']['change_user_id'] = user_id
    await callback.message.answer('Yangi ismni kiriting:')
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('user_edit_last_'))
async def handle_user_edit_last(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    parts = callback.data.split('_')
    user_id = int(parts[-1])
    state = get_admin_state(callback.message.chat.id)
    state['step'] = 'user_edit_last'
    state['data']['change_user_id'] = user_id
    await callback.message.answer('Yangi familyani kiriting:')
    await callback.answer()


@dp.callback_query(lambda c: c.data == 'group_create')
async def group_create_start(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    state = get_admin_state(callback.message.chat.id)
    state['step'] = 'ask_group_name'
    await callback.message.answer('Yangi guruh nomini kiriting:')
    await callback.answer()


@dp.callback_query(lambda c: c.data == 'group_list')
async def group_list_show(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    
    # Use the new _show_group_list function with correct callback pattern
    await _show_group_list(callback, page=0)


@dp.callback_query(lambda c: c.data.startswith('assign_test_user_'))
async def handle_assign_test_user_to_group(callback: CallbackQuery):
    """Handle assigning test user to group from admin notification"""
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    
    parts = callback.data.split('_')
    user_id = int(parts[3])
    group_id = int(parts[4])
    
    user = get_user_by_id(user_id)
    group = get_group(group_id)
    
    if not user or not group:
        await callback.answer("❌ Xatolik: Foydalanuvchi yoki guruh topilmadi")
        return
    
    # Add user to group
    add_user_to_group(user_id, group_id)
    
    # Update user access if needed
    if not is_access_active(user):
        enable_access(user_id)
    
    await callback.message.answer(
        f"✅ Foydalanuvchi guruhga qo'shildi!\n\n"
        f"👤 {user['first_name']} {user['last_name']}\n"
        f"🏫 {group['name']} ({group.get('level', '—')})\n"
        f"👨‍🏫 {group.get('teacher_name', '—')}"
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('group_create_for_user_'))
async def handle_group_create_for_user(callback: CallbackQuery):
    """Handle creating group for specific user from admin notification"""
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    
    parts = callback.data.split('_')
    user_id = int(parts[4])
    subject = parts[5]
    level = parts[6]
    
    user = get_user_by_id(user_id)
    if not user:
        await callback.answer("❌ Foydalanuvchi topilmadi")
        return
    
    state = get_admin_state(callback.message.chat.id)
    state['step'] = 'ask_group_name'
    state['data'] = {
        'target_user_id': user_id,
        'subject': subject,
        'level': level
    }
    
    await callback.message.answer(
        f"👤 {user['first_name']} {user['last_name']} uchun yangi guruh yaratish\n\n"
        f"📚 Fan: {subject}\n"
        f"🎯 Daraja: {level}\n\n"
        f"Yangi guruh nomini kiriting:"
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('user_type_'))
async def handle_user_type_selection(callback: CallbackQuery):
    """Handle user type selection for new user creation"""
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer()
        return
    
    user_type = int(callback.data.split('_')[-1])
    state = get_admin_state(callback.message.chat.id)
    state['step'] = 'ask_first_name'
    state['data']['login_type'] = user_type
    
    lang = detect_lang_from_user(callback.from_user)
    await callback.answer()
    await callback.message.answer(t(lang, 'ask_first_name'), reply_markup=cancel_keyboard(lang))


@dp.callback_query(lambda c: c.data.startswith(('set_lang_me_', 'att_noop', 'noop', 'pay_search:', 'pay_list:', 'subject_', 'user_test_', 'user_control_sub_', 'user_change_sub_', 'user_add_sub_', 'user_delete_sub_', 'delete_subject_confirm_', 'user_block_', 'user_unblock_', 'user_reset_', 'user_select_', 'admin_export_group_attendance:', 'group_days:', 'cancel_group_creation', 'edit_group_days:', 'group_teacher_select_', 'group_create', 'group_list', 'grp_search_students:', 'grp_students_page:', 'grp_add_student:', 'grp_remove_student:', 'grp_set:', 'grp_delete_yes:', 'grp_delete_no:', 'approve_access_yes:', 'approve_access_no:', 'teacher_select_', 'teacher_detail_', 'teacher_edit_', 'teacher_groups_', 'teacher_reset_', 'teacher_block_', 'teacher_unblock_', 'teacher_change_sub_', 'teacher_change_lang_', 'user_change_lang_', 'set_lang_', 'test_', 'teachers_next', 'teachers_prev', 'teachers_list', 'group_teacher_select_')))
async def handle_callback(callback: CallbackQuery):
    logger.info(f"🔘 CALLBACK: {callback.data} | User: {callback.from_user.id}")
    data = callback.data
    state = get_admin_state(callback.message.chat.id)
    lang = detect_lang_from_user(callback.from_user)

    # IMPORTANT: handle language selection here, otherwise this catch-all
    # callback handler swallows the update before the dedicated handler runs.
    if data.startswith('set_lang_me_'):
        code = data.split('_')[-1]
        ok = set_user_language_by_telegram(str(callback.from_user.id), code)
        # Admin uchun maxsus: DB da row bo'lmasa ham til o'zgartirish ishlaydi
        if ok or str(callback.from_user.id) in map(str, ADMIN_CHAT_IDS):
            await callback.answer()
            await callback.message.answer(t(code, 'lang_set'))
            await callback.message.answer(t(code, 'select_from_menu'), reply_markup=admin_main_keyboard(code))
        else:
            await callback.answer()
            await callback.message.answer(t(code, 'please_send_start'))
        return

    # Let dedicated handlers handle teacher callbacks
    if data.startswith(('teacher_detail_', 'teacher_edit_', 'teacher_groups_')):
        return

    # Attendance callbacks (admin)
    if data == 'att_noop':
        await callback.answer()
        return

    # User selection separator callbacks
    if data == 'noop':
        await callback.answer()
        return

    # ===================== PAYMENTS =====================
    if data == 'pay_search:login':
        state['step'] = 'pay_search_login'
        await callback.message.answer(t(lang, "enter_login_id_example"))
        await callback.answer()
        return

    if data == 'pay_search:name':
        state['step'] = 'pay_search_name'
        await callback.message.answer(t(lang, "enter_name_or_fullname"))
        await callback.answer()
        return

    if data.startswith('pay_list:'):
        parts = data.split(':')
        if len(parts) < 5:
            await callback.answer()
            return
        mode = parts[1]
        query = parts[2]
        action = parts[3]
        if action == 'page':
            try:
                page = int(parts[4])
            except Exception:
                page = 0
            await _render_payment_search_results(callback, mode, query, page)
            return
        if action == 'pick':
            try:
                user_id = int(parts[4])
            except Exception:
                await callback.answer()
                return
            await _show_student_payment_card(callback, user_id)
            return

    if data.startswith('pay_set:'):
        parts = data.split(':')
        if len(parts) < 4:
            await callback.answer()
            return
        try:
            user_id = int(parts[1])
        except Exception:
            await callback.answer()
            return
        group_id = None
        try:
            group_id = int(parts[2])
        except Exception:
            await callback.answer()
            return
        action = parts[3]
        groups = get_user_groups(user_id)
        group = next((g for g in groups if g['id'] == group_id), None)
        subject = group.get('subject') if group else None
        if action == 'paid':
            set_month_paid(user_id, group_id=group_id, subject=subject, paid=True)
            await callback.message.answer(f"✅ To‘lov tasdiqlandi: {group.get('name', '-') if group else ''}")
            # notify student
            student = get_user_by_id(user_id)
            if student and student.get('telegram_id'):
                try:
                    await bot.send_message(int(student['telegram_id']),
                        f"✅ To'lov muvaffaqiyatli qabul qilindi. Guruh: {group.get('name','-')} | Fan: {subject or '-'}")
                except Exception:
                    pass
        elif action == 'unpaid':
            set_month_paid(user_id, group_id=group_id, subject=subject, paid=False)
            await callback.message.answer(f"❌ To‘lov bekor qilindi: {group.get('name', '-') if group else ''}")
            student = get_user_by_id(user_id)
            if student and student.get('telegram_id'):
                try:
                    await bot.send_message(int(student['telegram_id']),
                        f"❌ To'lov bekor qilindi. Guruh: {group.get('name','-')} | Fan: {subject or '-'}")
                except Exception:
                    pass
        await callback.answer()
        return

    if data.startswith('att_page_'):
        parts = data.split('_')
        session_id = int(parts[2])
        page = int(parts[3])
        session = get_session(session_id)
        if not session:
            await callback.answer()
            return
    if data.startswith('users_') or data.startswith('user_select_'):
        await handle_admin_user_action(callback)
        return

    # Handle subject selection for various flows
    if data.startswith('subject_') and state.get('step') in ('admin_export_choose_subject', 'admin_await_vocab_subject', 'change_subject', 'ask_test_subject', 'ask_subject', 'add_subject', 'change_teacher_subject'):
        await handle_subject_for_admin_vocab(callback)
        return

    # Handle group actions (these are already handled by dedicated handlers)
    if data.startswith('grp_set:') or data.startswith('grp_delete_') or data.startswith('grp_remove:'):
        # These are handled by dedicated handlers above
        await callback.answer()
        return

    # Handle attendance actions
    if data.startswith('admin_attendance_group:'):
        group_id = int(data.split(":")[1])
        group = get_group(group_id)
        if not group:
            await callback.answer()
            return
        
        from attendance_manager import get_group_sessions
        sessions = get_group_sessions(group_id)
        if not sessions:
            await callback.message.answer("Bu guruhda davomat sessiyalari topilmadi.")
            await callback.answer()
            return
        
        # Show recent sessions
        keyboard = []
        for session in sessions[:5]:  # Show last 5 sessions
            date = session['date']
            keyboard.append([InlineKeyboardButton(text=f"📅 {date}", callback_data=f"admin_take_attendance:{group_id}:{date}")])
        
        keyboard.append([InlineKeyboardButton(text="📥 Export Attendance (Excel)", callback_data=f"admin_export_group_attendance:{group_id}")])
        keyboard.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_attendance_back")])
        
        await callback.message.answer(
            f"📊 <b>{group['name']}</b> guruhining davomati\n\nOxirgi sessiyalar:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode='HTML'
        )
        await callback.answer()
        return

    # Handle attendance session actions
    if data.startswith('admin_take_attendance:'):
        parts = data.split(":")
        group_id = int(parts[1])
        date = parts[2]
        from attendance_manager import get_session, send_attendance_panel
        session = get_session(group_id, date)
        if not session:
            # Create new session
            from attendance_manager import set_session
            set_session(group_id, date, {})
            session = get_session(group_id, date)
        await send_attendance_panel(callback.bot, callback.message.chat.id, session["id"], group_id, date, 0)
        await callback.answer()
        return

    # Handle export actions
    if data == "admin_export_attendance":
        from vocabulary import export_all_attendance_to_xlsx
        try:
            bio, fname = export_all_attendance_to_xlsx()
            await callback.bot.send_document(callback.message.chat.id, BufferedInputFile(bio.getvalue(), filename=fname))
            await callback.answer(t(lang, 'export_success'))
        except Exception as e:
            logger.exception("Failed to export attendance")
            await callback.answer(t(lang, 'export_error'))
        return

    if data.startswith('export_group_attendance:'):
        group_id = int(data.split(":")[1])
        from vocabulary import export_group_attendance_to_xlsx
        try:
            bio, fname = export_group_attendance_to_xlsx(group_id)
            await callback.bot.send_document(callback.message.chat.id, BufferedInputFile(bio.getvalue(), filename=fname))
            await callback.answer()
        except Exception as e:
            logger.exception("Failed to export group attendance")
            await callback.answer("Xatolik yuz berdi")
        return

    if data == "admin_attendance_back":
        await show_attendance_menu(callback.message)
        await callback.answer()
        return

    if data == "admin_back_to_main":
        """Handle back to main menu"""
        lang = detect_lang_from_user(callback.from_user)
        await callback.message.answer(t(lang, 'main_menu_prompt'), reply_markup=admin_main_keyboard(lang))
        await callback.answer()
        return

    # Handle user language change
    if data.startswith('user_change_lang_'):
        user_id = int(data.split('_')[-1])
        keyboard = create_language_selection_keyboard_for_user(user_id)
        await callback.message.answer(t(lang, 'select_language_prompt'), reply_markup=keyboard)
        await callback.answer()
        return

    if data.startswith('teacher_change_lang_'):
        teacher_id = int(data.split('_')[-1])
        keyboard = create_language_selection_keyboard_for_user(teacher_id)
        await callback.message.answer(t(lang, 'select_language_prompt'), reply_markup=keyboard)
        await callback.answer()
        return

    # Set language for specified user id (do not match set_lang_me_)
    if data.startswith('set_lang_') and not data.startswith('set_lang_me_'):
        parts = data.split('_')
        if len(parts) >= 3:
            lang_code = parts[2]
            try:
                target_id = int(parts[3])
            except Exception:
                await callback.answer(t(lang, 'err_invalid_format'))
                return
            
            from db import set_user_language_by_telegram
            ok = set_user_language_by_telegram(str(target_id), lang_code)
            
            if ok:
                await callback.answer("✅ Til o'zgartirildi")
            else:
                await callback.answer("❌ Xatolik")
        return

    if data.startswith('group_list:page:'):
        try:
            page = int(data.split(':')[-1])
        except Exception:
            await callback.answer()
            return
        await _show_group_list(callback, page)
        return

    if data.startswith('group_list:pick:'):
        try:
            group_id = int(data.split(':')[-1])
        except Exception:
            await callback.answer()
            return
        await _show_group_details(callback, group_id)
        return

    # Recommended groups for a new student after placement test
    if data.startswith('rec_groups:'):
        # format: rec_groups:<user_id>:page:<n>  OR rec_groups:<user_id>:pick:<group_id>
        parts = data.split(':')
        if len(parts) < 3:
            await callback.answer()
            return
        try:
            target_user_id = int(parts[1])
        except Exception:
            await callback.answer()
            return

        action = parts[2]
        if action == 'page':
            try:
                page = int(parts[3])
            except Exception:
                page = 0
        else:
            page = 0

        target = get_user_by_id(target_user_id)
        if not target:
            await callback.message.answer(t(lang, "user_not_found"))
            await callback.answer()
            return

        groups = get_all_groups()
        subj = (target.get('subject') or '').title()
        lvl = (target.get('level') or '').upper()
        # Filter by subject then (best-effort) by level
        subject_groups = [g for g in groups if (g.get('subject') or '').title() == subj] if subj else list(groups)
        lvl_groups = [g for g in subject_groups if (g.get('level') or '').upper() == lvl] if lvl else subject_groups
        rec = lvl_groups or subject_groups

        if action == 'pick':
            try:
                group_id = int(parts[3])
            except Exception:
                await callback.answer()
                return
            group = get_group(group_id)
            if not group:
                await callback.message.answer(t(lang, "group_not_found"))
                await callback.answer()
                return
            add_user_to_group(target_user_id, group_id)
            teacher = get_user_by_id(group.get('teacher_id')) if group.get('teacher_id') else None
            teacher_name = f"{teacher.get('first_name','')} {teacher.get('last_name','')}".strip() if teacher else "-"
            await callback.message.answer(
                f"✅ O‘quvchi guruhga biriktirildi.\n"
                f"👤 {target.get('first_name')} {target.get('last_name')} ({target.get('login_id')})\n"
                f"👥 Guruh: {group.get('name')} | {group.get('level')}\n"
                f"👨‍🏫 Teacher: {teacher_name}\n"
                f"⏰ Dars: {(group.get('lesson_date') or '-') } | {(group.get('lesson_start') or '-')[:5]}-{(group.get('lesson_end') or '-')[:5]}"
            )

            # Notify student about schedule if they are connected to bot
            try:
                if student_notify_bot and target.get('telegram_id'):
                    # Get proper day label for lesson_date
                    raw_date = (group.get('lesson_date') or '-').strip().upper()
                    if raw_date in ('MWF', 'MON/WED/FRI', 'MON,WED,FRI'):
                        date_label = 'Mon, Wed, Fri'
                    elif raw_date in ('TTS', 'TUE/THU/SAT', 'TUE,THU,SAT'):
                        date_label = 'Tue, Thu, Sat'
                    else:
                        date_label = raw_date
                    
                    await student_notify_bot.send_message(
                        int(target['telegram_id']),
                        f"✅ Siz guruhga biriktirildingiz: {group.get('name')}\n"
                        f"🎓 Level: {group.get('level')}\n"
                        f"👨‍🏫 Teacher: {teacher_name}\n"
                        f"📅 Dars kunlari: {date_label}\n"
                        f"⏰ Vaqt: {(group.get('lesson_start') or '-')[:5]}-{(group.get('lesson_end') or '-')[:5]} (Toshkent)"
                    )
            except Exception:
                logger.exception("Failed to notify student about group assignment")

            # Ask admin to approve access (yes/no)
            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text=t(lang, "btn_yes"), callback_data=f"approve_access_yes:{target_user_id}"),
                InlineKeyboardButton(text=t(lang, "btn_no"), callback_data=f"approve_access_no:{target_user_id}"),
            ]])
            await callback.message.answer(t(lang, "approve_access_prompt"), reply_markup=kb)
            await callback.answer()
            return

        # Render recommendation list page
        lang = detect_lang_from_user(callback.from_user)
        if not rec:
            await callback.message.answer(t(lang, "no_results_found"))
            await callback.answer()
            return
        rec = list(reversed(rec))
        page_size = 10
        total_pages = (len(rec) - 1) // page_size + 1
        page = max(0, min(page, total_pages - 1))
        page_groups = _groups_page(rec, page, page_size)

        out = []
        out.append("📌 Recommendation guruhlar")
        out.append(f"👤 {target.get('first_name')} {target.get('last_name')} | {subj} | {lvl}")
        out.append(f"(Sahifa {page+1}/{total_pages})\n")
        for idx, g in enumerate(page_groups, start=1):
            teacher = get_user_by_id(g.get('teacher_id')) if g.get('teacher_id') else None
            teacher_name = f"{teacher.get('first_name','')} {teacher.get('last_name','')}".strip() if teacher else "-"
            students = get_group_users(g['id'])
            raw_date = (g.get('lesson_date') or '-').strip().upper()
            if raw_date in ('MWF', 'MON/WED/FRI', 'MON,WED,FRI'):
                date_label = 'Mon, Wed, Fri'
            elif raw_date in ('TTS', 'TUE/THU/SAT', 'TUE,THU,SAT'):
                date_label = 'Tue, Thu, Sat'
            else:
                date_label = raw_date or '-'
            start = (g.get("lesson_start") or "-")[:5]
            end = (g.get("lesson_end") or "-")[:5]
            out.append(
                f"{idx}. Fan: {(g.get('subject') or g.get('level') or '-')}\n"
                f"   Nomi: {g.get('name') or '-'}\n"
                f"   Level: {g.get('level') or '-'}\n"
                f"   Dars: {date_label} | {start}-{end}"
            )
            out.append(f"   Teacher: {teacher_name}")
            out.append(f"   O‘quvchilar: {len(students)}\n")

        kb = _group_list_keyboard(page_groups, page, total_pages, base=f"rec_groups:{target_user_id}", lang=lang)
        await callback.message.answer("\n".join(out), reply_markup=kb)
        await callback.answer()
        return

    if data.startswith('approve_access_yes:'):
        try:
            user_id = int(data.split(':')[-1])
        except Exception:
            await callback.answer()
            return
        
        enable_access(user_id)
        set_pending_approval(user_id, False)
        await callback.message.answer(t(lang, "full_access_granted"))
        await callback.answer()
        return

    if data.startswith('approve_access_no:'):
        try:
            user_id = int(data.split(':')[-1])
        except Exception:
            await callback.answer()
            return
        await callback.message.answer(t(lang, "access_not_granted"))
        await callback.answer()
        return

    # Attach an existing (type2) student to a group during creation
    if data.startswith('assign_new:'):
        parts = data.split(':')
        if len(parts) < 3:
            await callback.answer()
            return
        try:
            target_user_id = int(parts[1])
        except Exception:
            await callback.answer()
            return
        action = parts[2]
        if action == 'page':
            try:
                page = int(parts[3])
            except Exception:
                page = 0
        else:
            page = 0

        target = get_user_by_id(target_user_id)
        if not target:
            await callback.message.answer(t(lang, "user_not_found"))
            await callback.answer()
            return

        groups = get_all_groups()
        subj = (target.get('subject') or '').title()
        subject_groups = [g for g in groups if (g.get('subject') or '').title() == subj] if subj else list(groups)
        pick_pool = subject_groups or groups

        if action == 'pick':
            try:
                group_id = int(parts[3])
            except Exception:
                await callback.answer()
                return
            group = get_group(group_id)
            if not group:
                await callback.message.answer(t(lang, "group_not_found"))
                await callback.answer()
                return
            add_user_to_group(target_user_id, group_id)
            await callback.message.answer(
                f"✅ O‘quvchi guruhga qo‘shildi: {group.get('name')} | {group.get('level')}\n"
                f"👤 {target.get('first_name')} {target.get('last_name')} ({target.get('login_id')})"
            )
            await callback.answer()
            return

        if not pick_pool:
            await callback.message.answer(t(lang, "group_not_found"))
            await callback.answer()
            return
        pick_pool = list(reversed(pick_pool))
        page_size = 10
        total_pages = (len(pick_pool) - 1) // page_size + 1
        page = max(0, min(page, total_pages - 1))
        page_groups = _groups_page(pick_pool, page, page_size)

        out = []
        out.append("👥 Guruh tanlang")
        out.append(f"👤 {target.get('first_name')} {target.get('last_name')} | {subj}")
        out.append(f"(Sahifa {page+1}/{total_pages})\n")
        for idx, g in enumerate(page_groups, start=1):
            teacher = get_user_by_id(g.get('teacher_id')) if g.get('teacher_id') else None
            teacher_name = f"{teacher.get('first_name','')} {teacher.get('last_name','')}".strip() if teacher else "-"
            students = get_group_users(g['id'])
            out.append(_format_group_line(idx, g).rstrip())
            out.append(f"   Teacher: {teacher_name}")
            out.append(f"   O‘quvchilar: {len(students)}\n")

        kb = _group_list_keyboard(page_groups, page, total_pages, base=f"assign_new:{target_user_id}", lang=lang)
        await callback.message.answer("\n".join(out), reply_markup=kb)
        await callback.answer()
        return

    # Group settings
    if data.startswith('grp_set:'):
        parts = data.split(':')
        if len(parts) < 3:
            await callback.answer()
            return
        try:
            group_id = int(parts[1])
        except Exception:
            await callback.answer()
            return
        action = parts[2]
        state = get_admin_state(callback.message.chat.id)
        state['data']['edit_group_id'] = group_id

        if action == 'name':
            state['step'] = 'edit_group_name'
            await callback.message.answer(t(lang, "new_group_name_prompt"))
            await callback.answer()
            return

        if action == 'level':
            state['step'] = 'edit_group_level'
            await callback.message.answer(t(lang, "ask_group_level"))
            await callback.answer()
            return

        if action == 'time':
            state['step'] = 'edit_group_days'
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=t(lang, "odd_days_btn"), callback_data="edit_group_days:odd")],
                [InlineKeyboardButton(text=t(lang, "even_days_btn"), callback_data="edit_group_days:even")],
            ])
            await callback.message.answer(t(lang, "ask_group_days"), reply_markup=kb)
            await callback.answer()
            return

        if action == 'teacher':
            state['step'] = 'edit_group_teacher'
            teachers = get_all_teachers()
            if not teachers:
                await callback.message.answer(t(lang, "teachers_not_found"))
                await callback.answer()
                return
            await callback.message.answer(t(lang, "choose_teacher"), reply_markup=create_teacher_selection_keyboard(teachers))
            await callback.answer()
            return

        if action == 'add_student':
            state['step'] = None
            # show available students not in group
            all_users = [u for u in get_all_users() if u.get('login_type') in (1, 2)]
            group_users = get_group_users(group_id)
            group_user_ids = {u['id'] for u in group_users}
            available = [u for u in all_users if u['id'] not in group_user_ids]
            if not available:
                await callback.message.answer(t(lang, "no_available_students"))
                await callback.answer()
                return
            await callback.message.answer(t(lang, "choose_student_add"), reply_markup=create_user_selection_keyboard_by_type(available, group_id))
            await callback.answer()
            return

        if action == 'remove_student':
            users = get_group_users(group_id)
            if not users:
                await callback.message.answer(t(lang, "no_students_in_group"))
                await callback.answer()
                return
            rows = []
            for u in users[:50]:
                rows.append([InlineKeyboardButton(text=f"{u.get('first_name','')} {u.get('last_name','')}", callback_data=f"grp_remove:{group_id}:{u['id']}")])
            await callback.message.answer(t(lang, "choose_student_remove"), reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
            await callback.answer()
            return

        if action == 'delete':
            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text=t(lang, "btn_yes"), callback_data=f"grp_delete_yes:{group_id}"),
                InlineKeyboardButton(text=t(lang, "btn_no"), callback_data=f"grp_delete_no:{group_id}"),
            ]])
            await callback.message.answer(t(lang, "confirm_delete_group"), reply_markup=kb)
            await callback.answer()
            return

    if data.startswith('grp_remove:'):
        parts = data.split(':')
        try:
            group_id = int(parts[1])
            user_id = int(parts[2])
        except Exception:
            await callback.answer()
            return
        remove_user_from_group(user_id, group_id)
        await callback.message.answer(t(lang, "student_removed_from_group"))
        await callback.answer()
        return

    if data.startswith('grp_delete_yes:'):
        try:
            group_id = int(data.split(':')[-1])
        except Exception:
            await callback.answer()
            return
        delete_group(group_id)
        await callback.message.answer(t(lang, "group_deleted"))
        await callback.answer()
        return

    if data.startswith('grp_delete_no:'):
        await callback.answer()
        return

    if data.startswith('add_user_to_group_'):
        parts = data.split('_')
        group_id = int(parts[-2])
        user_id = int(parts[-1])
        
        add_user_to_group(user_id, group_id)
        user = get_user_by_id(user_id)
        group = get_group(group_id)
        lang = detect_lang_from_user(callback.from_user)
        await callback.message.answer(t(lang, 'user_added_to_group', first=user['first_name'], last=user['last_name'], group=group['name']))
        await callback.answer()
        return

    # Group subject selection when teacher has "Both"
    if data.startswith('group_subj_'):
        state = get_admin_state(callback.message.chat.id)
        if state.get('step') != 'select_subject_for_group':
            await callback.answer()
            return
        subject = data.split('_', 2)[-1].title()
        if subject not in ('English', 'Russian'):
            await callback.answer()
            return
        group_name = state['data'].get('group_name')
        group_level = state['data'].get('group_level')
        lesson_date = state['data'].get('lesson_date')
        lesson_start = state['data'].get('lesson_start')
        lesson_end = state['data'].get('lesson_end')
        teacher_id = state['data'].get('teacher_id')
        
        # Debug log before validation
        logger.info(f"Group creation validation - name={group_name}, level={group_level}, date={lesson_date}, start={lesson_start}, end={lesson_end}, teacher={teacher_id}")
        
        if not (group_name and group_level and lesson_date and lesson_start and lesson_end and teacher_id):
            logger.error(f"Group creation failed - missing data: name={bool(group_name)}, level={bool(group_level)}, date={bool(lesson_date)}, start={bool(lesson_start)}, end={bool(lesson_end)}, teacher={bool(teacher_id)}")
            await callback.answer()
            reset_admin_state(callback.message.chat.id)
            return
        create_group(
            group_name,
            int(teacher_id),
            group_level,
            subject=subject,
            lesson_date=lesson_date,
            lesson_start=lesson_start,
            lesson_end=lesson_end,
            tz='Asia/Tashkent',
        )
        lang = detect_lang_from_user(callback.from_user)
        if lesson_date.upper() in ('MWF', 'MON/WED/FRI', 'MON,WED,FRI'):
            date_label = 'Mon, Wed, Fri'
        elif lesson_date.upper() in ('TTS', 'TUE/THU/SAT', 'TUE,THU,SAT'):
            date_label = 'Tue, Thu, Sat'
        else:
            date_label = lesson_date or '-'
        await callback.message.answer(
            t(lang, 'group_created', name=group_name, level=group_level) + f"\n🗓 {date_label} ⏰ {lesson_start}-{lesson_end} (Toshkent)"
        )
        reset_admin_state(callback.message.chat.id)
        await callback.answer()
        return

        # Check for teacher conflicts
        if _teacher_conflicts(teacher_id, lesson_date, lesson_start, lesson_end):
            await callback.message.answer('❌ Ushbu o\'qituvchida shu vaqtda boshqa guruh darsi bor. Amal bekor qilindi.')
            reset_admin_state(callback.message.chat.id)
            await callback.answer()
            return
        
        # Create the group
        subject = (teacher.get('subject') or '').title()
        group_id = create_group(
            group_name,
            teacher_id,
            group_level,
            subject=subject,
            lesson_date=lesson_date,
            lesson_start=lesson_start,
            lesson_end=lesson_end,
            tz='Asia/Tashkent'
        )
        
        # Show success message
        lang = detect_lang_from_user(callback.from_user)
        if lesson_date.upper() in ('MWF', 'MON/WED/FRI', 'MON,WED,FRI'):
            date_label = 'Mon, Wed, Fri'
        elif lesson_date.upper() in ('TTS', 'TUE/THU/SAT', 'TUE,THU,SAT'):
            date_label = 'Tue, Thu, Sat'
        else:
            date_label = lesson_date or '-'
        
        await callback.message.answer(
            t(lang, 'group_created', name=group_name, level=group_level) + f"\n🗓 {date_label} ⏰ {lesson_start}-{lesson_end} (Toshkent)\n👨‍🏫 {teacher['first_name']} {teacher['last_name']}"
        )
        reset_admin_state(callback.message.chat.id)
        await callback.answer()
        return

    # Handle "Create group without teacher" option
    if data == 'create_group_no_teacher' and state.get('step') == 'ask_teacher_for_group':
        # Create group without teacher
        await create_group_from_state(callback.message, state)
        await callback.answer()
        return

    if data.startswith('grp_remove:'):
        parts = data.split(':')
        try:
            group_id = int(parts[1])
            user_id = int(parts[2])
        except Exception:
            await callback.answer()
            return
        remove_user_from_group(user_id, group_id)
        await callback.message.answer(t(lang, "student_removed_from_group"))
        await callback.answer()
        return

    if data.startswith('grp_delete_yes:'):
        try:
            group_id = int(data.split(':')[-1])
        except Exception:
            await callback.answer()
            return
        delete_group(group_id)
        await callback.message.answer(t(lang, "group_deleted"))
        await callback.answer()
        return

    if data.startswith('grp_delete_no:'):
        await callback.answer()
        return

    if data.startswith('add_user_to_group_'):
        parts = data.split('_')
        group_id = int(parts[-2])
        user_id = int(parts[-1])
        
        add_user_to_group(user_id, group_id)
        user = get_user_by_id(user_id)
        group = get_group(group_id)
        lang = detect_lang_from_user(callback.from_user)
        await callback.message.answer(t(lang, 'user_added_to_group', first=user['first_name'], last=user['last_name'], group=group['name']))
        await callback.answer()
        return

# Group subject selection is no longer needed since "Both" is removed

    if data.startswith('teacher_select_') and state.get('step') == 'edit_group_teacher':
        teacher_id = int(data.split('_')[-1])
        group_id = state['data'].get('edit_group_id')
        teacher = get_user_by_id(teacher_id)
        if not group_id or not teacher:
            await callback.answer()
            return
        update_group_teacher(int(group_id), teacher_id)
        subj = (teacher.get('subject') or '').title()
        if subj:
            update_group_subject(int(group_id), subj)
        await callback.message.answer(t(lang, "teacher_updated_simple"))
        reset_admin_state(callback.message.chat.id)
        await callback.answer()
        return

    if data.startswith('teacher_select_'):
        teacher_id = int(data.split('_')[-1])
        teacher = get_user_by_id(teacher_id)
        
        if not teacher:
            lang = detect_lang_from_user(callback.from_user)
            await callback.message.answer(t(lang, 'teacher_not_found'))
            await callback.answer()
            return
        
        if teacher.get('blocked'):
            status = f"🔒 {t(lang, 'status_blocked_short')}"
        elif is_access_active(teacher):
            status = f"✅ {t(lang, 'status_open_short')}"
        else:
            status = f"❌ {t(lang, 'status_closed_short')}"
        
        state = get_admin_state(callback.message.chat.id)
        state['selected_teacher'] = teacher
        
        await callback.message.answer(
            f"👨‍🏫 {teacher['first_name']} {teacher['last_name']}\n"
            f"🧩 {teacher['subject']} | 📱 {teacher.get('phone', '-')}\n"
            f"🔑 {teacher['login_id']}\n"
            f"📌 Status: {status}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=t(lang, 'btn_block'), callback_data=f'teacher_block_{teacher_id}')],
                [InlineKeyboardButton(text=t(lang, 'btn_unblock'), callback_data=f'teacher_unblock_{teacher_id}')],
                [InlineKeyboardButton(text=t(lang, 'btn_reset_pw'), callback_data=f'teacher_reset_{teacher_id}')],
                [InlineKeyboardButton(text=t(lang, 'btn_change_subject'), callback_data=f'teacher_change_sub_{teacher_id}')],
                [InlineKeyboardButton(text=t(lang, 'btn_edit_info'), callback_data=f'teacher_edit_{teacher_id}')],
            [InlineKeyboardButton(text=t(lang, 'btn_change_lang'), callback_data=f'teacher_change_lang_{teacher_id}')],
                [InlineKeyboardButton(text=t(lang, 'btn_home_menu'), callback_data='back_to_menu')],
            ])
        )
        await callback.answer()
        return

    if data.startswith('subject_') and get_admin_state(callback.message.chat.id).get('step') == 'change_teacher_subject':
        subject = data.split('_', 1)[1]
        state = get_admin_state(callback.message.chat.id)
        teacher_id = state['data'].get('change_teacher_id')
        teacher = get_user_by_id(teacher_id)
        if not teacher:
            lang = detect_lang_from_user(callback.from_user)
            await callback.message.answer(t(lang, 'teacher_not_found'))
            await callback.answer()
            return
        update_user_subject(teacher_id, subject)
        lang = detect_lang_from_user(callback.from_user)
        await callback.message.answer(t(lang, 'teacher_updated', changes=f"Fan o'zgartirildi: {teacher['subject']} → {subject}"))
        state['step'] = None
        state['data'] = {}
        await callback.answer()
        return

    # Handle teacher block/unblock
    if data.startswith('teacher_block_'):
        teacher_id = int(data.split('_')[-1])
        teacher = get_user_by_id(teacher_id)
        if not teacher:
            lang = detect_lang_from_user(callback.from_user)
            await callback.message.answer(t(lang, 'teacher_not_found'))
            await callback.answer()
            return
        
        from db import block_user
        block_user(teacher_id)
        lang = detect_lang_from_user(callback.from_user)
        await callback.message.answer(f"🚫 O'qituvchi bloklandi: {teacher['first_name']} {teacher['last_name']}")
        await callback.answer()
        return

    if data.startswith('teacher_unblock_'):
        teacher_id = int(data.split('_')[-1])
        teacher = get_user_by_id(teacher_id)
        if not teacher:
            lang = detect_lang_from_user(callback.from_user)
            await callback.message.answer(t(lang, 'teacher_not_found'))
            await callback.answer()
            return
        
        from db import unblock_user
        unblock_user(teacher_id)
        lang = detect_lang_from_user(callback.from_user)
        await callback.message.answer(f"✅ O'qituvchi blokdan olindi: {teacher['first_name']} {teacher['last_name']}")
        await callback.answer()
        return

    if data.startswith('teacher_reset_'):
        teacher_id = int(data.split('_')[-1])
        teacher = get_user_by_id(teacher_id)
        if not teacher:
            lang = detect_lang_from_user(callback.from_user)
            await callback.message.answer(t(lang, 'teacher_not_found'))
            await callback.answer()
            return
        
        from db import reset_user_password
        import random
        import string
        
        # Generate random password
        new_password = ''.join(random.choices(string.digits, k=6))
        reset_user_password(teacher_id, new_password)
        
        lang = detect_lang_from_user(callback.from_user)
        await callback.message.answer(f"🔑 O'qituvchi uchun yangi parol: <code>{new_password}</code>", parse_mode='HTML')
        await callback.answer()
        return

    # Start language change flow for a user
    if data.startswith('user_change_lang_'):
        user_id = int(data.split('_')[-1])
        keyboard = create_language_selection_keyboard_for_user(user_id)
        await callback.message.answer(t(lang, 'select_language_prompt'), reply_markup=keyboard)
        await callback.answer()
        return

    if data.startswith('teacher_change_lang_'):
        teacher_id = int(data.split('_')[-1])
        keyboard = create_language_selection_keyboard_for_user(teacher_id)
        await callback.message.answer(t(lang, 'select_language_prompt'), reply_markup=keyboard)
        await callback.answer()
        return

    # Admin selecting their own language via inline keyboard (callbacks like set_lang_me_uz)
    # (moved to a dedicated filtered handler at file end to avoid swallowing callbacks)

    # Set language for specified user id (do not match set_lang_me_)
    if data.startswith('set_lang_') and not data.startswith('set_lang_me_'):
        parts = data.split('_')
        if len(parts) >= 3:
            lang_code = parts[2]
            try:
                target_id = int(parts[3])
            except Exception:
                await callback.answer(t(lang, 'err_invalid_format'))
                return
            update_user_language(target_id, lang_code)
            await callback.message.answer(f"Foydalanuvchi tili {lang_code} ga o'zgartirildi.")
            await callback.answer()
            return

    if data.startswith('test_'):
        subject = data.split('_', 1)[1]
        state = get_admin_state(callback.message.chat.id)
        user_id = state['data'].get('test_user_id')
        user = get_user_by_id(user_id)
        if not user:
            await callback.message.answer(t(lang, 'user_not_found'))
            await callback.answer()
            return

        prepare_user_for_new_test(user_id, subject)
        student_chat_id = user.get('telegram_id')
        if not student_chat_id:
            lang = detect_lang_from_user(callback.from_user)
            await callback.message.answer(t(lang, 'user_no_telegram'))
            state['step'] = None
            state['data'] = {}
            await callback.answer()
            return

        try:
            student_chat_id_int = int(student_chat_id)
        except Exception:
            lang = detect_lang_from_user(callback.from_user)
            await callback.message.answer(t(lang, 'invalid_telegram_id_format'))
            state['step'] = None
            state['data'] = {}
            await callback.answer()
            return

        if student_chat_id_int in ADMIN_CHAT_IDS:
            lang = detect_lang_from_user(callback.from_user)
            await callback.message.answer(t(lang, 'telegram_id_conflicts_admin'))
            state['step'] = None
            state['data'] = {}
            await callback.answer()
            return

        # Send localized notification to the student (use student's preferred language)
        student_lang = detect_lang_from_user(user)
        await bot.send_message(
            student_chat_id_int,
            t(student_lang, 'you_have_new_test', subject=subject),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t(student_lang, 'btn_start_test'), callback_data='start_test')]]),
        )
        lang = detect_lang_from_user(callback.from_user)
        await callback.message.answer(t(lang, 'test_sent_to_user'))

        state['step'] = None
        state['data'] = {}
        await callback.answer()
        return

@dp.callback_query(lambda c: c.data == "payment_export_history")
async def handle_payment_export_history(callback: CallbackQuery):
    """Handle payment history export request"""
    from payment import export_payment_history_to_xlsx, cleanup_old_payment_history
    
    try:
        # Clean up old records first
        deleted_count = cleanup_old_payment_history()
        
        # Export payment history
        file_data, filename = export_payment_history_to_xlsx()
        await callback.bot.send_document(
            callback.message.chat.id,
            BufferedInputFile(file_data.getvalue(), filename)
        )
        
        message = t(lang, 'export_success', type="To'lov")
        if deleted_count > 0:
            message += "\n\n" + t(lang, 'export_cleanup', count=deleted_count)
        
        await callback.answer(message)
    except Exception as e:
        logger.exception("Failed to export payment history")
        await callback.answer(t(lang, 'export_error'))


@dp.callback_query(lambda c: c.data == "admin_export_attendance")
async def handle_admin_export_attendance(callback: CallbackQuery):
    from vocabulary import export_all_attendance_to_xlsx

    try:
        file_data, filename = export_all_attendance_to_xlsx()
        await callback.bot.send_document(
            callback.message.chat.id,
            BufferedInputFile(file_data.getvalue(), filename)
        )
        await callback.answer("Davomat tarixi yuklandi")
    except Exception as e:
        logger.exception("Failed to export attendance")
        await callback.answer("Xatolik yuz berdi")


# Agar callback handler'da match bo'lmasa, asosiy menyuga qayt tugmasini ko'rsatadi
    lang = detect_lang_from_user(callback.from_user)
    await callback.answer()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, 'btn_home_admin'), callback_data='back_to_menu')]
    ])
    await callback.message.answer(t(lang, 'action_not_allowed'), reply_markup=keyboard)


async def show_group_menu(message: Message):
    lang = detect_lang_from_user(message.from_user)
    kb = create_group_action_keyboard(lang)          # utils.py dagi funksiya
    await message.answer(t(lang, 'group_mgmt'), reply_markup=kb)


async def _show_group_list(callback: CallbackQuery, page: int = 0):
    """Show group list with pagination using group_list: callback pattern"""
    groups = get_all_groups()
    if not groups:
        await callback.message.edit_text('Hech qanday guruh mavjud emas.')
        await callback.answer()
        return

    per_page = 10
    total = len(groups)
    start = page * per_page
    chunk = groups[start:start + per_page]
    total_pages = (total - 1) // per_page + 1 if total else 1

    text = f"👥 **Guruhlar ro'yxati** — sahifa {page+1}/{total_pages}\n\n"
    for i, g in enumerate(chunk, start=1):
        teacher = get_user_by_id(g.get("teacher_id")) if g.get("teacher_id") else None
        t_name = f"{teacher.get('first_name','')} {teacher.get('last_name','')}".strip() if teacher else "—"
        text += (f"{i}. {g['name']} ({g.get('level','—')})\n"
                 f"   👨‍🏫 {t_name} | ⏰ {g.get('lesson_start','—')[:5]}-{g.get('lesson_end','—')[:5]}\n\n")

    # Create keyboard with group_list: pattern
    keyboard = _group_list_keyboard(chunk, page, total_pages, "group_list", detect_lang_from_user(callback.from_user))
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


async def _send_group_list(message: Message, state: dict):
    groups = state['groups']
    page = state.get('groups_page', 0)
    per_page = 10
    total = len(groups)
    start = page * per_page
    chunk = groups[start:start + per_page]

    total_pages = (total - 1) // per_page + 1 if total else 1

    text = f"👥 **Guruhlar ro'yxati** — sahifa {page+1}/{total_pages}\n\n"
    for i, g in enumerate(chunk, start=1):
        teacher = get_user_by_id(g.get("teacher_id")) if g.get("teacher_id") else None
        t_name = f"{teacher.get('first_name','')} {teacher.get('last_name','')}".strip() if teacher else "—"
        text += (f"{i}. {g['name']} ({g.get('level','—')})\n"
                 f"   👨‍🏫 {t_name} | ⏰ {g.get('lesson_start','—')[:5]}-{g.get('lesson_end','—')[:5]}\n\n")

    # Numbered buttons 1-10
    buttons = []
    row = []
    for i in range(len(chunk)):
        row.append(InlineKeyboardButton(
            text=str(i+1),
            callback_data=f"group_select_{chunk[i]['id']}"
        ))
        if len(row) == 5:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    # Pagination
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data="groups_prev"))
    if start + per_page < total:
        nav.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data="groups_next"))
    if nav:
        buttons.append(nav)

    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@dp.callback_query(lambda c: c.data in ("groups_next", "groups_prev"))
async def handle_groups_pagination(callback: CallbackQuery):
    state = get_admin_state(callback.message.chat.id)
    if callback.data == "groups_next":
        state['groups_page'] = state.get('groups_page', 0) + 1
    else:
        state['groups_page'] = max(0, state.get('groups_page', 0) - 1)
    await _send_group_list(callback.message, state)
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("group_select_"))
async def handle_group_select(callback: CallbackQuery):
    group_id = int(callback.data.split("_")[-1])
    group = get_group(group_id)
    if not group:
        await callback.answer("Guruh topilmadi!")
        return

    state = get_admin_state(callback.message.chat.id)
    state["current_group_id"] = group_id

    teacher = get_user_by_id(group.get("teacher_id")) if group.get("teacher_id") else None
    t_name = f"{teacher.get('first_name','')} {teacher.get('last_name','')}".strip() if teacher else "—"

    students_count = len(get_group_users(group_id))

    text = (
        f"📚 **{group['name']}**\n\n"
        f"Fan: {group.get('subject','—')}\n"
        f"Daraja: {group.get('level','—')}\n"
        f"O'qituvchi: {t_name}\n"
        f"Dars: {group.get('lesson_date','—')} | {group.get('lesson_start','—')[:5]}-{group.get('lesson_end','—')[:5]}\n"
        f"O'quvchilar: {students_count} ta"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👨‍🏫 O'qituvchini almashtirish", callback_data=f"group_edit_teacher_{group_id}")],
        [InlineKeyboardButton(text="➕ Yangi o'quvchi qo'shish",     callback_data=f"group_add_student_{group_id}")],
        [InlineKeyboardButton(text="➖ O'quvchini chiqarib yuborish", callback_data=f"group_remove_student_{group_id}")],
        [InlineKeyboardButton(text="✏️ Nomi o'zgartirish",          callback_data=f"group_edit_name_{group_id}")],
        [InlineKeyboardButton(text="🎯 Daraja o'zgartirish",         callback_data=f"group_edit_level_{group_id}")],
        [InlineKeyboardButton(text="🗑 Guruhni o'chirish",           callback_data=f"group_delete_confirm_{group_id}")],
        [InlineKeyboardButton(text="🔙 Ro'yxatga qaytish",           callback_data="group_list")],
    ])

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


async def show_payment_menu(message: Message):
    lang = detect_lang_from_user(message.from_user)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "payments_search_login"), callback_data="pay_search:login")],
        [InlineKeyboardButton(text=t(lang, "payments_search_name"), callback_data="pay_search:name")],
        [InlineKeyboardButton(text="📥 To'lov tarixi (Excel)", callback_data="payment_export_history")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back_to_main")],
    ])
    await message.answer(t(lang, "payments_menu_title"), reply_markup=kb)


async def _render_payment_search_results(update, mode: str, query: str, page: int):
    """
    update can be Message or CallbackQuery.
    mode: 'login' or 'name'
    query: for name mode, spaces are encoded as underscore
    """
    if isinstance(update, CallbackQuery):
        send = update.message.answer
        from_user = update.from_user
    else:
        send = update.answer
        from_user = update.from_user

    lang = detect_lang_from_user(from_user)
    users = [u for u in get_all_users() if u.get('login_type') in (1, 2)]

    matches = []
    if mode == 'login':
        q = (query or '').strip().upper()
        matches = [u for u in users if (u.get('login_id') or '').strip().upper() == q]
        # Ensure only student/parent accounts are considered for login searches
        matches = [u for u in matches if u.get('login_type') in (1, 2)]
    else:
        q = (query or '').replace('_', ' ').strip().lower()
        for u in users:
            fn = (u.get('first_name') or '').lower()
            ln = (u.get('last_name') or '').lower()
            full = (fn + ' ' + ln).strip()
            if q and (q in fn or q in ln or q in full):
                matches.append(u)

    if not matches:
        await send("Natija topilmadi.")
        return

    # newest first
    matches = list(reversed(matches))
    page_size = 10
    total_pages = (len(matches) - 1) // page_size + 1
    page = max(0, min(page, total_pages - 1))
    start = page * page_size
    page_users = matches[start:start + page_size]

    import pytz
    ym = datetime.now(pytz.timezone("Asia/Tashkent")).strftime("%Y-%m")
    out = []
    out.append("💳 To‘lov qidiruv natijalari")
    out.append(f"(Sahifa {page+1}/{total_pages})\n")

    for idx, u in enumerate(page_users, start=1):
        group = get_group(u.get('group_id')) if u.get('group_id') else None
        teacher = get_user_by_id(group.get('teacher_id')) if group and group.get('teacher_id') else None
        teacher_name = f"{teacher.get('first_name','')} {teacher.get('last_name','')}".strip() if teacher else "-"
        subject = (u.get('subject') or '-').title()
        gname = group.get('name') if group else "-"
        lvl = (u.get('level') or (group.get('level') if group else None) or '-')
        start_t = (group.get('lesson_start') if group else '-') or '-'
        end_t = (group.get('lesson_end') if group else '-') or '-'
        raw_date = (group.get('lesson_date') if group else '-') or '-'
        raw_date = raw_date.strip().upper()
        if raw_date in ('MWF', 'MON/WED/FRI', 'MON,WED,FRI'):
            date = 'Mon, Wed, Fri'
        elif raw_date in ('TTS', 'TUE/THU/SAT', 'TUE,THU,SAT'):
            date = 'Tue, Thu, Sat'
        else:
            date = raw_date
        groups = get_user_groups(u['id'])
        out.append(f"{idx}. {u.get('first_name','-')} {u.get('last_name','-')}\n   Fan: {subject}\n   Guruhlar:\n")
        for g in groups:
            teacher = get_user_by_id(g.get('teacher_id')) if g and g.get('teacher_id') else None
            teacher_name = f"{teacher.get('first_name','')} {teacher.get('last_name','')}".strip() if teacher else "-"
            raw_date = (g.get('lesson_date') or '-').strip().upper()
            if raw_date in ('MWF', 'MON/WED/FRI', 'MON,WED,FRI'):
                date = 'Mon, Wed, Fri'
            elif raw_date in ('TTS', 'TUE/THU/SAT', 'TUE,THU,SAT'):
                date = 'Tue, Thu, Sat'
            else:
                date = raw_date
            paid = is_month_paid(u['id'], ym=ym, group_id=g['id'])
            mark = '✅' if paid else '❌'
            out.append(
                f"   - {g.get('name','-')} | {g.get('subject','-')} | {date} | {g.get('lesson_start','-')[:5]}-{g.get('lesson_end','-')[:5]} | {teacher_name} | {mark}"
            )

    base = f"pay_list:{mode}:{query}"
    kb = _student_list_keyboard(page_users, page, total_pages, base=base, lang=lang)
    await send("\n".join(out), reply_markup=kb)


async def _show_student_payment_card(callback: CallbackQuery, user_id: int):
    u = get_user_by_id(user_id)
    if not u:
        await callback.message.answer(t('uz', "user_not_found"))
        await callback.answer()
        return
    import pytz
    ym = datetime.now(pytz.timezone("Asia/Tashkent")).strftime("%Y-%m")
    lang = detect_lang_from_user(callback.from_user)
    groups = get_user_groups(user_id)

    lines = [
        f"👤 {u.get('first_name','-')} {u.get('last_name','-')}",
        f"🆔 Login ID: {u.get('login_id') or '-'}",
        f"📞 Telefon: {u.get('phone') or '-'}",
        f"🎓 Level: {u.get('level') or '-'}",
        f"📚 Fan(lar): {((u.get('subject') or '').title() or '-') if u.get('subject') else '-'}",
        f"🕒 Oy: {ym}",
        "",
    ]

    kb_rows = []
    if groups:
        for g in groups:
            teacher = get_user_by_id(g.get('teacher_id')) if g.get('teacher_id') else None
            teacher_name = f"{teacher.get('first_name','')} {teacher.get('last_name','')}".strip() if teacher else "-"
            raw_date = (g.get('lesson_date') or '-').strip().upper()
            if raw_date in ('MWF', 'MON/WED/FRI', 'MON,WED,FRI'):
                date = 'Mon, Wed, Fri'
            elif raw_date in ('TTS', 'TUE/THU/SAT', 'TUE,THU,SAT'):
                date = 'Tue, Thu, Sat'
            else:
                date = raw_date
            start_t = (g.get('lesson_start') or '-')[:5]
            end_t = (g.get('lesson_end') or '-')[:5]
            paid = is_month_paid(user_id, ym=ym, group_id=g['id'])
            mark = '✅' if paid else '❌'
            lines.append(f"👥 {g.get('name','-')} | {g.get('subject','-')} | {date} {start_t}-{end_t} | {mark}")
            kb_rows.append([
                InlineKeyboardButton(text=f"✅ {g.get('name')}", callback_data=f"pay_set:{user_id}:{g['id']}:paid"),
                InlineKeyboardButton(text=f"❌ {g.get('name')}", callback_data=f"pay_set:{user_id}:{g['id']}:unpaid"),
            ])
    else:
        lines.append("Bu o‘quvchi biror guruhga qo‘shilmagan.")

    await callback.message.answer("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows or [[InlineKeyboardButton(text=t(lang, 'btn_back'), callback_data='back_to_menu')]]))
    await callback.answer()


async def show_teachers_list(message: Message):
    teachers = get_all_teachers()
    if not teachers:
        await message.answer("❌ Hech qanday o'qituvchi topilmadi.")
        return

    text = "👨‍🏫 **O'qituvchilar ro'yxati**\n\n"
    keyboard = []

    for t in teachers:
        name = f"{t.get('first_name','')} {t.get('last_name','')}".strip() or "Noma'lum"
        text += f"• {name} | {t.get('login_id','—')} | {t.get('subject','—')}\n"
        
        keyboard.append([
            InlineKeyboardButton(
                text=f"👤 {name}", 
                callback_data=f"teacher_detail_{t['id']}"   # ← Eng muhim qator
            )
        ])

    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")


async def send_teachers_list(chat_id: int, message: Message, state: dict):
    teachers = state.get('teachers', [])
    page = state.get('teachers_page', 0)
    per_page = 10
    total = len(teachers)
    start = page * per_page
    end = start + per_page
    if start >= total:
        state['teachers_page'] = 0
        start = 0
        end = per_page
    chunk = teachers[start:end]

    total_pages = (total - 1) // per_page + 1 if total else 1
    text = f"👨‍🏫 O'qituvchilar ro'yxati — sahifa {page+1}/{total_pages}\n\n"
    
    for i, teacher in enumerate(chunk, start=1):
        if teacher.get('blocked'):
            status = '🔒'
        elif is_access_active(teacher):
            status = '✅'
        else:
            status = '❌'

        # Get teacher's groups
        from db import get_groups_by_teacher
        teacher_groups = get_groups_by_teacher(teacher['id'])
        group_count = len(teacher_groups)
        
        # Get total student count
        total_students = 0
        if teacher_groups:
            from db import get_group_users
            for group in teacher_groups:
                group_students = get_group_users(group['id'])
                total_students += len(group_students)

        line = (
            f"{i}. {teacher['subject']}\n"
            f"   {teacher['first_name']} {teacher['last_name']}\n"
            f"   🔑 {teacher['login_id']} | {status}\n"
            f"   📁 Guruhlar: {group_count} | 👥 O'quvchilar: {total_students}\n"
        )
        text += line + "\n"

    # Create number buttons (1-10)
    number_buttons = []
    for i in range(1, min(6, len(chunk) + 1)):
        number_buttons.append(InlineKeyboardButton(text=str(i), callback_data=f'teacher_detail_{chunk[i-1]["id"]}'))
    
    for i in range(6, min(11, len(chunk) + 1)):
        number_buttons.append(InlineKeyboardButton(text=str(i), callback_data=f'teacher_detail_{chunk[i-1]["id"]}'))
    
    # Split into two rows
    buttons = []
    if len(number_buttons) >= 5:
        buttons.append(number_buttons[:5])
        if len(number_buttons) > 5:
            buttons.append(number_buttons[5:])
    elif number_buttons:
        buttons.append(number_buttons)

    # Navigation buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Orqaga", callback_data='teachers_prev'))
    if end < total:
        nav_buttons.append(InlineKeyboardButton(text="➡️ Keyingi", callback_data='teachers_next'))
    
    if nav_buttons:
        buttons.append(nav_buttons)

    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(text, reply_markup=markup)


@dp.callback_query(lambda c: c.data in ('teachers_next', 'teachers_prev'))
async def handle_teachers_pagination(callback: CallbackQuery):
    state = get_admin_state(callback.message.chat.id)
    if callback.data == 'teachers_next':
        state['teachers_page'] = state.get('teachers_page', 0) + 1
    else:
        state['teachers_page'] = max(0, state.get('teachers_page', 0) - 1)
    
    await show_teachers_list(callback.message)
    await callback.answer()


@dp.callback_query(lambda c: c.data == "teachers_list")
async def handle_teachers_list_back(callback: CallbackQuery):
    """Handle back to teachers list"""
    await show_teachers_list(callback.message)
    await callback.answer()


# ==================== TEACHERS LIST TANLASH ====================
@dp.callback_query(lambda c: c.data.startswith('teacher_detail_'))
async def handle_teacher_detail(callback: CallbackQuery):
    teacher_id = int(callback.data.split('_')[-1])
    teacher = get_user_by_id(teacher_id)
    
    if not teacher:
        await callback.answer("❌ O'qituvchi topilmadi")
        return

    lang = detect_lang_from_user(callback.from_user)
    text = (
        f"👨‍🏫 **O'qituvchi ma'lumotlari**\n\n"
        f"Ism: {teacher['first_name']} {teacher['last_name']}\n"
        f"Login ID: {teacher['login_id']}\n"
        f"Telefon: {teacher.get('phone', '—')}\n"
        f"Fan: {teacher.get('subject', '—')}\n"
        f"Guruhlar soni: {get_teacher_groups_count(teacher_id)}\n"
        f"Jami o'quvchilar: {get_teacher_total_students(teacher_id)}"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Password Reset", callback_data=f"teacher_reset_{teacher_id}")],
        [InlineKeyboardButton(text="✏️ Tahrirlash", callback_data=f"teacher_edit_{teacher_id}")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="teachers_list_back")]
    ])

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer("✅ Ma'lumotlar ochildi")


@dp.callback_query(lambda c: c.data == "teachers_list_back")
async def handle_teachers_list_back(callback: CallbackQuery):
    await show_teachers_list(callback.message)
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("teacher_groups_"))
async def handle_teacher_groups(callback: CallbackQuery):
    """Show teacher's groups with details"""
    try:
        teacher_id = int(callback.data.split("_")[-1])
        teacher = get_user_by_id(teacher_id)
        
        if not teacher:
            await callback.answer("❌ O'qituvchi topilmadi")
            return
        
        from db import get_groups_by_teacher, get_group_users
        teacher_groups = get_groups_by_teacher(teacher_id)
        
        if not teacher_groups:
            text = f"👨‍🏫 **{teacher['first_name']} {teacher['last_name']}**\n\n"
            text += "📚 Guruhlari: Yo'q"
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"teacher_detail_{teacher_id}")]
            ])
        else:
            text = f"👨‍🏫 **{teacher['first_name']} {teacher['last_name']}**\n\n"
            text += "**Guruhlari:**\n\n"
            
            for i, group in enumerate(teacher_groups, start=1):
                students = get_group_users(group['id'])
                student_count = len(students)
                
                # Format lesson time
                lesson_time = "—"
                if group.get('lesson_start') and group.get('lesson_end'):
                    lesson_time = f"{group['lesson_start'][:5]}-{group['lesson_end'][:5]}"
                
                # Format lesson days
                lesson_days = group.get('lesson_date', '—')
                if lesson_days == 'MWF':
                    lesson_days = 'Du, Cho, Jum'
                elif lesson_days == 'TTS':
                    lesson_days = 'Sesh, Pay, Shan'
                
                text += f"{i}. 📚 **{group.get('name', 'Noma\'lum')}**\n"
                text += f"   🎓 Level: {group.get('level', '—')}\n"
                text += f"   📅 Dars kunlari: {lesson_days}\n"
                text += f"   🕒 Vaqti: {lesson_time}\n"
                text += f"   👥 O'quvchilar: {student_count} ta\n\n"
            
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"teacher_detail_{teacher_id}")]
            ])
        
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in teacher_groups handler: {e}")
        await callback.answer("❌ Xatolik yuz berdi")


@dp.callback_query(lambda c: c.data.startswith("teacher_edit_"))
async def handle_teacher_edit(callback: CallbackQuery):
    """Handle teacher edit button click"""
    try:
        teacher_id = int(callback.data.split("_")[-1])
        teacher = get_user_by_id(teacher_id)
        
        if not teacher:
            await callback.answer("❌ O'qituvchi topilmadi")
            return
        
        lang = detect_lang_from_user(callback.from_user)
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👤 Ism", callback_data=f"teach_edit_first_{teacher_id}")],
            [InlineKeyboardButton(text="👤 Familya", callback_data=f"teach_edit_last_{teacher_id}")],
            [InlineKeyboardButton(text="📱 Telefon", callback_data=f"teach_edit_phone_{teacher_id}")],
            [InlineKeyboardButton(text="📚 Fan", callback_data=f"teach_edit_subject_{teacher_id}")],
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"teacher_detail_{teacher_id}")]
        ])
        
        text = f"✏️ **{teacher['first_name']} {teacher['last_name']}**\n\n"
        text += "Tahrirlash uchun maydonni tanlang:"
        
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in teacher_edit handler: {e}")
        await callback.answer("❌ Xatolik yuz berdi")

async def send_user_list(chat_id: int, message: Message, state: dict):
    page = state.get('list_page', 0)
    users = state.get('list_users', [])
    per_page = 10
    start = page * per_page
    chunk = users[start:start + per_page]
    
    total_pages = (len(users) - 1) // per_page + 1 if users else 1
    
    text = f"👥 O'quvchilar ro'yxati — sahifa {page+1}/{total_pages}\n\n"
    for i, u in enumerate(chunk, start + 1):
        status = "✅" if is_access_active(u) else "❌"
        text += f"{i}. {u.get('first_name','')} {u.get('last_name','')} | {u.get('login_id','')} | {status}\n"
    
    # === KEYBOARD ===
    keyboard = []
    
    # 1. Oldingi tugmalar (sonli)
    row = []
    for i, u in enumerate(chunk):
        row.append(InlineKeyboardButton(
            text=f"{start+i+1}",
            callback_data=f"user_detail_{u['id']}"
        ))
        if len(row) == 5:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    # 2. Pagination
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"students_page_{page-1}"))
    if start + per_page < len(users):
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"students_page_{page+1}"))
    if nav:
        keyboard.append(nav)
    
    # 3. YANGI QIDIRUV TUGMASI (eng pastda)


async def handle_admin_user_action(callback: CallbackQuery):
    data = callback.data
    state = get_admin_state(callback.message.chat.id)
    if data == 'users_next':
        state['list_page'] += 1
        await send_user_list(callback.message.chat.id, callback.message, state)
        await callback.answer()
        return
    if data == 'users_prev':
        state['list_page'] = max(0, state.get('list_page', 0) - 1)
        await send_user_list(callback.message.chat.id, callback.message, state)
        await callback.answer()
        return
    if data.startswith('user_select_'):
        idx = int(data.split('_')[-1])
        users = state.get('list_users', [])
        if idx < 0 or idx >= len(users):
            await callback.answer(t(lang, 'err_invalid_choice'))
            return
        selected_user = users[idx]
        state['selected_user'] = selected_user
        if selected_user.get('blocked'):
            status = '🔒 Bloklangan'
        elif is_access_active(selected_user):
            status = '✅ Ochiq'
        else:
            status = '❌ Yopiq'

        await callback.message.answer(
            f"👤 {selected_user['first_name']} {selected_user['last_name']}\n"
            f"🔑 {selected_user['login_id']} | 🧩 {selected_user['subject']} | 🎓 {selected_user['level'] or '-'}\n"
            f"📌 Status: {status}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=t(lang, 'btn_send_test'), callback_data=f'user_test_{selected_user["id"]}')],
                [InlineKeyboardButton(text='📚 Subject settings', callback_data=f'user_control_sub_{selected_user["id"]}')],
            ])
        )
        await callback.answer()
        return



async def show_attendance_menu(message: Message):
    lang = detect_lang_from_user(message.from_user)
    groups = get_all_groups()
    if not groups:
        await message.answer(t(lang, "no_groups"))
        return

    # Create inline keyboard with groups
    keyboard = []
    for group in groups:
        teacher = get_user_by_id(group.get("teacher_id")) if group.get("teacher_id") else None
        teacher_name = f"{teacher.get('first_name', '')} {teacher.get('last_name', '')}".strip() if teacher else "-"
        keyboard.append([InlineKeyboardButton(
            text=f"{group.get('name', '')} | {group.get('level', '')} | {teacher_name}",
            callback_data=f"admin_attendance_group:{group['id']}"
        )])

    keyboard.append([InlineKeyboardButton(text="📥 Export Attendance (Excel)", callback_data="admin_export_attendance")])
    keyboard.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back_to_main")])

    await message.answer("📊 <b>Davomat boshqaruvi</b>\n\nGuruhni tanlang:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode='HTML')


# Helper functions for students list
def get_student_subjects(user_id: int):
    """Get student's subjects"""
    user = get_user_by_id(user_id)
    if user and user.get('subject'):
        return [user['subject']]
    return []

def get_student_teachers(user_id: int):
    """Get student's teachers"""
    groups = get_user_groups(user_id)
    teacher_ids = {g.get('teacher_id') for g in groups if g.get('teacher_id')}
    teachers = []
    for teacher_id in teacher_ids:
        teacher = get_user_by_id(teacher_id)
        if teacher:
            teachers.append(teacher)
    return teachers

def _to_lesson_days_text(days: str) -> str:
    """Convert lesson days code to text"""
    if days == 'MWF':
        return 'Du, Cho, Jum'
    elif days == 'TTS':
        return 'Sesh, Pay, Shan'
    return days


async def show_students_list(message: Message, page: int = 0, search_query: str = ""):
    """Admin uchun chiroyli Students List"""
    state = get_admin_state(message.chat.id)
    state['step'] = 'students_list_view'
    state['data']['students_page'] = page
    state['data']['students_search'] = search_query

    all_users = [u for u in get_all_users() if u.get('login_type') in (1, 2)]
    
    # Qidiruv
    if search_query:
        q = search_query.lower()
        filtered = [u for u in all_users if 
                    q in (u.get('first_name','') + ' ' + u.get('last_name','')).lower() or 
                    q in (u.get('login_id','')).lower()]
    else:
        filtered = all_users

    # Pagination
    per_page = 10
    total = len(filtered)
    start = page * per_page
    end = start + per_page
    students = filtered[start:end]

    text = f"👥 <b>O'quvchilar ro'yxati</b> — Sahifa {page+1}/{(total-1)//per_page + 1}\n\n"

    keyboard = []
    row = []

    for i, student in enumerate(students, start=1):
        # Ma'lumotlarni boyitish
        subjects = get_student_subjects(student['id']) or ['—']
        teachers = get_student_teachers(student['id'])
        groups = get_user_groups(student['id'])
        diamonds = get_diamonds(student['id'])

        teacher_names = ", ".join([f"{t['first_name']} {t['last_name']}" for t in teachers]) if teachers else "—"
        
        group_info = []
        for g in groups:
            days = _to_lesson_days_text(g.get('lesson_date', '—'))
            time = f"{g.get('lesson_start','?')[:5]}-{g.get('lesson_end','?')[:5]}"
            group_info.append(f"{g['name']} ({days} {time})")
        
        group_str = "\n   ".join(group_info) if group_info else "—"

        # Chiroyli blok
        text += (
            f"<b>{start + i}.</b> {student['first_name']} {student['last_name']}\n"
            f"   📚 Fan: {', '.join(subjects)}\n"
            f"   🎯 Level: {student.get('level','—')}\n"
            f"   👨‍🏫 Teacher: {teacher_names}\n"
            f"   👥 Guruh: {group_str}\n"
            f"   💎 Diamond: {diamonds}\n\n"
        )

        # Raqam tugmalari
        row.append(InlineKeyboardButton(
            text=str(start + i), 
            callback_data=f"student_detail_{student['id']}"
        ))
        if len(row) == 5:
            keyboard.append(row)
            row = []

        if row:
            keyboard.append(row)

    # Pagination va Search
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"students_page_{page-1}"))
    if end < total:
        nav.append(InlineKeyboardButton(text="➡️ Keyingi", callback_data=f"students_page_{page+1}"))
    
    keyboard.append(nav)
    keyboard.append([InlineKeyboardButton(text="🔍 Search by name", callback_data="students_search_start")])
    keyboard.append([InlineKeyboardButton(text="🔙 Asosiy menu", callback_data="admin_back_to_main")])

    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode='HTML')


async def run_admin_bot():
    global bot, student_notify_bot
    if not ADMIN_BOT_TOKEN:
        raise RuntimeError("ADMIN_BOT_TOKEN is not set. Put it in .env (ADMIN_BOT_TOKEN=...) and retry.")
    if not STUDENT_BOT_TOKEN:
        raise RuntimeError("STUDENT_BOT_TOKEN is not set. Put it in .env (STUDENT_BOT_TOKEN=...) and retry.")
    bot = Bot(token=ADMIN_BOT_TOKEN)
    student_notify_bot = Bot(token=STUDENT_BOT_TOKEN)
    
    # Restore user sessions after bot restart
    try:
        restored_count = restore_sessions_on_startup()
        logger.info(f"🔄 Restored login sessions for {restored_count} users")
    except Exception as e:
        logger.error(f"Error restoring user sessions: {e}")
    
    # Attendance scheduler (Toshkent time)
    asyncio.create_task(attendance_scheduler(bot, role="admin", admin_chat_ids=ADMIN_CHAT_IDS))
    asyncio.create_task(monthly_payment_scheduler(student_notify_bot))
    
    logger.info("Admin bot started successfully")
    await dp.start_polling(bot)


@dp.error()
async def error_handler(event: types.ErrorEvent):
    """Global error handler for admin bot"""
    logger.error(f"Error in admin bot: {event.exception}", exc_info=True)




@dp.callback_query(lambda c: c.data.startswith("admin_attendance_group:"))
async def handle_admin_attendance_group(callback: CallbackQuery):
    group_id = int(callback.data.split(":")[1])
    group = get_group(group_id)
    if not group:
        await callback.answer("Guruh topilmadi")
        return

    lang = detect_lang_from_user(callback.from_user)
    today = datetime.now(pytz.timezone("Asia/Tashkent")).strftime("%Y-%m-%d")

    # Create inline keyboard for attendance actions
    keyboard = [
        [InlineKeyboardButton(text="📝 Davomat qilish", callback_data=f"admin_take_attendance:{group_id}:{today}")],
        [InlineKeyboardButton(text="📥 Tarixni yuklab olish (Excel)", callback_data=f"admin_export_group_attendance:{group_id}")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_attendance_back")]
    ]

    await callback.message.answer(
        f"📊 <b>{group.get('name', '')} - Davomat</b>\n\n"
        f"🎓 Level: {group.get('level', '')}\n"
        f"👨‍🏫 Teacher: {group.get('teacher_name', '-')}\n"
        f"📅 Bugun: {today}\n",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("admin_take_attendance:"))
async def handle_admin_take_attendance(callback: CallbackQuery):
    parts = callback.data.split(":")
    group_id = int(parts[1])
    date = parts[2]

    from attendance_manager import ensure_session, build_attendance_keyboard

    session = ensure_session(group_id, date)
    if not session:
        await callback.answer("Davomat sessiyasi yaratilmadi")
        return

    await send_attendance_panel(callback.bot, callback.message.chat.id, session["id"], group_id, date, 0)
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("export_group_attendance:"))
async def handle_admin_export_group_attendance(callback: CallbackQuery):
    group_id = int(callback.data.split(":")[1])
    from vocabulary import export_group_attendance_to_xlsx

    try:
        file_data, filename = export_group_attendance_to_xlsx(group_id)
        await callback.bot.send_document(
            callback.message.chat.id,
            BufferedInputFile(file_data.getvalue(), filename)
        )
        await callback.answer("Guruh davomati yuklandi")
    except Exception as e:
        logger.exception("Failed to export group attendance")
        await callback.answer("Xatolik yuz berdi")

@dp.callback_query(lambda c: c.data == "admin_attendance_back")
async def handle_admin_attendance_back(callback: CallbackQuery):
    await show_attendance_menu(callback.message)
    await callback.answer()


@dp.callback_query(lambda c: c.data == "admin_back_to_main")
async def handle_admin_back_to_main(callback: CallbackQuery):
    """Handle back to main menu"""
    lang = detect_lang_from_user(callback.from_user)
    await callback.message.answer(t(lang, 'admin_panel'), reply_markup=admin_main_keyboard(lang))
    await callback.answer()



@dp.callback_query(lambda c: c.data.startswith('set_lang_me_'))
async def handle_set_lang_me_admin(callback: CallbackQuery):
    code = callback.data.split('_')[-1]
    from db import set_user_language_by_telegram
    ok = set_user_language_by_telegram(str(callback.from_user.id), code)

    # Admin uchun maxsus: DB da row bo'lmasa ham til o'zgartirish ishlaydi
    if ok or str(callback.from_user.id) in map(str, ADMIN_CHAT_IDS):
        await callback.answer()
        await callback.message.answer(t(code, 'lang_set'))
        # Yangi til bilan menyuni yuborish
        await callback.message.answer(
            t(code, 'select_from_menu'), 
            reply_markup=admin_main_keyboard(code)
        )
    else:
        await callback.answer()
        await callback.message.answer(t(code, 'please_send_start'))




# Setup broadcast handlers
def setup_admin_bot():
    """Setup admin bot with broadcast handlers"""
    setup_broadcast_handlers(dp, bot)


# Initialize broadcast handlers when bot starts
setup_admin_bot()


# === NEW GROUP CREATION FLOW (with teacher selection) ===
@dp.callback_query(lambda c: c.data == "group_create")
async def handle_group_create_start(callback: CallbackQuery):
    state = get_admin_state(callback.message.chat.id)
    state['step'] = 'ask_group_name'
    state['data'] = {}
    await callback.message.answer("📝 Yangi guruh nomini kiriting:", reply_markup=cancel_keyboard('uz'))
    await callback.answer()


@dp.message(lambda m: get_admin_state(m.chat.id).get('step') == 'search_group_students')
async def handle_group_student_search_input(message: Message):
    """Handle search input for group students"""
    state = get_admin_state(message.chat.id)
    search_query = message.text.strip()
    state['data']['search_query'] = search_query
    state['data']['students_page'] = 0  # Reset to first page
    
    group_id = state['data']['group_id']
    step = state.get('step', '')
    
    # Determine which mode we're in
    if 'remove' in step:
        await show_group_student_list_by_message(message, group_id, remove_mode=True)
    elif 'teacher' in step:
        await show_group_student_list_by_message(message, group_id, show_for_teacher_change=True)
    else:
        await show_group_student_list_by_message(message, group_id)


async def show_group_student_list_by_message(message: Message, group_id: int, remove_mode: bool = False, show_for_teacher_change: bool = False):
    """Show group student list as a new message (for search results)"""
    state = get_admin_state(message.chat.id)
    search_query = state['data'].get('search_query', '')
    page = state['data'].get('students_page', 0)
    
    # Get all students (login_type 1 and 2)
    all_users = get_all_users()
    students = [u for u in all_users if u.get('login_type') in [1, 2]]
    
    # Filter by search query
    if search_query:
        search_lower = search_query.lower()
        students = [u for u in students if 
                   search_lower in u.get('first_name', '').lower() or 
                   search_lower in u.get('last_name', '').lower()]
    
    # Get current group students
    group = get_group(group_id)
    current_group_students = []
    if group:
        current_group_students = get_group_users(group_id)
        current_group_student_ids = {s['id'] for s in current_group_students}
    else:
        current_group_student_ids = set()
    
    # Mark which students are already in group
    for student in students:
        student['in_group'] = student['id'] in current_group_student_ids
    
    # Pagination
    per_page = 10
    total = len(students)
    start = page * per_page
    end = start + per_page
    chunk = students[start:end]
    
    total_pages = (total - 1) // per_page + 1 if total else 1
    
    # Build message
    if show_for_teacher_change:
        title = f"👥 Guruh o'qituvchisini o'zgartirish — sahifa {page+1}/{total_pages}"
    elif remove_mode:
        title = f"➖ Guruhdan o'quvchini o'chirish — sahifa {page+1}/{total_pages}"
    else:
        title = f"➕ Guruhga o'quvchi qo'shish — sahifa {page+1}/{total_pages}"
    
    if search_query:
        title += f" (qidirish: {search_query})"
    
    text = f"{title}\n\n"
    
    for i, student in enumerate(chunk, start=1):
        # Get student status
        if student.get('blocked'):
            status = '🔒'
        elif is_access_active(student):
            status = '✅'
        else:
            status = '❌'
        
        # Get student's current group info
        student_groups = get_user_groups(student['id'])
        group_count = len(student_groups)
        
        # Get teacher info
        teacher_name = "-"
        if student_groups:
            first_group = student_groups[0]
            if first_group.get('teacher_id'):
                teacher = get_user_by_id(first_group['teacher_id'])
                if teacher:
                    teacher_name = f"{teacher['first_name']} {teacher['last_name']}"
        
        # Get class time
        class_time = "-"
        if student_groups:
            first_group = student_groups[0]
            class_time = f"{first_group.get('start_time', '?')}-{first_group.get('end_time', '?')}"
        
        # Group student count
        group_student_count = 0
        if student_groups:
            from db import get_group_users
            first_group = student_groups[0]
            group_students = get_group_users(first_group['id'])
            group_student_count = len(group_students)
        
        # Add status indicator for group membership
        in_group_indicator = " ✅" if student['in_group'] else ""
        
        text += (
            f"{i}. {student['subject']}{in_group_indicator}\n"
            f"   {student['first_name']} {student['last_name']}\n"
            f"   🔑 {student['login_id']} | 📱 {student.get('phone', '—')} | 🎓 {student.get('level', '—')} | {status}\n"
            f"   👨‍🏫 {teacher_name} | ⏰ {class_time} | 👥 {group_student_count}\n\n"
        )
    
    # Create keyboard
    keyboard = []
    
    # Number buttons (1-10)
    number_buttons = []
    for i in range(1, min(6, len(chunk) + 1)):
        if remove_mode:
            if chunk[i-1]['in_group']:
                number_buttons.append(InlineKeyboardButton(
                    text=f"{i} ✅", 
                    callback_data=f"grp_remove:{group_id}:{chunk[i-1]['id']}"
                ))
            else:
                number_buttons.append(InlineKeyboardButton(text=f"{i}", callback_data="noop"))
        elif show_for_teacher_change:
            number_buttons.append(InlineKeyboardButton(
                text=f"{i}", 
                callback_data=f"teacher_select_{chunk[i-1]['id']}"
            ))
        else:  # add_student mode
            if chunk[i-1]['in_group']:
                number_buttons.append(InlineKeyboardButton(text=f"{i} ✅", callback_data="noop"))
            else:
                number_buttons.append(InlineKeyboardButton(
                    text=f"{i}", 
                    callback_data=f"grp_add_student:{group_id}:{chunk[i-1]['id']}"
                ))
    
    for i in range(6, min(11, len(chunk) + 1)):
        if remove_mode:
            if chunk[i-1]['in_group']:
                number_buttons.append(InlineKeyboardButton(
                    text=f"{i} ✅", 
                    callback_data=f"grp_remove:{group_id}:{chunk[i-1]['id']}"
                ))
            else:
                number_buttons.append(InlineKeyboardButton(text=f"{i}", callback_data="noop"))
        elif show_for_teacher_change:
            number_buttons.append(InlineKeyboardButton(
                text=f"{i}", 
                callback_data=f"teacher_select_{chunk[i-1]['id']}"
            ))
        else:  # add_student mode
            if chunk[i-1]['in_group']:
                number_buttons.append(InlineKeyboardButton(text=f"{i} ✅", callback_data="noop"))
            else:
                number_buttons.append(InlineKeyboardButton(
                    text=f"{i}", 
                    callback_data=f"grp_add_student:{group_id}:{chunk[i-1]['id']}"
                ))
    
    # Split number buttons into rows
    if number_buttons:
        keyboard.append(number_buttons[:5])
        if len(number_buttons) > 5:
            keyboard.append(number_buttons[5:])
    
    # Search and navigation buttons
    nav_buttons = []
    
    # Search buttons
    if show_for_teacher_change:
        nav_buttons.append(InlineKeyboardButton(text="🔍 Ism/Familya qidirish", callback_data=f"grp_search_students:{group_id}:name"))
    else:
        nav_buttons.append(InlineKeyboardButton(text="🔍 Ism/Familya qidirish", callback_data=f"grp_search_students:{group_id}:name"))
    
    # Pagination buttons
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"grp_students_page:{group_id}:{page-1}"))
    
    if end < total:
        nav_buttons.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"grp_students_page:{group_id}:{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Back button
    keyboard.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"group_detail_{group_id}")])
    
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")


@dp.message(lambda m: get_admin_state(m.chat.id).get('step') == 'ask_group_name')
async def handle_group_name(message: Message):
    state = get_admin_state(message.chat.id)
    state['data']['name'] = message.text.strip()
    state['step'] = 'ask_group_level'
    await message.answer("🎯 Guruh darajasini tanlang (A1, A2, B1, B2, C1):", reply_markup=cancel_keyboard('uz'))


@dp.message(lambda m: get_admin_state(m.chat.id).get('step') == 'ask_group_level')
async def handle_group_level(message: Message):
    state = get_admin_state(message.chat.id)
    state['data']['level'] = message.text.strip().upper()
    state['step'] = 'choose_teacher'
    
    teachers = get_all_teachers()
    kb = create_group_teacher_selection_keyboard(teachers)   # ← sizning utils.py dagi funksiya
    await message.answer("👨‍🏫 Guruhga o'qituvchini tanlang (yoki \"O'qituvchisiz yaratish\"):", 
                         reply_markup=kb)


# Teacher tanlash
@dp.callback_query(lambda c: c.data.startswith("group_teacher_select_"))
async def handle_group_teacher_select(callback: CallbackQuery):
    teacher_id = int(callback.data.split("_")[-1])
    state = get_admin_state(callback.message.chat.id)
    
    group_id = state.get('data', {}).get('group_id')
    
    if group_id:                     # ← mavjud guruh
        from db import update_group_teacher
        update_group_teacher(group_id, teacher_id)
        
        teacher = get_user_by_id(teacher_id)
        teacher_name = f"{teacher.get('first_name','')} {teacher.get('last_name','')}".strip() if teacher else "Noma'lum"
        
        await callback.message.edit_text(f"✅ Guruhga o'qituvchi biriktirildi!\nO'qituvchi: {teacher_name}")
        # state ni tozalash
        state['data'].pop('group_id', None)
    else:                            # ← yangi guruh
        state['data']['teacher_id'] = teacher_id
        await create_group_from_state(callback.message, state)
    
    await callback.answer()


@dp.callback_query(lambda c: c.data == "create_group_no_teacher")
async def handle_group_no_teacher(callback: CallbackQuery):
    state = get_admin_state(callback.message.chat.id)
    state['data']['teacher_id'] = None
    state['step'] = None
    await create_group_from_state(callback.message, state)
    await callback.answer()


async def create_group_from_state(message: Message, state: dict):
    data = state['data']
    if not data.get('name') or not data.get('level'):
        await message.answer("❌ Guruh nomi yoki leveli yo'q")
        return

    group_id = create_group(
        name=data['name'],
        teacher_id=data.get('teacher_id'),
        level=data['level'],
        subject=data.get('subject', 'English'),
        lesson_date=data.get('lesson_date', 'MWF'),
        lesson_start=data.get('lesson_start', '14:00'),
        lesson_end=data.get('lesson_end', '15:00'),
        tz='Asia/Tashkent'
    )

    teacher_name = "Yo'q"
    if data.get('teacher_id'):
        t = get_user_by_id(data['teacher_id'])
        if t:
            teacher_name = f"{t['first_name']} {t['last_name']}"

    await message.answer(
        f"✅ Guruh yaratildi!\n"
        f"ID: {group_id}\n"
        f"Nomi: {data['name']}\n"
        f"Level: {data['level']}\n"
        f"O'qituvchi: {teacher_name}"
    )
    reset_admin_state(message.chat.id)


# ==================== O'QITUVCHINI ALMASHTIRISH ====================
@dp.callback_query(lambda c: c.data.startswith("group_edit_teacher_"))
async def handle_group_edit_teacher(callback: CallbackQuery):
    group_id = int(callback.data.split("_")[-1])
    
    # ← BU QATORLARNI QO'SHING
    state = get_admin_state(callback.message.chat.id)
    state['data']['group_id'] = group_id   # <--- muhim!
    
    teachers = get_all_teachers()
    
    kb = create_group_teacher_selection_keyboard(teachers)  # sizning utils.py dagi funksiya
    await callback.message.edit_text("👨‍🏫 Yangi o'qituvchini tanlang:", reply_markup=kb)
    await callback.answer()


# ==================== YANGI O'QUVCHI QO'SHISH ====================
@dp.callback_query(lambda c: c.data.startswith("group_add_student_"))
async def handle_group_add_student(callback: CallbackQuery):
    group_id = int(callback.data.split("_")[-1])
    state = get_admin_state(callback.message.chat.id)
    state['adding_to_group'] = group_id

    # Hozirgi guruhda bo'lmagan barcha o'quvchilarni ko'rsatamiz
    all_users = get_all_users()
    group_users = {u['id'] for u in get_group_users(group_id)}
    available = [u for u in all_users if u.get('login_type') in (1,2) and u['id'] not in group_users]

    if not available:
        await callback.message.edit_text("❌ Qo'shish uchun mavjud o'quvchi qolmadi.")
        await callback.answer()
        return

    await callback.message.edit_text(
        "➕ Qo'shish uchun o'quvchini tanlang:",
        reply_markup=create_user_selection_keyboard(available, group_id=group_id)
    )
    await callback.answer()


# ==================== O'QUVCHINI CHIQARIB YUBORISH ====================
@dp.callback_query(lambda c: c.data.startswith("group_remove_student_"))
async def handle_group_remove_student(callback: CallbackQuery):
    group_id = int(callback.data.split("_")[-1])
    students = get_group_users(group_id)

    if not students:
        await callback.message.edit_text("❌ Guruhda o'quvchi yo'q.")
        await callback.answer()
        return

    await callback.message.edit_text(
        "➖ Chiqarib yuborish uchun o'quvchini tanlang:",
        reply_markup=create_user_selection_keyboard(students, group_id=group_id)
    )
    await callback.answer()


# ==================== USER GROUP MANAGEMENT ====================
@dp.callback_query(lambda c: c.data.startswith("add_user_to_group_"))
async def handle_add_user_to_group(callback: CallbackQuery):
    _, group_id, user_id = callback.data.split("_")
    group_id, user_id = int(group_id), int(user_id)
    
    add_user_to_group(user_id, group_id)
    await callback.answer("✅ O'quvchi guruhga qo'shildi!")
    # Guruh sahifasiga qaytish
    await handle_group_select(callback)   # yangi funksiyani chaqiramiz


@dp.callback_query(lambda c: c.data.startswith("remove_user_from_group_"))
async def handle_remove_user_from_group(callback: CallbackQuery):
    _, group_id, user_id = callback.data.split("_")
    group_id, user_id = int(group_id), int(user_id)
    
    remove_user_from_group(user_id, group_id)
    await callback.answer("✅ O'quvchi guruhdan chiqarildi!")
    await handle_group_select(callback)


async def show_group_student_list_for_remove(message: Message, group_id: int):
    students = get_group_users(group_id)
    if not students:
        await message.edit_text("❌ Bu guruhda o'quvchi yo'q.")
        return
    kb = []
    for u in students:
        kb.append([InlineKeyboardButton(
            text=f"{u['first_name']} {u['last_name']} ({u.get('login_id','')})",
            callback_data=f"grp_remove_student:{group_id}:{u['id']}"
        )])
    await message.edit_text("➖ O'chirish uchun o'quvchini tanlang:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


async def show_group_student_list_for_add(message: Message, group_id: int):
    all_students = [u for u in get_all_users() if u.get('login_type') in (1,2)]
    group_ids = {u['id'] for u in get_group_users(group_id)}
    available = [u for u in all_students if u['id'] not in group_ids]

    if not available:
        await message.edit_text("❌ Qo'shish uchun boshqa o'quvchi qolmadi.")
        return

    kb = []
    for u in available[:20]:
        kb.append([InlineKeyboardButton(
            text=f"{u['first_name']} {u['last_name']}",
            callback_data=f"grp_add_student:{group_id}:{u['id']}"
        )])
    await message.edit_text("➕ Qo'shish uchun o'quvchini tanlang:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


# ====================== TEACHERS LIST ======================
async def show_teachers_list(message: Message, page: int = 0, search_query: str = ""):
    """Chiroyli Teachers List (siz xohlagan formatda)"""
    state = get_admin_state(message.chat.id)
    state['step'] = 'teachers_list_view'
    state['data']['teachers_page'] = page
    state['data']['teachers_search'] = search_query

    teachers = get_all_teachers()
    
    # Qidiruv
    if search_query:
        q = search_query.lower()
        filtered = [t for t in teachers if 
                    q in (t.get('first_name','') + ' ' + t.get('last_name','')).lower() or 
                    q in (t.get('login_id','')).lower()]
    else:
        filtered = teachers

    # Pagination
    per_page = 10
    total = len(filtered)
    start = page * per_page
    end = start + per_page
    current_teachers = filtered[start:end]

    text = f"👨‍🏫 <b>O'qituvchilar ro'yxati</b> — Sahifa {page+1}/{ (total-1)//per_page + 1 }\n\n"

    keyboard = []
    row = []

    for i, teacher in enumerate(current_teachers, start=1):
        groups_count = get_teacher_groups_count(teacher['id'])
        students_count = get_teacher_total_students(teacher['id'])
        
        text += (
            f"<b>{start + i}.</b> {teacher['first_name']} {teacher['last_name']}\n"
            f"   📚 Fan: {teacher.get('subject', '—')}\n"
            f"   📞 Telefon: {teacher.get('phone', '—')}\n"
            f"   🔑 Login ID: {teacher['login_id']}\n"
            f"   👥 Guruhlar: {groups_count} ta | O'quvchilar: {students_count} ta\n\n"
        )

        row.append(InlineKeyboardButton(
            text=str(start + i), 
            callback_data=f"teacher_detail_{teacher['id']}"
        ))
        if len(row) == 5:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    # Navigation
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"teachers_page_{page-1}"))
    if end < total:
        nav.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"teachers_page_{page+1}"))
    
    keyboard.append(nav)
    keyboard.append([InlineKeyboardButton(text="🔍 Search by name", callback_data="teachers_search_start")])
    keyboard.append([InlineKeyboardButton(text="🔙 Asosiy menu", callback_data="admin_back_to_main")])

    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode='HTML')


# Qidiruvni boshlash
@dp.callback_query(lambda c: c.data == "teachers_search_start")
async def handle_teachers_search_start(callback: CallbackQuery):
    state = get_admin_state(callback.message.chat.id)
    state['step'] = 'teachers_search'
    await callback.message.answer("🔍 Ism, familya yoki Login ID kiriting:", 
                                 reply_markup=cancel_keyboard('uz'))
    await callback.answer()


# Qidiruv natijasi
@dp.message(lambda m: get_admin_state(m.chat.id).get('step') == 'teachers_search')
async def handle_teachers_search_input(message: Message):
    query = message.text.strip()
    await show_teachers_list(message, page=0, search_query=query)


# Pagination
@dp.callback_query(lambda c: c.data.startswith("teachers_page_"))
async def handle_teachers_pagination(callback: CallbackQuery):
    page = int(callback.data.split("_")[-1])
    await show_teachers_list(callback.message, page=page)
    await callback.answer()


# Teacher tanlanganda chiqadigan Detail sahifa
@dp.callback_query(lambda c: c.data.startswith("teacher_detail_"))
async def handle_teacher_detail(callback: CallbackQuery):
    teacher_id = int(callback.data.split("_")[-1])
    teacher = get_user_by_id(teacher_id)
    if not teacher:
        await callback.answer("O'qituvchi topilmadi")
        return

    groups = get_groups_by_teacher(teacher_id)
    groups_count = len(groups)
    students_count = get_teacher_total_students(teacher_id)

    text = (
        f"👨‍🏫 <b>O'qituvchi ma'lumotlari</b>\n\n"
        f"👤 Ism Familya: {teacher['first_name']} {teacher['last_name']}\n"
        f"📚 Dars beradigan fan: {teacher.get('subject', '—')}\n"
        f"📞 Telefon: {teacher.get('phone', '—')}\n"
        f"🔑 Login ID: {teacher['login_id']}\n"
        f"👥 Jami guruhlar: {groups_count} ta\n"
        f"👨‍🎓 Jami o'quvchilar: {students_count} ta\n\n"
        f"<b>Guruhlar ro'yxati:</b>\n"
    )

    for g in groups:
        text += f"• {g['name']} ({g.get('level','—')})\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Ism Familyani o'zgartirish", callback_data=f"teacher_edit_name_{teacher_id}")],
        [InlineKeyboardButton(text="📱 Telefon raqamni o'zgartirish", callback_data=f"teacher_edit_phone_{teacher_id}")],
        [InlineKeyboardButton(text="🔑 Password Reset qilish", callback_data=f"teacher_reset_password_{teacher_id}")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="teachers_list_back")]
    ])

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
    await callback.answer()
