import logging
import re
from aiogram import Bot, Dispatcher, types
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import ReplyKeyboardRemove
from aiogram.filters import Command
import asyncio
import time

from config import STUDENT_BOT_TOKEN, ADMIN_BOT_TOKEN, SUBJECTS, ADMIN_CHAT_IDS
from db import (
    get_user_by_telegram, get_tests_by_subject, save_test_result, update_user_level, 
    enable_access, get_test_by_id, is_access_active, get_user_by_id, save_placement_session, 
    get_placement_session, clear_placement_session, add_diamonds, get_diamonds, 
    get_leaderboard_global, get_leaderboard_by_group, get_leaderboard_count, 
    get_leaderboard_count_by_group, get_group, get_user_groups, get_user_subjects, update_user_subjects,
    get_student_subjects, get_student_teachers
)
from auth import (
    verify_login, activate_user, compute_level, restore_sessions_on_startup, cleanup_inactive_accounts,
    process_login_message, get_login_state, set_login_state, clear_login_state, AuthMiddleware
)
from utils import student_main_keyboard, student_vocab_keyboard, create_dual_choice_keyboard, create_leaderboard_pagination_keyboard, create_language_selection_keyboard_for_self
from i18n import t, detect_lang_from_user
from vocabulary import search_words, get_words_by_subject_level, get_available_vocabulary_levels
from grammar_content import get_grammar_rules, A1_TOPICS, A2_TOPICS, B1_TOPICS
from logging_config import get_logger

# Setup logger
logger = get_logger(__name__)

bot: Bot | None = None
admin_bot: Bot | None = None
dp = Dispatcher()

# Setup authentication middleware
auth_middleware = AuthMiddleware(bot_type='student', expected_login_type=2)
dp.message.middleware(auth_middleware)
dp.callback_query.middleware(auth_middleware)

placement_state = {}
student_state = {}
vocab_state = {}
vocab_poll_map = {}  # poll_id -> metadata for vocab quiz
grammar_poll_map = {}  # poll_id -> metadata for grammar quiz

def get_student_state(chat_id: int):
    return student_state.setdefault(chat_id, {'step': None, 'data': {}})

def reset_student_state(chat_id: int):
    student_state.pop(chat_id, None)


def get_placement_state(user_id):
    key = str(user_id)
    return placement_state.setdefault(key, {'active': False, 'poll_map': {}})


def reset_placement_state(user_id):
    placement_state.pop(str(user_id), None)


def get_vocab_state(chat_id: int):
    return vocab_state.setdefault(chat_id, {'step': None, 'data': {}})


@dp.message(Command('vocab'))
async def cmd_vocab(message: types.Message):
    logger.debug(f"/vocab called by user_id={message.from_user.id}")
    user = get_user_by_telegram(str(message.from_user.id))
    lang = detect_lang_from_user(user or message.from_user)
    if not user or not is_access_active(user):
        await message.answer(t(lang, 'please_send_start'))
        return
    await message.answer(t(lang, 'vocab_title'), reply_markup=student_vocab_keyboard(lang))


@dp.message(Command('vocab_search'))
async def cmd_vocab_search(message: types.Message):
    logger.debug(f"/vocab_search called by user_id={message.from_user.id}")
    state = get_vocab_state(message.chat.id)
    state['step'] = 'search_wait'
    user = get_user_by_telegram(str(message.from_user.id))
    lang = detect_lang_from_user(user or message.from_user)
    await message.answer(t(lang, 'vocab_enter_query'))


@dp.message(Command('vocab_pref'))
async def cmd_vocab_pref(message: types.Message):
    logger.debug(f"/vocab_pref called by user_id={message.from_user.id}")
    state = get_vocab_state(message.chat.id)
    state['step'] = 'pref_wait'
    user = get_user_by_telegram(str(message.from_user.id))
    lang = detect_lang_from_user(user or message.from_user)
    await message.answer(t(lang, 'vocab_pref_prompt'))


@dp.message(Command('vocab_quiz'))
async def cmd_vocab_quiz(message: types.Message):
    logger.debug(f"/vocab_quiz called by user_id={message.from_user.id}")
    user = get_user_by_telegram(str(message.from_user.id))
    lang = detect_lang_from_user(user or message.from_user)
    if not user or not is_access_active(user):
        await message.answer(t(lang, 'please_send_start'))
        return
    from vocabulary import get_student_preference
    pref = get_student_preference(user['id'])
    if pref not in ('uz', 'ru'):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🇺🇿 Uzbekcha", callback_data="vocab_pref_uz")],
            [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="vocab_pref_ru")],
        ])
        await message.answer(t(lang, 'vocab_choose_language'), reply_markup=kb)
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1) Multiple choice", callback_data="vocab_quiz_type_multiple_choice")],
        [InlineKeyboardButton(text="2) Gap filling", callback_data="vocab_quiz_type_gap_filling")],
        [InlineKeyboardButton(text="3) Definition", callback_data="vocab_quiz_type_definition")],
    ])
    await message.answer(t(lang, 'vocab_choose_type'), reply_markup=kb)


@dp.callback_query(lambda c: c.data.startswith("vocab_pref_"))
async def handle_vocab_pref_inline(callback: CallbackQuery):
    code = callback.data.split("_")[-1]
    user = get_user_by_telegram(str(callback.from_user.id))
    lang = detect_lang_from_user(user or callback.from_user)
    if not user:
        await callback.answer()
        await callback.message.answer(t(lang, 'please_send_start'))
        return
    if code not in ('uz', 'ru'):
        await callback.answer()
        return
    from vocabulary import save_student_preference
    save_student_preference(user['id'], code)
    await callback.answer(t(lang, 'saved'))
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1) Multiple choice", callback_data="vocab_quiz_type_multiple_choice")],
        [InlineKeyboardButton(text="2) Gap filling", callback_data="vocab_quiz_type_gap_filling")],
        [InlineKeyboardButton(text="3) Definition", callback_data="vocab_quiz_type_definition")],
    ])
    await callback.message.answer(t(lang, 'vocab_choose_type'), reply_markup=kb)


@dp.callback_query(lambda c: c.data.startswith("vocab_quiz_type_"))
async def handle_vocab_quiz_type(callback: CallbackQuery):
    qtype = callback.data.split("vocab_quiz_type_")[-1]
    user = get_user_by_telegram(str(callback.from_user.id))
    lang = detect_lang_from_user(user or callback.from_user)
    if not user or not is_access_active(user):
        await callback.answer()
        await callback.message.answer(t(lang, 'please_send_start'))
        return
    if qtype not in ('multiple_choice', 'gap_filling', 'definition'):
        await callback.answer()
        return
    state = get_vocab_state(callback.message.chat.id)
    state['data'] = {'qtype': qtype}
    state['step'] = 'quiz_choose_count'
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="5", callback_data="vocab_quiz_cnt_5"),
         InlineKeyboardButton(text="10", callback_data="vocab_quiz_cnt_10"),
         InlineKeyboardButton(text="15", callback_data="vocab_quiz_cnt_15")],
        [InlineKeyboardButton(text="20", callback_data="vocab_quiz_cnt_20"),
         InlineKeyboardButton(text="25", callback_data="vocab_quiz_cnt_25"),
         InlineKeyboardButton(text="30", callback_data="vocab_quiz_cnt_30")],
    ])
    await callback.answer()
    await callback.message.answer(t(lang, 'vocab_choose_count'), reply_markup=kb)


async def _countdown_message(chat_id: int, base_text: str, seconds: int):
    # Backwards-compat helper: send + edit countdown
    msg = await bot.send_message(chat_id, f"{base_text}\n⏳ {seconds} s")
    start = time.monotonic()
    for s in [15, 10, 5, 4, 3, 2, 1]:
        target = seconds - s
        now = time.monotonic() - start
        if target > now:
            await asyncio.sleep(target - now)
        try:
            await bot.edit_message_text(f"{base_text}\n⏳ {s} s", chat_id=chat_id, message_id=msg.message_id)
        except Exception:
            pass
    return msg


async def _edit_countdown_steps(chat_id: int, message_id: int, base_text: str, total_seconds: int = 20):
    """Edit countdown message at specific remaining seconds."""
    # Dynamic schedule for both 20s (vocab) and 30s (grammar)
    candidates = [total_seconds, 20, 15, 10, 5, 4, 3, 2, 1]
    schedule = []
    for s in candidates:
        if 1 <= s <= total_seconds and s not in schedule:
            schedule.append(s)
    start = time.monotonic()
    for s in schedule:
        target = total_seconds - s
        now = time.monotonic() - start
        if target > now:
            await asyncio.sleep(target - now)
        try:
            remaining = total_seconds - int((time.monotonic() - start))
            await bot.edit_message_text(f"{base_text}\n⏳ {remaining} s", chat_id=chat_id, message_id=message_id)
        except Exception:
            pass


