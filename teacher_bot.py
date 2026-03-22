import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ReplyKeyboardRemove
from aiogram.types.input_file import BufferedInputFile
from aiogram.filters import Command

from utils import teacher_main_keyboard, create_language_selection_keyboard_for_user, create_subject_keyboard, cancel_keyboard, student_main_keyboard, create_language_selection_keyboard_for_self
from i18n import t, detect_lang_from_user
from config import TEACHER_BOT_TOKEN
from db import get_groups_by_teacher, get_user_by_id, get_group_users, add_attendance, is_access_active, get_group, get_user_groups, get_group_users, add_attendance, is_access_active, get_group, get_teacher_total_students, get_student_subjects, get_user_by_telegram
from auth import verify_login, activate_user, restore_sessions_on_startup, process_login_message, get_login_state, set_login_state, clear_login_state, AuthMiddleware
from attendance_manager import attendance_scheduler, build_attendance_keyboard, get_session, set_session_closed, set_session_opened
from logging_config import get_logger

# Setup logger
logger = get_logger(__name__)

bot: Bot | None = None
dp = Dispatcher()

# Setup authentication middleware
auth_middleware = AuthMiddleware(bot_type='teacher', expected_login_type=3)
dp.message.middleware(auth_middleware)
dp.callback_query.middleware(auth_middleware)

# Teacher state for main menu
teacher_state = {}


def get_teacher_state(chat_id):
    return teacher_state.setdefault(chat_id, {'step': None, 'data': {}})


def reset_teacher_state(chat_id):
    teacher_state.pop(chat_id, None)


@dp.message(Command('start'))
async def cmd_start(message: Message):
    """Handle /start command - check login status or show login instructions"""
    logger.debug(f"/start called by user_id={message.from_user.id}")
    telegram_id = str(message.from_user.id)
    user = get_user_by_telegram(telegram_id)
    
    # If user is already logged in, show main menu
    if user and user.get('logged_in'):
        lang = detect_lang_from_user(user)
        await message.answer(t(lang, 'welcome_back'), reply_markup=teacher_main_keyboard(lang))
        return
    
    # Clear any existing login state and start new login flow
    clear_login_state(telegram_id)
    reset_teacher_state(message.chat.id)
    
    # Start two-step login flow
    set_login_state(telegram_id, {'step': 'ask_login', 'data': {}})
    
    lang = detect_lang_from_user(message.from_user)
    
    await message.answer(t(lang, 'teacher_login_title'))
    await message.answer(t(lang, 'ask_login_id'))


@dp.message(lambda m: not (m.text or '').startswith('/'))
async def handle_login_and_messages(message: Message):
    """Ikki bosqichli login + eski formatni qo‘llab-quvvatlaydi"""
    telegram_id = str(message.from_user.id)
    login_state = get_login_state(telegram_id)

    # Login jarayonida bo‘lsa yoki eski formatda (:) bo‘lsa — process qil
    if login_state.get('step') in ('ask_login', 'ask_password') or ':' in (message.text or ''):
        success = await process_login_message(message, expected_login_type=3)
        if success:
            user = get_user_by_telegram(telegram_id)
            lang = detect_lang_from_user(user or message.from_user)
            await message.answer(t(lang, 'login_success'))
            await message.answer(t(lang, 'welcome_back'), reply_markup=teacher_main_keyboard(lang))
        return  # Jarayon tugamaguncha boshqa hech narsa qilma

    # Agar login tugagan bo‘lsa — oddiy authenticated handler
    await handle_authenticated_message(message)


