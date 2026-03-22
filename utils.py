from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from i18n import t, detect_lang_from_user

def cancel_keyboard(lang='uz'):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text='❌ ' + t(lang, 'cancel'))]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def admin_main_keyboard(lang='uz'):
    labels = {
        'new_user': t(lang, 'choose_user_type'),
        'results': t(lang, 'no_results'),
        'students': t(lang, 'students_list_title'),
        'teachers': t(lang, 'teachers_list_title'),
        'groups': t(lang, 'groups_menu'),
        'attendance': '📊 Davomat',
        'vocab_io': '📥/📤 Sozlar Import/Export',
        'export_all': '📤 Export (XLSX)',
    }
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='➕ ' + labels['new_user'])],
            [KeyboardButton(text='📊 ' + labels['results']), KeyboardButton(text='👥 ' + labels['students'])],
            [KeyboardButton(text='👨‍🏫 ' + labels['teachers']), KeyboardButton(text='👥 ' + labels['groups'])],
            [KeyboardButton(text='📊 ' + labels['attendance']), KeyboardButton(text='💳 ' + t(lang, 'payments_btn'))],
            [KeyboardButton(text=labels['vocab_io']), KeyboardButton(text=labels['export_all'])],
            [KeyboardButton(text='🌐 ' + t(lang, 'choose_lang'))],
        ],
        resize_keyboard=True,
    )


def create_user_type_keyboard(lang='uz'):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text='👨‍🎓 ' + t(lang, 'new_student_with_test'), callback_data='user_type_1'),
            InlineKeyboardButton(text='👨‍🎓 ' + t(lang, 'existing_student_no_test'), callback_data='user_type_2')
        ],
        [InlineKeyboardButton(text='👨‍🏫 O\'qituvchi', callback_data='user_type_3')],
    ])


def create_subject_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🇬🇧 English', callback_data='subject_English')],
        [InlineKeyboardButton(text='🇷🇺 Russian', callback_data='subject_Russian')],
    ])


def create_dual_choice_keyboard(prefix="test", lang='uz'):
    """Foydalanuvchiga ingliz yoki rus tilini tanlash uchun tugmalar"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🇬🇧 English', callback_data=f'{prefix}_English')],
        [InlineKeyboardButton(text='🇷🇺 Russian', callback_data=f'{prefix}_Russian')],
    ])


def create_leaderboard_pagination_keyboard(current_page, total_pages, filter_type='global', lang='uz'):
    """Reyting sahifasini navigatsiya qilish uchun tugmalar"""
    keyboard = []
    nav = []
    if current_page > 0:
        nav.append(InlineKeyboardButton(
            text='⬅️ ' + t(lang, 'prev'), 
            callback_data=f'leaderboard_prev_{filter_type}'
        ))
    if current_page < total_pages - 1:
        nav.append(InlineKeyboardButton(
            text=t(lang, 'next') + ' ➡️', 
            callback_data=f'leaderboard_next_{filter_type}'
        ))

    if nav:
        keyboard.append(nav)

    # Filter buttons (keep icons, translate labels)
    filter_buttons = [
        InlineKeyboardButton(text='🌍 ' + t(lang, 'leaderboard'), callback_data='leaderboard_filter_global'),
        InlineKeyboardButton(text='👥 ' + t(lang, 'leaderboard'), callback_data='leaderboard_filter_group'),
    ]
    keyboard.append(filter_buttons)

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def student_main_keyboard(lang='uz'):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='📚 ' + t(lang, 'grammar_rules')), KeyboardButton(text='📝 ' + t(lang, 'test_btn'))],
            [KeyboardButton(text='📊 ' + t(lang, 'progress')), KeyboardButton(text='💬 ' + t(lang, 'survey'))],
            [KeyboardButton(text='💎 ' + t(lang, 'leaderboard')), KeyboardButton(text='💰 D\'coin')],
            [KeyboardButton(text='📖 ' + t(lang, 'vocab_menu'))],
            [KeyboardButton(text='👤 ' + t(lang, 'my_profile'))],
            [KeyboardButton(text='🌐 ' + t(lang, 'choose_lang'))],
        ],
        resize_keyboard=True,
    )


def student_vocab_keyboard(lang='uz'):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='🔎 ' + t(lang, 'vocab_search_btn')), KeyboardButton(text='🧠 ' + t(lang, 'vocab_quiz_btn'))],
            [KeyboardButton(text='⚙️ ' + t(lang, 'vocab_pref_btn'))],
            [KeyboardButton(text='⬅️ ' + t(lang, 'back_btn'))],
        ],
        resize_keyboard=True,
    )


def teacher_main_keyboard(lang='uz'):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='📥/📤 Sozlar Import/Export')],
            [KeyboardButton(text='✅ Davomat')],
            [KeyboardButton(text='👤 ' + t(lang, 'my_profile'))],
            [KeyboardButton(text='🌐 ' + t(lang, 'choose_lang'))],
        ],
        resize_keyboard=True,
    )


def create_group_action_keyboard(lang='uz'):
    """Adminning guruh boshqarish menyu"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='➕ ' + t(lang, 'group_create_btn'), callback_data='group_create')],
        [InlineKeyboardButton(text='👥 ' + t(lang, 'group_list_btn'), callback_data='group_list')],
        [InlineKeyboardButton(text='📢 Broadcast', callback_data='broadcast_start')],
    ])