async def _run_vocab_quiz(chat_id: int, user: dict, qtype: str, cnt: int):
    from vocabulary import generate_quiz, get_student_preference, get_available_vocabulary_levels
    pref = get_student_preference(user['id']) or 'uz'
    
    # Get words up to user's level only
    available_levels = get_available_vocabulary_levels(user.get('level', 'A1'))
    questions = []
    
    for level in available_levels:
        level_questions = generate_quiz(user['id'], user.get('subject'), level, cnt, qtype, pref)
        questions.extend(level_questions)
        if len(questions) >= cnt:
            break
    
    questions = questions[:cnt]  # Limit to requested count
    
    if not questions:
        lang = detect_lang_from_user(user)
        await bot.send_message(chat_id, t(lang, 'vocab_no_questions'))
        return

    correct_count = 0
    wrong_count = 0
    skipped_count = 0
    
    await bot.send_message(chat_id, f"🧠 <b>Vocabulary Test - Boshlandi!</b>\n\nHar bir to'g'ri javob uchun 0.5 D'coin beriladi.", parse_mode="HTML")
    
    for idx, q in enumerate(questions, start=1):
        opts = q.get('options') or []
        if len(opts) != 4:
            skipped_count += 1
            continue
        correct = q.get('correct')
        try:
            correct_idx = opts.index(correct)
        except Exception:
            correct_idx = 0
        question_text = f"{idx}/{len(questions)} — {q.get('prompt')}"

        # Countdown message under the poll (separate message, edited)
        countdown_msg = await bot.send_message(chat_id, f"{question_text}\n⏳ 30 s")

        poll_msg = await bot.send_poll(
            chat_id=chat_id,
            question=question_text,
            options=[str(o) for o in opts],
            type='quiz',
            correct_option_id=correct_idx,
            is_anonymous=False,
            open_period=30,
        )
        poll_id = poll_msg.poll.id
        ev = asyncio.Event()
        vocab_poll_map[poll_id] = {
            'event': ev,
            'chat_id': chat_id,
            'user_id': user['id'],
            'correct': correct_idx,
            'chosen': None,
            'poll_message_id': poll_msg.message_id,
            'countdown_message_id': countdown_msg.message_id,
        }

        # Run countdown edits in background so we can move on immediately after answer
        countdown_task = asyncio.create_task(_edit_countdown_steps(chat_id, countdown_msg.message_id, question_text, 30))

        try:
            await asyncio.wait_for(ev.wait(), timeout=30.5)
        except Exception:
            pass

        meta = vocab_poll_map.pop(poll_id, None)
        chosen = meta.get('chosen') if meta else None
        if chosen is None:
            skipped_count += 1
        elif chosen == correct_idx:
            correct_count += 1
        else:
            wrong_count += 1

        # Stop countdown ASAP
        try:
            countdown_task.cancel()
        except Exception:
            pass

        # Delete poll + countdown messages to keep chat clean and fast
        try:
            await bot.delete_message(chat_id, poll_msg.message_id)
        except Exception:
            pass
        try:
            await bot.delete_message(chat_id, countdown_msg.message_id)
        except Exception:
            pass

    total = correct_count + wrong_count + skipped_count
    
    # Calculate D'coin rewards
    dcoin_reward = correct_count * 0.5
    dcoin_penalty_skipped = skipped_count * 0.1
    dcoin_penalty_wrong = wrong_count * 0.25
    net_dcoin = dcoin_reward - dcoin_penalty_skipped - dcoin_penalty_wrong
    
    # Update D'coin balance only on first attempt
    if net_dcoin != 0:
        add_diamonds(user['id'], net_dcoin)
    
    # Record test history
    from db import add_test_history
    add_test_history(user['id'], 'vocabulary', None, correct_count, wrong_count, skipped_count)
    
    # Create detailed results
    result_lines = [
        f"🧠 <b>Vocabulary Test Natijalari</b>",
        "",
        f"📝 <b>Jami savollar:</b> {total}",
        f"✅ <b>To'g'ri javoblar:</b> {correct_count}",
        f"❌ <b>Xato javoblar:</b> {wrong_count}",
        f"⏭️ <b>O'tkazib yuborilgan:</b> {skipped_count}",
        "",
        f"� <b>D'coin hisobi:</b>",
        f"🪙 +{correct_count} × 0.5 = +{dcoin_reward:.1f} D'coin (to'g'ri javoblar)",
    ]
    
    if skipped_count > 0:
        result_lines.append(f"➖ {skipped_count} × 0.1 = -{dcoin_penalty_skipped:.1f} D'coin (o'tkazib yuborilgan)")
    
    if wrong_count > 0:
        result_lines.append(f"➖ {wrong_count} × 0.25 = -{dcoin_penalty_wrong:.1f} D'coin (xato javoblar)")
    
    result_lines.append(f"💎 <b>Jami D'coin:</b> {net_dcoin:+.1f}")
    
    current_balance = get_diamonds(user['id'])
    result_lines.append(f"💼 <b>Joriy balans:</b> {current_balance:.1f} D'coin")
    
    await bot.send_message(chat_id, "\n".join(result_lines), parse_mode="HTML")


async def show_grammar_levels(chat_id: int, user: dict):
    lang = detect_lang_from_user(user)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📘 A1 Level", callback_data="gr_lvl_A1")],
        [InlineKeyboardButton(text="📗 A2 Level", callback_data="gr_lvl_A2")],
        [InlineKeyboardButton(text="📙 B1 Level", callback_data="gr_lvl_B1")],
        [InlineKeyboardButton(text="📕 B2 Level", callback_data="gr_lvl_B2")],
        [InlineKeyboardButton(text="📓 C1 Level", callback_data="gr_lvl_C1")],
    ])
    await bot.send_message(chat_id, "📚 <b>Grammar Rules - Level Tanlang</b>\n\nQaysi leveldagi grammatika qoidalarini ko'rishni istaysiz?", reply_markup=kb)


def _topics_page(topics: list, page: int, size: int = 10):
    start = max(0, page) * size
    return topics[start:start + size]


def _topic_list_keyboard(level: str, page_topics: list, page: int, total_pages: int, lang: str):
    rows = []
    nums = []
    for i, tp in enumerate(page_topics, start=1):
        nums.append(InlineKeyboardButton(text=str(i), callback_data=f"gr_topic_pick:{level}:{tp.topic_id}"))
    if nums:
        rows.append(nums[:5])
        if len(nums) > 5:
            rows.append(nums[5:10])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text=t(lang, 'btn_back'), callback_data=f"gr_topic_page:{level}:{page-1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text=t(lang, 'btn_next'), callback_data=f"gr_topic_page:{level}:{page+1}"))
    if nav:
        rows.append(nav)
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _render_topics(chat_id: int, user: dict, level: str, page: int = 0):
    from grammar_content import get_topics_by_level
    lang = detect_lang_from_user(user)
    topics = get_topics_by_level(level)
    if not topics:
        await bot.send_message(chat_id, "❌ Bu level uchun grammatika mavzulari hozircha mavjud emas.")
        return
    
    # Show all topics at once with numbers
    lines = [f"📚 <b>{level} Level - Grammatika Mavzulari</b>", f"Jami {len(topics)} ta mavzu", ""]
    for idx, tp in enumerate(topics, start=1):
        lines.append(f"<b>{idx}.</b> {tp.title}")
    
    lines.append("\n📝 <b>Mavzu raqamini kiriting:</b>")
    lines.append("Masalan: 1, 5, 12")
    
    # Set state for number selection
    state = get_student_state(chat_id)
    state['step'] = 'grammar_topic_select'
    state['data'] = {'level': level, 'topics': topics}
    
    await bot.send_message(chat_id, "\n".join(lines), parse_mode="HTML")


async def _show_topic(chat_id: int, user: dict, level: str, topic_id: str):
    from grammar_content import get_topic
    from db import get_grammar_attempts
    lang = detect_lang_from_user(user)
    topic = get_topic(level, topic_id)
    if not topic:
        await bot.send_message(chat_id, "❌ Mavzu topilmadi")
        return
    
    attempts = get_grammar_attempts(user['id'], topic.topic_id)
    left = max(0, 2 - attempts)
    
    # Create topic display
    lines = [f"📚 <b>{topic.title}</b>", ""]
    lines.append(f"<b>📖 Qoida:</b>")
    lines.append(topic.rule)
    lines.append("")
    
    if left > 0:
        lines.append(f"🧪 <b>Test qilish imkoniyatlari: {left}/2</b>")
    else:
        lines.append(f"❌ <b>Test qilish imkoniyatlari tugagan: 0/2</b>")
    
    # Create keyboard
    if left > 0:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"🧪 Testni boshlash ({left}/2)", callback_data=f"gr_start:{level}:{topic.topic_id}")],
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"gr_back_to_topics:{level}")]
        ])
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"gr_back_to_topics:{level}")]
        ])
    
    await bot.send_message(chat_id, "\n".join(lines), reply_markup=kb, parse_mode="HTML")


async def _run_grammar_quiz(chat_id: int, user: dict, level: str, topic_id: str):
    from grammar_content import get_topic
    from db import get_grammar_attempts, increment_grammar_attempt
    lang = detect_lang_from_user(user)
    topic = get_topic(level, topic_id)
    if not topic:
        await bot.send_message(chat_id, "❌ Mavzu topilmadi")
        return
    
    attempts = get_grammar_attempts(user['id'], topic.topic_id)
    if attempts >= 2:
        await bot.send_message(chat_id, "❌ Bu mavzu uchun test qilish imkoniyatlari tugagan (maksimal 2 marta)")
        return
    
    # Consume an attempt at start
    increment_grammar_attempt(user['id'], topic.topic_id)

    total_seconds = 30
    correct_count = 0
    wrong_count = 0
    skipped_count = 0
    
    # Check if this is first attempt (for D'coin rewards)
    is_first_attempt = attempts == 0

    await bot.send_message(chat_id, f"🧪 <b>{topic.title} - Test boshlandi!</b>\n\nHar bir savol uchun {total_seconds} soniya vaqt bor.", parse_mode="HTML")

    for idx, q in enumerate(topic.questions, start=1):
        question_text = f"<b>{idx}/{len(topic.questions)} — {q.prompt}</b>"
        countdown_msg = await bot.send_message(chat_id, f"{question_text}\n⏳ {total_seconds} s", parse_mode="HTML")
        poll_msg = await bot.send_poll(
            chat_id=chat_id,
            question=question_text,
            options=[str(o) for o in q.options],
            type='quiz',
            correct_option_id=q.correct_index,
            is_anonymous=False,
            open_period=total_seconds,
        )
        poll_id = poll_msg.poll.id
        ev = asyncio.Event()
        grammar_poll_map[poll_id] = {
            'event': ev,
            'correct': q.correct_index,
            'chosen': None,
            'countdown_message_id': countdown_msg.message_id,
            'poll_message_id': poll_msg.message_id,
        }
        countdown_task = asyncio.create_task(_edit_countdown_steps(chat_id, countdown_msg.message_id, question_text, total_seconds))
        try:
            await asyncio.wait_for(ev.wait(), timeout=total_seconds + 0.5)
        except Exception:
            pass
        meta = grammar_poll_map.pop(poll_id, None)
        chosen = meta.get('chosen') if meta else None
        if chosen is None:
            skipped_count += 1
        elif chosen == q.correct_index:
            correct_count += 1
        else:
            wrong_count += 1
        try:
            countdown_task.cancel()
        except Exception:
            pass
        try:
            await bot.delete_message(chat_id, poll_msg.message_id)
        except Exception:
            pass
        try:
            await bot.delete_message(chat_id, countdown_msg.message_id)
        except Exception:
            pass

    total = correct_count + wrong_count + skipped_count
    
    # Calculate percentage
    percentage = (correct_count / total * 100) if total > 0 else 0
    
    # Calculate D'coin rewards (only for first attempt)
    dcoin_reward = 0
    dcoin_penalty_skipped = 0
    dcoin_penalty_wrong = 0
    
    if is_first_attempt:
        dcoin_reward = correct_count * 1.0  # 1 D'coin per correct answer
        dcoin_penalty_skipped = skipped_count * 0.25  # -0.25 per skipped
        dcoin_penalty_wrong = wrong_count * 0.5  # -0.5 per wrong answer
    
    net_dcoin = dcoin_reward - dcoin_penalty_skipped - dcoin_penalty_wrong
    
    # Update D'coin balance only on first attempt
    if is_first_attempt and net_dcoin != 0:
        add_diamonds(user['id'], net_dcoin)
    
    # Record test history
    from db import add_test_history
    add_test_history(user['id'], 'grammar', topic.topic_id, correct_count, wrong_count, skipped_count)
    
    # Detailed results
    result_lines = [
        f"📊 <b>{topic.title} - Test Natijalari</b>",
        "",
        f"📈 <b>Umumiy ko'rsatkich:</b> {percentage:.1f}%",
        "",
        f"📝 <b>Jami savollar:</b> {total}",
        f"✅ <b>To'g'ri javoblar:</b> {correct_count}",
        f"❌ <b>Xato javoblar:</b> {wrong_count}",
        f"⏭️ <b>O'tkazib yuborilgan:</b> {skipped_count}",
        "",
        f"🔄 <b>Qolgan urinishlar:</b> {max(0, 1 - attempts)}/2"
    ]
    
    # Add D'coin information only for first attempt
    if is_first_attempt:
        result_lines.extend([
            "",
            f"💰 <b>D'coin hisobi:</b>",
            f"🪙 +{correct_count} × 1.0 = +{dcoin_reward:.1f} D'coin (to'g'ri javoblar)",
        ])
        
        if skipped_count > 0:
            result_lines.append(f"➖ {skipped_count} × 0.25 = -{dcoin_penalty_skipped:.1f} D'coin (o'tkazib yuborilgan)")
        
        if wrong_count > 0:
            result_lines.append(f"➖ {wrong_count} × 0.5 = -{dcoin_penalty_wrong:.1f} D'coin (xato javoblar)")
        
        result_lines.extend([
            f"💎 <b>Jami D'coin:</b> {net_dcoin:+.1f}",
            f"💼 <b>Joriy balans:</b> {get_diamonds(user['id']):.1f} D'coin"
        ])
    else:
        result_lines.append("")
        result_lines.append("💰 <b>D'coin faqat birinchi urinishda beriladi</b>")
    
    # Add performance feedback
    if percentage >= 80:
        result_lines.append("\n🎉 <b>A'lo!</b> Siz ajoyib natija ko'rsatdingiz!")
    elif percentage >= 60:
        result_lines.append("\n👍 <b>Yaxshi!</b> Siz yaxshi natija ko'rsatdingiz!")
    elif percentage >= 40:
        result_lines.append("\n📚 <b>Qoniqarli!</b> Qoidalarni takrorlang, yaxshiroq bo'ladi!")
    else:
        result_lines.append("\n💪 <b>Harakat qiling!</b> Qoidalarni diqqat bilan o'qing va qayta urinib ko'ring!")
    
    await bot.send_message(chat_id, "\n".join(result_lines), parse_mode="HTML")