async def handle_authenticated_message(message: Message):
    """Handle messages from authenticated teachers"""
    logger.info(f"💬 TEACHER MESSAGE: {message.text} | User: {message.from_user.id}")
    user = get_user_by_telegram(str(message.from_user.id))
    lang = detect_lang_from_user(user or message.from_user)
    
    logger.info(f"🔍 Teacher user data: {user}")
    
    if not user or user.get('login_type') != 3:
        await message.answer(t(lang, 'please_send_start'))
        return

    if user['blocked']:
        await message.answer(t(lang, 'blocked_contact_admin'))
        return

    # Do not force access_enabled for teachers; they remain logged in once activated
    
    txt = message.text
    # Teacher menu buttons
    vocab_menu_btn = '📥/📤 Sozlar Import/Export'
    attendance_btn = '✅ Davomat'
    profile_btn = '👤 ' + t(lang, 'my_profile')
    my_groups_btn = '📚 Mening guruhlarim'

    # Show inline language selector when teacher presses the language button
    choose_lang_btn = '🌐 ' + t(lang, 'choose_lang')
    if txt == choose_lang_btn or (txt or '').strip().startswith('🌐'):
        await message.answer(t(lang, 'choose_lang'), reply_markup=create_language_selection_keyboard_for_self())
        return

    if txt == profile_btn:
        await show_my_profile(message.chat.id, user)
        return

    if txt == my_groups_btn:
        await show_my_groups(message.chat.id, user)
        return

    if txt == vocab_menu_btn:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='📥 Import (.xlsx)', callback_data='teacher_vocab_action_import')],
            [InlineKeyboardButton(text='📤 Export (.xlsx)', callback_data='teacher_vocab_action_export')],
        ])
        await message.answer(t(lang, 'choose'), reply_markup=kb)
        return
    if txt == attendance_btn:
        # Show today's groups and allow opening attendance panel
        groups = get_groups_by_teacher(user['id'])
        if not groups:
            await message.answer(t(lang, 'groups_not_found'))
            return
        # pick groups that have today's lesson_date
        from datetime import datetime
        import pytz, re
        tz = pytz.timezone("Asia/Tashkent")
        now = datetime.now(tz)
        today = now.strftime("%Y-%m-%d")
        weekday = now.weekday()  # 0=Mon ... 6=Sun

        def has_lesson_today(g: dict) -> bool:
            ld = (g.get("lesson_date") or "").strip()
            if not ld:
                return False
            # Explicit calendar date
            if re.match(r"^\d{4}-\d{2}-\d{2}$", ld):
                return ld == today
            code = ld.upper()
            if code == "ODD":
                return weekday in (0, 2, 4)  # Mon/Wed/Fri
            if code == "EVEN":
                return weekday in (1, 3, 5)  # Tue/Thu/Sat
            return False

        todays = [g for g in groups if has_lesson_today(g)]
        if not todays:
            await message.answer(t(lang, 'no_lessons_today'))
            return
        kb_rows = []
        for g in todays:
            kb_rows.append([InlineKeyboardButton(text=f"{g.get('name')} ({g.get('lesson_start')}-{g.get('lesson_end')})", callback_data=f"att_open_{g['id']}_{today}")])
        await message.answer(t(lang, 'choose_group_for_attendance'), reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))
        return

    await message.answer(t(lang, 'select_from_menu'), reply_markup=teacher_main_keyboard(lang))


async def show_my_groups(chat_id: int, user: dict):
    lang = detect_lang_from_user(user)
    groups = get_user_groups(user['id'])
    
    if not groups:
        await bot.send_message(chat_id, t(lang, 'no_groups'))
        return
    
    text = f"👥 {t(lang, 'my_groups')}\n\n"
    
    for g in groups:
        # Get group statistics
        group_id = g['id']
        
        # Count students in this group
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as cnt FROM users WHERE group_id=? AND login_type IN (1,2)", (group_id,))
        student_row = cur.fetchone()
        student_count = student_row['cnt'] if student_row else 0
        conn.close()
        
        # Count Diamond users in this group
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as cnt FROM users WHERE group_id=? AND diamonds > 0", (group_id,))
        diamond_row = cur.fetchone()
        diamond_count = diamond_row['cnt'] if diamond_row else 0
        conn.close()
        
        text += f"📚 {g['name']} ({g['level'] or 'N/A'})\n"
        text += f"   👥 O'quvchilar: {student_count} ta\n"
        text += f"   💎 Diamond foydalanuvchilar: {diamond_count} ta\n\n"
    
    await bot.send_message(chat_id, text)


async def show_my_profile(chat_id: int, user: dict):
    lang = detect_lang_from_user(user)
    
    # Teacher uchun to'g'ri ma'lumotlar
    groups = get_groups_by_teacher(user['id'])
    total_students = get_teacher_total_students(user['id'])  # multi-group

    lines = []
    lines.append("👤 " + t(lang, 'my_profile'))
    lines.append("")
    lines.append(f"👨‍🏫 Ism Familya: {user.get('first_name','-')} {user.get('last_name','-')}")
    lines.append(f"📞 Telefon: {user.get('phone') or '-'}")
    lines.append(f"🆔 Login ID: {user.get('login_id') or '-'}")
    lines.append(f"📚 Fan: {user.get('subject') or '-'}")
    lines.append(f"👥 Guruhlar soni: {len(groups)}")
    lines.append(f"👨‍� Jami o'quvchilar: {total_students} ta")

    # Guruhlar ro'yxati (ixtiyoriy, chiroyli)
    if groups:
        lines.append("\n📋 Guruhlar:")
        for g in groups:
            students_in_group = len(get_group_users(g['id']))
            lines.append(f"   • {g.get('name')} ({g.get('level') or '-'}) — {students_in_group} talaba")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🚪 ' + t(lang, 'logout'), callback_data='logout_me')],
    ])

    await bot.send_message(chat_id, "\n".join(lines), reply_markup=kb)