def create_group_list_keyboard(groups, lang='uz'):
    """Guruhlar ro'yxati uchun buttons"""
    buttons = []
    for g in groups:
        user_count = len(g.get('users', []))
        text = f"{g['name']} ({t(lang, 'ask_group_level')} {g['level']}) - {user_count} {t(lang, 'students_list_title').split()[0]}"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f'group_select_{g["id"]}')])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_teacher_selection_keyboard(teachers):
    """O'qituvchi tanlash uchun buttons"""
    buttons = []
    for t in teachers:
        name = f"{t.get('first_name', '')} {t.get('last_name', '')}"
        buttons.append([
            InlineKeyboardButton(text=name, callback_data=f'teacher_select_{t["id"]}'),
            InlineKeyboardButton(text="🔄 Password Reset", callback_data=f'teacher_reset_{t["id"]}')
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_group_teacher_selection_keyboard(teachers):
    """Guruh yaratish uchun o'qituvchi tanlash (password reset tugmasiz)"""
    buttons = []
    for t in teachers:
        name = f"{t.get('first_name', '')} {t.get('last_name', '')}"
        buttons.append([InlineKeyboardButton(
            text=name, 
            callback_data=f'group_teacher_select_{t["id"]}'   # Fixed prefix
        )])
    
    # "O'qituvchisiz yaratish" tugmasi
    buttons.append([InlineKeyboardButton(
        text="🚀 O'qituvchisiz yaratish", 
        callback_data='create_group_no_teacher'
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_user_selection_keyboard(users, group_id=None):
    """O'quvchi tanlash uchun buttons"""
    buttons = []
    for u in users:
        name = f"{u.get('first_name', '')} {u.get('last_name', '')}"
        callback = f'add_user_to_group_{group_id}_{u["id"]}' if group_id else f'select_user_{u["id"]}'
        buttons.append([InlineKeyboardButton(text=name, callback_data=callback)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_user_selection_keyboard_by_type(users, group_id=None):
    """Show users in separate columns by type (teachers and students)"""
    teachers = []
    students = []
    
    for u in users:
        name = f"{u.get('first_name', '')} {u.get('last_name', '')}"
        if u.get('login_type') == 3:
            teachers.append((u, name))
        else:
            students.append((u, name))
    
    buttons = []
    
    # Add teachers section if any
    if teachers:
        buttons.append([InlineKeyboardButton(text="👨‍🏫 O'QITUVCHILAR", callback_data='noop')])
        for u, name in teachers:
            callback = f'add_user_to_group_{group_id}_{u["id"]}' if group_id else f'select_user_{u["id"]}'
            buttons.append([InlineKeyboardButton(text=f"👨‍🏫 {name}", callback_data=callback)])
    
    # Add students section if any
    if students:
        if teachers:  # Add separator if both types exist
            buttons.append([InlineKeyboardButton(text="───", callback_data='noop')])
        buttons.append([InlineKeyboardButton(text="👨‍🎓 O'QUVCHILAR", callback_data='noop')])
        for u, name in students:
            callback = f'add_user_to_group_{group_id}_{u["id"]}' if group_id else f'select_user_{u["id"]}'
            buttons.append([InlineKeyboardButton(text=f"👨‍🎓 {name}", callback_data=callback)])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_language_selection_keyboard_for_user(user_id):
    """Create inline keyboard for selecting language for a specific user id"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🇺🇿 O\'zbekcha', callback_data=f'set_lang_uz_{user_id}')],
        [InlineKeyboardButton(text='🇷🇺 Русский', callback_data=f'set_lang_ru_{user_id}')],
        [InlineKeyboardButton(text='🇬🇧 English', callback_data=f'set_lang_en_{user_id}')],
    ])

def create_language_selection_keyboard_for_self():
    """Create inline keyboard for user to set their own language (callbacks handled in student/teacher bots)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🇺🇿 O\'zbekcha', callback_data='set_lang_me_uz')],
        [InlineKeyboardButton(text='🇷🇺 Русский', callback_data='set_lang_me_ru')],
        [InlineKeyboardButton(text='🇬🇧 English', callback_data='set_lang_me_en')],
    ])