@dp.callback_query(lambda c: c.data.startswith("vocab_quiz_cnt_"))
async def handle_vocab_quiz_count(callback: CallbackQuery):
    try:
        cnt = int(callback.data.split("_")[-1])
    except Exception:
        await callback.answer()
        return
    if cnt not in (5, 10, 15, 20, 25, 30):
        await callback.answer()
        return
    state = get_vocab_state(callback.message.chat.id)
    qtype = (state.get('data') or {}).get('qtype')
    user = get_user_by_telegram(str(callback.from_user.id))
    lang = detect_lang_from_user(user or callback.from_user)
    if not user or not is_access_active(user) or not qtype:
        await callback.answer()
        await callback.message.answer(t(lang, 'please_send_start'))
        return
    state['step'] = None
    await callback.answer(t(lang, 'started'))
    await _run_vocab_quiz(callback.message.chat.id, user, qtype, cnt)


@dp.callback_query(lambda c: c.data.startswith("gr_lvl_"))
async def handle_grammar_level(callback: CallbackQuery):
    user = get_user_by_telegram(str(callback.from_user.id))
    lang = detect_lang_from_user(user or callback.from_user)
    if not user or not is_access_active(user):
        await callback.answer()
        await callback.message.answer(t(lang, 'please_send_start'))
        return
    level = callback.data.split("_")[-1].upper()
    await callback.answer()
    await _render_topics(callback.message.chat.id, user, level, 0)


@dp.callback_query(lambda c: c.data.startswith("gr_topic_page:"))
async def handle_grammar_topic_page(callback: CallbackQuery):
    user = get_user_by_telegram(str(callback.from_user.id))
    lang = detect_lang_from_user(user or callback.from_user)
    if not user or not is_access_active(user):
        await callback.answer()
        await callback.message.answer(t(lang, 'please_send_start'))
        return
    parts = callback.data.split(":")
    level = parts[1].upper()
    page = int(parts[2])
    await callback.answer()
    await _render_topics(callback.message.chat.id, user, level, page)


@dp.callback_query(lambda c: c.data.startswith("gr_topic_pick:"))
async def handle_grammar_topic_pick(callback: CallbackQuery):
    user = get_user_by_telegram(str(callback.from_user.id))
    lang = detect_lang_from_user(user or callback.from_user)
    if not user or not is_access_active(user):
        await callback.answer()
        await callback.message.answer(t(lang, 'please_send_start'))
        return
    _, level, topic_id = callback.data.split(":", 2)
    await callback.answer()
    await _show_topic(callback.message.chat.id, user, level.upper(), topic_id)


@dp.callback_query(lambda c: c.data.startswith("grammar_topic:"))
async def handle_grammar_topic_selection(callback: CallbackQuery):
    user = get_user_by_telegram(str(callback.from_user.id))
    if not user:
        await callback.answer("User not found")
        return
    
    topic_id = callback.data.split(":", 1)[1]
    lang = detect_lang_from_user(user)
    
    # Get the topic details
    from grammar_content import get_topic
    from db import get_grammar_attempts
    
    # Find the topic by ID across all levels
    topic = None
    for level in ['A1', 'A2', 'B1', 'B2', 'C1']:
        found_topic = get_topic(level, topic_id)
        if found_topic:
            topic = found_topic
            break
    
    if not topic:
        await callback.answer("Topic not found")
        return
    
    attempts = get_grammar_attempts(user['id'], topic.topic_id)
    left = max(0, 2 - attempts)
    rules = topic.rule
    text = f"📚 {topic.title}\n\n{rules}\n\n{t(lang, 'grammar_attempts_left', left=left)}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, 'grammar_start_test'), callback_data=f"gr_start:{topic.level}:{topic.topic_id}")],
    ])
    await callback.message.answer(text, reply_markup=kb)
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("gr_back_to_topics:"))
async def handle_back_to_topics(callback: CallbackQuery):
    user = get_user_by_telegram(str(callback.from_user.id))
    if not user:
        await callback.answer("User not found")
        return
    
    level = callback.data.split(":")[-1]
    await callback.answer()
    await _render_topics(callback.message.chat.id, user, level, 0)


async def handle_show_dcoin_balance(chat_id: int, user: dict = None):
    """D'coin balansini ko'rsatish"""
    if user is None:
        user = get_user_by_telegram(str(chat_id))
        if not user:
            return
    
    diamonds = get_diamonds(user['id'])
    lang = detect_lang_from_user(user)
    
    text = f"💎 **Sizning D'coin balansingiz:** {diamonds:.1f} D'coin"
    await bot.send_message(chat_id, text, parse_mode='HTML')


@dp.callback_query(lambda c: c.data == "exit_vocab_search")
async def handle_exit_vocab_search(callback: CallbackQuery):
    user = get_user_by_telegram(str(callback.from_user.id))
    if not user:
        await callback.answer("User not found")
        return
    
    lang = detect_lang_from_user(user)
    state = get_vocab_state(callback.message.chat.id)
    state['step'] = None  # Clear search state
    state['data'] = {}
    
    await callback.message.edit_text("🔙 <b>So'z qidirishdan chiqildi</b>", parse_mode="HTML")
    await callback.answer()


@dp.callback_query(lambda c: c.data == "show_more_vocab_results")
async def handle_show_more_vocab_results(callback: CallbackQuery):
    user = get_user_by_telegram(str(callback.from_user.id))
    if not user:
        await callback.answer("User not found")
        return
    
    lang = detect_lang_from_user(user)
    state = get_vocab_state(callback.message.chat.id)
    
    # Get search data from state
    search_data = state.get('data', {})
    subject = search_data.get('subject') or user.get('subject')
    query = search_data.get('query', '')
    
    if not subject or not query:
        await callback.answer("Search data not found")
        return
    
    # Get more results
    results = search_words(subject, query)
    if not results:
        await callback.answer("No more results")
        return
    
    # Show next 5 results
    start_idx = search_data.get('shown_count', 5)
    next_results = results[start_idx:start_idx + 5]
    
    if not next_results:
        await callback.answer("No more results")
        return
    
    # Update shown count
    search_data['shown_count'] = start_idx + len(next_results)
    state['data'] = search_data
    
    lines = [f"🔍 <b>Yana {len(next_results)} ta natija:</b>"]
    
    for i, r in enumerate(next_results, start=start_idx + 1):
        word = r.get('word', '-')
        translation_uz = r.get('translation_uz', '-')
        translation_ru = r.get('translation_ru', '-')
        definition = r.get('definition', '-')
        example = r.get('example', '-')
        
        result_text = f"<b>{i}. {word}</b>\n"
        if translation_uz != '-':
            result_text += f"🇺🇿 {translation_uz}\n"
        if translation_ru != '-':
            result_text += f"🇷🇺 {translation_ru}\n"
        if definition != '-':
            result_text += f"📖 {definition}\n"
        if example != '-':
            result_text += f"💬 {example}\n"
        
        lines.append(result_text)
    
    # Add navigation buttons
    nav_buttons = []
    if start_idx + len(next_results) < len(results):
        nav_buttons.append(InlineKeyboardButton(text="📄 Ko'proq natijalar", callback_data="show_more_vocab_results"))
    
    nav_buttons.append(InlineKeyboardButton(text="🔙 Chiqish", callback_data="exit_vocab_search"))
    
    if nav_buttons:
        kb = InlineKeyboardMarkup(inline_keyboard=[nav_buttons])
        lines.append("")
        lines.append("📊 Boshqaqa tugmalar orqali navlash:")
    else:
        kb = None
        lines.append("🔙 Barcha natijalar ko'rsatildi.")
    
    await callback.message.edit_text("\n".join(lines), reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("rating_"))
async def handle_rating_period(callback: CallbackQuery):
    user = get_user_by_telegram(str(callback.from_user.id))
    if not user:
        await callback.answer("User not found")
        return
    
    period = callback.data.split("_")[1]  # daily, weekly, monthly
    lang = detect_lang_from_user(user)
    
    from db import get_rating_leaderboard
    leaderboard_data = get_rating_leaderboard(user['id'], period)
    
    if not leaderboard_data:
        await callback.answer(f"❌ {period} reytingi hozircha mavjud emas.")
        return
    
    lines = [
        f"🏆 <b>{period.title()} Reytingi</b>",
        "",
        f"📊 <b>Top 10 o'quvchi:</b>",
        ""
    ]
    
    for i, entry in enumerate(leaderboard_data[:10], start=1):
        name = entry.get('name', 'Noma\'lum')
        score = entry.get('score', 0)
        dcoin = entry.get('dcoin', 0)
        
        lines.append(f"{i}. {name} - {score:.1f} ball ({dcoin:.1f} D'coin)")
    
    await callback.message.edit_text("\n".join(lines), parse_mode="HTML")
    await callback.answer()


async def show_student_progress(chat_id: int, user: dict, lang: str):
    """Show student's detailed progress"""
    from i18n import t
    from db import get_student_monthly_stats
    stats = get_student_monthly_stats(user['id'])
    
    lines = [
        f"📊 <b>Bu Oygi Progress</b>",
        "",
        f"📚 <b>O'rganilgan so'zlar:</b> {stats['words_learned']} ta",
        f"📖 <b>Tugallangan mavzular:</b> {stats['topics_completed']} ta",
        f"📝 <b>Testlar soni:</b> {stats['tests_taken']} ta",
        f"✅ <b>To'g'ri javoblar:</b> {stats['total_correct']} ta",
        f"❌ <b>Xato javoblar:</b> {stats['total_wrong']} ta",
        f"⏭️ <b>O'tkazib yuborilgan:</b> {stats['total_skipped']} ta",
        "",
        f"📈 <b>Umumiy ko'rsatkich:</b> {(stats['total_correct'] / (stats['tests_taken'] or 1) * 100):.1f}%" if stats['tests_taken'] > 0 else "0%"
    ]
    
    # Add previous months navigation
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 O'tgan oy", callback_data="progress_previous")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="progress_back")]
    ])
    
    await bot.send_message(chat_id, "\n".join(lines), reply_markup=kb, parse_mode="HTML")