@dp.callback_query(lambda c: c.data == 'logout_me')
async def handle_logout_me_teacher(callback: CallbackQuery):
    from db import logout_user_by_telegram
    user = get_user_by_telegram(str(callback.from_user.id))
    lang = detect_lang_from_user(user or callback.from_user)
    logout_user_by_telegram(str(callback.from_user.id))
    clear_login_state(str(callback.from_user.id))
    reset_teacher_state(callback.message.chat.id)
    await callback.answer()
    await callback.message.answer(t(lang, 'logged_out'), reply_markup=ReplyKeyboardRemove())


@dp.callback_query(lambda c: c.data.startswith("att_open_"))
async def handle_teacher_att_open(callback: CallbackQuery):
    user = get_user_by_telegram(str(callback.from_user.id))
    lang = detect_lang_from_user(user or callback.from_user)
    if not user or user.get("login_type") != 3:
        await callback.answer()
        await callback.message.answer(t(lang, 'please_send_start'))
        return
    parts = callback.data.split("_")
    group_id = int(parts[2])
    date_str = parts[3]
    group = get_group(group_id)
    if not group or group.get("teacher_id") != user.get("id"):
        await callback.answer()
        return
    from attendance_manager import ensure_session, send_attendance_panel
    session = ensure_session(group_id, date_str)
    await callback.answer()
    await send_attendance_panel(bot, callback.message.chat.id, session["id"], group_id, date_str, 0)


@dp.callback_query(lambda c: c.data == "att_noop" or c.data.startswith("att_page_") or c.data.startswith("att_mark_") or c.data.startswith("att_finish_"))
async def handle_teacher_att_actions(callback: CallbackQuery):
    data = callback.data
    user = get_user_by_telegram(str(callback.from_user.id))
    if data == "att_noop":
        await callback.answer()
        return
    if not user or user.get("login_type") != 3:
        await callback.answer()
        return
    if data.startswith("att_page_"):
        parts = data.split("_")
        session_id = int(parts[2])
        page = int(parts[3])
        session = get_session(session_id)
        if not session:
            await callback.answer()
            return
        group = get_group(session["group_id"])
        if not group or group.get("teacher_id") != user.get("id"):
            await callback.answer()
            return
        kb = build_attendance_keyboard(session_id, session["group_id"], session["date"], page)
        await callback.message.edit_reply_markup(reply_markup=kb)
        await callback.answer()
        return
    if data.startswith("att_mark_"):
        parts = data.split("_")
        session_id = int(parts[2])
        student_id = int(parts[3])
        status = parts[4]
        page = int(parts[5])
        session = get_session(session_id)
        if not session or session.get("status") == "closed":
            await callback.answer()
            return
        group = get_group(session["group_id"])
        if not group or group.get("teacher_id") != user.get("id"):
            await callback.answer()
            return
        add_attendance(student_id, session["group_id"], session["date"], status=status)
        kb = build_attendance_keyboard(session_id, session["group_id"], session["date"], page)
        await callback.message.edit_reply_markup(reply_markup=kb)
        await callback.answer()
        return
    if data.startswith("att_finish_"):
        session_id = int(data.split("_")[-1])
        session = get_session(session_id)
        if not session:
            await callback.answer()
            return
        group = get_group(session["group_id"])
        if not group or group.get("teacher_id") != user.get("id"):
            await callback.answer()
            return
        set_session_closed(session_id)
        await callback.answer()
        await callback.message.answer(t(detect_lang_from_user(user or callback.from_user), 'attendance_done_closed'))
        # notify admins via teacher bot (best-effort: cannot access admin IDs list here reliably)
        return