async def show_feedback_menu(chat_id: int, user: dict, lang: str):
    """Show feedback menu with anonymous option"""
    from i18n import t
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Fikr bildirish", callback_data="feedback_anonymous")],
        [InlineKeyboardButton(text="👤 Fikr bildirish (ism bilan)", callback_data="feedback_named")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="feedback_back")]
    ])
    
    lines = [
        f"💬 <b>Fikr va Takliflar</b>",
        "",
        "Admin bilan bog'lanish uchun fikr bildirishingiz mumkin.",
        "",
        "🔒 <b>Anonim tarzda yuborilsangiz,</b>",
        "fikringiz adminga sizsiz yuboriladi.",
        "",
        "Agar o'zingiz ismingiz bilan yuborishni istasangiz,",
        "'👤 Fikr bildirish (ism bilan)' tugmasini bosing."
    ]
    
    await bot.send_message(chat_id, "\n".join(lines), reply_markup=kb, parse_mode="HTML")


async def show_test_menu(chat_id: int, user: dict, lang: str):
    """Show test menu options"""
    from i18n import t
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Grammar Test", callback_data="test_menu_grammar")],
        [InlineKeyboardButton(text="🧠 Vocabulary Test", callback_data="test_menu_vocabulary")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="test_menu_back")]
    ])
    await bot.send_message(chat_id, "📝 <b>Test Menyu</b>\n\nQaysi turdagi testni ishlamoqchisiz?", reply_markup=kb, parse_mode="HTML")


async def handle_test_menu(callback: CallbackQuery):
    """Handle test menu selection"""
    user = get_user_by_telegram(str(callback.from_user.id))
    if not user:
        await callback.answer("User not found")
        return
    
    action = callback.data.split("_")[-1]
    
    if action == "back":
        await callback.message.delete()
        return
    
    if action == "grammar":
        await callback.message.edit_text("📚 Grammar test uchun 📚 Grammar Rules tugmasini bosing.", parse_mode="HTML")
    elif action == "vocabulary":
        await callback.message.edit_text("🧠 Vocabulary test uchun 📖 Vocabulary tugmasini bosing.", parse_mode="HTML")
    
    await callback.answer()


async def handle_progress_navigation(callback: CallbackQuery):
    """Handle progress navigation"""
    user = get_user_by_telegram(str(callback.from_user.id))
    if not user:
        await callback.answer("User not found")
        return
    
    action = callback.data.split("_")[-1]
    
    if action == "back":
        await callback.message.delete()
        return
    
    # Handle previous month logic here if needed
    await callback.answer()


async def handle_feedback_submission(callback: CallbackQuery):
    """Handle feedback submission"""
    user = get_user_by_telegram(str(callback.from_user.id))
    if not user:
        await callback.answer("User not found")
        return
    
    action = callback.data.split("_")[-1]
    
    if action == "back":
        await callback.message.delete()
        return
    
    # Start feedback collection
    is_anonymous = action == "anonymous"
    
    state = get_student_state(callback.message.chat.id)
    state['step'] = 'feedback_wait'
    state['data'] = {'anonymous': is_anonymous}
    
    if is_anonymous:
        prompt = "📝 <b>Anonim fikr yuborish</b>\n\nFikringizni kiriting:"
    else:
        prompt = f"📝 <b>Fikr yuborish (ism bilan)</b>\n\nFikringizni kiriting:\n\nIsm: {user.get('first_name', '')}"
    
    await callback.message.edit_text(prompt, parse_mode="HTML")
    await callback.answer()


async def handle_feedback_text(message: types.Message):
    """Handle feedback text submission"""
    state = get_student_state(message.chat.id)
    
    if state.get('step') != 'feedback_wait':
        return
    
    user = get_user_by_telegram(str(message.from_user.id))
    if not user:
        return
    
    feedback_text = message.text.strip()
    is_anonymous = state.get('data', {}).get('anonymous', True)
    
    if not feedback_text:
        await message.answer("❌ Fikr bo'sh bo'lishi mumkin emas. Iltimos, fikr kiriting.")
        return
    
    # Save feedback
    from db import add_feedback
    add_feedback(user['id'], feedback_text, is_anonymous)
    
    # Clear state
    state['step'] = None
    state['data'] = {}
    
    # Confirm submission
    if is_anonymous:
        confirm_text = "✅ <b>Anonim fikringiz yuborildi!</b>\n\nAdmin ga yetkazildi. Rahmat!"
    else:
        confirm_text = f"✅ <b>Fikringiz yuborildi!</b>\n\nAdmin ga yetkazildi. Rahmat, {user.get('first_name', '')}!"
    
    await message.answer(confirm_text, parse_mode="HTML")


# Add callback handlers for feedback and progress
@dp.callback_query(lambda c: c.data.startswith("feedback_"))
async def handle_feedback_callbacks(callback: CallbackQuery):
    await handle_feedback_submission(callback)


@dp.callback_query(lambda c: c.data.startswith("progress_"))
async def handle_progress_callbacks(callback: CallbackQuery):
    await handle_progress_navigation(callback)


@dp.callback_query(lambda c: c.data.startswith("test_menu_"))
async def handle_test_menu_callbacks(callback: CallbackQuery):
    await handle_test_menu(callback)


# Add message handler for feedback text
@dp.message(lambda m: get_student_state(m.chat.id).get('step') == 'feedback_wait')
async def handle_feedback_message(message: types.Message):
    await handle_feedback_text(message)


@dp.callback_query(lambda c: c.data.startswith("gr_start:"))
async def handle_gr_start(callback: CallbackQuery):
    user = get_user_by_telegram(str(callback.from_user.id))
    lang = detect_lang_from_user(user or callback.from_user)
    if not user:
        await callback.answer(t(lang, 'not_registered'))
        return
    if not is_access_active(user):
        await callback.answer(t(lang, 'access_denied'))
        return

    parts = callback.data.split(":")
    level = parts[1]
    topic_id = parts[2]
    await _run_grammar_quiz(callback.message.chat.id, user, level.upper(), topic_id)
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("vocab_search_subject:"))
async def handle_vocab_search_subject(callback: CallbackQuery):
    user = get_user_by_telegram(str(callback.from_user.id))
    if not user:
        await callback.answer("User not found")
        return
    
    subject = callback.data.split(":", 1)[1]
    lang = detect_lang_from_user(user)
    
    # Set search state with selected subject
    state = get_vocab_state(callback.message.chat.id)
    state['step'] = 'search_wait'
    state['data'] = {'subject': subject}
    
    await callback.message.edit_text(
        f"🔎 <b>{subject} - So'z izlash</b>\n\nIzlash uchun so'zni kiriting:",
        parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("grammar_rules:"))
async def handle_grammar_rules_subject(callback: CallbackQuery):
    user = get_user_by_telegram(str(callback.from_user.id))
    if not user:
        await callback.answer("User not found")
        return
    
    user_subjects = get_user_subjects(user['id'])
    if len(user_subjects) <= 1:
        # If only one subject, proceed directly
        subject = user_subjects[0] if user_subjects else 'English'
        await show_grammar_topics(callback.message.chat.id, user, subject)
    else:
        # Show subject selection
        await show_subject_selection(callback.message.chat.id, user, "grammar_rules")
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("grammar_rules:"))
async def handle_grammar_rules_subject_selection(callback: CallbackQuery):
    user = get_user_by_telegram(str(callback.from_user.id))
    if not user:
        await callback.answer("User not found")
        return
    
    parts = callback.data.split(":")
    subject = parts[1] if len(parts) > 1 else 'English'
    
    await show_grammar_topics(callback.message.chat.id, user, subject)
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("vocab_quiz:"))
async def handle_vocab_quiz_subject(callback: CallbackQuery):
    user = get_user_by_telegram(str(callback.from_user.id))
    if not user:
        await callback.answer("User not found")
        return
    
    user_subjects = get_user_subjects(user['id'])
    if len(user_subjects) <= 1:
        # If only one subject, proceed directly
        subject = user_subjects[0] if user_subjects else 'English'
        await cmd_vocab_quiz_with_subject(callback.message.chat.id, user, subject)
    else:
        # Show subject selection
        await show_subject_selection(callback.message.chat.id, user, "vocab_quiz")
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("vocab_quiz:"))
async def handle_vocab_quiz_subject_selection(callback: CallbackQuery):
    user = get_user_by_telegram(str(callback.from_user.id))
    if not user:
        await callback.answer("User not found")
        return
    
    parts = callback.data.split(":")
    subject = parts[1] if len(parts) > 1 else 'English'
    
    await cmd_vocab_quiz_with_subject(callback.message.chat.id, user, subject)
    await callback.answer()


@dp.message(lambda m: bool(get_vocab_state(m.chat.id).get('step')) and not (m.text and m.text.startswith('/')))
async def handle_vocab_message(message: types.Message):
    state = get_vocab_state(message.chat.id)
    logger.info(f"💬 STUDENT VOCAB MESSAGE: {message.text} | User: {message.from_user.id}")
    user = get_user_by_telegram(str(message.from_user.id))
    lang = detect_lang_from_user(user or message.from_user)
    from vocabulary import search_words, save_student_preference

    if state['step'] == 'search_wait':
        query = message.text.strip()
        
        # Handle exit command
        if query.lower() in ['exit', 'chiqish', 'quit', 'orqaga']:
            state['step'] = None
            state['data'] = {}
            await message.answer("🔙 <b>So'z qidirishdan chiqildi</b>", parse_mode="HTML")
            return
        
        # Get subject from state data (for multi-subject users) or from user
        subject = state.get('data', {}).get('subject') or user.get('subject')
        
        if not subject:
            await message.answer("❌ Fan ma'lumotlari topilmadi. Iltimos, qaytadan urinib ko'ring.")
            state['step'] = None
            return
        
        results = search_words(subject, query)
        if not results:
            # Add exit button
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Chiqish", callback_data="exit_vocab_search")]
            ])
            await message.answer("🔍 So'zlar topilmadi. Qayta urinib ko'ring yoki chiqish:", reply_markup=kb)
            state['data'] = {'subject': subject, 'query': query, 'shown_count': 0}
            return
        
        await message.answer(f"🔍 <b>{subject} - '{query}' uchun {len(results)} ta natija:</b>", parse_mode="HTML")
        
        # Store search data in state
        state['data'] = {'subject': subject, 'query': query, 'shown_count': 5}
        
        # Display first 5 results with exit button
        for i, r in enumerate(results[:5], 1):
            word = r.get('word', '-')
            translation_uz = r.get('translation_uz', '-')
            translation_ru = r.get('translation_ru', '-')
            definition = r.get('definition', '-')
            example = r.get('example', '-')
            
            result_text = f"<b>{i}. {word}</b>\n"
            if translation_uz != '-':
                result_text += f"🇺🇿 {translation_uz}\n"
            if translation_ru != '-':
                result_text += f"🇷🇺 {translation_ru}\n"
            if definition != '-':
                result_text += f"📖 {definition}\n"
            if example != '-':
                result_text += f"💬 {example}\n"
            
            await message.answer(result_text, parse_mode="HTML")
        
        # Add navigation buttons
        nav_buttons = [InlineKeyboardButton(text="🔙 Chiqish", callback_data="exit_vocab_search")]
        if len(results) > 5:
            nav_buttons.insert(0, InlineKeyboardButton(text="📄 Ko'proq natijalar", callback_data="show_more_vocab_results"))
        
        kb = InlineKeyboardMarkup(inline_keyboard=[nav_buttons])
        await message.answer("📊 Boshqaqa tugmalar orqali navlash:", reply_markup=kb)
        
        state['step'] = None
        state['data'] = {}
        return

    if state['step'] == 'pref_wait':
        pref = message.text.strip().lower()
        if pref not in ('uz', 'ru'):
            await message.answer(t(lang, 'only_uz_or_ru'))
            return
        save_student_preference(user['id'], pref)
        await message.answer(t(lang, 'saved'))
        state['step'] = None
        return

    # Vocabulary tests must be Telegram quiz polls only (no text-mode quizzes)
    if state.get('step') in ('quiz_ask_type', 'quiz_ask_count'):
        state['step'] = None
        state['data'] = {}
        await message.answer(t(lang, 'vocab_quiz_only_polls'))
        return


@dp.message(Command('start'))
async def cmd_start(message: types.Message):
    """Handle /start command - check login status or show login instructions"""
    telegram_id = str(message.from_user.id)
    user = get_user_by_telegram(telegram_id)
    
    # If user is already logged in, show main menu
    if user and user.get('logged_in'):
        lang = detect_lang_from_user(user)
        await message.answer(t(lang, 'welcome_back'), reply_markup=student_main_keyboard(lang))
        return
    
    # Clear any existing login state and start new login flow
    clear_login_state(telegram_id)
    reset_placement_state(message.from_user.id)
    
    # Start two-step login flow
    set_login_state(telegram_id, {'step': 'ask_login', 'data': {}})
    
    lang = detect_lang_from_user(message.from_user)
    
    await message.answer(t(lang, 'student_login_title'))
    await message.answer(t(lang, 'ask_login_id'))


@dp.message(lambda m: not (m.text or '').startswith('/'))
async def handle_login_and_messages(message: types.Message):
    """Ikki bosqichli login + eski formatni qo‘llab-quvvatlaydi"""
    telegram_id = str(message.from_user.id)
    login_state = get_login_state(telegram_id)

    # Login jarayonida bo‘lsa yoki eski formatda (:) bo‘lsa — process qil
    if login_state.get('step') in ('ask_login', 'ask_password') or ':' in (message.text or ''):
        success = await process_login_message(message, expected_login_type=2)
        if success:
            user = get_user_by_telegram(telegram_id)
            lang = detect_lang_from_user(user or message.from_user)
            await message.answer(t(lang, 'login_success'))
            
            # Check if this is a new user (first time login) and needs placement test
            if user and user.get('password_used') == 0:
                # This is a new user, start placement test
                try:
                    await start_placement_test(message.chat.id)
                except Exception as e:
                    logger.error(f"Error starting placement test for new user {user['id']}: {e}")
                    # If placement test fails, send to main menu
                    await message.answer(t(lang, 'select_from_menu'), reply_markup=student_main_keyboard(lang))
            else:
                # Existing user, send to main menu
                await message.answer(t(lang, 'select_from_menu'), reply_markup=student_main_keyboard(lang))
        return  # Jarayon tugamaguncha boshqa hech narsa qilma

    # Agar login tugagan bo‘lsa — oddiy authenticated handler
    await handle_authenticated_message(message)


async def handle_authenticated_message(message: types.Message):
    """Handle messages from authenticated users"""
    user = get_user_by_telegram(str(message.from_user.id))
    lang = detect_lang_from_user(user or message.from_user)
    
    # Accept both legacy student login types (1 and 2)
    if not user or user.get('login_type') not in (1, 2):
        await message.answer(t(lang, 'please_send_start'))
        return

    state = get_student_state(message.chat.id)
    
    # Handle grammar topic number selection
    if state.get('step') == 'grammar_topic_select':
        try:
            topic_num = int(message.text.strip())
            topics = state.get('data', {}).get('topics', [])
            level = state.get('data', {}).get('level')
            
            if 1 <= topic_num <= len(topics):
                selected_topic = topics[topic_num - 1]
                state['step'] = None  # Clear state
                state['data'] = {}
                await _show_topic(message.chat.id, user, level, selected_topic.topic_id)
            else:
                await message.answer(f"❌ Noto'g'ri raqam! 1 dan {len(topics)} gacha bo'lgan raqamni kiriting.")
        except ValueError:
            await message.answer("❌ Iltimos, faqat raqam kiriting (masalan: 1, 5, 12)")
        return
    
    # Note: Subject handling is now done via inline buttons, no text input needed
    
    # Localized button comparisons
    materials_btn = '📚 ' + t(lang, 'grammar_rules')
    test_btn = '📝 ' + t(lang, 'test_btn')
    progress_btn = '📊 ' + t(lang, 'progress')
    survey_btn = '💬 ' + t(lang, 'survey')
    coins_btn = '💰 D\'coin'
    leaderboard_btn = '💎 ' + t(lang, 'leaderboard')
    vocab_btn = '📖 ' + t(lang, 'vocab_menu')

    vocab_search_btn = '🔎 ' + t(lang, 'vocab_search_btn')
    vocab_quiz_btn = '🧠 ' + t(lang, 'vocab_quiz_btn')
    vocab_pref_btn = '⚙️ ' + t(lang, 'vocab_pref_btn')
    back_btn = '⬅️ ' + t(lang, 'back_btn')
    profile_btn = '👤 ' + t(lang, 'my_profile')

    # Handle language reply-button press (show inline language selector)
    choose_lang_btn = '🌐 ' + t(lang, 'choose_lang')
    if message.text == choose_lang_btn or (message.text or '').strip().startswith('🌐'):
        await message.answer(t(lang, 'choose_lang'), reply_markup=create_language_selection_keyboard_for_self())
        return

    if message.text == profile_btn:
        await show_my_profile(message.chat.id, user)
        return

    if message.text == materials_btn:
        # Show grammar rules subject selection
        await show_subject_selection(message.chat.id, user, "grammar_rules")
        return

    if message.text == test_btn:
        await show_test_menu(message.chat.id, user, lang)
        return

    if message.text == progress_btn:
        await show_student_progress(message.chat.id, user, lang)
        return

    if message.text == survey_btn:
        await show_feedback_menu(message.chat.id, user, lang)
        return

    if message.text == coins_btn:
        await handle_show_dcoin_balance(message.chat.id, user)
        return

    if message.text == leaderboard_btn:
        await show_leaderboard(message.from_user.id, message.chat.id, 0, 'global')
        return

    # Vocabulary reply-menu
    if message.text == vocab_btn:
        await message.answer(t(lang, 'vocab_title'), reply_markup=student_vocab_keyboard(lang))
        return
    if message.text == back_btn:
        await message.answer(t(lang, 'select_from_menu'), reply_markup=student_main_keyboard(lang))
        return
    if message.text == vocab_search_btn:
        # Check if user has multiple subjects
        user_subjects = get_user_subjects(user['id'])
        if len(user_subjects) <= 1:
            # If only one subject, proceed directly with search
            state = get_vocab_state(message.chat.id)
            state['step'] = 'search_wait'
            state['data'] = {'subject': user_subjects[0] if user_subjects else 'English'}
            await message.answer(t(lang, 'vocab_enter_query'))
        else:
            # Show subject selection for search
            await show_subject_selection_for_search(message.chat.id, user, user_subjects)
        return
    if message.text == vocab_pref_btn:
        state = get_vocab_state(message.chat.id)
        state['step'] = 'pref_wait'
        await message.answer(t(lang, 'vocab_pref_prompt'))
        return
    if message.text == vocab_quiz_btn:
        await cmd_vocab_quiz(message)
        return

    await message.answer(t(lang, 'unknown_command'))


async def show_my_profile(chat_id: int, user: dict):
    from i18n import t, detect_lang_from_user
    lang = detect_lang_from_user(user)
    
    subjects = get_student_subjects(user['id'])
    groups = get_user_groups(user['id'])
    teachers = get_student_teachers(user['id'])
    
    lines = []
    lines.append("👤 " + t(lang, 'my_profile'))
    lines.append("")
    lines.append(f"👨‍🎓 Ism Familya: {user.get('first_name','-')} {user.get('last_name','-')}")
    lines.append(f"🆔 Login ID: {user.get('login_id') or '-'}")
    
    # === KO'P FAN KO'RSATISH ===
    if subjects:
        if len(subjects) == 1:
            lines.append(f"📚 Fan: {subjects[0]}")
        else:
            lines.append(f"� Fan(lar): {', '.join(subjects)} ({len(subjects)} ta)")
    else:
        lines.append(f"📚 Fan: {user.get('subject') or '-'}")
    
    lines.append(f"👥 Guruhlar soni: {len(groups)}")
    
    # O'qituvchilar
    if teachers:
        lines.append(f"👨‍🏫 O'qituvchi(lar): {len(teachers)} ta")
        for t in teachers:
            lines.append(f"   • {t['first_name']} {t['last_name']} ({t['group_name']})")
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🚪 ' + t(lang, 'logout'), callback_data='logout_me')],
    ])

    await bot.send_message(chat_id, "\n".join(lines), reply_markup=kb)


@dp.callback_query(lambda c: c.data == 'student_subject_settings')
async def handle_student_subject_settings(callback: CallbackQuery):
    user = get_user_by_telegram(str(callback.from_user.id))
    lang = detect_lang_from_user(user or callback.from_user)
    if not user:
        await callback.answer()
        await callback.message.answer(t(lang, 'please_send_start'))
        return
    user_subjects = get_user_subjects(user['id'])
    subj_line = ', '.join(user_subjects) if user_subjects else '-'
    await callback.message.answer(
        f"📚 Current subjects: {subj_line}\n\nWhat do you want?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='➕ Add subject', callback_data='student_add_subject')],
            [InlineKeyboardButton(text='➖ Delete subject', callback_data='student_delete_subject')],
            [InlineKeyboardButton(text='🔙 Back', callback_data='student_subject_settings_back')],
        ])
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data == 'student_add_subject')
async def handle_student_add_subject(callback: CallbackQuery):
    user = get_user_by_telegram(str(callback.from_user.id))
    if not user:
        await callback.answer()
        return
    
    # Show inline buttons for subject selection
    await callback.message.answer(
        'Qaysi subjectni qo‘shmoqchisiz?',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='English', callback_data='student_add_subject_English')],
            [InlineKeyboardButton(text='Russian', callback_data='student_add_subject_Russian')],
            [InlineKeyboardButton(text='🔙 Back', callback_data='student_subject_settings')],
        ])
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data == 'student_delete_subject')
async def handle_student_delete_subject(callback: CallbackQuery):
    user = get_user_by_telegram(str(callback.from_user.id))
    if not user:
        await callback.answer()
        return
    
    user_subjects = get_user_subjects(user['id'])
    if not user_subjects:
        await callback.message.answer('Sizda hech qanday subject yo‘q')
        await callback.answer()
        return
    
    # Create inline buttons for each subject
    keyboard_rows = []
    for subject in user_subjects:
        keyboard_rows.append([InlineKeyboardButton(text=f'➖ {subject}', callback_data=f'student_delete_subject_{subject}')])
    keyboard_rows.append([InlineKeyboardButton(text='🔙 Back', callback_data='student_subject_settings')])
    
    await callback.message.answer(
        'Qaysi subjectni o‘chirmoqchisiz?',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data == 'student_subject_settings_back')