@dp.callback_query(lambda c: c.data in ('teacher_vocab_action_import', 'teacher_vocab_action_export'))
async def handle_teacher_vocab_action(callback: CallbackQuery):
    action = callback.data.split('_')[-1]  # import/export
    user = get_user_by_telegram(str(callback.from_user.id))
    lang = detect_lang_from_user(user or callback.from_user)
    if not user or user.get('login_type') != 3:
        await callback.answer()
        await callback.message.answer(t(lang, 'please_send_start'))
        return

    subj = (user.get('subject') or '').title()
    state = get_teacher_state(callback.message.chat.id)

    if action == 'import':
        logger.info(f"📥 Teacher vocab import action user_id={callback.from_user.id}")
        # Directly use teacher's subject since "Both" is removed
        state['step'] = 'await_vocab_file'
        state['data']['subject'] = subj
        await callback.message.answer(t(lang, 'send_vocab_file'), reply_markup=cancel_keyboard(lang))
        
        # ✅ Yangi to'g'ri template (user提供的实际文件)
        try:
            # Load the actual example file based on subject
            if subj.lower() == 'english':
                example_file = 'Vocabulary_importing_list_for_english.xlsx'
            else:
                example_file = 'Vocabulary_importing_list_for_russian.xlsx'
            
            # Read the actual template file
            with open(example_file, 'rb') as f:
                file_data = f.read()
            
            # Send the actual template file
            await bot.send_document(
                callback.message.chat.id,
                BufferedInputFile(file_data, filename="Vocabulary_importing_list_template.xlsx"),
                caption=f"📝 <b>{subj} faniga namuna fayl</b>\n\n"
                        f"Ushbu faylni to'ldirib yuboring. "
                        f"File nomi muhim emas, istalgan nom bilan yuborishingiz mumkin.\n"
                        f"Import qilish uchun faqat ustunlar tuzilishi muhim.",
                parse_mode='HTML'
            )
            
            # Save example words to database
            try:
                bio.seek(0)
                lang_code = 'en' if subj.lower() == 'english' else 'ru'
                import_words_from_excel(file_data, example_file, user['id'], subj, lang_code)
            except Exception as e:
                logger.error(f"Error saving example words to DB: {e}")
                
        except FileNotFoundError:
            # Fallback to generated template if file not found
            await callback.message.answer("❌ Namuna fayl topilmadi, avtomatik yaratilmoqda...")
            
            # Generate fallback template
            from openpyxl import Workbook
            from openpyxl.styles import Font
            import io

            wb = Workbook()
            ws = wb.active
            ws.title = "Template"
            
            # Headers based on subject
            if subj.lower() == 'english':
                headers = ['Level', 'Word', 'translation_uz', 'translation_ru', 'Example Sentence 1', 'Example Sentence 2']
            else:  # Russian
                headers = ['Level', 'Word', 'translation_uz', 'Definition', 'Example Sentence 1', 'Example Sentence 2']
            
            ws.append(headers)
            
            # Make headers bold
            for col in range(1, len(headers) + 1):
                ws.cell(row=1, column=col).font = Font(bold=True)
            
            bio = io.BytesIO()
            wb.save(bio)
            bio.seek(0)
            
            await bot.send_document(
                callback.message.chat.id,
                BufferedInputFile(bio.getvalue(), filename="Vocabulary_importing_list_template.xlsx"),
                caption=f"📝 <b>{subj} faniga namuna fayl</b>\n\n"
                        f"Ushbu faylni to'ldirib yuboring. "
                        f"File nomi muhim emas, istalgan nom bilan yuborishingiz mumkin.",
                parse_mode='HTML'
            )
            
        except Exception as e:
            logger.error(f"Template yuborish xatosi: {e}")
            await callback.message.answer("❌ Namuna faylni yuborishda xatolik yuz berdi")
        except Exception as e:
            logger.error(f"Template yuborish xatosi: {e}")
        await callback.answer()
        return

    if action == 'export':
        logger.info(f"📤 Teacher vocab export action user_id={callback.from_user.id}")
        # Directly export teacher's subject since "Both" is removed
        try:
            from vocabulary import export_words_to_xlsx
            file_data, filename = export_words_to_xlsx(subj)
            await bot.send_document(callback.message.chat.id, BufferedInputFile(file_data.getvalue(), filename))
        except Exception as e:
            await callback.message.answer(t(lang, 'export_failed', error=str(e)))
        await callback.answer()
        return



@dp.message(Command('import_vocab'))
async def cmd_import_vocab(message: Message):
    logger.debug(f"cmd_import_vocab: user_id={message.from_user.id}")
    user = get_user_by_telegram(str(message.from_user.id))
    lang = detect_lang_from_user(user or message.from_user)
    if not user or user.get('login_type') != 3:
        await message.answer(t(lang, 'please_send_start'))
        return
    await message.answer(t(lang, 'use_menu_button_vocab'))