async def handle_student_subject_settings_back(callback: CallbackQuery):
    user = get_user_by_telegram(str(callback.from_user.id))
    lang = detect_lang_from_user(user or callback.from_user)
    await callback.message.answer(t(lang, 'select_from_menu'), reply_markup=student_main_keyboard(lang))
    reset_student_state(callback.message.chat.id)
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('student_add_subject_'))
async def handle_student_add_subject_specific(callback: CallbackQuery):
    user = get_user_by_telegram(str(callback.from_user.id))
    if not user:
        await callback.answer()
        return
    
    subject = callback.data.split('_', 3)[-1]  # Get the subject name
    user_subjects = get_user_subjects(user['id'])
    
    if subject in user_subjects:
        await callback.message.answer('Bu subject allaqachon mavjud')
    elif len(user_subjects) >= 2:
        await callback.message.answer('Maxsus 2 ta subjectgacha qo‘shish mumkin')
    else:
        user_subjects.append(subject)
        update_user_subjects(user['id'], user_subjects)
        await callback.message.answer('✅ Subject qo‘shildi: ' + subject)
    
    # Go back to subject settings
    await handle_student_subject_settings(callback)
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('student_delete_subject_'))
async def handle_student_delete_subject_specific(callback: CallbackQuery):
    user = get_user_by_telegram(str(callback.from_user.id))
    if not user:
        await callback.answer()
        return
    
    subject = callback.data.split('_', 3)[-1]  # Get the subject name
    user_subjects = get_user_subjects(user['id'])
    
    if subject not in user_subjects:
        await callback.message.answer('Bu subject userga tegishli emas')
    else:
        user_subjects.remove(subject)
        update_user_subjects(user['id'], user_subjects)
        await callback.message.answer(f'✅ Subject o‘chirildi: {subject}')
    
    # Go back to subject settings
    await handle_student_subject_settings(callback)
    await callback.answer()




async def show_subject_selection_for_search(chat_id: int, user: dict, user_subjects: list):
    """Show subject selection specifically for vocabulary search"""
    lang = detect_lang_from_user(user)
    
    keyboard = []
    for subject in user_subjects:
        if subject == 'English':
            text = '🇬🇧 English'
        elif subject == 'Russian':
            text = '🇷🇺 Russian'
        else:
            text = f'📚 {subject}'
        
        keyboard.append([InlineKeyboardButton(
            text=text, 
            callback_data=f"vocab_search_subject:{subject}"
        )])
    
    await bot.send_message(
        chat_id, 
        "🔎 <b>So'z izlash - Fan tanlang</b>\n\nQaysi fanda so'z qidirmoqchisiz?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


async def show_subject_selection(chat_id: int, user: dict, callback_data_prefix: str):
    """Show subject selection for students with multiple subjects"""
    lang = detect_lang_from_user(user)
    user_subjects = get_user_subjects(user['id'])
    
    if len(user_subjects) <= 1:
        # If only one subject, proceed directly
        subject = user_subjects[0] if user_subjects else 'English'
        await handle_subject_selection(chat_id, user, subject, callback_data_prefix)
        return
    
    # Create keyboard for subject selection
    keyboard = []
    for subject in user_subjects:
        if subject == 'English':
            text = '🇬🇧 English'
        elif subject == 'Russian':
            text = '🇷🇺 Russian'
        else:
            text = f'📚 {subject}'
        
        keyboard.append([InlineKeyboardButton(
            text=text, 
            callback_data=f"{callback_data_prefix}:{subject}"
        )])
    
    await bot.send_message(
        chat_id, 
        "📚 <b>Fan tanlang</b>\n\nQaysi fanda davom etishni istaysiz?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


async def handle_subject_selection(chat_id: int, user: dict, subject: str, callback_data_prefix: str):
    """Handle subject selection and proceed with the original action"""
    # Store selected subject in user state for this session
    user_subject_state = f"{user['id']}_current_subject"
    placement_state[user_subject_state] = subject
    
    # Proceed based on the callback data prefix
    if callback_data_prefix == "grammar_rules":
        await show_grammar_topics(chat_id, user, subject)
    elif callback_data_prefix == "vocab_quiz":
        await cmd_vocab_quiz_with_subject(chat_id, user, subject)
    # Add more cases as needed


@dp.callback_query(lambda c: c.data == "menu_grammar")
async def menu_grammar(callback: CallbackQuery):
    user = get_user_by_telegram(callback.from_user.id)
    if not user:
        await callback.answer("Avval login qiling!", show_alert=True)
        return

    await callback.message.edit_text(
        "📚 Grammar\n\n"
        "Qaysi leveldagi mavzularni ko'ramoqchisiz?",
        reply_markup=get_grammar_level_keyboard()
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("grammar_level_"))
async def handle_grammar_level(callback: CallbackQuery):
    level = callback.data.split("_")[-1]
    await callback.message.edit_text(
        f"📚 {level} level mavzulari\n\n"
        "Quyidagi mavzulardan birini tanlang (raqam bosib):",
        reply_markup=get_paginated_topics_keyboard(level, page=0)
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("grammar_topic_"))
async def handle_grammar_topic(callback: CallbackQuery):
    parts = callback.data.split("_")
    level = parts[2]

    if len(parts) > 3 and parts[3] == "page":          # pagination
        page = int(parts[4])
        await callback.message.edit_text(
            f"📚 {level} level mavzulari (sahifa {page+1})\n\n"
            "Quyidagi mavzulardan birini tanlang:",
            reply_markup=get_paginated_topics_keyboard(level, page)
        )
        await callback.answer()
        return

    # Mavzu tanlandi
    topic_index = int(parts[3])
    topics = TOPICS_BY_LEVEL.get(level, [])
    if topic_index >= len(topics):
        await callback.answer("Mavzu topilmadi!", show_alert=True)
        return

    topic = topics[topic_index]

    text = f"📖 {topic.title}\n\n{topic.rule}\n\n"
    if hasattr(topic, 'examples') and topic.examples:
        text += "Misollar:\n" + "\n".join(f"• {ex}" for ex in topic.examples)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧪 Quiz boshlash", callback_data=f"start_grammar_quiz_{level}_{topic_index}")],
        [InlineKeyboardButton(text="🔙 Mavzularga qaytish", callback_data=f"grammar_level_{level}")]
    ])

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


async def show_grammar_topics(chat_id: int, user: dict, subject: str):
    """Show grammar topics for specific subject"""
    from grammar_content import get_topics_by_level_and_subject
    
    lang = detect_lang_from_user(user)
    level = user.get('level', 'A1')
    
    topics = get_topics_by_level_and_subject(level, subject)
    if not topics:
        await bot.send_message(chat_id, "Bu fan va level uchun grammatika mavzulari topilmadi.")
        return
    
    keyboard = []
    for topic in topics:
        keyboard.append([InlineKeyboardButton(
            text=topic['title'],
            callback_data=f"grammar_topic:{topic['topic_id']}"
        )])
    
    keyboard.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_main")])
    
    await bot.send_message(
        chat_id,
        f"📚 <b>{subject} - {level} Grammatika</b>\n\nMavzuni tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


async def cmd_vocab_quiz_with_subject(chat_id: int, user: dict, subject: str):
    """Start vocabulary quiz for specific subject"""
    from vocabulary import get_available_vocabulary_levels, get_words_by_subject_level
    
    lang = detect_lang_from_user(user)
    current_level = user.get('level', 'A1')
    
    # Get student subjects
    subjects = get_student_subjects(user['id'])
    
    # Bir nechta subject bo'lsa, fan tanlash ko'rsatish mumkin
    # yoki birinchi subjectni avtomatik olish
    selected_subject = subject if subject else (subjects[0] if subjects else 'English')
    
    available_levels = get_available_vocabulary_levels(current_level)

    # keyin quiz boshlanadi...
    words = get_words_by_subject_level(
        subject=selected_subject,
        levels=available_levels   # list sifatida beriladi
    )

    if not words:
        await bot.send_message(chat_id, "Bu darajada so'zlar hali yuklanmagan.")
        return

    # keyin quiz boshlanadi...
    await bot.send_message(chat_id, f"📚 {selected_subject} bo'yicha vocab quiz boshlanadi!")
    # For now, call the original function
    await cmd_vocab_quiz(chat_id)


@dp.callback_query(lambda c: c.data == 'logout_me')
async def handle_logout_me(callback: CallbackQuery):
    from db import logout_user_by_telegram
    user = get_user_by_telegram(str(callback.from_user.id))
    lang = detect_lang_from_user(user or callback.from_user)
    logout_user_by_telegram(str(callback.from_user.id))
    clear_login_state(callback.message.chat.id)
    reset_placement_state(callback.from_user.id)
    await callback.answer()
    await callback.message.answer(t(lang, 'logged_out'), reply_markup=ReplyKeyboardRemove())


async def start_placement_test(chat_id: int, override_subject: str = None):
    """Start placement test for the specified subject"""
    user = get_user_by_telegram(str(chat_id))
    if not user:
        return
    
    logger.debug('start_placement_test called user=%s chat_id=%s override_subject=%s', user, chat_id, override_subject)
    lang = detect_lang_from_user(user)
    
    # Use the provided subject or user's subject
    subject = (override_subject or user.get('subject') or '').strip().title()
    
    # Validate subject
    if subject not in ['English', 'Russian']:
        await bot.send_message(chat_id, t(lang, 'subject_not_set'))
        return
    
    if not subject:
        logger.warning('start_placement_test: user has no subject user=%s', user['id'])
        await bot.send_message(chat_id, t(lang, 'subject_not_set'))
        return

    ps = get_placement_state(chat_id)
    logger.debug('placement_state before init: %s', ps)
    if ps.get('active'):
        logger.info('Test already active for user %s', chat_id)
        await bot.send_message(chat_id, t(lang, 'test_already_active'))
        return

    questions = get_tests_by_subject(subject)
    logger.debug('Loaded %s questions for subject %s', len(questions), subject)
    if not questions:
        await bot.send_message(chat_id, t(lang, 'no_questions_for_subject', subject=subject))
        return

    ps.update({
        'active': True,
        'user_id': user['id'],
        'subject': subject,
        'question_index': 0,
        'score': 0,
        'questions': [q['id'] for q in questions],
        'poll_map': {},
    })
    save_placement_session(user['id'], {
        'active': True,
        'subject': subject,
        'question_index': 0,
        'score': 0,
        'questions': [q['id'] for q in questions],
    })
    await bot.send_message(chat_id, f"{subject} - " + t(lang, 'placement_test_starting') + f". 1/{len(ps['questions'])}")
    try:
        await send_next_question(chat_id)
    except Exception:
        logger.exception('Test savol yuborishda xatolik yuz berdi')
        await bot.send_message(chat_id, 'Test savollarini yuborishda xatolik yuz berdi. Iltimos, admin bilan bog\'laning va qayta urinib ko\'ring.')


async def send_next_question(chat_id):
    key = str(chat_id)
    ps = get_placement_state(key)
    logger.debug('send_next_question called chat_id=%s key=%s ps=%s', chat_id, key, ps)
    user_for_lang = get_user_by_telegram(str(chat_id))
    lang = detect_lang_from_user(user_for_lang or {})
    if not ps.get('active'):
        user = get_user_by_telegram(str(chat_id))
        if user:
            session = get_placement_session(user['id'])
            if session and session.get('active'):
                ps.update({
                    'active': True,
                    'subject': session['subject'],
                    'question_index': session['question_index'],
                    'score': session['score'],
                    'questions': session['questions'],
                    'poll_map': {},
                })
                logger.info('Resumed placement session from DB for chat %s', chat_id)
            else:
                logger.info('send_next_question: placement not active for chat %s', chat_id)
                return
        else:
            logger.info('send_next_question: placement not active for chat %s', chat_id)
            return

    idx = ps.get('question_index', 0)
    if idx >= len(ps.get('questions', [])):
        logger.info('send_next_question: question_index out of range %s >= %s', idx, len(ps.get('questions', [])))
        return

    q_id = ps['questions'][idx]
    question = get_test_by_id(q_id)
    if not question:
        logger.error('send_next_question: test question not found id=%s', q_id)
        await bot.send_message(chat_id, t(lang, 'question_not_found'))
        return

    options = [question['option_a'], question['option_b'], question['option_c'], question['option_d']]
    if len(options) != 4 or any(opt is None or opt == '' for opt in options):
        logger.error('send_next_question: invalid options for question id=%s options=%s', q_id, options)
        await bot.send_message(chat_id, t(lang, 'question_options_incomplete'))
        return

    correct_option = question.get('correct_option', '').strip().upper()
    if correct_option not in 'ABCD':
        logger.error('send_next_question: noto‘g‘ri correct_option for question id=%s: %s', q_id, correct_option)
        await bot.send_message(chat_id, t(lang, 'question_correct_option_error'))
        return

    correct_index = 'ABCD'.index(correct_option)
    poll_question = f"{idx + 1}/{len(ps['questions'])} - {question['question']}\n\nVariantlar:"
    
    # Send timer message first
    timer_msg = await bot.send_message(chat_id, "⏱️ 30 soniya ichida javob berishingiz kerak!")
    
    try:
        msg = await bot.send_poll(
            chat_id=chat_id,
            question=poll_question,
            options=options,
            type='quiz',
            correct_option_id=correct_index,
            is_anonymous=False,
            open_period=30,  # 30-second timer
        )
        poll_id = msg.poll.id
        ps['poll_map'][poll_id] = {
            'question_id': q_id,
            'correct_option': correct_index,
        }
        
        # Delete timer message after poll is sent
        try:
            await bot.delete_message(chat_id, timer_msg.message_id)
        except Exception:
            pass  # Ignore if we can't delete the timer message
            
    except Exception:
        logger.exception('send_next_question: bot.send_poll failed for chat=%s q_id=%s', chat_id, q_id)
        # Fallback: send plain text question if poll fails
        opts_text = '\n'.join([f"{chr(65+i)}. {o}" for i, o in enumerate(options)])
        await bot.send_message(chat_id, f"{poll_question}\n{opts_text}\n\n⏱️ 30 soniya ichida javob bering! Javobni A/B/C/D shaklida yozing.")
        
        # Schedule auto-advance after 30 seconds
        asyncio.create_task(auto_advance_question(chat_id, 30))
        
        # keep test active, but current question may need manual answer handling (not implemented)
        ps['active'] = False
        return


async def auto_advance_question(chat_id: int, delay: int):
    """Automatically advance to next question after delay seconds"""
    await asyncio.sleep(delay)
    
    ps = get_placement_state(str(chat_id))
    if ps.get('active') and not ps.get('poll_map'):  # Only advance if no active poll
        user = get_user_by_telegram(str(chat_id))
        if user:
            lang = detect_lang_from_user(user)
            await bot.send_message(chat_id, f"⏰ Vaqt tugadi! Keyingi savol...")
            await send_next_question(chat_id)


@dp.callback_query(lambda c: c.data == 'start_test')
async def handle_start_test(callback: CallbackQuery):
    user = get_user_by_telegram(str(callback.from_user.id))
    if not user:
        lang = detect_lang_from_user(callback.from_user)
        await callback.answer(t(lang, 'not_registered'))
        return
    lang = detect_lang_from_user(user)
    await callback.answer(t(lang, 'test_starting'))
    await start_placement_test(callback.message.chat.id)


@dp.poll_answer()
async def handle_poll_answer(poll_answer: types.PollAnswer):
    chat_id = poll_answer.user.id
    logger.debug('handle_poll_answer: chat_id=%s poll_id=%s option_ids=%s', chat_id, poll_answer.poll_id, poll_answer.option_ids)
    # First handle vocabulary quiz polls
    if poll_answer.poll_id in vocab_poll_map:
        meta = vocab_poll_map.get(poll_answer.poll_id)
        if meta:
            chosen = poll_answer.option_ids[0] if poll_answer.option_ids else None
            meta['chosen'] = chosen
            ev = meta.get('event')
            if ev:
                ev.set()
        return

    # Grammar quiz polls
    if poll_answer.poll_id in grammar_poll_map:
        meta = grammar_poll_map.get(poll_answer.poll_id)
        if meta:
            chosen = poll_answer.option_ids[0] if poll_answer.option_ids else None
            meta['chosen'] = chosen
            ev = meta.get('event')
            if ev:
                ev.set()
        return

    ps = get_placement_state(chat_id)
    if not ps.get('active'):
        logger.warning('handle_poll_answer: no active placement for chat_id=%s', chat_id)
        return

    poll_id = poll_answer.poll_id
    if poll_id not in ps['poll_map']:
        return

    chosen = poll_answer.option_ids[0] if poll_answer.option_ids else None
    meta = ps['poll_map'].pop(poll_id, None)
    if meta is None:
        return

    if chosen == meta['correct_option']:
        ps['score'] += 10

    user = get_user_by_telegram(str(chat_id))
    if not user:
        logger.warning('handle_poll_answer: user not found for chat_id=%s', chat_id)
        reset_placement_state(chat_id)
        return

    ps['question_index'] += 1
    save_placement_session(user['id'], {
        'active': True,
        'subject': ps['subject'],
        'question_index': ps['question_index'],
        'score': ps['score'],
        'questions': ps['questions'],
    })

    if ps['question_index'] >= len(ps['questions']):
        await finish_placement_test(user, chat_id)
        return

    lang = detect_lang_from_user(user)
    await bot.send_message(chat_id, t(lang, 'next_question'))
    await send_next_question(chat_id)


async def send_test_completion_to_admin(user: dict, subject: str, percentage: int, correct_count: int, level: str):
    """Send detailed test completion notification to admin with group recommendations"""
    from admin_bot import bot as admin_bot
    from config import ADMIN_CHAT_IDS
    from db import get_all_groups, get_group_users, get_user_by_id as get_user_by_id_db
    
    if not ADMIN_CHAT_IDS or not admin_bot:
        return
    
    # Find suitable groups based on subject and level
    all_groups = get_all_groups()
    suitable_groups = []
    
    for group in all_groups:
        # Filter by subject
        if group.get('subject', '').lower() != subject.lower():
            continue
        
        # Filter by level (exact match or close level)
        group_level = group.get('level', '').upper()
        if group_level == level.upper():
            suitable_groups.append(group)
    
    # If no exact level match, include groups with similar levels
    if not suitable_groups:
        level_mapping = {
            'A1': ['A1', 'A2'],
            'A2': ['A1', 'A2', 'B1'],
            'B1': ['A2', 'B1', 'B2'],
            'B2': ['B1', 'B2']
        }
        
        acceptable_levels = level_mapping.get(level.upper(), [level])
        for group in all_groups:
            if group.get('subject', '').lower() == subject.lower():
                group_level = group.get('level', '').upper()
                if group_level in acceptable_levels:
                    suitable_groups.append(group)
    
    # Create admin notification message
    admin_msg = (
        f"🎓 **TEST YAKUNLANDI**\n\n"
        f"👤 **Ism Familya:** {user['first_name']} {user['last_name']}\n"
        f"🔑 **Login ID:** {user['login_id']}\n"
        f"📱 **Telefon raqam:** {user.get('phone', '—')}\n"
        f"📚 **Fan:** {subject}\n"
        f"✅ **To'g'ri javoblar:** {correct_count}/50\n"
        f"📊 **Foiz:** {percentage}%\n"
        f"🎯 **Daraja:** {level}\n\n"
    )
    
    # Add group recommendations
    if suitable_groups:
        admin_msg += f"🏫 **Tavsiya etilgan guruhlar ({len(suitable_groups)} ta):**\n\n"
        
        for i, group in enumerate(suitable_groups[:10], 1):  # Show max 10 groups
            teacher = get_user_by_id_db(group.get('teacher_id')) if group.get('teacher_id') else None
            teacher_name = f"{teacher['first_name']} {teacher['last_name']}" if teacher else "—"
            student_count = len(get_group_users(group['id']))
            
            admin_msg += (
                f"{i}. **Guruh nomi:** {group['name']}\n"
                f"   📚 **Darajasi:** {group.get('level', '—')}\n"
                f"   👨‍🏫 **O'qituvchi:** {teacher_name}\n"
                f"   👥 **O'quvchilar:** {student_count} ta\n"
                f"   ⏰ **Vaqt:** {group.get('lesson_start', '—')[:5]}-{group.get('lesson_end', '—')[:5]}\n\n"
            )
        
        # Create inline keyboard for quick group assignment
        keyboard_buttons = []
        for i, group in enumerate(suitable_groups[:5], 1):  # First 5 groups as buttons
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"{i}. {group['name']} ({group.get('level', '—')})",
                    callback_data=f"assign_test_user_{user['id']}_{group['id']}"
                )
            ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    else:
        admin_msg += "❌ **Mos guruh topilmadi.** Yangi guruh yaratish kerak.\n\n"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Yangi guruh yaratish", callback_data=f"group_create_for_user_{user['id']}_{subject}_{level}")]
        ])
    
    # Add general action buttons
    action_buttons = [
        [InlineKeyboardButton(text="👤 Foydalanuvchi ma'lumotlari", callback_data=f"user_detail_{user['id']}")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_menu")]
    ]
    
    if keyboard.inline_keyboard:
        keyboard.inline_keyboard.extend(action_buttons)
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=action_buttons)
    
    # Send to all admin chat IDs
    for admin_chat in ADMIN_CHAT_IDS:
        try:
            await admin_bot.send_message(
                admin_chat,
                admin_msg,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Admin notification failed: {e}")


async def finish_placement_test(user: dict, chat_id: int):
    ps = get_placement_state(chat_id)
    lang = detect_lang_from_user(user)
    score = ps['score']
    correct_count = score // 10
    level = compute_level(score, ps['subject'])
    
    update_user_level(user['id'], level)
    save_test_result(user['id'], ps['subject'], score, level)
    # Set pending approval flag
    from db import set_pending_approval
    set_pending_approval(user['id'], True)
    clear_placement_session(user['id'])

    subject = ps.get('subject', 'unknown').title()
    percentage = int((score / 500) * 100)  # Convert to percentage
    result_msg = f"Test natijasi: {percentage}% (Correct: {correct_count}/50)\nDaraja: {level}"
    
    # Show results and continue with main flow
    await bot.send_message(chat_id, result_msg)
    
    # Send detailed notification to admin with group recommendations
    await send_test_completion_to_admin(user, subject, percentage, correct_count, level)
    
    # Continue to main menu if access is enabled
    user = get_user_by_telegram(str(chat_id))
    if is_access_active(user):
        await bot.send_message(chat_id, t(lang, 'select_from_menu'), reply_markup=student_main_keyboard(lang))
        
        # Foydalanuvchiga ikkinchi test uchun til tanlashini so'rash
        msg_text = f"{subject} - {t(lang, 'placement_test_starting')}\n{result_msg}\n\n" + t(lang, 'which_language_start_test')
        await bot.send_message(chat_id, msg_text, reply_markup=create_dual_choice_keyboard(prefix="start_test", lang=lang))

        reset_placement_state(chat_id)
        return

    admin_subject_name = 'English' if subject.lower() == 'english' else 'Russian' if subject.lower() == 'russian' else subject
    percentage = int((score / 500) * 100)  # Convert to percentage
    admin_text = (
        f"{admin_subject_name} test natijasi: {user['first_name']} {user['last_name']} | {user['login_id']} | "
        f"{percentage}% | {correct_count} tog'ri javob | {level}\n"
        f"📌 <b>Guruh tanlang:</b>"
    )
    approve_btn = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📌 Recommendation guruhlar", callback_data=f"rec_groups:{user['id']}:page:0")],
    ])
    logger.info('Adminga natija yuborilmoqda: %s', admin_text)
    if not ADMIN_CHAT_IDS:
        logger.warning('ADMIN_CHAT_IDS bo`sh: adminga xabar yuborilmadi')
    if ADMIN_CHAT_IDS and admin_bot:
        for admin_chat in ADMIN_CHAT_IDS:
            try:
                await admin_bot.send_message(admin_chat, admin_text, reply_markup=approve_btn)
            except Exception as e:
                logger.error('Adminga xabar yuborish xatosi: %s', e)
                continue

    await bot.send_message(chat_id, result_msg)
    reset_placement_state(chat_id)
    clear_login_state(chat_id)