@dp.message()
async def handle_teacher_file(message: Message):
    """Handles document upload only when in import flow"""
    state = get_teacher_state(message.chat.id)
    user = get_user_by_telegram(str(message.from_user.id))
    lang = detect_lang_from_user(user or message.from_user)
    if not state.get('step'):
        return

    if state['step'] == 'await_vocab_file':
        subject = state['data'].get('subject')
        # Validate subject
        if subject not in ['English', 'Russian']:
            await message.answer(t(lang, 'invalid_subject'))
            state['step'] = None
            return

        from vocabulary import import_words_from_excel
        import io

        doc = message.document
        bio = io.BytesIO()
        await message.bot.download(file=doc.file_id, destination=bio)
        bio.seek(0)

        # Enforce teacher's subject again for safety
        if user and (user.get('subject') or '').title() != subject.title() and (user.get('subject') or '').title() != 'Both':
            await message.answer(t(lang, 'only_own_subject_allowed'))
            state['step'] = None
            state['data'] = {}
            return

        lang_code = 'en' if subject.lower() == 'english' else 'ru'
        try:
            report = import_words_from_excel(bio.read(), doc.file_name or 'upload.xlsx', user['id'], subject, lang_code)
            await message.answer(
                f"✅ Import tugadi!\n"
                f"🆕 Yangi: {report['inserted']}\n"
                f"⏭ Duplicate (o'tkazib yuborildi): {report['skipped']}\n"
                f"Duplikatlarni ko‘rish: {', '.join(report.get('duplicates', [])[:5]) if report.get('duplicates') else 'Yo‘q'}"
            )
        except Exception as e:
            await message.answer(f"❌ Xatolik: {e}")

        state['step'] = None
        state['data'] = {}
        return


@dp.message(Command('export_vocab'))
async def cmd_export_vocab_teacher(message: Message):
    user = get_user_by_telegram(str(message.from_user.id))
    lang = detect_lang_from_user(user or message.from_user)
    if not user or user.get('login_type') != 3:
        await message.answer(t(lang, 'please_send_start'))
        return
    await message.answer(t(lang, 'use_menu_button_vocab'))


@dp.callback_query(lambda c: c.data.startswith('attendance_mark_'))
async def handle_callbacks(callback: CallbackQuery):
    data = callback.data
    
    if data.startswith('attendance_mark_'):
        parts = data.split('_')
        user_id = int(parts[2])
        group_id = int(parts[3])
        status = parts[4]  # Present/Absent
        
        today = datetime.utcnow().strftime('%Y-%m-%d')
        add_attendance(user_id, group_id, today, status)
        
        lang = detect_lang_from_user(get_user_by_telegram(str(user_id)) or callback.from_user)
        await callback.message.answer(t(lang, 'davomat_marked', status=status))
        await callback.answer()
        return


# Subject selection callback is no longer needed since "Both" is removed


async def run_teacher_bot():
    global bot
    if not TEACHER_BOT_TOKEN:
        raise RuntimeError("TEACHER_BOT_TOKEN is not set. Put it in .env (TEACHER_BOT_TOKEN=...) and retry.")
    bot = Bot(token=TEACHER_BOT_TOKEN)
    
    # Restore sessions on startup
    try:
        restored_count = restore_sessions_on_startup()
        logger.info(f"🔄 Restored {restored_count} teacher sessions on startup")
    except Exception as e:
        logger.error(f"Failed to restore sessions: {e}")
    
    import asyncio
    from config import ADMIN_CHAT_IDS
    asyncio.create_task(attendance_scheduler(bot, role="teacher", admin_chat_ids=ADMIN_CHAT_IDS))
    
    logger.info("Teacher bot started successfully")
    await dp.start_polling(bot)


@dp.error()
async def error_handler(event: types.ErrorEvent):
    logger.error(f"Error in teacher bot: {event.exception}", exc_info=True)


@dp.callback_query(lambda c: c.data.startswith('set_lang_me_'))
async def handle_set_lang_me_teacher(callback: CallbackQuery):
    code = callback.data.split('_')[-1]
    from db import set_user_language_by_telegram
    ok = set_user_language_by_telegram(str(callback.from_user.id), code)
    if ok:
        await callback.answer()
        await callback.message.answer(t(code, 'lang_set'))
        # Send updated main menu in new language
        await callback.message.answer(t(code, 'select_from_menu'), reply_markup=teacher_main_keyboard(code))
    else:
        await callback.answer()
        await callback.message.answer(t(code, 'please_send_start'))