async def show_leaderboard(user_id, chat_id, page, filter_type='global'):
    """Reytingni sahifa bilan ko'rsatish"""
    user = get_user_by_telegram(str(user_id))
    if not user:
        lang = 'uz'  # default
        await bot.send_message(chat_id, t(lang, 'not_registered'))
        return
    
    # ← BU QATORNI QO'SHING (agar hali yo'q bo'lsa)
    lang = detect_lang_from_user(user)
    
    limit = 10
    offset = page * limit
    
    if filter_type == 'global':
        leaderboard = get_leaderboard_global(limit=limit, offset=offset)
        total_count = get_leaderboard_count()
        title = '🌍 <b>GLOBAL REYTING</b>'
    else:  # group
        group = get_group(user.get('group_id')) if user.get('group_id') else None
        if not group:
            lang = detect_lang_from_user(user)
            await bot.send_message(chat_id, t(lang, 'subject_not_set'))
            return
        leaderboard = get_leaderboard_by_group(user['group_id'], limit=limit, offset=offset)
        total_count = get_leaderboard_count_by_group(user['group_id'])
        title = f'👥 <b>GURUH REYTINGI: {group["name"]}</b>'
    
    current_diamonds = get_diamonds(user['id'])
    
    # User's rank aniqlash
    if filter_type == 'global':
        all_users = get_leaderboard_global(limit=10000)  # Barcha foydalanuvchilarni olish rankini aniqlash uchun
    else:
        all_users = get_leaderboard_by_group(user['group_id'], limit=10000)
    
    user_rank = None
    for idx, lb_user in enumerate(all_users, 1):
        if lb_user['id'] == user['id']:
            user_rank = idx
            break
    
    total_pages = (total_count - 1) // limit + 1 if total_count else 1
    
    # Sticky header
    header = f"{title}\n"
    header += f"<b>Sizning reytingingiz: #{user_rank or '—'} | Diamondlar: {current_diamonds} 💎</b>\n"
    header += f"(Sahifa {page + 1}/{total_pages})\n\n"
    
    # Leaderboard entries
    text = header
    if leaderboard:
        for idx, lb_user in enumerate(leaderboard, start=offset+1):
            medal = '🥇' if idx == 1 else '🥈' if idx == 2 else '🥉' if idx == 3 else f'{idx}.'
            text += f"{medal} {lb_user['first_name']} {lb_user['last_name']}: {lb_user['diamonds']} 💎\n"
    else:
        text += t(lang, 'no_results')
    
    await bot.send_message(chat_id, text, parse_mode='HTML', 
                          reply_markup=create_leaderboard_pagination_keyboard(page, total_pages, filter_type))


@dp.callback_query(lambda c: c.data.startswith('leaderboard_'))
async def handle_leaderboard_callback(callback: CallbackQuery):
    logger.info(f"🔘 CALLBACK: {callback.data} | User: {callback.from_user.id}")
    """Reyting paginatsiya va filter callbacklari"""
    data = callback.data
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id
    
    if data.startswith('leaderboard_prev_'):
        filter_type = data.split('_')[-1]
        # Oldingi sahifa raqamini olish (message-dan yoki default 0)
        page_text = callback.message.text
        current_page_match = re.search(r'Sahifa (\d+)/', page_text)
        current_page = int(current_page_match.group(1)) - 1 if current_page_match else 0
        next_page = max(0, current_page - 1)
        await show_leaderboard(user_id, chat_id, next_page, filter_type)
        await callback.answer()
        return
    
    if data.startswith('leaderboard_next_'):
        filter_type = data.split('_')[-1]
        page_text = callback.message.text
        current_page_match = re.search(r'Sahifa (\d+)/', page_text)
        current_page = int(current_page_match.group(1)) - 1 if current_page_match else 0
        next_page = current_page + 1
        await show_leaderboard(user_id, chat_id, next_page, filter_type)
        await callback.answer()
        return
    
    if data.startswith('leaderboard_filter_'):
        filter_type = data.split('_')[-1]
        await show_leaderboard(user_id, chat_id, 0, filter_type)
        await callback.answer()
        return


async def run_student_bot():
    global bot, admin_bot
    if not STUDENT_BOT_TOKEN:
        raise RuntimeError("STUDENT_BOT_TOKEN is not set. Put it in .env (STUDENT_BOT_TOKEN=...) and retry.")
    bot = Bot(token=STUDENT_BOT_TOKEN)
    
    # Initialize admin bot for sending notifications
    from config import ADMIN_BOT_TOKEN
    if ADMIN_BOT_TOKEN:
        admin_bot = Bot(token=ADMIN_BOT_TOKEN)
    else:
        logger.warning("ADMIN_BOT_TOKEN not set, admin notifications will not work")
    
    # Restore sessions on startup
    try:
        restored_count = restore_sessions_on_startup()
        logger.info(f"🔄 Restored {restored_count} user sessions on startup")
    except Exception as e:
        logger.error(f"Failed to restore sessions: {e}")
    
    # Start cleanup scheduler for inactive accounts (runs once per day)
    async def cleanup_scheduler():
        while True:
            try:
                await asyncio.sleep(86400)  # Sleep for 24 hours
                deleted_count = cleanup_inactive_accounts()
                logger.info(f"🧹 Cleanup completed: {deleted_count} inactive accounts deleted (60+ days)")
            except Exception as e:
                logger.error(f"Cleanup scheduler error: {e}")
    
    # Run scheduler in background
    asyncio.create_task(cleanup_scheduler())
    logger.info("🧹 Inactive account cleanup scheduler started (runs every 24 hours)")
    
    # Restore user sessions after bot restart
    try:
        restored_count = restore_sessions_on_startup()
        logger.info(f"🔄 Restored login sessions for {restored_count} users")
    except Exception as e:
        logger.error(f"Error restoring user sessions: {e}")
    
    logger.info("Student bot started successfully")
    await dp.start_polling(bot)


# ==================== GRAMMAR LEVEL + PAGINATION ====================

LEVELS = ["A1", "A2", "B1"]  # hozircha faqat bu levellar mavjud
TOPICS_BY_LEVEL = {
    "A1": A1_TOPICS,
    "A2": A2_TOPICS,
    "B1": B1_TOPICS,
    # B2 va C1 keyinchalik qo'shiladi
}

def get_grammar_level_keyboard():
    keyboard = []
    row = []
    for level in LEVELS:
        row.append(InlineKeyboardButton(text=level, callback_data=f"grammar_level_{level}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="menu_main")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_paginated_topics_keyboard(level: str, page: int = 0, per_page: int = 5):
    topics = TOPICS_BY_LEVEL.get(level, [])
    start = page * per_page
    end = min(start + per_page, len(topics))
    current_topics = topics[start:end]

    keyboard = []
    row = []
    for i, _ in enumerate(current_topics):
        global_index = start + i
        row.append(InlineKeyboardButton(
            text=str(global_index + 1),
            callback_data=f"grammar_topic_{level}_{global_index}"
        ))
        if len(row) == 5:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    # Pagination tugmalari
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"grammar_topic_page_{level}_{page-1}"))
    if end < len(topics):
        nav_row.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"grammar_topic_page_{level}_{page+1}"))
    if nav_row:
        keyboard.append(nav_row)

    keyboard.append([InlineKeyboardButton(text="🔙 Levelga qaytish", callback_data=f"grammar_level_{level}")])
    keyboard.append([InlineKeyboardButton(text="🔙 Asosiy menu", callback_data="menu_main")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


async def error_handler(update: types.Update, exception: Exception):
    logger.error(f"Error in {'teacher' if 'teacher' in __file__ else 'student'} bot: {exception}", exc_info=True)


@dp.callback_query(lambda c: c.data.startswith('set_lang_me_'))
async def handle_set_lang_me(callback: CallbackQuery):
    code = callback.data.split('_')[-1]
    from db import set_user_language_by_telegram
    ok = set_user_language_by_telegram(str(callback.from_user.id), code)
    if ok:
        await callback.answer()
        await callback.message.answer(t(code, 'lang_set'))
        # Send updated main menu in new language
        await callback.message.answer(t(code, 'select_from_menu'), reply_markup=student_main_keyboard(code))
    else:
        await callback.answer()
        await callback.message.answer(t(code, 'please_send_start'))
