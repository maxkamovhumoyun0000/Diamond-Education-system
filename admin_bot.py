import logging
import os
import traceback
from pathlib import Path
from aiogram import Bot, Dispatcher, types
from aiogram.types import ErrorEvent
from aiogram.exceptions import TelegramBadRequest
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types.input_file import BufferedInputFile
from aiogram.filters import Command
import unicodedata
import html as html_module
import re
import asyncio
import secrets
from datetime import datetime, timedelta
from uuid import uuid4
import pytz
from openpyxl import Workbook
from openpyxl.styles import Font

from admin_shared_menus import (
    build_admin_teacher_detail_reply,
    build_student_share_keyboard_rows,
    send_admin_payments_root_menu,
    send_admin_student_control_message,
)
from config import (
    ADMIN_BOT_TOKEN,
    ADMIN_CHAT_IDS,
    ALL_ADMIN_IDS,
    DIAMONDVOY_DB_RESET_SECRET,
    LIMITED_ADMIN_CHAT_IDS,
    STUDENT_BOT_TOKEN,
    SUBJECTS,
    ADMIN_WEBHOOK_PORT,
)
from bot_runtime import create_resilient_bot, run_bot_dispatcher, spawn_guarded_task
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
    cleanup_student_subject_side_effects,
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
    get_bot_start_ym,
    get_teacher_groups_count,
    get_teacher_students_count,
    get_teacher_total_students,
    get_student_subjects,
    get_student_teachers,
    get_dcoins,
    ensure_subject_dcoin_schema,
    ensure_dcoin_schema_migrations,
    validate_dcoin_runtime_ready,
    get_latest_test_result,
    get_latest_test_result_for_subject,
    extract_cefr_level_code,
    get_shared_student_ids_for_admin,
    search_student_users_for_group_pick,
    is_student_shared_with_admin,
    share_student_between_admins,
    unshare_student_between_admins,
    is_lesson_holiday,
    get_pending_lesson_otmen_request_by_date,
    create_lesson_otmen_request,
    get_lesson_otmen_request,
    list_cancelled_lesson_otmen_requests,
    mark_lesson_otmen_request_status,
    list_lesson_bookings_by_date,
    set_lesson_booking_status,
    set_branch_date_closed,
    open_branch_date_for_booking,
    is_branch_date_closed_for_booking,
    get_branch_date_closed_reason,
    cancel_group_arena_sessions_for_date,
    wipe_postgresql_database_and_reinit,
    get_daily_test_history_global,
    get_daily_tests_unused_stock_by_subject_level,
    get_staff_leaderboard_by_subject,
    get_staff_leaderboard_student_count,
)
from holiday_manager import get_days_status, get_next_11_days_status
from auth import create_user_sync, level_display_from_score, normalize_level_to_cefr, restore_sessions_on_startup
from utils import admin_main_keyboard, cancel_keyboard, create_user_type_keyboard, create_subject_keyboard, create_dual_choice_keyboard, create_group_action_keyboard, create_group_list_keyboard, create_teacher_selection_keyboard, create_user_selection_keyboard_by_type, create_language_selection_keyboard_for_user, create_group_teacher_selection_keyboard, create_language_selection_keyboard_for_self
from i18n import (
    format_group_level_display,
    format_stored_user_level_display,
    otmen_full_info_line,
    t,
    t_from_update,
    detect_lang_from_user,
    level_ui_label,
)
from payment import set_month_paid, is_month_paid, was_notified_on_day, mark_notified_day
from attendance_manager import (
    attendance_scheduler,
    send_attendance_panel,
    build_attendance_keyboard,
    get_panel_ui_lang,
    get_session,
    set_session_closed,
    set_session_opened,
    set_attendance_student_notify_bot,
)
from broadcast_system import setup_broadcast_handlers
from logging_config import get_logger
from bot_error_notify import notify_admins_unhandled_bot_error
from ai_generator import levels_for_ai_generation
from diamondvoy_core import DiamondVoyAdmin, admin_diamondvoy_trigger, handle_diamondvoy_admin_callback

# Setup logger
logger = get_logger(__name__)

bot: Bot | None = None
student_notify_bot: Bot | None = None
dp = Dispatcher()


def _admin_lang_from_message(message: Message) -> str:
    """Admin language must persist from DB, not Telegram's language_code."""
    try:
        db_user = get_user_by_telegram(str(message.from_user.id))
    except Exception:
        db_user = None
    return detect_lang_from_user(db_user or message.from_user)


def _admin_lang_from_callback(callback: CallbackQuery) -> str:
    """Admin language must persist from DB, not Telegram's language_code."""
    try:
        db_user = get_user_by_telegram(str(callback.from_user.id))
    except Exception:
        db_user = None
    return detect_lang_from_user(db_user or callback.from_user)


def _admin_format_global_daily_tests_history(lang: str) -> str:
    history = get_daily_test_history_global(days=14)
    lines = [t(lang, 'admin_daily_tests_history_title')]
    if not history:
        lines.append(t(lang, 'admin_daily_tests_history_empty'))
    else:
        for row in history:
            td = row.get('test_date')
            completed = row.get('completed_attempts') or 0
            correct_total = row.get('correct_total') or 0
            wrong_total = row.get('wrong_total') or 0
            unanswered_total = row.get('unanswered_total') or 0
            avg_net = row.get('avg_net_dcoins') or 0
            lines.append(
                t(
                    lang,
                    "admin_daily_tests_history_row",
                    td=td,
                    completed=completed,
                    correct_total=correct_total,
                    wrong_total=wrong_total,
                    unanswered_total=unanswered_total,
                    avg_net=avg_net,
                )
            )
    return "\n".join(lines)


def _admin_format_daily_tests_stock_html(lang: str) -> str:
    rows = get_daily_tests_unused_stock_by_subject_level()
    lines = [t(lang, 'daily_tests_stock_report_title')]
    by_sub = {}
    total = 0
    for r in rows:
        sub = (r.get("subject") or "").strip().title()
        lvl = (r.get("level") or "").strip().upper()
        c = int(r.get("c") or 0)
        by_sub.setdefault(sub, []).append((lvl, c))
        total += c
    for sub in sorted(by_sub.keys()):
        lines.append(t(lang, "daily_tests_stock_subject_header", subject=html_module.escape(sub)))
        for lvl, c in sorted(by_sub[sub], key=lambda x: x[0]):
            lines.append(
                t(
                    lang,
                    "daily_tests_stock_level_line",
                    level=html_module.escape(lvl),
                    count=c,
                )
            )
    lines.append(t(lang, "daily_tests_stock_total", total=total))
    return "\n".join(lines)


@dp.errors()
async def admin_global_error_handler(event: ErrorEvent):
    exc = event.exception
    if isinstance(exc, TelegramBadRequest):
        msg = str(exc).lower()
        if "query is too old" in msg or "query id is invalid" in msg:
            logger.warning("Suppressed stale callback error: %s", exc)
            return True
    try:
        # Admin bot o‘zi bilan bir xil sessiyadan foydalanmaslik — yangi Bot orqali yuborish.
        await notify_admins_unhandled_bot_error(
            bot_label="Admin bot",
            event=event,
            admin_bot_instance=None,
        )
    except Exception:
        logger.exception("Adminlarga admin bot xato xabari yuborilmadi")
    return False


# Keep transient admin state between steps in-memory.
admin_state = {}


@dp.callback_query(lambda c: bool(c.data) and c.data.startswith("dv:") and c.from_user.id in ALL_ADMIN_IDS)
async def diamondvoy_core_callback(callback: CallbackQuery):
    lang = detect_lang_from_user(callback.from_user)
    await handle_diamondvoy_admin_callback(bot, callback, lang)


def _is_main_admin(admin_id: int) -> bool:
    return admin_id in ADMIN_CHAT_IDS


def _is_limited_admin(admin_id: int) -> bool:
    return admin_id in LIMITED_ADMIN_CHAT_IDS


def _can_manage_user(admin_id: int, user: dict | None) -> bool:
    """
    General admin (ADMIN_CHAT_IDS): full access.
    Limited admins:
    - students (login_type 1/2): only own users
    - teachers/others: shared (not owner-scoped)
    """
    if not user:
        return False
    if _is_main_admin(admin_id) or not _is_limited_admin(admin_id):
        return True
    if user.get("login_type") in (1, 2):
        if user.get("owner_admin_id") == admin_id:
            return True
        uid = user.get("id")
        if uid is not None and is_student_shared_with_admin(int(uid), admin_id):
            return True
        return False
    return True


def _can_manage_group(admin_id: int, group: dict | None) -> bool:
    """
    General admin (ADMIN_CHAT_IDS): full access.
    Limited admins: only own groups.
    """
    if not group:
        return False
    if _is_main_admin(admin_id) or not _is_limited_admin(admin_id):
        return True
    return group.get("owner_admin_id") == admin_id


def _scope_users_for_admin(admin_id: int, users: list[dict], login_type_filter: tuple[int, ...] | None = None) -> list[dict]:
    if _is_main_admin(admin_id) or not _is_limited_admin(admin_id):
        if login_type_filter is None:
            return users
        return [u for u in users if u.get("login_type") in login_type_filter]
    # Limited admins:
    # - students (1/2): own students ∪ peers with active share
    # - teachers/admins (other types): shared/common visibility
    shared_student_ids = get_shared_student_ids_for_admin(admin_id)
    scoped: list[dict] = []
    for u in users:
        login_type = u.get("login_type")
        if login_type_filter is not None and login_type not in login_type_filter:
            continue
        if login_type in (1, 2):
            uid = u.get("id")
            if u.get("owner_admin_id") == admin_id or (
                uid is not None and int(uid) in shared_student_ids
            ):
                scoped.append(u)
        else:
            scoped.append(u)
    return scoped


def _scope_groups_for_admin(admin_id: int, groups: list[dict]) -> list[dict]:
    if _is_main_admin(admin_id) or not _is_limited_admin(admin_id):
        return groups
    return [g for g in groups if g.get("owner_admin_id") == admin_id]


def _students_for_group_picker(admin_id: int, search_query: str | None) -> list[dict]:
    """
    Students visible to this admin for group add/remove/teacher flows.
    With a non-empty search string, uses DB-backed match on name, login_id, telegram_id.
    """
    sq = (search_query or "").strip()
    if sq:
        raw = search_student_users_for_group_pick(sq, limit=500)
        return _scope_users_for_admin(admin_id, raw, login_type_filter=(1, 2))
    return _scope_users_for_admin(admin_id, get_all_users(), login_type_filter=(1, 2))


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


def _group_level_keyboard_for_subject(subject: str, lang: str) -> InlineKeyboardMarkup:
    subj = (subject or "English").strip().title()
    if subj == "Russian":
        rows = [
            [InlineKeyboardButton(text=t(lang, "level_ru_tier_beginner"), callback_data=f"group_level_pick:{t(lang, 'level_ru_tier_beginner')}")],
            [InlineKeyboardButton(text=t(lang, "level_ru_tier_elementary"), callback_data=f"group_level_pick:{t(lang, 'level_ru_tier_elementary')}")],
            [InlineKeyboardButton(text=t(lang, "level_ru_tier_basic"), callback_data=f"group_level_pick:{t(lang, 'level_ru_tier_basic')}")],
            [InlineKeyboardButton(text=t(lang, "level_ru_tier_upper_mid"), callback_data=f"group_level_pick:{t(lang, 'level_ru_tier_upper_mid')}")],
        ]
        rows.append([InlineKeyboardButton(text=t(lang, "btn_cancel"), callback_data="cancel_group_creation")])
    else:
        rows = [
            [InlineKeyboardButton(text=level_ui_label(lang, subject=subj, code="A1"), callback_data="group_level_pick:A1")],
            [InlineKeyboardButton(text=level_ui_label(lang, subject=subj, code="A2"), callback_data="group_level_pick:A2")],
            [InlineKeyboardButton(text=t(lang, "grammar_level_btn_b1_pre"), callback_data="group_level_pick:B1")],
            [InlineKeyboardButton(text=t(lang, "grammar_level_btn_b1_inter"), callback_data="group_level_pick:B1")],
            [InlineKeyboardButton(text=level_ui_label(lang, subject=subj, code="B2"), callback_data="group_level_pick:B2")],
            [InlineKeyboardButton(text=level_ui_label(lang, subject=subj, code="C1"), callback_data="group_level_pick:C1")],
            [InlineKeyboardButton(text=t(lang, "btn_cancel"), callback_data="cancel_group_creation")],
        ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _group_subject_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "english_subject"), callback_data="grp_subject_English")],
        [InlineKeyboardButton(text=t(lang, "russian_subject"), callback_data="grp_subject_Russian")],
        [InlineKeyboardButton(text=t(lang, "btn_cancel"), callback_data="cancel_group_creation")],
    ])


def _subject_levels_summary(user_id: int, subjects: list) -> str:
    parts: list[str] = []
    for sub in subjects or []:
        if not sub or sub == "—":
            continue
        last = get_latest_test_result_for_subject(int(user_id), str(sub))
        sc = last.get("score") if last else None
        try:
            sc_int = int(sc) if sc is not None else None
        except (TypeError, ValueError):
            sc_int = None
        lvl = level_display_from_score(sc_int, str(sub)) if sc_int is not None else "—"
        parts.append(f"{sub}: {lvl}")
    return ", ".join(parts) if parts else "—"


async def _notify_student_group_assigned(user_id: int, group_id: int) -> None:
    """
    Notify student when admin assigns them to a group.
    Includes group name, teacher, schedule and student count.
    """
    try:
        user = get_user_by_id(user_id)
        group = get_group(group_id)
        if not user or not group:
            return
        tg_id = user.get("telegram_id")
        if not tg_id:
            return
        teacher = get_user_by_id(group.get("teacher_id")) if group.get("teacher_id") else None
        teacher_name = f"{teacher.get('first_name','')} {teacher.get('last_name','')}".strip() if teacher else "-"
        days = _lesson_days_label(group.get("lesson_date"))
        start = (group.get("lesson_start") or "-")[:5]
        end = (group.get("lesson_end") or "-")[:5]
        students_count = len(get_group_users(group_id))

        student_lang = detect_lang_from_user(user)
        text = (
            f"✅ {t(student_lang, 'admin_auto_msg_52')}\n\n"
            f"📚 Guruh: {group.get('name') or '-'}\n"
            f"👨‍🏫 O'qituvchi: {teacher_name}\n"
            f"🗓 Kunlari: {days}\n"
            f"⏰ Vaqti: {start}-{end}\n"
            f"👥 Guruhdagi o'quvchilar: {students_count} ta"
        )
        notify_bot = student_notify_bot or bot
        if notify_bot:
            await notify_bot.send_message(int(tg_id), text)
    except Exception:
        logger.exception("Failed to notify student about new group assignment")


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


def _format_group_line(idx: int, g: dict, lang: str) -> str:
    subject = (g.get("subject") or g.get("level") or "-")
    name = g.get("name") or "-"
    level = g.get("level") or "-"
    start = (g.get("lesson_start") or "-")[:5]
    end = (g.get("lesson_end") or "-")[:5]
    raw_date = g.get("lesson_date") or "-"
    if raw_date.upper() in ('MWF', 'MON/WED/FRI', 'MON,WED,FRI'):
        date = t(lang, 'admin_btn_lesson_days_mwf')
    elif raw_date.upper() in ('TTS', 'TUE/THU/SAT', 'TUE,THU,SAT'):
        date = t(lang, 'admin_btn_lesson_days_tts')
    else:
        date = raw_date
    return t(
        lang,
        'admin_format_group_line',
        idx=idx,
        fan=subject,
        group_name=name,
        level=level,
        date_label=date,
        start=start,
        end=end,
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


def _render_group_list_page_text(lang: str, chunk: list[dict], page: int, total_pages: int) -> str:
    text = t(lang, "admin_group_list_title_with_page", page=page + 1, total=total_pages)
    for i, g in enumerate(chunk, start=1):
        teacher = get_user_by_id(g.get("teacher_id")) if g.get("teacher_id") else None
        t_name = f"{teacher.get('first_name','')} {teacher.get('last_name','')}".strip() if teacher else "—"
        students_count = len(get_group_users(g["id"]))
        lesson_days = _to_lesson_days_text(g.get("lesson_date", "—"), lang=lang)
        start = (g.get("lesson_start") or "—")[:5]
        end = (g.get("lesson_end") or "—")[:5]
        subject = g.get("subject") or "—"
        level = format_group_level_display(lang, g.get("level"), subject=g.get("subject"))
        text += (
            f"\n<b>{i}. {html_module.escape(g.get('name') or '-')}</b>\n"
            f"   📚 Fan: {html_module.escape(str(subject))}\n"
            f"   🎯 Daraja: {html_module.escape(str(level))}\n"
            f"   👨‍🏫 Teacher: {html_module.escape(t_name)}\n"
            f"   🗓 Kunlar: {html_module.escape(str(lesson_days))}\n"
            f"   🕒 Vaqt: {html_module.escape(start)}-{html_module.escape(end)}\n"
            f"   👥 O'quvchilar: {students_count}\n"
        )
    return text


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
    """Send monthly payment reminders on 5/10/15/20/25 to unpaid students."""
    tz = pytz.timezone("Asia/Tashkent")
    remind_days = {5, 10, 15, 20, 25}
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
                    lang = detect_lang_from_user(u)
                    unpaid_groups = [
                        g for g in groups
                        if not is_month_paid(u['id'], ym=ym, group_id=g['id'])
                    ]
                    # One reminder per unpaid group.
                    for g in unpaid_groups:
                        if was_notified_on_day(u['id'], day, ym, group_id=g['id']):
                            continue
                        try:
                            await student_bot.send_message(
                                int(tg),
                                t(lang, "payment_reminder_group_pending", group=g.get('name', '-')),
                            )
                            mark_notified_day(u['id'], day, ym, group_id=g['id'])
                        except Exception:
                            logger.exception(
                                "Monthly payment notify failed user_id=%s group_id=%s",
                                u['id'],
                                g.get('id'),
                            )
        except Exception:
            logger.exception("monthly_payment_scheduler loop error")

        # Sleep relatively often to avoid missing reminder windows.
        # (Notifications are still deduped per (user, ym, group_id, day).)
        await asyncio.sleep(900)


async def overdue_penalty_scheduler():
    """Har kuni kechikkan to'lovlar uchun -2 D'coin qo'llash (Toshkent vaqti)."""
    from payment import apply_daily_overdue_penalties
    tz = pytz.timezone("Asia/Tashkent")
    last_run_date = None
    while True:
        try:
            now = datetime.now(tz)
            today = now.strftime("%Y-%m-%d")
            if last_run_date != today:
                cnt = apply_daily_overdue_penalties()
                if cnt > 0:
                    logger.info(f"Kechikkan to'lov penalty: {cnt} ta -2 D'coin qo'llandi")
                last_run_date = today
        except Exception:
            logger.exception("overdue_penalty_scheduler error")
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
        f"2) Level: {format_group_level_display(lang, group.get('level'), subject=group.get('subject'))}\n"
        f"3) Teacher: {teacher_name}\n"
        f"4) Dars vaqti: {date} | {start}-{end} ({group.get('tz') or 'Asia/Tashkent'})\n"
        f"5) O‘quvchilar soni: {len(students)}"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "btn_grp_time"), callback_data=f"grp_set:{group_id}:time")],
        [InlineKeyboardButton(text=t(lang, 'admin_btn_lesson_days'), callback_data=f"grp_set:{group_id}:days")],
        
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


@dp.callback_query(lambda c: c.data.startswith("group_detail_"))
async def handle_group_detail_callback(callback: CallbackQuery):
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    try:
        gid = int(callback.data.split("_")[-1])
    except ValueError:
        await callback.answer()
        return
    await _show_group_details(callback, gid)


@dp.callback_query(lambda c: c.data.startswith("group_edit_name_"))
async def handle_group_edit_name_btn(callback: CallbackQuery):
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    group_id = int(callback.data.split("_")[-1])
    state = get_admin_state(callback.message.chat.id)
    state['step'] = 'edit_group_name'
    state['data']['edit_group_id'] = group_id
    lang = detect_lang_from_user(callback.from_user)
    await callback.message.answer(t(lang, 'ask_group_name'))
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("group_edit_level_"))
async def handle_group_edit_level_btn(callback: CallbackQuery):
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    group_id = int(callback.data.split("_")[-1])
    state = get_admin_state(callback.message.chat.id)
    state['step'] = 'edit_group_level'
    state['data']['edit_group_id'] = group_id
    lang = detect_lang_from_user(callback.from_user)
    grp = get_group(group_id)
    subj = (grp.get("subject") or "English") if grp else "English"
    await callback.message.answer(
        t(lang, 'ask_group_level'),
        reply_markup=_group_level_keyboard_for_subject(subj, lang),
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("group_delete_confirm_"))
async def handle_group_delete_confirm_btn(callback: CallbackQuery):
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    group_id = int(callback.data.split("_")[-1])
    group = get_group(group_id)
    lang = detect_lang_from_user(callback.from_user)
    if not group:
        await callback.answer(t(lang, 'group_not_found'))
        return
    confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, 'btn_yes'), callback_data=f"grp_delete_yes:{group_id}")],
        [InlineKeyboardButton(text=t(lang, 'btn_no'), callback_data=f"grp_delete_no:{group_id}")],
    ])
    await callback.message.answer(
        t(
            lang,
            "admin_confirm_delete_group_details",
            group_name=group.get("name"),
            group_level=group.get("level"),
            confirm=t(lang, "confirm_delete_group"),
        ),
        reply_markup=confirm_kb,
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data == "cancel_edit_group_days")
async def handle_cancel_edit_group_days(callback: CallbackQuery):
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    state = get_admin_state(callback.message.chat.id)
    if state.get('step') == 'edit_group_days':
        state['step'] = None
    lang = detect_lang_from_user(callback.from_user)
    await callback.message.answer(t(lang, 'operation_cancelled'))
    await callback.answer()


@dp.message(Command('main'))
async def cmd_main(message: Message):
    """Return to main menu"""
    if message.from_user.id not in ALL_ADMIN_IDS:
        await message.answer(t_from_update(message, 'admin_only'))
        return
    
    reset_admin_state(message.chat.id)
    lang = _admin_lang_from_message(message)
    await message.answer(t(lang, 'admin_panel'), reply_markup=admin_main_keyboard(lang))


@dp.message(Command('start'))
async def cmd_start(message: Message):
    if message.from_user.id not in ALL_ADMIN_IDS:
        await message.answer(t_from_update(message, 'admin_only'))
        return
    lang = _admin_lang_from_message(message)
    await message.answer(t(lang, 'welcome_admin'), reply_markup=admin_main_keyboard(lang))


@dp.message(Command('admin'))
async def cmd_admin(message: Message):
    if message.from_user.id not in ALL_ADMIN_IDS:
        await message.answer(t_from_update(message, 'admin_only'))
        return
    lang = _admin_lang_from_message(message)
    await message.answer(t(lang, 'admin_panel'), reply_markup=admin_main_keyboard(lang))


@dp.message(lambda m: get_admin_state(m.chat.id).get('step') not in {
    'students_search',
    'teachers_search',
    'search_group_students',
    'ask_group_name',
    'ask_group_level',
})
async def handle_admin_text(message: Message):
    if message.from_user.id not in ALL_ADMIN_IDS:
        await message.answer(t_from_update(message, 'admin_only'))
        return
    text = message.text.strip() if message.text else ''
    state = get_admin_state(message.chat.id)
    lang = _admin_lang_from_message(message)
    
    # Safety check: if state seems invalid, reset to main menu
    if state and not isinstance(state, dict) or 'step' not in state:
        logger.warning(f"Invalid state detected, resetting: {state}")
        reset_admin_state(message.chat.id)
        state = get_admin_state(message.chat.id)
    
    logger.info(f"Admin message received: text='{text}', step='{state.get('step')}', chat_id={message.chat.id}")

    # Cancel current flow (strict label match; avoid catching "Cancel lessons")
    text_l = text.lower().strip()
    text_l_no_emoji = text_l.lstrip("❌").strip()
    cancel_labels = set()
    for L in ("uz", "ru", "en"):
        try:
            lbl = t(L, "cancel").lower().strip()
            cancel_labels.add(lbl)
            cancel_labels.add(lbl.lstrip("❌").strip())
        except Exception:
            continue
    if (
        text_l in ("/cancel", "/bekor", "/stop")
        or text_l in cancel_labels
        or text_l_no_emoji in cancel_labels
    ):
        logger.info(f"Cancel triggered: text='{text}', step='{state.get('step')}', chat_id={message.chat.id}")
        reset_admin_state(message.chat.id)
        await message.answer(t(lang, 'admin_panel'), reply_markup=admin_main_keyboard(lang))
        return

    if state.get("step") == "dv_db_reset_await_code":
        if message.from_user.id not in ALL_ADMIN_IDS:
            reset_admin_state(message.chat.id)
            await message.answer(t(lang, "diamondvoy_db_reset_forbidden_limited"))
            return
        if not DIAMONDVOY_DB_RESET_SECRET:
            reset_admin_state(message.chat.id)
            await message.answer(t(lang, "diamondvoy_db_reset_secret_not_configured"))
            return
        provided = (text or "").strip()
        exp = DIAMONDVOY_DB_RESET_SECRET.encode("utf-8")
        prov = provided.encode("utf-8")
        try:
            ok = secrets.compare_digest(prov, exp)
        except TypeError:
            ok = False
        if ok:
            try:
                await asyncio.to_thread(wipe_postgresql_database_and_reinit)
            except Exception as e:
                logger.exception("wipe_postgresql_database_and_reinit")
                reset_admin_state(message.chat.id)
                await message.answer(t(lang, "error_with_reason", error=str(e)))
                return
            reset_admin_state(message.chat.id)
            await message.answer(t(lang, "diamondvoy_db_reset_success"))
        else:
            reset_admin_state(message.chat.id)
            await message.answer(t(lang, "diamondvoy_db_reset_wrong_code"))
        return

    # Normalize incoming text to handle emoji variants, smart quotes and other
    # minor differences between clients so button presses map correctly.
    try:
        norm = unicodedata.normalize('NFKC', text)
    except Exception:
        norm = text
    norm = norm.replace('‘', "'").replace('’', "'").replace('`', "'")
    tl = norm.lower()

    if admin_diamondvoy_trigger(norm):
        await DiamondVoyAdmin(bot).process(message, lang)
        return

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
    def matches_aliases(key: str):
        for L in langs:
            try:
                raw = str(t(L, key) or "")
            except Exception:
                raw = ""
            for token in [x.strip().lower() for x in raw.split(",") if x.strip()]:
                if token and token in tl:
                    return True
        return False

    # === STUDENTS LIST ===
    if matches_label('students_list_title') or matches_aliases("menu_students_aliases"):
        await show_students_list(message, page=0)
        return

    if matches_label('teachers_list_title') or matches_aliases("menu_teachers_aliases"):
        await show_teachers_list(message)
        return

    if matches_label('groups_menu') or 'guruh' in tl or 'group' in tl:
        await show_group_menu(message)
        return

    if matches_label('admin_dcoin_leaderboard_btn'):
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=s, callback_data=f"ad_lb_s:{s}")] for s in SUBJECTS
            ]
        )
        await message.answer(t(lang, 'staff_dcoin_pick_subject_prompt'), reply_markup=kb)
        return

    if matches_label('payments_btn') or matches_aliases("menu_payments_aliases"):
        await show_payment_menu(message)
        return

    if matches_label('admin_attendance_btn') or matches_aliases("menu_attendance_aliases"):
        await show_attendance_menu(message)
        return
    if matches_label('admin_cancel_lessons_btn') or 'otmen' in tl:
        await show_cancel_lessons_menu(message)
        return
    # Show language selection keyboard when admin presses the language button
    if matches_label('choose_lang') or 'til' in tl or 'language' in tl:
        await message.answer(t(lang, 'choose_lang'), reply_markup=create_language_selection_keyboard_for_self(lang))
        return

    if state['step'] == 'admin_otmen_reason':
        req_id = (state.get('data') or {}).get('otmen_req_id')
        reason = (text or "").strip()
        if not req_id:
            reset_admin_state(message.chat.id)
            await message.answer(t(lang, "admin_cancel_lessons_invalid"))
            return
        if not reason:
            await message.answer(t(lang, "admin_cancel_lessons_reason_prompt"))
            return
        ok, msg = await _execute_otmen_request(
            req_id=str(req_id),
            admin_user={"id": message.from_user.id},
            lang=lang,
            reason_override=reason,
        )
        reset_admin_state(message.chat.id)
        if ok:
            await message.answer(msg, parse_mode="HTML")
        else:
            await message.answer(msg)
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
        await message.answer(t(lang, 'ask_subject'), reply_markup=create_subject_keyboard(lang))
        return

    if state['step'] == 'ask_subject':
        subject = text.title()
        if subject not in SUBJECTS:
            await message.answer(t(lang, 'ask_subject'), reply_markup=create_subject_keyboard(lang))
            return
        state['data']['subject'] = subject

        login_type = state['data'].get('login_type', 1)
        user = create_user_sync(
            first_name=state['data']['first_name'],
            last_name=state['data']['last_name'],
            phone=state['data']['phone'],
            subject=state['data']['subject'],
            login_type=login_type,
            owner_admin_id=message.from_user.id if login_type in (1, 2) else None,
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
                    await message.answer(
                        t(lang, "admin_test_sent_to_admin", first_name=user['first_name'], last_name=user['last_name'])
                    )
                except Exception as e:
                    await message.answer(t(lang, "admin_test_send_error", error=e))
                
                # Reset to main menu after sending test
                reset_admin_state(message.chat.id)
            else:
                await message.answer(t(lang, 'admin_auto_msg_1'))
                
        elif login_type == 2:
            # Existing student - ask which group to attach
            groups = _scope_groups_for_admin(message.from_user.id, get_all_groups())
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
            await message.answer(t(lang, 'admin_auto_msg_2'))
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
            await message.answer(t(lang, 'admin_auto_msg_3'))
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
            await message.answer(t(lang, 'admin_auto_msg_2'))
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
            await message.answer(t(lang, 'admin_auto_msg_3'))
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
            await message.answer(t(lang, 'admin_auto_msg_4'))
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
                t(lang, "admin_select_subject_from_buttons_error"),
                reply_markup=create_subject_keyboard(lang)
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
        state['step'] = 'ask_group_subject'
        await message.answer(t(lang, 'ask_group_subject'), reply_markup=_group_subject_keyboard(lang))
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
            [InlineKeyboardButton(text=t(lang, 'admin_btn_lesson_days_mwf'), callback_data="group_days:MWF")],
            [InlineKeyboardButton(text=t(lang, 'admin_btn_lesson_days_tts'), callback_data="group_days:TTS")],
            [InlineKeyboardButton(text=t(lang, 'btn_cancel'), callback_data="cancel_group_creation")],
        ])
        await message.answer(t(lang, 'ask_group_days'), reply_markup=kb)
        return

    # Note: ask_group_days step is handled by callback queries only
    # Admin must use buttons (Mon,Wed,Fri or Tue,Thu,Sat) to select days
    
    if state.get('step') == 'ask_group_days':
        # Admin is trying to type days instead of using buttons
        days_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, 'admin_btn_lesson_days_mwf'), callback_data="group_days:MWF")],
            [InlineKeyboardButton(text=t(lang, 'admin_btn_lesson_days_tts'), callback_data="group_days:TTS")],
            [InlineKeyboardButton(text=t(lang, 'btn_cancel'), callback_data="cancel_group_creation")],
        ])
        await message.answer(
            t(lang, "admin_select_days_from_buttons_error"),
            reply_markup=days_kb
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
        
        # ─── O'QITUVCHI TANLASH ───────────────────────
        await ask_group_teacher(message, lang, state)
        return

    # Teacher selection handler
    if state.get('step') == 'ask_teacher_for_group':
        # This will be handled by callback query, but we can add text input handling
        await message.answer(
            t(lang, 'admin_auto_msg_5')
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
        from db import get_group, normalize_russian_group_level

        grp = get_group(int(group_id))
        raw = text.strip()
        if grp and (grp.get('subject') or '').strip().title() == 'Russian':
            norm_ru = normalize_russian_group_level(raw)
            if not norm_ru:
                await message.answer(t(lang, 'group_level_invalid'))
                return
            update_group_level(int(group_id), norm_ru, sync_students=True)
        else:
            update_group_level(int(group_id), raw.upper(), sync_students=True)
        await message.answer(t(lang, "group_level_updated"))
        reset_admin_state(message.chat.id)
        return

    if state.get('step') == 'edit_group_time':
        state['step'] = 'edit_group_start'
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

    if matches_label('choose_user_type') or matches_aliases("menu_new_user_aliases"):
        state['step'] = 'choose_type'
        await message.answer(t(lang, 'new_user_type_prompt'), reply_markup=create_user_type_keyboard(lang))
        return

    if matches_label('admin_results_btn') or matches_label('recent_results_title') or 'natija' in tl or 'result' in tl:
        results = get_recent_results(limit=15)
        if not results:
            await message.answer(t(lang, 'no_results'))
            return

        def _format_dmy(created_at_val) -> str:
            # Expect ISO-like formats; output DD.MM.YYYY.
            if not created_at_val:
                return ''
            if isinstance(created_at_val, str):
                iso_day = created_at_val[:10]
                try:
                    from datetime import datetime
                    dt = datetime.strptime(iso_day, "%Y-%m-%d")
                    return dt.strftime("%d.%m.%Y")
                except Exception:
                    return iso_day
            try:
                return created_at_val.strftime("%d.%m.%Y")
            except Exception:
                return ''

        total_questions = 50
        lines: list[str] = []
        for idx, r in enumerate(results, start=1):
            user = get_user_by_id(r.get('user_id'))
            first_name = user.get('first_name', '—') if user else '—'
            last_name = user.get('last_name', '') if user else ''

            raw_score = int(r.get('score') or 0)
            # Placement score: 0..500 where each correct answer is worth 10 points.
            correct_count = raw_score // 10
            percentage = min(100, int((raw_score / 500) * 100)) if raw_score is not None else 0

            subj = (r.get('subject') or "").strip().title()
            lvl_code = (r.get('level') or "").strip()
            level_line = level_ui_label(lang, subject=subj, code=lvl_code) if lvl_code else "—"

            date_dmy = _format_dmy(r.get('created_at'))

            entry = t(
                lang,
                'admin_placement_results_entry',
                i=idx,
                first_name=html_module.escape(str(first_name or '—')),
                last_name=html_module.escape(str(last_name or '')),
                subject=html_module.escape(subj or '—'),
                level=html_module.escape(str(level_line or '—')),
                correct_count=correct_count,
                percentage=percentage,
                date=date_dmy,
            )
            lines.append(entry.strip())

        await message.answer("\n\n".join(lines), parse_mode="HTML")
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
    if (
        matches_aliases("menu_vocab_io_aliases")
        or ('sozlar import/export' in tl)
        or ('sozlar import' in tl and 'export' in tl)
        or ('import_vocab' in tl)
        or (text.strip().lower() == '/vocab')
    ):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, 'vocab_import_btn'), callback_data='admin_vocab_action_import')],
            [InlineKeyboardButton(text=t(lang, 'vocab_export_btn'), callback_data='admin_vocab_action_export')],
        ])
        await message.answer(t(lang, 'choose'), reply_markup=kb)
        return

    # AI menu (admin main control)
    if matches_label('admin_ai_menu_btn'):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, 'admin_ai_menu_vocab_generate_btn'), callback_data='admin_ai_vocab_action_generate')],
            [InlineKeyboardButton(text=t(lang, 'admin_ai_menu_daily_tests_generate_btn'), callback_data='admin_ai_daily_tests_action_generate')],
            [InlineKeyboardButton(text=t(lang, 'admin_ai_menu_daily_tests_stock_btn'), callback_data='admin_ai_daily_tests_stock_view')],
            [InlineKeyboardButton(text=t(lang, 'admin_ai_menu_daily_tests_history_btn'), callback_data='admin_ai_daily_tests_history_view')],
            [InlineKeyboardButton(text=t(lang, 'vocab_export_btn'), callback_data='admin_vocab_action_export')],
        ])
        await message.answer(t(lang, 'choose'), reply_markup=kb)
        return

    # Export full system to XLSX
    if text.strip().lower() in ('/export_all', '/export') or ('export (xlsx)' in tl) or (tl.startswith('📤') and 'export' in tl):
        if message.from_user.id not in ALL_ADMIN_IDS:
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
            await message.answer(t(lang, "admin_xlsx_error", error=e))
            state['step'] = None
            state['data'] = {}
            return

        await message.answer(t(lang, 'vocab_import_result', inserted=report['inserted'], skipped=report['skipped'], total=report['total']))
        # Show duplicates to uploader (admin) as a compact list
        if report.get('duplicates'):
            words = report['duplicates'][:30]
            more = len(report['duplicates']) - len(words)
            items = "\n".join([f"- {w}" for w in words])
            msg = t(lang, "admin_vocab_duplicates_skipped_header", items=items)
            if more > 0:
                msg += t(lang, "admin_vocab_duplicates_skipped_more", more=more)
            await message.answer(msg)

        state['step'] = None
        state['data'] = {}
        return

    # ===== AI generation flows (admin) =====
    if state.get('step') == 'admin_ai_vocab_await_count':
        if not text.isdigit():
            await message.answer(t(lang, "validation_enter_number_example", example=50))
            return
        count = int(text)
        if count <= 0 or count > 5000:
            await message.answer(t(lang, "validation_count_range", min=1, max=5000))
            return

        from ai_generator import generate_vocabulary_and_insert

        subject = state['data'].get('subject')
        level = state['data'].get('level')
        created_by = state['data'].get('created_by')
        try:
            progress_msg = await message.answer(
                t(lang, "ai_generation_progress_pct_detail", pct=0, current=0, total=count)
            )
            remaining = count
            batch_size = 50
            requested = generated = inserted = skipped = 0
            while remaining > 0:
                cur = min(batch_size, remaining)
                rep = await generate_vocabulary_and_insert(
                    subject=subject,
                    level=level,
                    count=cur,
                    added_by=created_by,
                )
                requested += int(rep.requested or 0)
                generated += int(rep.generated or 0)
                inserted += int(rep.inserted or 0)
                skipped += int(rep.skipped or 0)
                remaining -= cur
                done = count - remaining
                pct = int((done * 100) / max(1, count))
                try:
                    await progress_msg.edit_text(
                        t(lang, "ai_generation_progress_pct_detail", pct=pct, current=done, total=count)
                    )
                except Exception:
                    pass
            report = type("R", (), {"requested": requested, "generated": generated, "inserted": inserted, "skipped": skipped})()
            await message.answer(t(lang, "admin_ai_vocab_done_report", requested=report.requested, generated=report.generated, inserted=report.inserted, skipped=report.skipped))
        except Exception as e:
            await message.answer(t(lang, "admin_ai_vocab_error", error=str(e)))

        state['step'] = None
        state['data'] = {}
        return

    if state.get('step') == 'admin_ai_daily_tests_await_count':
        if not text.isdigit():
            await message.answer(t(lang, "validation_enter_number_example", example=20))
            return
        count = int(text)
        if count <= 0 or count > 5000:
            await message.answer(t(lang, "validation_count_range", min=1, max=5000))
            return

        from ai_generator import generate_daily_tests_and_insert
        from db import count_available_daily_tests_global

        subject = state['data'].get('subject')
        level = state['data'].get('level')
        created_by = state['data'].get('created_by')
        try:
            stock_before = int(count_available_daily_tests_global() or 0)
            progress_msg = await message.answer(
                t(lang, "ai_generation_progress_pct_detail", pct=0, current=0, total=count)
            )
            remaining = count
            batch_size = 50
            requested = generated = inserted = skipped = 0
            while remaining > 0:
                cur = min(batch_size, remaining)
                rep = await generate_daily_tests_and_insert(
                    subject=subject,
                    level=level,
                    count=cur,
                    created_by=created_by,
                )
                requested += int(rep.requested or 0)
                generated += int(rep.generated or 0)
                inserted += int(rep.inserted or 0)
                skipped += int(rep.skipped or 0)
                remaining -= cur
                done = count - remaining
                pct = int((done * 100) / max(1, count))
                try:
                    await progress_msg.edit_text(
                        t(lang, "ai_generation_progress_pct_detail", pct=pct, current=done, total=count)
                    )
                except Exception:
                    pass
            report = type("R", (), {"requested": requested, "generated": generated, "inserted": inserted, "skipped": skipped})()
            stock_after = int(count_available_daily_tests_global() or 0)
            await message.answer(
                t(
                    lang,
                    "admin_ai_daily_tests_done_report",
                    requested=report.requested,
                    generated=report.generated,
                    inserted=report.inserted,
                    skipped=report.skipped,
                    stock_before=stock_before,
                    stock_after=stock_after,
                    stock_delta=(stock_after - stock_before),
                )
            )
        except Exception as e:
            await message.answer(t(lang, "admin_ai_daily_tests_error", error=str(e)))

        state['step'] = None
        state['data'] = {}
        return


@dp.callback_query(lambda c: c.data in ('admin_vocab_action_import', 'admin_vocab_action_export'))
async def handle_admin_vocab_action(callback: CallbackQuery):
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        await callback.message.answer(t_from_update(callback, 'admin_only'))
        return
    state = get_admin_state(callback.message.chat.id)
    lang = _admin_lang_from_callback(callback)
    action = callback.data.split('_')[-1]  # import/export
    if action == 'import':
        state['step'] = 'admin_await_vocab_subject'
        state['data'] = {}
        await callback.answer()
        await callback.message.answer(t(lang, 'send_vocab_subject'), reply_markup=create_subject_keyboard(lang))
        return
    if action == 'export':
        state['step'] = 'admin_export_choose_subject'
        state['data'] = {}
        await callback.answer()
        await callback.message.answer(t(lang, 'choose_subject_export'), reply_markup=create_subject_keyboard(lang))
        return


@dp.callback_query(lambda c: c.data == 'admin_ai_vocab_action_generate')
async def handle_admin_ai_vocab_generate_start(callback: CallbackQuery):
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        await callback.message.answer(t_from_update(callback, 'admin_only'))
        return

    state = get_admin_state(callback.message.chat.id)
    state['step'] = 'admin_ai_vocab_choose_subject'
    state['data'] = {'created_by': callback.from_user.id}

    await callback.answer()
    alang = _admin_lang_from_callback(callback)
    await callback.message.answer(
        t(alang, "admin_ai_choose_subject_vocab_prompt"),
        reply_markup=create_subject_keyboard(alang),
    )


@dp.callback_query(lambda c: c.data == 'admin_ai_daily_tests_action_generate')
async def handle_admin_ai_daily_tests_generate_start(callback: CallbackQuery):
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        await callback.message.answer(t_from_update(callback, 'admin_only'))
        return

    state = get_admin_state(callback.message.chat.id)
    state['step'] = 'admin_ai_daily_tests_choose_subject'
    state['data'] = {'created_by': callback.from_user.id}

    await callback.answer()
    alang = _admin_lang_from_callback(callback)
    await callback.message.answer(
        t(alang, "admin_ai_choose_subject_daily_tests_prompt"),
        reply_markup=create_subject_keyboard(alang),
    )


@dp.callback_query(lambda c: c.data.startswith('subject_') and get_admin_state(c.message.chat.id).get('step') in ('admin_ai_vocab_choose_subject', 'admin_ai_daily_tests_choose_subject'))
async def handle_admin_ai_choose_subject(callback: CallbackQuery):
    state = get_admin_state(callback.message.chat.id)
    if state.get('step') not in ('admin_ai_vocab_choose_subject', 'admin_ai_daily_tests_choose_subject'):
        return

    lang = _admin_lang_from_callback(callback)
    data = callback.data
    subject = data.split('_', 1)[1]
    subject = subject.strip().title()

    if state.get('step') == 'admin_ai_vocab_choose_subject':
        state['data']['subject'] = subject
        state['step'] = 'admin_ai_vocab_choose_level'
        lvls = levels_for_ai_generation(subject)
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=level_ui_label(lang, subject=subject, code=lvl),
                        callback_data=f"admin_ai_vocab_level_{lvl}",
                    )
                ]
                for lvl in lvls
            ]
        )
        await callback.answer()
        await callback.message.answer(t(lang, "choose_level_prompt"), reply_markup=kb)
        return

    if state.get('step') == 'admin_ai_daily_tests_choose_subject':
        state['data']['subject'] = subject
        state['step'] = 'admin_ai_daily_tests_choose_level'
        lvls = levels_for_ai_generation(subject)
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=level_ui_label(lang, subject=subject, code=lvl),
                        callback_data=f"admin_ai_daily_tests_level_{lvl}",
                    )
                ]
                for lvl in lvls
            ]
        )
        await callback.answer()
        await callback.message.answer(t(lang, "choose_level_prompt"), reply_markup=kb)
        return


@dp.callback_query(lambda c: c.data.startswith('admin_ai_vocab_level_') and get_admin_state(c.message.chat.id).get('step') == 'admin_ai_vocab_choose_level')
async def handle_admin_ai_vocab_level(callback: CallbackQuery):
    state = get_admin_state(callback.message.chat.id)
    lang = _admin_lang_from_callback(callback)
    level = callback.data.split('admin_ai_vocab_level_', 1)[-1].strip().upper()
    subj = (state.get("data") or {}).get("subject") or ""
    if level not in set(levels_for_ai_generation(subj)):
        await callback.answer(t(lang, "group_level_invalid"), show_alert=True)
        return
    state['data']['level'] = level
    state['step'] = 'admin_ai_vocab_await_count'

    await callback.answer()
    await callback.message.answer(
        t(
            lang,
            "admin_ai_vocab_count_prompt",
            subject=state["data"].get("subject"),
            level=level_ui_label(lang, subject=subj, code=level),
            example=50,
            max=5000,
        ),
        reply_markup=cancel_keyboard(lang),
    )


@dp.callback_query(lambda c: c.data.startswith('admin_ai_daily_tests_level_') and get_admin_state(c.message.chat.id).get('step') == 'admin_ai_daily_tests_choose_level')
async def handle_admin_ai_daily_tests_level(callback: CallbackQuery):
    state = get_admin_state(callback.message.chat.id)
    lang = _admin_lang_from_callback(callback)
    level = callback.data.split('admin_ai_daily_tests_level_', 1)[-1].strip().upper()
    subj = (state.get("data") or {}).get("subject") or ""
    if level not in set(levels_for_ai_generation(subj)):
        await callback.answer(t(lang, "group_level_invalid"), show_alert=True)
        return
    state['data']['level'] = level
    state['step'] = 'admin_ai_daily_tests_await_count'

    await callback.answer()
    await callback.message.answer(
        t(
            lang,
            "admin_ai_daily_tests_count_prompt",
            subject=state["data"].get("subject"),
            level=level_ui_label(lang, subject=subj, code=level),
            example=20,
            max=5000,
        ),
        reply_markup=cancel_keyboard(lang),
    )


async def _admin_send_dcoin_leaderboard_message(message: Message, lang: str, subject: str, page: int) -> None:
    per_page = 20
    total_users = get_staff_leaderboard_student_count(subject)
    total_pages = max(1, (total_users + per_page - 1) // per_page)
    page = max(0, min(int(page), total_pages - 1))
    offset = page * per_page
    rows = get_staff_leaderboard_by_subject(subject, limit=per_page, offset=offset)
    lines = [
        t(lang, 'staff_dcoin_leaderboard_title', subject=html_module.escape(subject)),
        t(lang, 'staff_dcoin_leaderboard_subtitle'),
        "",
    ]
    if not rows:
        lines.append(t(lang, 'staff_dcoin_leaderboard_empty'))
    else:
        for i, r in enumerate(rows):
            raw_name = f"{r.get('first_name') or ''} {r.get('last_name') or ''}".strip() or "-"
            name = html_module.escape(raw_name)
            bal = float(r.get("dcoin_balance") or 0)
            rank = offset + i + 1
            lines.append(t(lang, 'staff_dcoin_leaderboard_line', rank=rank, name=name, dcoin=bal))
    lines.append("")
    lines.append(
        t(
            lang,
            'staff_dcoin_leaderboard_footer',
            page=page + 1,
            total_pages=total_pages,
            total=total_users,
        )
    )
    nav = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(
                text=t(lang, 'btn_prev'),
                callback_data=f"ad_lb_p:{subject}:{page - 1}",
            )
        )
    if page < total_pages - 1:
        nav.append(
            InlineKeyboardButton(
                text=t(lang, 'btn_next'),
                callback_data=f"ad_lb_p:{subject}:{page + 1}",
            )
        )
    rows = []
    if nav:
        rows.append(nav)
    rows.append(
        [
            InlineKeyboardButton(
                text=t(lang, "staff_dcoin_export_btn"),
                callback_data=f"ad_lb_exp:{subject}",
            )
        ]
    )
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=kb)


@dp.callback_query(lambda c: c.data == 'admin_ai_daily_tests_stock_view')
async def handle_admin_ai_daily_tests_stock_view(callback: CallbackQuery):
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    lang = _admin_lang_from_callback(callback)
    await callback.answer()
    await callback.message.answer(_admin_format_daily_tests_stock_html(lang), parse_mode="HTML")


@dp.callback_query(lambda c: c.data == 'admin_ai_daily_tests_history_view')
async def handle_admin_ai_daily_tests_history_view(callback: CallbackQuery):
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    lang = _admin_lang_from_callback(callback)
    await callback.answer()
    await callback.message.answer(_admin_format_global_daily_tests_history(lang), parse_mode="HTML")


@dp.callback_query(lambda c: c.data.startswith('ad_lb_s:'))
async def handle_admin_dcoin_lb_subject(callback: CallbackQuery):
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    lang = _admin_lang_from_callback(callback)
    raw = callback.data.split(":", 1)[1].strip()
    norm = next((s for s in SUBJECTS if s.lower() == raw.lower()), None)
    if not norm:
        await callback.answer(t(lang, "invalid_subject"), show_alert=True)
        return
    await callback.answer()
    await _admin_send_dcoin_leaderboard_message(callback.message, lang, norm, 0)


@dp.callback_query(lambda c: c.data.startswith('ad_lb_p:'))
async def handle_admin_dcoin_lb_page(callback: CallbackQuery):
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    lang = _admin_lang_from_callback(callback)
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer()
        return
    _, subj_raw, p = parts
    norm = next((s for s in SUBJECTS if s.lower() == subj_raw.strip().lower()), None)
    if not norm:
        await callback.answer(t(lang, "invalid_subject"), show_alert=True)
        return
    try:
        page = int(p)
    except ValueError:
        await callback.answer()
        return
    await callback.answer()
    await _admin_send_dcoin_leaderboard_message(callback.message, lang, norm, page)


@dp.callback_query(lambda c: c.data.startswith('ad_lb_exp:'))
async def handle_admin_dcoin_lb_export(callback: CallbackQuery):
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    lang = _admin_lang_from_callback(callback)
    raw = callback.data.split(":", 1)[1].strip()
    norm = next((s for s in SUBJECTS if s.lower() == raw.lower()), None)
    if not norm:
        await callback.answer(t(lang, "invalid_subject"), show_alert=True)
        return
    owner_filter = callback.from_user.id if _is_limited_admin(callback.from_user.id) else None
    try:
        from vocabulary import export_subject_dcoin_history_to_xlsx

        bio, fname = export_subject_dcoin_history_to_xlsx(
            norm,
            owner_admin_id=owner_filter,
            lang=lang,
        )
    except ValueError:
        await callback.answer()
        await callback.message.answer(
            t(lang, "staff_dcoin_export_empty", subject=html_module.escape(norm)),
            parse_mode="HTML",
        )
        return
    except Exception:
        logger.exception("D'coin history export failed for subject=%s", norm)
        await callback.answer()
        await callback.message.answer(t(lang, "staff_dcoin_export_error"))
        return

    await callback.answer(t(lang, "staff_dcoin_export_started"))
    await callback.message.answer_document(
        BufferedInputFile(bio.getvalue(), filename=fname),
        caption=t(lang, "staff_dcoin_export_caption", subject=html_module.escape(norm)),
        parse_mode="HTML",
    )


@dp.callback_query(lambda c: c.data.startswith('subject_') and get_admin_state(c.message.chat.id).get('step') in ('admin_export_choose_subject', 'admin_await_vocab_subject', 'ask_subject', 'ask_test_subject', 'add_subject'))
async def handle_subject_for_admin_vocab(callback: CallbackQuery):
    data = callback.data
    state = get_admin_state(callback.message.chat.id)
    lang = _admin_lang_from_callback(callback)
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
                            t(
                                lang,
                                "admin_subject_added_to_user",
                                subject=subject,
                                first_name=user.get("first_name", ""),
                                last_name=user.get("last_name", ""),
                                subjects=", ".join(subjects),
                            )
                        )
                    else:
                        await callback.message.answer(
                            t(
                                lang,
                                "admin_subject_add_limit_two_error",
                                first_name=user.get("first_name", ""),
                                last_name=user.get("last_name", ""),
                            )
                        )
                else:
                    await callback.message.answer(
                        t(lang, "admin_subject_already_exists", subject=subject)
                    )
            else:
                await callback.message.answer(t(lang, 'admin_auto_msg_6'))
        await callback.answer()
        return

    # New user creation subject selection
    if state.get('step') == 'ask_subject':
        state['data']['subject'] = subject
        user_data = state['data']
        from auth import create_user_sync
        user = create_user_sync(
            first_name=user_data['first_name'],
            last_name=user_data['last_name'],
            phone=user_data['phone'],
            login_type=user_data['login_type'],
            subject=subject,
            owner_admin_id=callback.from_user.id if user_data['login_type'] in (1, 2) else None,
        )
        
        await callback.message.answer(
            t(
                lang,
                "admin_user_created_credentials",
                login_id=user["login_id"],
                password=user["password"],
            ),
            parse_mode="HTML",
        )

        # Keep old behavior by login_type:
        # 1 -> placement test flow, 2 -> attach to group flow
        login_type = int(user_data.get('login_type') or 1)
        if login_type == 1:
            from db import prepare_user_for_new_test
            prepare_user_for_new_test(user['id'], subject)

            if user.get('telegram_id'):
                try:
                    from student_bot import start_placement_test
                    await start_placement_test(int(user['telegram_id']), subject)
                    await callback.message.answer(
                        t(lang, "admin_test_sent_to_admin", first_name=user['first_name'], last_name=user['last_name'])
                    )
                except Exception as e:
                    await callback.message.answer(t(lang, "admin_test_send_error", error=e))
            else:
                await callback.message.answer(t(lang, 'admin_auto_msg_1'))
            reset_admin_state(callback.message.chat.id)
            await callback.answer()
            return

        if login_type == 2:
            groups = _scope_groups_for_admin(callback.from_user.id, get_all_groups())
            if not groups:
                await callback.message.answer(t(lang, "no_groups"))
                reset_admin_state(callback.message.chat.id)
                await callback.answer()
                return
            await callback.message.answer(
                t(lang, "select_group_to_add_user"),
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text=t(lang, "btn_choose_group"), callback_data=f"assign_new:{user['id']}:page:0")]
                    ]
                )
            )
            reset_admin_state(callback.message.chat.id)
            await callback.answer()
            return

        reset_admin_state(callback.message.chat.id)
        await callback.answer()
        return

    # Test subject selection
    if state.get('step') == 'ask_test_subject':
        user_id = state['data'].get('test_user_id')
        if not user_id:
            await callback.answer(t(lang, 'admin_auto_msg_7'))
            return
        
        user = get_user_by_id(user_id)
        if not user:
            await callback.answer(t(lang, 'admin_auto_msg_7'))
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
                    [InlineKeyboardButton(text=t(lang, 'admin_btn_start_test_rocket'), callback_data="start_test")]
                ])
                
                await student_notify_bot.send_message(
                    student_chat_id,
                    t(
                        lang,
                        "admin_student_new_test_notification",
                        subject=subject,
                        login_id=user['login_id'],
                    ),
                    reply_markup=keyboard,
                    parse_mode='HTML'
                )
                await callback.message.answer(
                    t(
                        lang,
                        "admin_test_sent_to_user",
                        subject=subject,
                        first_name=user['first_name'],
                        last_name=user['last_name'],
                    )
                )
            except Exception as e:
                await callback.message.answer(t(lang, "admin_test_send_user_error", error=e))
        else:
            await callback.message.answer(t(lang, 'admin_auto_msg_8'))
        
        state['step'] = None
        state['data'] = {}
        await callback.answer()
        return

    # Change subject for existing user
    if state.get('step') == 'change_subject':
        user_id = state['data'].get('change_user_id')
        if not user_id:
            await callback.answer(t(lang, 'admin_auto_msg_7'))
            return
        
        user = get_user_by_id(user_id)
        if not user:
            await callback.answer(t(lang, 'admin_auto_msg_7'))
            return
        
        update_user_subject(user_id, subject)
        await callback.message.answer(
            t(
                lang,
                "admin_user_subject_updated",
                first_name=user['first_name'],
                last_name=user['last_name'],
                subject=subject,
            )
        )
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
            await callback.message.answer(t(lang, 'admin_auto_msg_9'))
            
            # Generate fallback template
            wb = Workbook()
            ws = wb.active
            ws.title = "Template"
            
            # Headers based on subject
            if subject.lower() == 'english':
                headers = ['Level', 'Word', 'translation_uz', 'translation_ru', 'Definition', 'Example Sentence 1', 'Example Sentence 2']
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
            await callback.message.answer(t(lang, 'admin_auto_msg_10'))
        
        return


@dp.message(Command('export_all'))
async def cmd_export_all_admin(message: Message):
    if message.from_user.id not in ALL_ADMIN_IDS:
        await message.answer(t_from_update(message, 'admin_only'))
        return
    lang = _admin_lang_from_message(message)
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
            await message.answer(
                f"{t(lang, 'ask_last_name')} {teacher['last_name']}\n\n{t(lang, 'ask_last_name')} {t(lang, 'admin_skip_suffix')}"
            )
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
            await message.answer(t(lang, 'admin_auto_msg_11'))
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
    lang = _admin_lang_from_callback(callback)
    state = get_admin_state(callback.message.chat.id)
    search_query = state['data'].get('search_query', '')
    page = state['data'].get('students_page', 0)
    
    admin_id = callback.from_user.id
    students = _students_for_group_picker(admin_id, search_query)
    
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
        title += t(lang, "admin_group_search_suffix", query=search_query)
    
    text = f"{title}\n\n"
    
    for i, student in enumerate(chunk, start=1):
        in_group_indicator = " ✅" if student['in_group'] else ""
        full_name = f"{student.get('first_name', '').strip()} {student.get('last_name', '').strip()}".strip()
        full_name = full_name or "—"
        text += (
            f"{i}. {full_name}{in_group_indicator}\n"
            f"   📚 {student.get('subject') or '—'}\n"
            f"   📱 {student.get('phone', '—') or '—'}\n"
            f"   🔑 {student.get('login_id', '—') or '—'}\n\n"
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
    
    nav_buttons.append(InlineKeyboardButton(text=t(lang, 'admin_btn_search_fullname'), callback_data=f"grp_search_students:{group_id}:name"))
    
    # Pagination buttons
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text=t(lang, 'btn_prev'), callback_data=f"grp_students_page:{group_id}:{page-1}"))
    
    if end < total:
        nav_buttons.append(InlineKeyboardButton(text=t(lang, 'btn_next_arrow'), callback_data=f"grp_students_page:{group_id}:{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Back button
    keyboard.append([InlineKeyboardButton(text=t(lang, 'btn_back'), callback_data=f"group_detail_{group_id}")])
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")


@dp.callback_query(lambda c: c.data.startswith('grp_search_students:'))
async def handle_group_student_search(callback: CallbackQuery):
    """Handle student search in group management"""
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    lang = detect_lang_from_user(callback.from_user)
    
    parts = callback.data.split(':')
    group_id = int(parts[2])
    search_type = parts[3]
    
    state = get_admin_state(callback.message.chat.id)
    prev_step = state.get('step') or ''
    if prev_step == 'remove_student_from_group':
        state['data']['group_student_ui_mode'] = 'remove'
    elif prev_step == 'edit_group_teacher':
        state['data']['group_student_ui_mode'] = 'teacher'
    else:
        state['data']['group_student_ui_mode'] = 'add'
    state['step'] = 'search_group_students'
    state['data']['group_id'] = group_id
    state['data']['search_type'] = search_type
    
    if search_type == 'name':
        await callback.message.answer(t(lang, 'admin_auto_msg_12'))
    
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('grp_students_page:'))
async def handle_group_students_pagination(callback: CallbackQuery):
    """Handle pagination for group student list"""
    if callback.from_user.id not in ALL_ADMIN_IDS:
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
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return

    page = int(callback.data.split('_')[-1])
    state = get_admin_state(callback.message.chat.id)
    state['list_page'] = page
    search = (state.get('data') or {}).get('students_search', '') or ''
    await show_students_list(callback.message, page=page, search_query=search)
    await callback.answer()


@dp.callback_query(lambda c: c.data == "students_search_start")
async def handle_students_search_start(callback: CallbackQuery):
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    state = get_admin_state(callback.message.chat.id)
    lang = _admin_lang_from_callback(callback)
    state['step'] = 'students_search'
    await callback.message.answer(
        t(lang, 'admin_auto_msg_13'),
        reply_markup=cancel_keyboard(lang),
    )
    await callback.answer()


# Qidiruv natijasi
@dp.message(lambda m: get_admin_state(m.chat.id).get('step') == 'students_search')
async def handle_students_search_input(message: Message):
    query = message.text.strip()
    await show_students_list(message, page=0, search_query=query)


@dp.callback_query(lambda c: c.data.startswith('grp_add_student:'))
async def handle_add_student_to_group(callback: CallbackQuery):
    """Handle adding student to group"""
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    
    lang = detect_lang_from_user(callback.from_user)
    try:
        _, group_id, user_id = callback.data.split(":")
        group_id = int(group_id)
        user_id = int(user_id)
        
        # Check if user already in group
        from db import get_group_users
        current_users = get_group_users(group_id)
        if any(u['id'] == user_id for u in current_users):
            await callback.answer(t(lang, 'admin_auto_msg_14'))
            return
        
        # Add user to group
        from db import add_user_to_group
        add_user_to_group(user_id, group_id)
        await _notify_student_group_assigned(user_id, group_id)
        
        # Get user name for display
        user = get_user_by_id(user_id)
        user_name = f"{user['first_name']} {user['last_name']}" if user else t(lang, 'admin_unknown_student_label')

        await callback.answer(t(lang, 'admin_user_added_to_group_confirm', user_name=user_name))
        await _show_group_details(callback, group_id)   # yangi detail sahifasiga qaytadi
        
    except Exception as e:
        logger.error(f"Error adding student to group: {e}")
        await callback.answer(t(lang, 'admin_auto_msg_15'))


@dp.callback_query(lambda c: c.data.startswith("grp_remove_student:"))
async def handle_remove_student_by_inline(callback: CallbackQuery):
    """grp_set remove flow uses grp_remove_student:<group_id>:<user_id> (same as grp_remove:)."""
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    lang = detect_lang_from_user(callback.from_user)
    try:
        _, group_id, user_id = callback.data.split(":")
        group_id = int(group_id)
        user_id = int(user_id)
        remove_user_from_group(user_id, group_id)
        await callback.answer(t(lang, 'admin_auto_msg_16'))
        await _show_group_details(callback, group_id)
    except Exception as e:
        logger.error(f"Error removing student from group: {e}")
        await callback.answer(t(lang, 'admin_auto_msg_15'))


@dp.callback_query(lambda c: c.data == 'noop')
async def handle_noop(callback: CallbackQuery):
    """Handle no-operation callbacks"""
    lang = detect_lang_from_user(callback.from_user)
    await callback.answer(t(lang, 'admin_auto_msg_17'))


@dp.callback_query(lambda c: c.data.startswith("grp_set:"))
async def handle_grp_set(callback: CallbackQuery):
    lang = detect_lang_from_user(callback.from_user)
    try:
        _, group_id_str, action = callback.data.split(":")
        group_id = int(group_id_str)
        state = get_admin_state(callback.message.chat.id)
        state['data']['group_id'] = group_id

        if action == "teacher":
            teachers = get_all_teachers()
            if not teachers:
                await callback.message.edit_text(t(lang, 'admin_auto_msg_58'))
                await callback.answer()
                return
            state['step'] = 'edit_group_teacher'
            state['data']['edit_group_id'] = group_id
            state['data']['group_id'] = group_id
            kb = create_group_teacher_selection_keyboard(teachers, lang)
            await callback.message.edit_text(t(lang, 'admin_auto_msg_59'), reply_markup=kb)

        elif action == "add_student":
            state['step'] = 'add_student_to_group'
            state['data']['students_page'] = 0
            state['data']['search_query'] = ""
            await show_group_student_list(callback, group_id)

        elif action == "remove_student":
            state['step'] = 'remove_student_from_group'
            state['data']['students_page'] = 0
            state['data']['search_query'] = ""
            await show_group_student_list(callback, group_id, remove_mode=True)

        elif action == 'time':
            state = get_admin_state(callback.message.chat.id)
            state['step'] = 'edit_group_time'
            state['data']['edit_group_id'] = group_id
            # Keep existing lesson_date so schedule update doesn't wipe the day
            group = get_group(group_id)
            state['data']['new_lesson_date'] = (group.get('lesson_date') if group else None)
            await callback.message.answer(t(lang, 'admin_auto_msg_18'))

        elif action == 'days':
            state = get_admin_state(callback.message.chat.id)
            state['step'] = 'edit_group_days'
            state['data']['edit_group_id'] = group_id
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=t(lang, 'admin_btn_lesson_days_mwf'), callback_data="edit_group_days:MWF")],
                [InlineKeyboardButton(text=t(lang, 'admin_btn_lesson_days_tts'), callback_data="edit_group_days:TTS")],
                [InlineKeyboardButton(text=t(lang, 'btn_cancel'), callback_data="cancel_edit_group_days")],
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
        [InlineKeyboardButton(text=t(lang, 'btn_yes'), callback_data=f"grp_delete_yes:{group_id}")],
        [InlineKeyboardButton(text=t(lang, 'btn_no'), callback_data=f"grp_delete_no:{group_id}")]
            ])
            await callback.message.edit_text(
                t(
                    lang,
                    "admin_confirm_delete_group_details",
                    group_name=group.get("name"),
                    group_level=group.get("level"),
                    confirm=t(lang, "confirm_delete_group"),
                ),
                reply_markup=confirm_kb,
            )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in handle_grp_set: {e}")
        await callback.answer(t(lang, 'admin_auto_msg_15'))


@dp.callback_query(lambda c: c.data.startswith('grp_delete_yes:'))
async def handle_group_delete_yes(callback: CallbackQuery):
    """Handle group deletion confirmation"""
    if callback.from_user.id not in ALL_ADMIN_IDS:
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
        await callback.message.answer(t(lang, 'admin_auto_msg_19'))
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('grp_delete_no:'))
async def handle_group_delete_no(callback: CallbackQuery):
    """Handle group deletion cancellation"""
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('grp_remove:'))
async def handle_group_remove_student_legacy(callback: CallbackQuery):
    """Handle removing student from group"""
    if callback.from_user.id not in ALL_ADMIN_IDS:
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
        await callback.message.answer(t(lang, 'admin_auto_msg_19'))
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('approve_access_yes:'))
async def handle_approve_access_yes(callback: CallbackQuery):
    """Handle access approval confirmation"""
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    
    try:
        user_id = int(callback.data.split(':')[-1])
        admin_id = callback.from_user.id
        if _is_limited_admin(admin_id):
            u = get_user_by_id(user_id)
            if not _can_manage_user(admin_id, u):
                await callback.answer(t(lang, 'admin_auto_msg_20'), show_alert=True)
                return
        enable_access(user_id)
        lang = detect_lang_from_user(callback.from_user)
        await callback.message.answer(t(lang, "access_approved"))
    except Exception as e:
        logger.error(f"Error approving access: {e}")
        await callback.message.answer(t(lang, 'admin_auto_msg_19'))
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('approve_access_no:'))
async def handle_approve_access_no(callback: CallbackQuery):
    """Handle access rejection"""
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    
    try:
        user_id = int(callback.data.split(':')[-1])
        admin_id = callback.from_user.id
        if _is_limited_admin(admin_id):
            u = get_user_by_id(user_id)
            if not _can_manage_user(admin_id, u):
                await callback.answer(t(lang, 'admin_auto_msg_20'), show_alert=True)
                return
        disable_access(user_id)
        lang = detect_lang_from_user(callback.from_user)
        await callback.message.answer(t(lang, "access_rejected"))
    except Exception as e:
        logger.error(f"Error rejecting access: {e}")
        await callback.message.answer(t(lang, 'admin_auto_msg_19'))
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('user_test_'))
async def handle_user_test(callback: CallbackQuery):
    """Handle sending test to user"""
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    
    user_id = int(callback.data.split('_')[-1])
    state = get_admin_state(callback.message.chat.id)
    state['step'] = 'ask_test_subject'
    state['data']['test_user_id'] = user_id
    lang = _admin_lang_from_callback(callback)
    await callback.message.answer(t(lang, "ask_test_subject"), reply_markup=create_subject_keyboard(lang))
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('user_control_sub_'))
async def handle_user_control_subjects(callback: CallbackQuery):
    """Handle control subjects for a user"""
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    
    user_id = int(callback.data.split('_')[-1])
    user = get_user_by_id(user_id)
    if not user:
        await callback.answer(t(lang, 'admin_auto_msg_21'))
        return
    
    lang = _admin_lang_from_callback(callback)
    await callback.message.answer(
        t(
            lang,
            "admin_user_subjects_management_title",
            first_name=user["first_name"],
            last_name=user["last_name"],
        ),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, 'admin_btn_add_subject_admin'), callback_data=f'user_add_sub_{user_id}')],
            [InlineKeyboardButton(text=t(lang, 'admin_btn_change_subject_admin'), callback_data=f'user_change_sub_{user_id}')],
            [InlineKeyboardButton(text=t(lang, 'admin_btn_delete_subject_admin'), callback_data=f'user_delete_sub_{user_id}')],
            [InlineKeyboardButton(text=t(lang, 'btn_back'), callback_data='back_to_menu')],
        ])
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('user_change_sub_'))
async def handle_user_change_subject(callback: CallbackQuery):
    """Handle changing user subject"""
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    
    user_id = int(callback.data.split('_')[-1])
    state = get_admin_state(callback.message.chat.id)
    state['step'] = 'change_subject'
    state['data']['change_user_id'] = user_id
    lang = _admin_lang_from_callback(callback)
    await callback.message.answer(t(lang, "ask_new_subject"), reply_markup=create_subject_keyboard(lang))
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('user_add_sub_'))
async def handle_user_add_subject(callback: CallbackQuery):
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    user_id = int(callback.data.split('_')[-1])
    state = get_admin_state(callback.message.chat.id)
    state['step'] = 'add_subject'
    state['data']['change_user_id'] = user_id
    
    lang = _admin_lang_from_callback(callback)
    # Show subject selection buttons instead of text input
    await callback.message.answer(t(lang, 'admin_auto_msg_22'), reply_markup=create_subject_keyboard(lang))
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('user_delete_sub_'))
async def handle_user_delete_subject(callback: CallbackQuery):
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    user_id = int(callback.data.split('_')[-1])
    state = get_admin_state(callback.message.chat.id)
    state['step'] = 'delete_subject'
    state['data']['change_user_id'] = user_id
    lang = _admin_lang_from_callback(callback)
    
    # Show user's current subjects as buttons for deletion
    user = get_user_by_id(user_id)
    if user and user.get('subject'):
        subjects = [s.strip() for s in (user.get('subject') or '').split(',') if s.strip()]
        if subjects:
            # Create buttons for each subject
            buttons = []
            for subject in subjects:
                buttons.append([InlineKeyboardButton(
                    text=t(lang, "admin_delete_subject_option_label", subject=subject),
                    callback_data=f'delete_subject_confirm_{user_id}_{subject}'
                )])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            await callback.message.answer(
                t(
                    lang,
                    "admin_delete_subject_prompt",
                    first_name=user.get("first_name", ""),
                    last_name=user.get("last_name", ""),
                ),
                reply_markup=keyboard,
            )
        else:
            await callback.message.answer(t(lang, 'admin_auto_msg_23'))
    else:
        await callback.message.answer(t(lang, 'admin_auto_msg_6'))
    await callback.answer()


# Handle subject deletion confirmation
@dp.callback_query(lambda c: c.data.startswith('delete_subject_confirm_'))
async def handle_delete_subject_confirm(callback: CallbackQuery):
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    
    lang = _admin_lang_from_callback(callback)
    # callback_data: delete_subject_confirm_{user_id}_{subject}
    # subject may contain underscores; split only after user id.
    prefix = "delete_subject_confirm_"
    data = callback.data or ""
    if not data.startswith(prefix):
        await callback.answer(t(lang, "admin_auto_msg_24"))
        return
    rest = data[len(prefix) :]
    if "_" not in rest:
        await callback.answer(t(lang, "admin_auto_msg_24"))
        return
    user_id_str, subject = rest.split("_", 1)
    try:
        user_id = int(user_id_str)
    except ValueError:
        await callback.answer(t(lang, "admin_auto_msg_24"))
        return
    
    user = get_user_by_id(user_id)
    if user and user.get('subject'):
        subjects = [s.strip() for s in (user.get('subject') or '').split(',') if s.strip()]
        if subject in subjects:
            subjects.remove(subject)
            update_user_subjects(user_id, subjects)
            cleanup_student_subject_side_effects(user_id, subject)
            remaining_subjects = ', '.join(subjects) if subjects else t(lang, "none_short")
            await callback.message.answer(
                t(
                    lang,
                    "admin_subject_removed_confirm",
                    subject=subject,
                    remaining_subjects=remaining_subjects,
                )
            )
        else:
            await callback.message.answer(t(lang, "admin_subject_not_found", subject=subject))
    else:
        await callback.message.answer(t(lang, 'admin_auto_msg_6'))
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('user_block_'))
async def handle_user_block(callback: CallbackQuery):
    """Handle blocking a user"""
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    
    user_id = int(callback.data.split('_')[-1])
    from db import block_user
    block_user(user_id)
    
    lang = detect_lang_from_user(callback.from_user)
    await callback.message.answer(t(lang, 'admin_auto_msg_25'), parse_mode='HTML')
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('user_unblock_'))
async def handle_user_unblock(callback: CallbackQuery):
    """Handle unblocking a user"""
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    
    user_id = int(callback.data.split('_')[-1])
    from db import unblock_user
    unblock_user(user_id)
    
    lang = detect_lang_from_user(callback.from_user)
    await callback.message.answer(t(lang, 'admin_auto_msg_26'), parse_mode='HTML')
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('user_reset_'))
async def handle_user_reset_password(callback: CallbackQuery):
    """Handle user password reset"""
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    
    user_id = int(callback.data.split('_')[-1])
    from db import reset_user_password
    import random
    import string

    lang = detect_lang_from_user(callback.from_user)
    user_row = get_user_by_id(user_id)
    if not user_row:
        await callback.answer(t(lang, "admin_auto_msg_6"), show_alert=True)
        return

    new_password = "".join(random.choices(string.digits, k=6))
    reset_user_password(user_id, new_password)

    lid = html_module.escape(str(user_row.get("login_id") or ""))
    fn = html_module.escape(str(user_row.get("first_name") or ""))
    ln = html_module.escape(str(user_row.get("last_name") or ""))
    pw = html_module.escape(new_password)
    await callback.message.answer(
        t(
            lang,
            "admin_student_password_reset_detailed",
            first_name=fn,
            last_name=ln,
            login_id=lid,
            password=pw,
        ),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('back_to_menu'))
async def handle_back_to_menu(callback: CallbackQuery):
    """Handle back to main menu"""
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    
    lang = _admin_lang_from_callback(callback)
    await callback.message.answer(t(lang, 'main_menu_prompt'), reply_markup=admin_main_keyboard(lang))
    await callback.answer()


@dp.callback_query(lambda c: c.data in ('users_next', 'users_prev'))
async def handle_user_pagination(callback: CallbackQuery):
    """Handle user list pagination"""
    if callback.from_user.id not in ALL_ADMIN_IDS:
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
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    
    idx = int(callback.data.split('_')[-1])
    state = get_admin_state(callback.message.chat.id)
    users = state.get('list_users', [])
    
    if idx < 0 or idx >= len(users):
        lang = _admin_lang_from_callback(callback)
        await callback.answer(t(lang, 'err_invalid_choice'))
        return
    
    selected_user = users[idx]
    state['selected_user'] = selected_user

    lang = _admin_lang_from_callback(callback)
    if not _can_manage_user(callback.from_user.id, selected_user):
        await callback.answer(t(lang, "admin_share_forbidden"), show_alert=True)
        return
    await send_admin_student_control_message(
        callback.bot,
        callback.message.chat.id,
        selected_user,
        lang,
        viewer_admin_id=callback.from_user.id,
    )
    await callback.answer()


@dp.callback_query(lambda c: bool(c.data) and (c.data.startswith("ashr:") or c.data.startswith("aush:")))
async def handle_admin_student_share_callbacks(callback: CallbackQuery):
    """Share / unshare student between limited admins (ashr:/aush: callbacks)."""
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    lang = _admin_lang_from_callback(callback)
    parts = (callback.data or "").split(":")
    if len(parts) != 3:
        await callback.answer(t(lang, "admin_share_invalid"), show_alert=True)
        return
    kind, sid_s, peer_s = parts[0], parts[1], parts[2]
    try:
        sid = int(sid_s)
        peer = int(peer_s)
    except ValueError:
        await callback.answer(t(lang, "admin_share_invalid"), show_alert=True)
        return
    user = get_user_by_id(sid)
    if not user or not _can_manage_user(callback.from_user.id, user):
        await callback.answer(t(lang, "admin_share_forbidden"), show_alert=True)
        return
    if kind == "ashr":
        ok, err = share_student_between_admins(sid, peer, callback.from_user.id)
    elif kind == "aush":
        ok, err = unshare_student_between_admins(sid, peer, callback.from_user.id)
    else:
        await callback.answer()
        return
    if ok:
        await callback.message.answer(t(lang, "admin_share_success"))
    else:
        key = f"admin_share_err_{err}" if err else "admin_share_err_unknown"
        try:
            msg = t(lang, key)
        except Exception:
            msg = t(lang, "admin_share_err_unknown")
        await callback.message.answer(msg)
    await callback.answer()


@dp.callback_query(lambda c: c.data in ('pay_search:login', 'pay_search:name'))
async def handle_payment_search(callback: CallbackQuery):
    """Handle payment search initialization"""
    if callback.from_user.id not in ALL_ADMIN_IDS:
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
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    
    from payment import export_payment_history_to_xlsx, cleanup_old_payment_history
    lang = detect_lang_from_user(callback.from_user)
    admin_id = callback.from_user.id
    owner_filter = admin_id if _is_limited_admin(admin_id) else None
    
    try:
        cleanup_old_payment_history()
        bio, fname = export_payment_history_to_xlsx(owner_admin_id=owner_filter)
        await callback.bot.send_document(callback.message.chat.id, BufferedInputFile(bio.getvalue(), filename=fname))
        await callback.answer(t(lang, 'export_success'))
    except Exception as e:
        logger.exception("Failed to export payment history")
        await callback.answer(t(lang, 'export_error'))


@dp.callback_query(lambda c: c.data.startswith('admin_attendance_group:'))
async def handle_admin_attendance_group(callback: CallbackQuery):
    """Handle attendance group selection"""
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    
    lang = _admin_lang_from_callback(callback)
    group_id = int(callback.data.split(":")[1])
    group = get_group(group_id)
    if not group:
        await callback.answer()
        return

    admin_id = callback.from_user.id
    if not _can_manage_group(admin_id, group):
        await callback.answer(t(lang, 'admin_auto_msg_20'), show_alert=True)
        return
    
    from attendance_manager import get_group_sessions
    sessions = get_group_sessions(group_id)
    if not sessions:
        today = datetime.now(pytz.timezone("Asia/Tashkent")).strftime("%Y-%m-%d")
        await callback.message.answer(
            t(lang, "admin_attendance_no_sessions_header"),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=t(lang, "admin_attendance_today_btn", today=today), callback_data=f"admin_take_attendance:{group_id}:{today}")],
                [InlineKeyboardButton(text=t(lang, 'btn_back'), callback_data="admin_attendance_back")],
            ]),
        )
        await callback.answer()
        return
    
    # Show recent sessions
    keyboard = []
    for session in sessions[:5]:  # Show last 5 sessions
        date = session['date']
        keyboard.append([InlineKeyboardButton(text=t(lang, "admin_attendance_date_btn", date=date), callback_data=f"admin_take_attendance:{group_id}:{date}")])
    
    keyboard.append([InlineKeyboardButton(text=t(lang, 'admin_btn_export_attendance_excel'), callback_data=f"admin_export_group_attendance:{group_id}")])
    keyboard.append([InlineKeyboardButton(text=t(lang, 'btn_back'), callback_data="admin_attendance_back")])
    
    await callback.message.answer(
        t(lang, "admin_attendance_panel_title", group_name=group['name']),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode='HTML'
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('admin_take_attendance:'))
async def handle_admin_take_attendance(callback: CallbackQuery):
    """Handle taking attendance for a group"""
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    lang = _admin_lang_from_callback(callback)
    
    parts = callback.data.split(":")
    group_id = int(parts[1])
    date = parts[2]
    if is_lesson_holiday(date):
        await callback.answer(t(lang, "lesson_canceled_for_date_alert", date=date), show_alert=True)
        return

    group = get_group(group_id)
    if not group:
        await callback.answer()
        return
    admin_id = callback.from_user.id
    if not _can_manage_group(admin_id, group):
        await callback.answer(t(lang, 'admin_auto_msg_20'), show_alert=True)
        return
    
    from attendance_manager import ensure_session, send_attendance_panel
    session = ensure_session(group_id, date)
    if not session:
        await callback.answer(t(lang, 'admin_auto_msg_27'))
        return
    
    await send_attendance_panel(callback.bot, callback.message.chat.id, session["id"], group_id, date, 0)
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('admin_export_group_attendance:'))
async def handle_admin_export_group_attendance(callback: CallbackQuery):
    """Handle exporting group attendance"""
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    lang = _admin_lang_from_callback(callback)
    
    group_id = int(callback.data.split(":")[1])
    group = get_group(group_id)
    admin_id = callback.from_user.id
    if group and not _can_manage_group(admin_id, group):
        await callback.answer(t(lang, 'admin_auto_msg_20'), show_alert=True)
        return
    from vocabulary import export_group_attendance_to_xlsx
    
    try:
        bio, fname = export_group_attendance_to_xlsx(group_id)
        await callback.bot.send_document(callback.message.chat.id, BufferedInputFile(bio.getvalue(), filename=fname))
        await callback.answer()
    except Exception as e:
        logger.exception("Failed to export group attendance")
        await callback.answer(t(lang, 'admin_auto_msg_19'))


@dp.callback_query(lambda c: c.data == "admin_attendance_back")
async def handle_admin_attendance_back(callback: CallbackQuery):
    """Handle back to attendance menu"""
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    
    await show_attendance_menu(callback.message)
    await callback.answer()


@dp.callback_query(lambda c: c.data == "admin_back_to_main")
async def handle_admin_back_to_main(callback: CallbackQuery):
    """Handle back to main menu"""
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    
    lang = detect_lang_from_user(callback.from_user)
    await callback.message.answer(t(lang, 'main_menu_prompt'), reply_markup=admin_main_keyboard(lang))
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('assign_new:'))
async def handle_assign_new_user(callback: CallbackQuery):
    """Handle assigning new user to group"""
    if callback.from_user.id not in ALL_ADMIN_IDS:
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
    
    await _render_assign_select_groups_page(callback, user_id=user_id, page=page, use_edit=False)
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('assign_select:') and ':pick:' in c.data)
async def handle_assign_select_group(callback: CallbackQuery):
    """Handle group selection for user assignment (assign_select:<user_id>:pick:<group_id>)"""
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    
    parts = callback.data.split(':')
    # assign_select, user_id, pick, group_id
    if len(parts) < 4 or parts[2] != 'pick':
        await callback.answer()
        return
    
    user_id = int(parts[1])
    group_id = int(parts[3])
    
    from db import add_user_to_group
    add_user_to_group(user_id, group_id)
    await _notify_student_group_assigned(user_id, group_id)
    
    db_user = get_user_by_telegram(str(callback.from_user.id))
    lang = detect_lang_from_user(db_user or callback.from_user)
    user = get_user_by_id(user_id)
    group = get_group(group_id)
    
    await callback.message.answer(
        t(
            lang,
            "admin_group_add_student_confirm",
            first_name=user["first_name"],
            last_name=user["last_name"],
            group_name=group["name"],
        )
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('group_days:'))
async def handle_group_days(callback: CallbackQuery):
    """Handle group days selection"""
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    
    days = callback.data.split(':')[1]
    state = get_admin_state(callback.message.chat.id)
    state['data']['group_days'] = _to_lesson_days_key(days)
    state['data']['lesson_date'] = _to_lesson_days_key(days)
    state['step'] = 'ask_group_time'  # Set next step to time input
    lang = detect_lang_from_user(callback.from_user)
    label = t(lang, 'admin_btn_lesson_days_mwf') if _to_lesson_days_key(days) == 'MWF' else t(lang, 'admin_btn_lesson_days_tts')
    await callback.message.answer(t(lang, 'admin_group_days_saved_and_prompt_time', days_label=label))
    await callback.answer()


@dp.callback_query(lambda c: c.data == 'cancel_group_creation')
async def handle_cancel_group_creation(callback: CallbackQuery):
    """Handle group creation cancellation"""
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    
    reset_admin_state(callback.message.chat.id)
    lang = detect_lang_from_user(callback.from_user)
    # edit_text only supports InlineKeyboardMarkup; reply keyboards must be sent via answer().
    try:
        await callback.message.edit_text(t(lang, 'operation_cancelled'))
    except Exception:
        pass
    await callback.message.answer(t(lang, 'admin_panel'), reply_markup=admin_main_keyboard(lang))
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('edit_group_days:'))
async def handle_edit_group_days(callback: CallbackQuery):
    """Handle edit group days selection"""
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    
    days = callback.data.split(':')[1]
    state = get_admin_state(callback.message.chat.id)
    group_id = state['data'].get('edit_group_id')
    if group_id:
        group = get_group(group_id)
        if not group:
            await callback.answer(t(lang, 'admin_auto_msg_28'))
            return
        teacher_id = group.get('teacher_id')
        if teacher_id and _teacher_conflicts(teacher_id, days, group.get('lesson_start') or '', group.get('lesson_end') or '', exclude_group_id=group_id):
            await callback.message.answer(t(lang, 'admin_auto_msg_29'))
            await callback.answer()
            return

        from db import update_group_days
        update_group_days(group_id, _to_lesson_days_key(days))

        lang = detect_lang_from_user(callback.from_user)
        label = t(lang, 'admin_btn_lesson_days_mwf') if _to_lesson_days_key(days) == 'MWF' else t(lang, 'admin_btn_lesson_days_tts')
        await callback.message.answer(t(lang, 'admin_group_days_updated', days_label=label))
    await callback.answer()


def _attendance_session_owned_by_admin(session: dict | None, admin_id: int) -> bool:
    """Limited admin can only act on sessions for their groups."""
    if not session:
        return False
    group = get_group(session.get("group_id"))
    return _can_manage_group(admin_id, group)


@dp.callback_query(lambda c: c.data.startswith('att_mark_'))
async def handle_attendance_mark(callback: CallbackQuery):
    """Handle attendance marking"""
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    lang = _admin_lang_from_callback(callback)
    
    parts = callback.data.split('_')
    session_id = int(parts[2])
    user_id = int(parts[3])
    status = parts[4]
    
    session = get_session(session_id)
    if not _attendance_session_owned_by_admin(session, callback.from_user.id):
        await callback.answer(t(lang, 'admin_auto_msg_20'), show_alert=True)
        return
    
    from attendance_manager import mark_attendance
    mark_attendance(session_id, user_id, status)
    
    page = int(parts[5]) if len(parts) > 5 else 0
    session = get_session(session_id)
    if session:
        admin_kb = build_attendance_keyboard(
            session_id,
            session["group_id"],
            session["date"],
            page,
            lang=get_panel_ui_lang(session_id, "admin", lang),
        )
        teacher_kb = build_attendance_keyboard(
            session_id,
            session["group_id"],
            session["date"],
            page,
            lang=get_panel_ui_lang(session_id, "teacher", "uz"),
        )
        # Telegram sometimes throws "message is not modified" when the markup is unchanged.
        try:
            await callback.message.edit_reply_markup(reply_markup=admin_kb)
        except Exception as e:
            if "message is not modified" not in str(e).lower():
                raise
        # Realtime sync: update teacher's panel too (if available).
        try:
            from attendance_manager import _get_panel_message
            teacher_panel = _get_panel_message(session_id, "teacher")
            if teacher_panel:
                teacher_chat_id, teacher_message_id = teacher_panel
                import teacher_bot
                if getattr(teacher_bot, "bot", None):
                    await teacher_bot.bot.edit_message_reply_markup(
                        chat_id=teacher_chat_id,
                        message_id=teacher_message_id,
                        reply_markup=teacher_kb,
                    )
        except Exception:
            logger.exception("Failed to sync teacher attendance panel")
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('att_page_'))
async def handle_attendance_page_nav(callback: CallbackQuery):
    """Pagination on attendance inline keyboard (att_page_<session_id>_<page>)."""
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    try:
        parts = callback.data.split('_')
        session_id = int(parts[2])
        page = int(parts[3])
    except (IndexError, ValueError):
        await callback.answer()
        return
    session = get_session(session_id)
    if not session or not _attendance_session_owned_by_admin(session, callback.from_user.id):
        await callback.answer()
        return
    alang = _admin_lang_from_callback(callback)
    admin_kb = build_attendance_keyboard(
        session_id,
        session["group_id"],
        session["date"],
        page,
        lang=get_panel_ui_lang(session_id, "admin", alang),
    )
    teacher_kb = build_attendance_keyboard(
        session_id,
        session["group_id"],
        session["date"],
        page,
        lang=get_panel_ui_lang(session_id, "teacher", "uz"),
    )
    try:
        await callback.message.edit_reply_markup(reply_markup=admin_kb)
    except Exception as e:
        if "message is not modified" not in str(e).lower():
            raise
    # Realtime sync: update teacher's panel too (if available).
    try:
        from attendance_manager import _get_panel_message
        teacher_panel = _get_panel_message(session_id, "teacher")
        if teacher_panel:
            teacher_chat_id, teacher_message_id = teacher_panel
            import teacher_bot
            if getattr(teacher_bot, "bot", None):
                await teacher_bot.bot.edit_message_reply_markup(
                    chat_id=teacher_chat_id,
                    message_id=teacher_message_id,
                    reply_markup=teacher_kb,
                )
    except Exception:
        logger.exception("Failed to sync teacher attendance panel on page nav")
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('att_finish_'))
async def handle_attendance_finish(callback: CallbackQuery):
    """Handle attendance session finish"""
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    lang = _admin_lang_from_callback(callback)
    
    session_id = int(callback.data.split('_')[2])
    session = get_session(session_id)
    if not _attendance_session_owned_by_admin(session, callback.from_user.id):
        await callback.answer(t(lang, 'admin_auto_msg_20'), show_alert=True)
        return
    from attendance_manager import set_session_closed, finalize_attendance_session
    set_session_closed(session_id)
    await callback.answer(t(lang, 'admin_auto_msg_30'))
    try:
        await finalize_attendance_session(
            callback.bot,
            session_id,
            admin_chat_ids=ALL_ADMIN_IDS,
            student_notify_bot=student_notify_bot,
        )
    except Exception:
        logger.exception("Failed to finalize attendance session from admin finish callback")


@dp.callback_query(lambda c: c.data.startswith('att_reopen_'))
async def handle_attendance_reopen(callback: CallbackQuery):
    """Handle attendance session reopen"""
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    lang = _admin_lang_from_callback(callback)
    
    session_id = int(callback.data.split('_')[2])
    session = get_session(session_id)
    if not _attendance_session_owned_by_admin(session, callback.from_user.id):
        await callback.answer(t(lang, 'admin_auto_msg_20'), show_alert=True)
        return
    from attendance_manager import set_session_opened
    set_session_opened(session_id, str(callback.from_user.id))
    
    session = get_session(session_id)
    if session:
        admin_kb = build_attendance_keyboard(
            session_id,
            session["group_id"],
            session["date"],
            0,
            lang=get_panel_ui_lang(session_id, "admin", lang),
        )
        await callback.message.edit_reply_markup(reply_markup=admin_kb)
    await callback.answer(t(lang, 'admin_auto_msg_31'))


@dp.callback_query(lambda c: bool(c.data) and ':pick:' in c.data and not c.data.startswith(('group_list:', 'rec_groups:', 'assign_new:')))
async def handle_generic_pick(callback: CallbackQuery):
    """Handle generic pick callbacks for pagination (<base>:pick:<id>)"""
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return

    parts = callback.data.split(':')
    if len(parts) < 3:
        await callback.answer()
        return

    try:
        pick_idx = parts.index('pick')
        base = ':'.join(parts[:pick_idx])
        item_id = int(parts[pick_idx + 1])
    except (ValueError, IndexError):
        await callback.answer()
        return

    if base.startswith('pay_list:'):
        await _show_student_payment_card(callback, item_id, use_edit=False)
        await callback.answer()
        return

    # Handle different base types
    if base.startswith('assign_select:'):
        user_id = int(base.split(':')[1])
        group_id = item_id
        
        from db import add_user_to_group
        add_user_to_group(user_id, group_id)
        await _notify_student_group_assigned(user_id, group_id)
        
        lang = detect_lang_from_user(callback.from_user)
        user = get_user_by_id(user_id)
        group = get_group(group_id)
        
        await callback.message.answer(
            t(
                lang,
                "admin_group_add_student_confirm",
                first_name=user["first_name"],
                last_name=user["last_name"],
                group_name=group["name"],
            )
        )
    
    await callback.answer()


@dp.callback_query(lambda c: bool(c.data) and ':page:' in c.data and not c.data.startswith(('group_list:', 'rec_groups:', 'assign_new:', 'pay_list:')))
async def handle_generic_page(callback: CallbackQuery):
    """Handle generic page callbacks (<base>:page:<n>)"""
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    
    parts = callback.data.split(':')
    if len(parts) < 3:
        await callback.answer()
        return
    
    try:
        page_idx = parts.index('page')
        base = ':'.join(parts[:page_idx])
        page = int(parts[page_idx + 1])
    except (ValueError, IndexError):
        await callback.answer()
        return
    
    # Handle pagination for different base types
    if base.startswith('assign_select:'):
        user_id = int(base.split(':')[1])
        await _render_assign_select_groups_page(callback, user_id=user_id, page=page, use_edit=True)
    
    await callback.answer()


@dp.callback_query(
    lambda c: bool(c.data)
    and c.data.startswith('user_delete_profile_')
    and not c.data.startswith('user_delete_profile_confirm_yes_')
    and not c.data.startswith('user_delete_profile_confirm_no_')
)
async def handle_user_delete_profile_prompt(callback: CallbackQuery):
    if (callback.data or "").startswith("user_delete_profile_confirm_"):
        await callback.answer()
        return
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    lang = _admin_lang_from_callback(callback)
    user_id = int(callback.data.split('_')[-1])
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_yes"), callback_data=f"user_delete_profile_confirm_yes_{user_id}")],
            [InlineKeyboardButton(text=t(lang, "btn_no"), callback_data=f"user_delete_profile_confirm_no_{user_id}")],
        ]
    )
    await callback.message.answer(t(lang, "admin_confirm_delete_student_profile"), reply_markup=kb)
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('user_delete_profile_confirm_yes_'))
async def handle_user_delete_profile_yes(callback: CallbackQuery):
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    lang = _admin_lang_from_callback(callback)
    user_id = int(callback.data.split('_')[-1])
    from db import hard_delete_user_profile
    ok = hard_delete_user_profile(user_id)
    await callback.message.answer(t(lang, "admin_student_profile_deleted") if ok else t(lang, "operation_failed"))
    # If admin currently views the students list, re-render it so the deleted profile disappears.
    if ok:
        try:
            state = get_admin_state(callback.message.chat.id)
            if state.get("step") == "students_list_view":
                page = int(state.get("data", {}).get("students_page") or 0)
                search_query = str(state.get("data", {}).get("students_search") or "")
                await show_students_list(callback.message, page=page, search_query=search_query)
        except Exception:
            pass
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('user_delete_profile_confirm_no_'))
async def handle_user_delete_profile_no(callback: CallbackQuery):
    lang = _admin_lang_from_callback(callback)
    await callback.message.answer(t(lang, "operation_cancelled"))
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('user_detail_') or c.data.startswith('student_detail_'))
async def handle_user_detail(callback: CallbackQuery):
    """Handle user detail view (user_detail_* and student list student_detail_*)"""
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return

    lang = _admin_lang_from_callback(callback)
    try:
        user_id = int(callback.data.split('_')[-1])
        user = get_user_by_id(user_id)
        if not user:
            await callback.answer(t(lang, 'admin_auto_msg_21'))
            return

        if not _can_manage_user(callback.from_user.id, user):
            await callback.answer(t(lang, 'admin_share_forbidden'), show_alert=True)
            return

        if user.get('blocked'):
            status = t(lang, "admin_status_blocked_label")
        elif is_access_active(user):
            status = t(lang, "admin_status_open_label")
        else:
            status = t(lang, "admin_status_closed_label")

        kb_rows = [
            [InlineKeyboardButton(text=t(lang, 'btn_send_test'), callback_data=f'user_test_{user["id"]}')],
            [InlineKeyboardButton(text=t(lang, 'admin_btn_subject_settings'), callback_data=f'user_control_sub_{user["id"]}')],
            [InlineKeyboardButton(text=t(lang, 'admin_btn_edit_first_change'), callback_data=f'user_edit_first_{user["id"]}'), 
             InlineKeyboardButton(text=t(lang, 'admin_btn_edit_last_change'), callback_data=f'user_edit_last_{user["id"]}')],
            [InlineKeyboardButton(text=t(lang, 'admin_btn_phone_change'), callback_data=f'user_edit_phone_{user["id"]}')],
            [InlineKeyboardButton(text=t(lang, 'admin_btn_password_reset_change'), callback_data=f'user_reset_{user["id"]}')],
            [InlineKeyboardButton(text=t(lang, 'admin_btn_delete_student_profile'), callback_data=f'user_delete_profile_{user["id"]}')],
        ]
        if user.get('blocked'):
            kb_rows.append([InlineKeyboardButton(text=t(lang, 'admin_btn_unblock_admin'), callback_data=f'user_unblock_{user["id"]}')])
        else:
            kb_rows.append([InlineKeyboardButton(text=t(lang, 'btn_block'), callback_data=f'user_block_{user["id"]}')])
        kb_rows.extend(build_student_share_keyboard_rows(lang, user, callback.from_user.id))
        kb_rows.append([InlineKeyboardButton(text=t(lang, 'btn_home_menu'), callback_data='back_to_menu')])

        subjs = get_student_subjects(user_id) or []
        levels_detail = _subject_levels_summary(user_id, subjs)
        await callback.message.answer(
            t(
                lang,
                "admin_user_card_full",
                first_name=user["first_name"],
                last_name=user["last_name"],
                login_id=user["login_id"],
                subject=user.get("subject") or "-",
                level=format_stored_user_level_display(lang, user.get("level"), subject=user.get("subject")),
                levels_detail=levels_detail,
                phone=user.get("phone", "—"),
                status=status,
            ),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows),
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in user_detail handler: {e}")
        await callback.answer(t(lang, 'admin_auto_msg_15'))


@dp.callback_query(lambda c: c.data.startswith('teacher_select_'))
async def handle_teacher_selection(callback: CallbackQuery):
    """Handle teacher selection"""
    if callback.from_user.id not in ALL_ADMIN_IDS:
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
            await callback.message.answer(t(lang, 'admin_auto_msg_32'))
        await callback.answer()
        return
    
    if state.get('step') == 'ask_teacher_for_group':
        group_id = state['data'].get('group_id')
        if group_id:
            from db import update_group_teacher
            update_group_teacher(group_id, teacher_id)
            await callback.message.answer(t(lang, 'admin_auto_msg_32'))
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
        status = t(lang, "admin_status_blocked_label")
    elif is_access_active(teacher):
        status = t(lang, "admin_status_open_label")
    else:
        status = t(lang, "admin_status_closed_label")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, 'admin_btn_edit_first'), callback_data=f'teach_edit_first_{teacher_id}')],
        [InlineKeyboardButton(text=t(lang, 'admin_btn_edit_last'), callback_data=f'teach_edit_last_{teacher_id}')],
        [InlineKeyboardButton(text=t(lang, 'admin_btn_teacher_edit_phone'), callback_data=f'teach_edit_phone_{teacher_id}')],
        [InlineKeyboardButton(text=t(lang, 'admin_btn_teacher_edit_subject'), callback_data=f'teach_edit_subject_{teacher_id}')],
        [InlineKeyboardButton(text=t(lang, 'admin_btn_teacher_password_reset'), callback_data=f'teacher_reset_{teacher_id}')]
    ])

    await callback.message.answer(
        t(
            lang,
            "admin_teacher_card_basic",
            first_name=teacher["first_name"],
            last_name=teacher["last_name"],
            subject=teacher.get("subject") or "-",
            phone=teacher.get("phone") or "-",
            login_id=teacher["login_id"],
            status=status,
        ),
        reply_markup=kb,
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('teacher_reset_'))
async def handle_teacher_password_reset(callback: CallbackQuery):
    """Handle teacher password reset"""
    if callback.from_user.id not in ALL_ADMIN_IDS:
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
        t(
            lang,
            "admin_teacher_password_reset_detailed",
            first_name=teacher['first_name'],
            last_name=teacher['last_name'],
            password=new_password,
        ),
        parse_mode='HTML',
    )
    await callback.answer()


# Old teach_edit_ handler replaced by new short prefix handlers (t_edit_*)


@dp.callback_query(lambda c: c.data.startswith('user_edit_first_'))
async def handle_user_edit_first(callback: CallbackQuery):
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    lang = detect_lang_from_user(callback.from_user)
    parts = callback.data.split('_')
    user_id = int(parts[-1])
    state = get_admin_state(callback.message.chat.id)
    state['step'] = 'user_edit_first'
    state['data']['change_user_id'] = user_id
    await callback.message.answer(t(lang, 'admin_auto_msg_33'))
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('user_edit_last_'))
async def handle_user_edit_last(callback: CallbackQuery):
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    lang = detect_lang_from_user(callback.from_user)
    parts = callback.data.split('_')
    user_id = int(parts[-1])
    state = get_admin_state(callback.message.chat.id)
    state['step'] = 'user_edit_last'
    state['data']['change_user_id'] = user_id
    await callback.message.answer(t(lang, 'admin_auto_msg_34'))
    await callback.answer()


@dp.callback_query(lambda c: c.data == 'group_create')
async def group_create_start(callback: CallbackQuery):
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    lang = detect_lang_from_user(callback.from_user)
    state = get_admin_state(callback.message.chat.id)
    state['step'] = 'ask_group_name'
    await callback.message.answer(t(lang, 'admin_auto_msg_35'))
    await callback.answer()


@dp.callback_query(lambda c: c.data == 'group_list')
async def group_list_show(callback: CallbackQuery):
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    
    # Use the new _show_group_list function with correct callback pattern
    await _show_group_list(callback, page=0)


@dp.callback_query(lambda c: c.data.startswith('assign_test_user_'))
async def handle_assign_test_user_to_group(callback: CallbackQuery):
    """Handle assigning test user to group from admin notification"""
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    
    parts = callback.data.split('_')
    user_id = int(parts[3])
    group_id = int(parts[4])
    
    user = get_user_by_id(user_id)
    group = get_group(group_id)
    
    if not user or not group:
        await callback.answer(t(lang, 'admin_auto_msg_36'))
        return
    
    # Add user to group
    add_user_to_group(user_id, group_id)
    await _notify_student_group_assigned(user_id, group_id)
    
    # Update user access if needed
    if not is_access_active(user):
        enable_access(user_id)

    lang = detect_lang_from_user(callback.from_user)
    
    await callback.message.answer(
        t(
            lang,
            "admin_notify_user_added_to_group",
            first_name=user["first_name"],
            last_name=user["last_name"],
            group_name=group["name"],
            group_level=group.get("level", "—"),
            teacher_name=group.get("teacher_name", "—"),
        )
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('group_create_for_user_'))
async def handle_group_create_for_user(callback: CallbackQuery):
    """Handle creating group for specific user from admin notification"""
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    
    parts = callback.data.split('_')
    user_id = int(parts[4])
    subject = parts[5]
    level = parts[6]
    
    user = get_user_by_id(user_id)
    if not user:
        await callback.answer(t(lang, 'admin_auto_msg_37'))
        return
    
    state = get_admin_state(callback.message.chat.id)
    state['step'] = 'ask_group_name'
    state['data'] = {
        'target_user_id': user_id,
        'subject': subject,
        'level': level
    }
    
    lang = detect_lang_from_user(callback.from_user)
    
    await callback.message.answer(
        t(
            lang,
            "admin_create_group_for_user_prompt",
            first_name=user["first_name"],
            last_name=user["last_name"],
            subject=subject,
            level=level,
        )
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('user_type_'))
async def handle_user_type_selection(callback: CallbackQuery):
    """Handle user type selection for new user creation"""
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    
    user_type = int(callback.data.split('_')[-1])
    state = get_admin_state(callback.message.chat.id)
    state['step'] = 'ask_first_name'
    state['data']['login_type'] = user_type
    
    db_user = get_user_by_telegram(str(callback.from_user.id))
    lang = detect_lang_from_user(db_user or callback.from_user)
    await callback.answer()
    await callback.message.answer(t(lang, 'ask_first_name'), reply_markup=cancel_keyboard(lang))


# Do NOT include prefixes handled by dedicated @dp.callback_query handlers registered *after* this
# block (e.g. teacher_detail_, group_teacher_select_, teachers_next) — otherwise the catch-all runs
# first and either swallows the update or returns without callback.answer().
@dp.callback_query(lambda c: c.data.startswith(('set_lang_me_', 'att_noop', 'noop', 'pay_search:', 'pay_list:', 'pay_card:', 'pay_set:', 'subject_', 'user_test_', 'user_control_sub_', 'user_change_sub_', 'user_add_sub_', 'user_delete_sub_', 'delete_subject_confirm_', 'user_block_', 'user_unblock_', 'user_reset_', 'user_select_', 'admin_export_group_attendance:', 'group_list', 'grp_search_students:', 'grp_students_page:', 'grp_add_student:', 'grp_remove_student:', 'grp_set:', 'grp_delete_yes:', 'grp_delete_no:', 'approve_access_yes:', 'approve_access_no:', 'teacher_reset_', 'teacher_block_', 'teacher_unblock_', 'teacher_change_sub_', 'teacher_change_lang_', 'user_change_lang_', 'set_lang_', 'test_')))
async def handle_callback(callback: CallbackQuery):
    logger.info(f"🔘 CALLBACK: {callback.data} | User: {callback.from_user.id}")
    data = callback.data
    state = get_admin_state(callback.message.chat.id)
    # Use persisted language from DB to prevent "revert" after admin changes language.
    db_user = get_user_by_telegram(str(callback.from_user.id))
    lang = detect_lang_from_user(db_user or callback.from_user)

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

    if data.startswith('pay_card:'):
        parts = data.split(':')
        if len(parts) < 2:
            await callback.answer()
            return
        try:
            user_id = int(parts[1])
        except Exception:
            await callback.answer()
            return
        ym = parts[2] if len(parts) >= 3 else None
        await _show_student_payment_card(callback, user_id, ym=ym, use_edit=True)
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
            await _show_student_payment_card(callback, user_id, use_edit=False)
            return

    if data.startswith('pay_set:'):
        parts = data.split(':')
        lang = detect_lang_from_user(callback.from_user)
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
        tz = pytz.timezone("Asia/Tashkent")
        now = datetime.now(tz)
        current_ym = now.strftime("%Y-%m")
        min_ym = get_bot_start_ym()
        day = now.day
        if len(parts) >= 5:
            ym, action = parts[3], parts[4]
        else:
            ym, action = current_ym, parts[3]

        # Prevent editing months before bot startup.
        if ym < min_ym:
            await callback.answer(t(lang, 'payment_card_month_not_available'), show_alert=True)
            return
        groups = get_user_groups(user_id)
        group = next((g for g in groups if g['id'] == group_id), None)
        subject = group.get('subject') if group else None
        admin_id = callback.from_user.id
        if _is_limited_admin(admin_id):
            student = get_user_by_id(user_id)
            group_row = get_group(group_id)
            if not _can_manage_user(admin_id, student) or not _can_manage_group(admin_id, group_row):
                await callback.answer(t(lang, 'permission_denied_short'), show_alert=True)
                return

        def dcoin_for_day(d: int) -> tuple[float, str]:
            if 1 <= d <= 10:
                return 10.0, t(lang, "payment_dcoin_day_1_10_reason")
            if 11 <= d <= 15:
                return 7.0, t(lang, "payment_dcoin_day_11_15_reason")
            if 16 <= d <= 20:
                return 4.0, t(lang, "payment_dcoin_day_16_20_reason")
            if 21 <= d <= 25:
                return 1.0, t(lang, "payment_dcoin_day_21_25_reason")
            if 26 <= d <= 30:
                return -3.0, t(lang, "payment_dcoin_day_26_30_reason")
            # 31-kun (agar bo'lsa) qoidaga moslab -3 deb olinadi
            return -3.0, t(lang, "payment_dcoin_day_31_reason")

        def dcoin_for_overdue(_paid_ym: str) -> tuple[float, str]:
            """Kechikkan to'lov tasdiqlashda -5 D'coin. -2 har kuni scheduler orqali beriladi."""
            return -5.0, t(lang, 'payment_dcoin_overdue_late_only')

        prev_paid = is_month_paid(user_id, ym=ym, group_id=group_id)
        if action == 'paid':
            set_month_paid(user_id, ym=ym, group_id=group_id, subject=subject, paid=True)
            await callback.message.answer(t(lang, 'payment_approved_for_group', group=group.get('name', '-') if group else '-'))
            student = get_user_by_id(user_id)
            if student and student.get('telegram_id'):
                try:
                    student_lang = detect_lang_from_user(student)
                    dcoin_amount = 0.0
                    dcoin_reason = ""
                    dcoin_awarded = False
                    if not prev_paid:
                        from db import add_dcoins
                        if ym < current_ym:
                            dcoin_amount, dcoin_reason = dcoin_for_overdue(ym)
                        else:
                            dcoin_amount, dcoin_reason = dcoin_for_day(day)
                        add_dcoins(user_id, dcoin_amount, subject, change_type="admin_adjust")
                        dcoin_awarded = True

                    student_groups = get_user_groups(user_id)
                    paid_groups = []
                    unpaid_groups = []
                    for sg in student_groups:
                        if is_month_paid(user_id, ym=ym, group_id=sg['id']):
                            paid_groups.append(sg)
                        else:
                            unpaid_groups.append(sg)

                    paid_list = ", ".join([pg.get('name', '-') for pg in paid_groups]) if paid_groups else "-"
                    unpaid_list = ", ".join([ug.get('name', '-') for ug in unpaid_groups]) if unpaid_groups else "-"

                    coin_line = ""
                    if dcoin_awarded:
                        new_balance = get_dcoins(user_id, subject)
                        sign = "+" if dcoin_amount >= 0 else ""
                        coin_line = t(
                            student_lang,
                            'payment_dcoin_awarded_line',
                            sign=sign,
                            amount=f"{dcoin_amount:.0f}",
                            reason=dcoin_reason,
                            balance=f"{new_balance:.1f}",
                        )
                    else:
                        coin_line = t(student_lang, 'payment_dcoin_not_repeated')

                    msg = t(
                        student_lang,
                        'payment_student_status_message',
                        approved_group=group.get('name', '-') if group else '-',
                        paid_groups=paid_list,
                        unpaid_groups=unpaid_list,
                        coin_line=coin_line,
                    )
                    notify_bot = student_notify_bot or bot
                    if notify_bot:
                        await notify_bot.send_message(int(student['telegram_id']), msg)
                except Exception:
                    logger.exception("Failed to notify student about payment")
        elif action == 'unpaid':
            set_month_paid(user_id, ym=ym, group_id=group_id, subject=subject, paid=False)
            await callback.message.answer(t(lang, 'payment_cancelled_for_group', group=group.get('name', '-') if group else '-'))
            student = get_user_by_id(user_id)
            if student and student.get('telegram_id'):
                try:
                    notify_bot = student_notify_bot or bot
                    if notify_bot:
                        student_lang = detect_lang_from_user(student)
                        msg = t(
                            student_lang,
                            'admin_payment_cancelled_student_notification',
                            group=group.get('name', '-') if group else '-',
                            subject=subject or '-',
                        )
                        await notify_bot.send_message(int(student['telegram_id']), msg)
                except Exception:
                    pass
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
        
        lang = detect_lang_from_user(callback.from_user)
        
        from attendance_manager import get_group_sessions
        sessions = get_group_sessions(group_id)
        if not sessions:
            today = datetime.now(pytz.timezone("Asia/Tashkent")).strftime("%Y-%m-%d")
            await callback.message.answer(
                t(lang, "admin_attendance_no_sessions_header"),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=t(lang, "admin_attendance_today_btn", today=today), callback_data=f"admin_take_attendance:{group_id}:{today}")],
                    [InlineKeyboardButton(text=t(lang, 'btn_back'), callback_data="admin_attendance_back")],
                ]),
            )
            await callback.answer()
            return
        
        # Show recent sessions
        keyboard = []
        for session in sessions[:5]:  # Show last 5 sessions
            date = session['date']
            keyboard.append([InlineKeyboardButton(text=t(lang, "admin_attendance_date_btn", date=date), callback_data=f"admin_take_attendance:{group_id}:{date}")])
        
        keyboard.append([InlineKeyboardButton(text=t(lang, 'admin_btn_export_attendance_excel'), callback_data=f"admin_export_group_attendance:{group_id}")])
        keyboard.append([InlineKeyboardButton(text=t(lang, 'btn_back'), callback_data="admin_attendance_back")])
        
        await callback.message.answer(
            t(lang, "admin_attendance_panel_title", group_name=group['name']),
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
        if is_lesson_holiday(date):
            await callback.answer(t(lang, "lesson_canceled_for_date_alert", date=date), show_alert=True)
            return
        from attendance_manager import ensure_session, send_attendance_panel
        session = ensure_session(group_id, date)
        if not session:
            await callback.answer(t(lang, 'admin_auto_msg_27'))
            return
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
            await callback.answer(t(lang, 'admin_auto_msg_19'))
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
        keyboard = create_language_selection_keyboard_for_user(user_id, lang)
        await callback.message.answer(t(lang, 'select_language_prompt'), reply_markup=keyboard)
        await callback.answer()
        return

    if data.startswith('teacher_change_lang_'):
        teacher_id = int(data.split('_')[-1])
        keyboard = create_language_selection_keyboard_for_user(teacher_id, lang)
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

            ok = set_user_language_by_telegram(str(target_id), lang_code)
            
            if ok:
                await callback.answer(t(lang, 'admin_auto_msg_38'))
            else:
                await callback.answer(t(lang, 'admin_auto_msg_39'))
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

        admin_id = callback.from_user.id
        if not _can_manage_user(admin_id, target):
            await callback.answer(t(lang, 'admin_auto_msg_20'), show_alert=True)
            return

        groups = _scope_groups_for_admin(admin_id, get_all_groups())
        tr = get_latest_test_result(target_user_id)
        subj = (tr.get('subject') if tr else target.get('subject') or '')
        subj = subj.strip().title()
        lvl_raw = (tr.get('level') if tr else target.get('level') or '')
        code = extract_cefr_level_code(lvl_raw)
        subject_groups = [g for g in groups if (g.get('subject') or '').strip().title() == subj] if subj else list(groups)
        rec = []
        if code:
            rec = [
                g for g in subject_groups
                if extract_cefr_level_code(g.get('level', '')) == code
            ]
        if not rec and code:
            level_mapping = {
                'A1': ['A1', 'A2'],
                'A2': ['A1', 'A2', 'B1'],
                'B1': ['A2', 'B1', 'B2'],
                'B2': ['B1', 'B2'],
            }
            acceptable = level_mapping.get(code, [code])
            rec = [
                g for g in subject_groups
                if extract_cefr_level_code(g.get('level', '')) in acceptable
            ]
        if not rec:
            rec = subject_groups
        lvl_display = level_ui_label(lang, subject=subj, code=code) if code else (lvl_raw or '—')

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
            if not _can_manage_group(admin_id, group):
                await callback.answer(t(lang, 'admin_auto_msg_20'), show_alert=True)
                return
            add_user_to_group(target_user_id, group_id)
            await _notify_student_group_assigned(target_user_id, group_id)
            teacher = get_user_by_id(group.get('teacher_id')) if group.get('teacher_id') else None
            teacher_name = f"{teacher.get('first_name','')} {teacher.get('last_name','')}".strip() if teacher else "-"
            await callback.message.answer(
                t(
                    lang,
                    "admin_user_group_assigned_admin_confirm",
                    first_name=target.get("first_name"),
                    last_name=target.get("last_name"),
                    login_id=target.get("login_id"),
                    group_name=group.get("name"),
                    group_level=group.get("level"),
                    teacher_name=teacher_name,
                    lesson_date=group.get('lesson_date') or '-',
                    lesson_start=(group.get('lesson_start') or '-')[:5],
                    lesson_end=(group.get('lesson_end') or '-')[:5],
                )
            )

            # Notify student about schedule if they are connected to bot
            try:
                if student_notify_bot and target.get('telegram_id'):
                    # Get proper day label for lesson_date
                    raw_date = (group.get('lesson_date') or '-').strip().upper()
                    if raw_date in ('MWF', 'MON/WED/FRI', 'MON,WED,FRI'):
                        date_label = t(lang, 'admin_btn_lesson_days_mwf')
                    elif raw_date in ('TTS', 'TUE/THU/SAT', 'TUE,THU,SAT'):
                        date_label = t(lang, 'admin_btn_lesson_days_tts')
                    else:
                        date_label = raw_date
                    
                    await student_notify_bot.send_message(
                        int(target['telegram_id']),
                        t(
                            lang,
                            "admin_user_group_assigned_student_notification",
                            group_name=group.get('name'),
                            group_level=group.get('level'),
                            teacher_name=teacher_name,
                            date_label=date_label,
                            lesson_start=(group.get('lesson_start') or '-')[:5],
                            lesson_end=(group.get('lesson_end') or '-')[:5],
                        )
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
        out.append(t(lang, "admin_rec_header"))
        out.append(
            t(
                lang,
                "admin_rec_user_line",
                first_name=target.get("first_name"),
                last_name=target.get("last_name"),
                subj=subj,
                lvl=lvl_display,
            )
        )
        out.append(t(lang, "admin_page_info", page=page + 1, total=total_pages))
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
            out.append(_format_group_line(idx, g, lang).rstrip())
            out.append(t(lang, "admin_rec_teacher_line", teacher_name=teacher_name))
            out.append(t(lang, "admin_rec_students_line", students_count=len(students)))

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

        groups = _scope_groups_for_admin(callback.from_user.id, get_all_groups())
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
            await _notify_student_group_assigned(target_user_id, group_id)
            await callback.message.answer(
                t(
                    lang,
                    "admin_assign_new_user_to_group_confirm",
                    group_name=group.get("name"),
                    group_level=group.get("level"),
                    first_name=target.get("first_name"),
                    last_name=target.get("last_name"),
                    login_id=target.get("login_id"),
                )
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
        out.append(t(lang, "admin_group_pick_header"))
        out.append(
            t(
                lang,
                "admin_group_pick_user_line",
                first_name=target.get('first_name'),
                last_name=target.get('last_name'),
                subj=subj,
            )
        )
        out.append(t(lang, "admin_page_info", page=page + 1, total=total_pages))
        for idx, g in enumerate(page_groups, start=1):
            teacher = get_user_by_id(g.get('teacher_id')) if g.get('teacher_id') else None
            teacher_name = f"{teacher.get('first_name','')} {teacher.get('last_name','')}".strip() if teacher else "-"
            students = get_group_users(g['id'])
            out.append(_format_group_line(idx, g, lang).rstrip())
            out.append(t(lang, "admin_rec_teacher_line", teacher_name=teacher_name))
            out.append(t(lang, "admin_rec_students_line", students_count=len(students)))

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
            await callback.message.answer(t(lang, "choose_teacher"), reply_markup=create_teacher_selection_keyboard(teachers, lang))
            await callback.answer()
            return

        if action == 'add_student':
            state['step'] = None
            # show available students not in group
            all_users = _scope_users_for_admin(callback.from_user.id, get_all_users(), login_type_filter=(1, 2))
            group_users = get_group_users(group_id)
            group_user_ids = {u['id'] for u in group_users}
            available = [u for u in all_users if u['id'] not in group_user_ids]
            if not available:
                await callback.message.answer(t(lang, "no_available_students"))
                await callback.answer()
                return
            await callback.message.answer(t(lang, "choose_student_add"), reply_markup=create_user_selection_keyboard_by_type(available, group_id, lang))
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
        await _notify_student_group_assigned(user_id, group_id)
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
            await callback.message.answer(t(lang, 'admin_auto_msg_40'))
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
            tz='Asia/Tashkent',
            owner_admin_id=callback.from_user.id,
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
        await create_group_from_state(callback.message, state, owner_admin_id=callback.from_user.id)
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
        await _notify_student_group_assigned(user_id, group_id)
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
            status = t(lang, "admin_status_blocked_label")
        elif is_access_active(teacher):
            status = t(lang, "admin_status_open_label")
        else:
            status = t(lang, "admin_status_closed_label")
        
        state = get_admin_state(callback.message.chat.id)
        state['selected_teacher'] = teacher
        
        await callback.message.answer(
            t(
                lang,
                "admin_teacher_card_basic",
                first_name=teacher["first_name"],
                last_name=teacher["last_name"],
                subject=teacher.get("subject") or "-",
                phone=teacher.get("phone") or "-",
                login_id=teacher["login_id"],
                status=status,
            ),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=t(lang, 'btn_block'), callback_data=f'teacher_block_{teacher_id}')],
                [InlineKeyboardButton(text=t(lang, 'btn_unblock'), callback_data=f'teacher_unblock_{teacher_id}')],
                [InlineKeyboardButton(text=t(lang, 'btn_reset_pw'), callback_data=f'teacher_reset_{teacher_id}')],
                [InlineKeyboardButton(text=t(lang, 'btn_change_subject'), callback_data=f'teacher_change_sub_{teacher_id}')],
                [InlineKeyboardButton(text=t(lang, 'btn_edit_info'), callback_data=f'teacher_detail_{teacher_id}')],
                [InlineKeyboardButton(text=t(lang, 'admin_btn_delete_teacher_profile'), callback_data=f'teacher_delete_profile_{teacher_id}')],
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
        admin_id = callback.from_user.id
        teacher = get_user_by_id(teacher_id)
        if not teacher:
            lang = detect_lang_from_user(callback.from_user)
            await callback.message.answer(t(lang, 'teacher_not_found'))
            await callback.answer()
            return
        if not _can_manage_user(admin_id, teacher):
            lang = detect_lang_from_user(callback.from_user)
            await callback.answer(t(lang, 'permission_denied_short'), show_alert=True)
            return
        
        from db import block_user
        block_user(teacher_id)
        lang = detect_lang_from_user(callback.from_user)
        await callback.message.answer(
            t(
                lang,
                "admin_teacher_blocked",
                first_name=teacher['first_name'],
                last_name=teacher['last_name'],
            )
        )
        await callback.answer()
        try:
            await handle_teacher_detail(callback)
        except Exception:
            pass
        return

    if data.startswith('teacher_unblock_'):
        teacher_id = int(data.split('_')[-1])
        admin_id = callback.from_user.id
        teacher = get_user_by_id(teacher_id)
        if not teacher:
            lang = detect_lang_from_user(callback.from_user)
            await callback.message.answer(t(lang, 'teacher_not_found'))
            await callback.answer()
            return
        if not _can_manage_user(admin_id, teacher):
            lang = detect_lang_from_user(callback.from_user)
            await callback.answer(t(lang, 'permission_denied_short'), show_alert=True)
            return
        
        from db import unblock_user
        unblock_user(teacher_id)
        lang = detect_lang_from_user(callback.from_user)
        await callback.message.answer(
            t(
                lang,
                "admin_teacher_unblocked",
                first_name=teacher['first_name'],
                last_name=teacher['last_name'],
            )
        )
        await callback.answer()
        try:
            await handle_teacher_detail(callback)
        except Exception:
            pass
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
        await callback.message.answer(
            t(
                lang,
                "admin_teacher_reset_new_password",
                password=new_password,
            ),
            parse_mode='HTML',
        )
        await callback.answer()
        return

    # Start language change flow for a user
    if data.startswith('user_change_lang_'):
        user_id = int(data.split('_')[-1])
        keyboard = create_language_selection_keyboard_for_user(user_id, lang)
        await callback.message.answer(t(lang, 'select_language_prompt'), reply_markup=keyboard)
        await callback.answer()
        return

    if data.startswith('teacher_change_lang_'):
        teacher_id = int(data.split('_')[-1])
        keyboard = create_language_selection_keyboard_for_user(teacher_id, lang)
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
            await callback.message.answer(t(lang, "admin_language_changed", lang_code=lang_code))
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


@dp.callback_query(lambda c: c.data == "admin_export_attendance")
async def handle_admin_export_attendance(callback: CallbackQuery):
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    lang = detect_lang_from_user(callback.from_user)
    from vocabulary import export_all_attendance_to_xlsx
    admin_id = callback.from_user.id
    owner_filter = admin_id if _is_limited_admin(admin_id) else None

    try:
        file_data, filename = export_all_attendance_to_xlsx(owner_admin_id=owner_filter)
        await callback.bot.send_document(
            callback.message.chat.id,
            BufferedInputFile(file_data.getvalue(), filename)
        )
        await callback.answer(t(lang, 'admin_auto_msg_41'))
    except Exception as e:
        logger.exception("Failed to export attendance")
        await callback.answer(t(lang, 'admin_auto_msg_19'))


async def show_group_menu(message: Message):
    lang = _admin_lang_from_message(message)
    kb = create_group_action_keyboard(lang)          # utils.py dagi funksiya
    await message.answer(t(lang, 'group_mgmt'), reply_markup=kb)


async def _show_group_list(callback: CallbackQuery, page: int = 0):
    """Show group list with pagination using group_list: callback pattern"""
    admin_id = callback.from_user.id
    lang = detect_lang_from_user(callback.from_user)
    groups = _scope_groups_for_admin(admin_id, get_all_groups())
    if not groups:
        await callback.message.edit_text(t(lang, 'no_groups'))
        await callback.answer()
        return

    per_page = 10
    total = len(groups)
    start = page * per_page
    chunk = groups[start:start + per_page]
    total_pages = (total - 1) // per_page + 1 if total else 1

    text = _render_group_list_page_text(lang, chunk, page, total_pages)

    # Create keyboard with group_list: pattern
    keyboard = _group_list_keyboard(chunk, page, total_pages, "group_list", detect_lang_from_user(callback.from_user))
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


async def _render_assign_select_groups_page(callback: CallbackQuery, user_id: int, page: int, *, use_edit: bool) -> None:
    """Render paginated group list for assign_select flow."""
    db_user = get_user_by_telegram(str(callback.from_user.id))
    lang = detect_lang_from_user(db_user or callback.from_user)
    groups = _scope_groups_for_admin(callback.from_user.id, get_all_groups())
    if not groups:
        await callback.message.answer(t(lang, "no_groups_found"))
        return

    page_size = 10
    total_pages = max(1, (len(groups) + page_size - 1) // page_size)
    page = max(0, min(page, total_pages - 1))
    start = page * page_size
    page_groups = groups[start:start + page_size]

    out = [t(lang, "admin_group_list_header"), t(lang, "admin_page_info", page=page + 1, total=total_pages)]
    for idx, g in enumerate(page_groups, start=1):
        teacher = get_user_by_id(g.get('teacher_id')) if g.get('teacher_id') else None
        teacher_name = f"{teacher.get('first_name','')} {teacher.get('last_name','')}".strip() if teacher else "-"
        out.append(
            t(
                lang,
                "admin_group_list_item",
                idx=idx,
                group_name=g["name"],
                teacher_name=teacher_name,
                students_count=len(get_group_users(g['id'])),
            )
        )
    kb = _group_list_keyboard(page_groups, page, total_pages, base=f"assign_select:{user_id}", lang=lang)
    if use_edit:
        await callback.message.edit_text("\n".join(out), reply_markup=kb)
    else:
        await callback.message.answer("\n".join(out), reply_markup=kb)


async def _send_group_list(message: Message, state: dict):
    groups = state['groups']
    page = state.get('groups_page', 0)
    lang = _admin_lang_from_message(message)
    per_page = 10
    total = len(groups)
    start = page * per_page
    chunk = groups[start:start + per_page]

    total_pages = (total - 1) // per_page + 1 if total else 1

    text = _render_group_list_page_text(lang, chunk, page, total_pages)

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
        nav.append(InlineKeyboardButton(text=t(lang, 'btn_prev'), callback_data="groups_prev"))
    if start + per_page < total:
        nav.append(InlineKeyboardButton(text=t(lang, 'btn_next_arrow'), callback_data="groups_next"))
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
    lang = detect_lang_from_user(callback.from_user)
    if not group:
        await callback.answer(t(lang, 'admin_auto_msg_42'))
        return

    admin_id = callback.from_user.id
    if not _can_manage_group(admin_id, group):
        await callback.answer(t(lang, 'admin_auto_msg_20'), show_alert=True)
        return

    state = get_admin_state(callback.message.chat.id)
    state["current_group_id"] = group_id

    teacher = get_user_by_id(group.get("teacher_id")) if group.get("teacher_id") else None
    t_name = f"{teacher.get('first_name','')} {teacher.get('last_name','')}".strip() if teacher else "—"

    students_count = len(get_group_users(group_id))

    text = (
        f"📚 <b>{group['name']}</b>\n\n"
        f"Fan: {group.get('subject','—')}\n"
        f"Daraja: {format_group_level_display(lang, group.get('level'), subject=group.get('subject'))}\n"
        f"O'qituvchi: {t_name}\n"
        f"Dars: {group.get('lesson_date','—')} | {group.get('lesson_start','—')[:5]}-{group.get('lesson_end','—')[:5]}\n"
        f"O'quvchilar: {students_count} ta"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, 'admin_btn_group_change_teacher'), callback_data=f"group_edit_teacher_{group_id}")],
        [InlineKeyboardButton(text=t(lang, 'admin_btn_group_add_student'), callback_data=f"group_add_student_{group_id}")],
        [InlineKeyboardButton(text=t(lang, 'admin_btn_group_remove_student'), callback_data=f"group_remove_student_{group_id}")],
        [InlineKeyboardButton(text=t(lang, 'admin_btn_group_edit_name'), callback_data=f"group_edit_name_{group_id}")],
        [InlineKeyboardButton(text=t(lang, 'admin_btn_group_edit_level'), callback_data=f"group_edit_level_{group_id}")],
        [InlineKeyboardButton(text=t(lang, 'admin_btn_group_delete'), callback_data=f"group_delete_confirm_{group_id}")],
        [InlineKeyboardButton(text=t(lang, 'admin_btn_back_to_list'), callback_data="group_list")],
    ])

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


async def show_payment_menu(message: Message):
    lang = _admin_lang_from_message(message)
    await send_admin_payments_root_menu(message.bot, message.chat.id, lang)


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
    admin_id = from_user.id
    users = _scope_users_for_admin(admin_id, get_all_users(), login_type_filter=(1, 2))

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
        await send(t(lang, "admin_payment_not_found"))
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
    out.append(t(lang, "admin_payment_search_header"))
    out.append(t(lang, "admin_page_info", page=page + 1, total=total_pages))

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
            date = t(lang, 'admin_btn_lesson_days_mwf')
        elif raw_date in ('TTS', 'TUE/THU/SAT', 'TUE,THU,SAT'):
            date = t(lang, 'admin_btn_lesson_days_tts')
        else:
            date = raw_date
        groups = get_user_groups(u['id'])
        out.append(
            t(
                lang,
                "admin_payment_student_header",
                idx=idx,
                first_name=u.get('first_name', '-'),
                last_name=u.get('last_name', '-'),
                subject=subject,
            )
        )
        for g in groups:
            teacher = get_user_by_id(g.get('teacher_id')) if g and g.get('teacher_id') else None
            teacher_name = f"{teacher.get('first_name','')} {teacher.get('last_name','')}".strip() if teacher else "-"
            raw_date = (g.get('lesson_date') or '-').strip().upper()
            if raw_date in ('MWF', 'MON/WED/FRI', 'MON,WED,FRI'):
                date = t(lang, 'admin_btn_lesson_days_mwf')
            elif raw_date in ('TTS', 'TUE/THU/SAT', 'TUE,THU,SAT'):
                date = t(lang, 'admin_btn_lesson_days_tts')
            else:
                date = raw_date
            paid = is_month_paid(u['id'], ym=ym, group_id=g['id'])
            mark = '✅' if paid else '❌'
            out.append(
                t(
                    lang,
                    "admin_payment_group_line",
                    group_name=g.get('name', '-'),
                    subject=g.get('subject', '-'),
                    date=date,
                    start=(g.get('lesson_start', '-') or '-')[:5],
                    end=(g.get('lesson_end', '-') or '-')[:5],
                    teacher_name=teacher_name,
                    mark=mark,
                )
            )

    base = f"pay_list:{mode}:{query}"
    kb = _student_list_keyboard(page_users, page, total_pages, base=base, lang=lang)
    await send("\n".join(out), reply_markup=kb)


def _prev_month_ym(ym: str) -> str | None:
    y, m = map(int, ym.split('-'))
    if m == 1:
        return f"{y-1}-12"
    return f"{y}-{m-1:02d}"


def _next_month_ym(ym: str) -> str | None:
    y, m = map(int, ym.split('-'))
    if m == 12:
        return f"{y+1}-01"
    return f"{y}-{m+1:02d}"


async def _show_student_payment_card(callback: CallbackQuery, user_id: int, ym: str | None = None, use_edit: bool = False):
    u = get_user_by_id(user_id)
    if not u:
        await callback.message.answer(t(lang, "user_not_found"))
        await callback.answer()
        return
    admin_id = callback.from_user.id
    if not _can_manage_user(admin_id, u):
        await callback.message.answer(t(lang, 'admin_auto_msg_43'))
        await callback.answer()
        return
    tz = pytz.timezone("Asia/Tashkent")
    current_ym = datetime.now(tz).strftime("%Y-%m")
    min_ym = get_bot_start_ym()
    ym = ym or current_ym
    # Don't allow viewing months before bot startup.
    if ym < min_ym:
        ym = min_ym
    lang = detect_lang_from_user(callback.from_user)
    groups = get_user_groups(user_id)

    unpaid_groups = [g for g in groups if not is_month_paid(user_id, ym=ym, group_id=g['id'])] if groups else []
    subjects_label = ((u.get('subject') or '').title() or '-') if u.get('subject') else '-'
    lines = [
        t(lang, "admin_payment_card_student_header", first_name=u.get('first_name', '-'), last_name=u.get('last_name', '-')),
        t(lang, "admin_payment_card_login_id", login_id=u.get('login_id') or '-'),
        t(lang, "admin_payment_card_phone", phone=u.get('phone') or '-'),
        t(
            lang,
            "admin_payment_card_level",
            level=format_stored_user_level_display(lang, u.get("level"), subject=u.get("subject")),
        ),
        t(lang, "admin_payment_card_subjects", subjects=subjects_label),
        t(lang, "admin_payment_card_month", month=ym),
        "",
    ]

    kb_rows = []
    if unpaid_groups:
        for g in unpaid_groups:
            raw_date = (g.get('lesson_date') or '-').strip().upper()
            if raw_date in ('MWF', 'MON/WED/FRI', 'MON,WED,FRI'):
                date = t(lang, 'admin_btn_lesson_days_mwf')
            elif raw_date in ('TTS', 'TUE/THU/SAT', 'TUE,THU,SAT'):
                date = t(lang, 'admin_btn_lesson_days_tts')
            else:
                date = raw_date
            start_t = (g.get('lesson_start') or '-')[:5]
            end_t = (g.get('lesson_end') or '-')[:5]
            lines.append(
                t(
                    lang,
                    "admin_payment_card_group_line",
                    group_name=g.get('name', '-'),
                    subject=g.get('subject', '-'),
                    date=date,
                    start_t=start_t,
                    end_t=end_t,
                    mark='❌',
                )
            )
            kb_rows.append([
                InlineKeyboardButton(
                    text=t(lang, "admin_payment_btn_paid", group_name=g.get('name')),
                    callback_data=f"pay_set:{user_id}:{g['id']}:{ym}:paid",
                ),
            ])
    elif groups:
        lines.append(t(lang, "admin_payment_card_all_paid"))
    else:
        lines.append(t(lang, "admin_payment_card_no_groups"))

    nav_row = []
    prev_ym = _prev_month_ym(ym)
    if prev_ym and prev_ym >= min_ym:
        nav_row.append(InlineKeyboardButton(text=t(lang, 'pay_card_prev_month'), callback_data=f"pay_card:{user_id}:{prev_ym}"))
    if ym < current_ym:
        next_ym = _next_month_ym(ym)
        if next_ym and next_ym <= current_ym:
            nav_row.append(InlineKeyboardButton(text=t(lang, 'pay_card_next_month'), callback_data=f"pay_card:{user_id}:{next_ym}"))
    if nav_row:
        kb_rows.append(nav_row)
    kb_rows.append([InlineKeyboardButton(text=t(lang, 'btn_back'), callback_data='back_to_menu')])

    msg_text = "\n".join(lines)
    kb = InlineKeyboardMarkup(inline_keyboard=kb_rows)
    if use_edit:
        try:
            await callback.message.edit_text(msg_text, reply_markup=kb)
        except Exception:
            await callback.message.answer(msg_text, reply_markup=kb)
    else:
        await callback.message.answer(msg_text, reply_markup=kb)
    await callback.answer()


async def send_teachers_list(chat_id: int, message: Message, state: dict):
    lang = _admin_lang_from_message(message)
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
    text = t(lang, "admin_teachers_list_title_with_page", page=page + 1, total=total_pages) + "\n\n"
    
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
            f"   📁 {t(lang, 'admin_teacher_list_label_groups_students', groups=group_count, students=total_students)}\n"
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
        nav_buttons.append(InlineKeyboardButton(text=t(lang, 'admin_btn_back_prev'), callback_data='teachers_prev'))
    if end < total:
        nav_buttons.append(InlineKeyboardButton(text=t(lang, 'btn_next'), callback_data='teachers_next'))
    
    if nav_buttons:
        buttons.append(nav_buttons)

    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(text, reply_markup=markup)


@dp.callback_query(lambda c: c.data in ('teachers_next', 'teachers_prev'))
async def handle_teachers_pagination_legacy(callback: CallbackQuery):
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
# Note: teacher_detail_ handler is defined later in the file (line 5150)


# Duplicate teachers_list_back handler removed - using teachers_list_view instead


@dp.callback_query(lambda c: c.data.startswith("teacher_groups_"))
async def handle_teacher_groups(callback: CallbackQuery):
    """Show teacher's groups with details"""
    try:
        teacher_id = int(callback.data.split("_")[-1])
        teacher = get_user_by_id(teacher_id)
        lang = detect_lang_from_user(callback.from_user)
        
        if not teacher:
            await callback.answer(t(lang, 'admin_auto_msg_44'))
            return
        
        from db import get_groups_by_teacher, get_group_users
        teacher_groups = get_groups_by_teacher(teacher_id)
        
        if not teacher_groups:
            text = f"👨‍🏫 <b>{teacher['first_name']} {teacher['last_name']}</b>\n\n"
            text += t(
                lang,
                "admin_teacher_groups_empty_label",
                none=t(lang, "none_short"),
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=t(lang, 'btn_back'), callback_data=f"teacher_detail_{teacher_id}")]
            ])
        else:
            text = f"👨‍🏫 <b>{teacher['first_name']} {teacher['last_name']}</b>\n\n"
            text += t(lang, "admin_teacher_groups_section_header")
            
            for i, group in enumerate(teacher_groups, start=1):
                students = get_group_users(group['id'])
                student_count = len(students)
                
                # Format lesson time
                lesson_time = "—"
                if group.get('lesson_start') and group.get('lesson_end'):
                    lesson_time = f"{group['lesson_start'][:5]}-{group['lesson_end'][:5]}"
                
                # Format lesson days (i18n)
                lesson_days = _to_lesson_days_text(group.get('lesson_date', '—'), lang=lang)
                
                text += f'{i}. 📚 <b>{group.get("name", "Noma\'lum")}</b>\n'
                text += f"   🎓 Level: {format_group_level_display(lang, group.get('level'), subject=group.get('subject'))}\n"
                text += f"   📅 Dars kunlari: {lesson_days}\n"
                text += f"   🕒 Vaqti: {lesson_time}\n"
                text += f"   👥 O'quvchilar: {student_count} ta\n\n"
            
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=t(lang, 'btn_back'), callback_data=f"teacher_detail_{teacher_id}")]
            ])
        
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in teacher_groups handler: {e}")
        await callback.answer(t(lang, 'admin_auto_msg_15'))


# Teacher edit handlers are now integrated into teacher_detail with short prefixes

async def send_user_list(chat_id: int, message: Message, state: dict):
    """Legacy entry: delegates to show_students_list (list_users kept for compatibility)."""
    page = state.get('list_page', 0)
    search = (state.get('data') or {}).get('students_search', '') or ''
    await show_students_list(message, page=page, search_query=search)


async def handle_admin_user_action(callback: CallbackQuery):
    data = callback.data
    state = get_admin_state(callback.message.chat.id)
    lang = _admin_lang_from_callback(callback)
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
        status = t(lang, "admin_status_blocked_label")
    elif is_access_active(selected_user):
        status = t(lang, "admin_status_open_label")
    else:
        status = t(lang, "admin_status_closed_label")

        await callback.message.answer(
            t(
                lang,
                "admin_user_card_basic",
                first_name=selected_user["first_name"],
                last_name=selected_user["last_name"],
                login_id=selected_user["login_id"],
                subject=selected_user.get("subject") or "-",
                level=format_stored_user_level_display(
                    lang,
                    selected_user.get("level"),
                    subject=selected_user.get("subject"),
                ),
                status=status,
            ),
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=t(lang, "btn_send_test"),
                            callback_data=f'user_test_{selected_user["id"]}',
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text=t(lang, "admin_btn_subject_settings"),
                            callback_data=f'user_control_sub_{selected_user["id"]}',
                        )
                    ],
                ]
            ),
        )
        await callback.answer()
        return



async def _send_attendance_groups_picker(message: Message, page: int = 0) -> None:
    lang = _admin_lang_from_message(message)
    admin_id = message.from_user.id
    groups = _scope_groups_for_admin(admin_id, get_all_groups())
    if not groups:
        await message.answer(t(lang, "no_groups"))
        return

    per_page = 10
    total = len(groups)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(0, min(int(page or 0), total_pages - 1))
    start = page * per_page
    chunk = groups[start:start + per_page]

    # Text: 1..10 list with details
    lines = [f"{t(lang, 'admin_auto_msg_45')}\n", f"{t(lang, 'admin_page_info', page=page + 1, total=total_pages)}\n"]
    for i, g in enumerate(chunk, start=1):
        teacher = get_user_by_id(g.get("teacher_id")) if g.get("teacher_id") else None
        teacher_name = f"{teacher.get('first_name','')} {teacher.get('last_name','')}".strip() if teacher else "—"
        lvl = format_group_level_display(lang, g.get("level"), subject=g.get("subject"))
        students_count = len(get_group_users(g["id"]))
        lines.append(
            f"<b>{start + i}.</b> {html_module.escape(g.get('name') or '-')}\n"
            f"   🎯 {html_module.escape(str(lvl))}\n"
            f"   👨‍🏫 {html_module.escape(teacher_name)}\n"
            f"   👥 {t(lang, 'admin_attendance_students_count', count=students_count)}\n"
        )
    text = "\n".join(lines)

    # Keyboard: numbered 1..10 + pagination
    rows: list[list[InlineKeyboardButton]] = []
    nums: list[InlineKeyboardButton] = []
    for i, g in enumerate(chunk, start=1):
        nums.append(InlineKeyboardButton(text=str(i), callback_data=f"admin_attendance_group:{g['id']}"))
    if nums:
        rows.append(nums[:5])
        if len(nums) > 5:
            rows.append(nums[5:10])

    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(InlineKeyboardButton(text=t(lang, "btn_prev"), callback_data=f"admin_attendance_page_{page-1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text=t(lang, "btn_next_arrow"), callback_data=f"admin_attendance_page_{page+1}"))
    if nav:
        rows.append(nav)

    rows.append([InlineKeyboardButton(text=t(lang, 'admin_btn_export_attendance_excel'), callback_data="admin_export_attendance")])
    rows.append([InlineKeyboardButton(text=t(lang, 'btn_back'), callback_data="admin_back_to_main")])

    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")


async def show_attendance_menu(message: Message):
    await _send_attendance_groups_picker(message, page=0)


@dp.callback_query(lambda c: bool(c.data) and c.data.startswith("admin_attendance_page_"))
async def handle_admin_attendance_groups_page(callback: CallbackQuery):
    lang = detect_lang_from_user(callback.from_user)
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    try:
        page = int((callback.data or "").split("_")[-1])
    except Exception:
        await callback.answer()
        return
    await callback.answer()
    await _send_attendance_groups_picker(callback.message, page=page)


def _groups_scheduled_for_date(date_str: str) -> list[dict]:
    import re as _re

    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        return []
    wd = d.weekday()
    groups = get_all_groups() or []
    out = []
    for g in groups:
        ld = (g.get("lesson_date") or "").strip()
        if not ld:
            continue
        if _re.match(r"^\d{4}-\d{2}-\d{2}$", ld):
            if ld == date_str:
                out.append(g)
            continue
        code = ld.upper()
        if code in ("MWF", "MON/WED/FRI", "MON,WED,FRI", "ODD") and wd in (0, 2, 4):
            out.append(g)
        elif code in ("TTS", "TUE/THU/SAT", "TUE,THU,SAT", "EVEN") and wd in (1, 3, 5):
            out.append(g)
    return out


def _ensure_otmen_request_for_day(date_str: str, reason: str) -> str | None:
    row = get_pending_lesson_otmen_request_by_date(date_str)
    if row:
        return str(row.get("id"))
    req_id = uuid4().hex[:20]
    tz = pytz.timezone("Asia/Tashkent")
    exp = (datetime.now(tz) + timedelta(hours=48)).isoformat()
    ok = create_lesson_otmen_request(req_id, date_str, reason, exp)
    return req_id if ok else None


def _cancel_lessons_stats_text(lang: str, groups: int, sessions: int, bookings: int) -> str:
    return t(lang, "admin_cancel_lessons_stats", groups=groups, sessions=sessions, bookings=bookings)


async def show_cancel_lessons_menu(message: Message):
    lang = _admin_lang_from_message(message)
    days = [d for d in get_next_11_days_status(lang=lang) if int((d.get("date")).weekday()) != 6]
    lines = []
    for i, day in enumerate(days, start=1):
        date_str = day.get("date_str")
        c1 = is_branch_date_closed_for_booking("branch_1", date_str)
        c2 = is_branch_date_closed_for_booking("branch_2", date_str)
        closed = bool(c1 or c2)
        st = t(lang, "admin_cancel_lessons_status_closed") if closed else t(lang, "admin_cancel_lessons_status_open")
        lines.append(f"{i}. {day['date_ui']}, {day['weekday']} — {st}")

    # 1..11 raqamli tanlash tugmalari
    keyboard = []
    row = []
    for i in range(1, len(days) + 1):
        row.append(InlineKeyboardButton(text=str(i), callback_data=f"admin_otmen_pick:{i - 1}"))
        if len(row) == 5:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton(text=t(lang, "admin_cancel_lessons_view_cancelled_btn"), callback_data="admin_otmen_view_cancelled")])
    keyboard.append([InlineKeyboardButton(text=t(lang, 'btn_back'), callback_data="admin_back_to_main")])
    await message.answer(
        t(lang, "admin_cancel_lessons_title", items="\n".join(lines)),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML",
    )


async def send_daily_otmen_alerts(start_offset: int = 0, days_count: int = 11):
    if not bot:
        return
    days = get_days_status(start_offset=start_offset, days_count=days_count, lang="uz")
    for day in days:
        # Weekendga xabar yubormaymiz; faqat rasmiy bayramlar.
        if not day.get("is_holiday"):
            continue
        req_id = _ensure_otmen_request_for_day(day["date_str"], day["reason_db"])
        if not req_id:
            continue
        for aid in ALL_ADMIN_IDS:
            try:
                au = get_user_by_telegram(str(aid)) if aid else None
                target_lang = detect_lang_from_user(au or {})
                info = otmen_full_info_line(target_lang, day["date"])
                await bot.send_message(
                    int(aid),
                    t(target_lang, "admin_cancel_lessons_scheduler_alert", info=info),
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[
                            [InlineKeyboardButton(text=t(target_lang, "admin_cancel_lessons_cancel_btn", date=day["date_ui"]), callback_data=f"cancel_day:{req_id}")],
                            [InlineKeyboardButton(text=t(target_lang, "admin_cancel_lessons_btn"), callback_data="admin_cancel_lessons")],
                        ]
                    ),
                    parse_mode="HTML",
                )
            except Exception:
                pass


@dp.callback_query(lambda c: c.data == "admin_cancel_lessons")
async def admin_cancel_lessons_menu(callback: CallbackQuery):
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    await callback.answer()
    await show_cancel_lessons_menu(callback.message)


@dp.callback_query(lambda c: c.data == "admin_otmen_view_cancelled")
async def admin_otmen_view_cancelled(callback: CallbackQuery):
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    lang = _admin_lang_from_callback(callback)
    rows = list_cancelled_lesson_otmen_requests(limit=20)
    if not rows:
        await callback.answer()
        await callback.message.answer(t(lang, "admin_cancel_lessons_cancelled_empty"))
        return
    lines: list[str] = []
    for i, r in enumerate(rows, start=1):
        date_str = str(r.get("date_str") or "—")
        reason = str(r.get("reason") or t(lang, "admin_cancel_lessons_default_reason"))
        c1 = is_branch_date_closed_for_booking("branch_1", date_str)
        c2 = is_branch_date_closed_for_booking("branch_2", date_str)
        closed = bool(c1 or c2)
        st = t(lang, "admin_cancel_lessons_status_closed") if closed else t(lang, "admin_cancel_lessons_status_open")
        lines.append(f"{i}. {st} {date_str} — {reason}")
    await callback.answer()
    await callback.message.answer(
        t(lang, "admin_cancel_lessons_cancelled_title", items="\n".join(lines)),
        parse_mode="HTML",
    )


@dp.callback_query(lambda c: bool(c.data) and c.data.startswith("admin_otmen_pick:"))
async def admin_otmen_pick_day(callback: CallbackQuery):
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    lang = _admin_lang_from_callback(callback)
    idx = int((callback.data or "").split(":")[-1] or 0)
    days = [d for d in get_next_11_days_status(lang=lang) if int((d.get("date")).weekday()) != 6]
    if idx < 0 or idx >= len(days):
        await callback.answer(t(lang, "admin_cancel_lessons_invalid"), show_alert=True)
        return
    day = days[idx]
    date_str = str(day["date_str"])
    c1 = is_branch_date_closed_for_booking("branch_1", date_str)
    c2 = is_branch_date_closed_for_booking("branch_2", date_str)
    if c1 or c2:
        state = get_admin_state(callback.message.chat.id)
        state["step"] = "admin_otmen_reopen_confirm"
        state["data"]["otmen_reopen_date"] = date_str
        rs = get_branch_date_closed_reason("branch_1", date_str) or get_branch_date_closed_reason("branch_2", date_str) or t(lang, "admin_cancel_lessons_default_reason")
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=t(lang, "admin_cancel_lessons_reopen_confirm_btn"), callback_data="admin_otmen_reopen_confirm")],
                [InlineKeyboardButton(text=t(lang, "admin_cancel_lessons_deny_btn"), callback_data="admin_otmen_cancel")],
            ]
        )
        await callback.message.answer(
            t(
                lang,
                "admin_cancel_lessons_reopen_prompt",
                date=day["date_ui"],
                weekday=day["weekday"],
                reason=rs,
            ),
            reply_markup=kb,
            parse_mode="HTML",
        )
        await callback.answer()
        return
    req_id = _ensure_otmen_request_for_day(day["date_str"], day["reason_db"])
    if not req_id:
        await callback.answer(t(lang, "admin_cancel_lessons_invalid"), show_alert=True)
        return
    state = get_admin_state(callback.message.chat.id)
    state["step"] = "admin_otmen_confirm"
    state["data"]["otmen_req_id"] = req_id
    state["data"]["otmen_date_ui"] = day["date_ui"]
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "admin_cancel_lessons_confirm_btn"), callback_data="admin_otmen_confirm")],
            [InlineKeyboardButton(text=t(lang, "admin_cancel_lessons_deny_btn"), callback_data="admin_otmen_cancel")],
        ]
    )
    await callback.message.answer(
        t(lang, "admin_cancel_lessons_confirm_prompt", date=day["date_ui"], weekday=day["weekday"], reason=day["reason"]),
        reply_markup=kb,
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data == "admin_otmen_cancel")
async def admin_otmen_cancel(callback: CallbackQuery):
    lang = _admin_lang_from_callback(callback)
    reset_admin_state(callback.message.chat.id)
    await callback.answer()
    await callback.message.answer(t(lang, "operation_cancelled"))


@dp.callback_query(lambda c: c.data == "admin_otmen_confirm")
async def admin_otmen_confirm(callback: CallbackQuery):
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    lang = _admin_lang_from_callback(callback)
    state = get_admin_state(callback.message.chat.id)
    req_id = (state.get("data") or {}).get("otmen_req_id")
    if not req_id:
        await callback.answer(t(lang, "admin_cancel_lessons_invalid"), show_alert=True)
        return
    state["step"] = "admin_otmen_reason"
    await callback.answer()
    await callback.message.answer(t(lang, "admin_cancel_lessons_reason_prompt"))


@dp.callback_query(lambda c: c.data == "admin_otmen_reopen_confirm")
async def admin_otmen_reopen_confirm(callback: CallbackQuery):
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    lang = _admin_lang_from_callback(callback)
    state = get_admin_state(callback.message.chat.id)
    date_str = str((state.get("data") or {}).get("otmen_reopen_date") or "")
    if not date_str:
        await callback.answer(t(lang, "admin_cancel_lessons_invalid"), show_alert=True)
        return
    open_branch_date_for_booking("branch_1", date_str)
    open_branch_date_for_booking("branch_2", date_str)
    still_closed = is_branch_date_closed_for_booking("branch_1", date_str) or is_branch_date_closed_for_booking("branch_2", date_str)
    reset_admin_state(callback.message.chat.id)
    await callback.answer()
    if still_closed:
        await callback.message.answer(t(lang, "operation_failed"))
    else:
        await callback.message.answer(t(lang, "admin_cancel_lessons_reopen_done", date=date_str))


async def _execute_otmen_request(req_id: str, admin_user: dict, lang: str, reason_override: str | None = None) -> tuple[bool, str]:
    req = get_lesson_otmen_request(req_id)
    if not req:
        return False, t(lang, "admin_cancel_lessons_invalid")
    if (req.get("status") or "") == "cancelled":
        return False, t(lang, "admin_cancel_lessons_already_done")
    if (req.get("status") or "") == "expired":
        return False, t(lang, "admin_cancel_lessons_expired")

    date_str = str(req.get("date_str"))
    expires_at = str(req.get("expires_at") or "")
    try:
        exp = datetime.fromisoformat(expires_at)
    except Exception:
        exp = None
    now_tz = datetime.now(pytz.timezone("Asia/Tashkent"))
    if exp and now_tz > exp:
        mark_lesson_otmen_request_status(req_id, "expired", admin_id=admin_user.get("id"))
        return False, t(lang, "admin_cancel_lessons_expired")

    groups = _groups_scheduled_for_date(date_str)
    conn = get_conn()
    cur = conn.cursor()
    blocked = False
    try:
        for g in groups:
            cur.execute("SELECT id, status FROM attendance_sessions WHERE group_id=? AND date=?", (g["id"], date_str))
            row = cur.fetchone()
            if not row:
                continue
            if str(row.get("status") or "") == "closed":
                blocked = True
                break
    finally:
        conn.close()
    if blocked:
        return False, t(lang, "admin_cancel_lessons_closed_block", date=date_str)

    sessions_count = 0
    if groups:
        conn = get_conn()
        cur = conn.cursor()
        try:
            for g in groups:
                cur.execute("DELETE FROM attendance WHERE group_id=? AND date=?", (g["id"], date_str))
                cur.execute(
                    "UPDATE attendance_sessions SET status='closed', closed_at=CURRENT_TIMESTAMP WHERE group_id=? AND date=?",
                    (g["id"], date_str),
                )
                if cur.rowcount > 0:
                    sessions_count += int(cur.rowcount)
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
        finally:
            conn.close()

    bookings = list_lesson_bookings_by_date(date_str, statuses=("pending", "approved"))
    booking_count = 0
    for b in bookings:
        if set_lesson_booking_status(str(b.get("id")), "canceled", admin_id=int(admin_user.get("id") or 0), admin_note="holiday_otmen"):
            booking_count += 1
            tg = b.get("student_telegram_id")
            if tg:
                stu = get_user_by_id(int(b.get("student_user_id") or 0)) if b.get("student_user_id") else None
                try:
                    await student_notify_bot.send_message(
                        int(tg),
                        t(detect_lang_from_user(stu or {"language": "uz"}), "support_student_canceled_by_admin"),
                    )
                except Exception:
                    pass

    # Close support booking date for both branches so no new support bookings
    # can be created for this cancelled day.
    close_b1 = set_branch_date_closed("branch_1", date_str, "holiday_otmen")
    close_b2 = set_branch_date_closed("branch_2", date_str, "holiday_otmen")
    _flow_msg = f"otmen support close date branch_1={close_b1} branch_2={close_b2} date={date_str}"
    logger.info(_flow_msg)

    # Requirement: Arena/Duel/Daily/Vocabulary must remain untouched.
    arena_count = 0

    reason = (reason_override or req.get("reason") or t(lang, "admin_cancel_lessons_default_reason")).strip()
    for g in groups:
        teacher = get_user_by_id(g.get("teacher_id")) if g.get("teacher_id") else None
        if teacher and teacher.get("telegram_id"):
            try:
                await bot.send_message(
                    int(teacher["telegram_id"]),
                    t(detect_lang_from_user(teacher), "admin_cancel_lessons_notify_teacher", date=date_str, reason=reason),
                )
            except Exception:
                pass
        for u in get_group_users(g["id"]):
            if int(u.get("login_type") or 0) not in (1, 2):
                continue
            tg = u.get("telegram_id")
            if not tg:
                continue
            try:
                await bot.send_message(
                    int(tg),
                    t(detect_lang_from_user(u), "admin_cancel_lessons_notify_student", date=date_str, reason=reason),
                )
            except Exception:
                pass

    mark_lesson_otmen_request_status(req_id, "cancelled", admin_id=admin_user.get("id"))
    stats = _cancel_lessons_stats_text(
        lang,
        groups=len(groups),
        sessions=sessions_count,
        bookings=booking_count,
    ) + "\n" + t(lang, "admin_cancel_lessons_stats_arena", arena=arena_count)
    return True, t(lang, "admin_cancel_lessons_done", date=date_str, stats=stats)


@dp.callback_query(lambda c: bool(c.data) and c.data.startswith("cancel_day:"))
async def handle_cancel_specific_day(callback: CallbackQuery):
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    lang = _admin_lang_from_callback(callback)
    req_id = (callback.data or "").split(":", 1)[-1]
    ok, msg = await _execute_otmen_request(req_id=req_id, admin_user={"id": callback.from_user.id}, lang=lang)
    if not ok:
        await callback.answer(msg, show_alert=True)
        return
    await callback.message.answer(msg, parse_mode="HTML")
    await callback.answer(t(lang, "btn_ok"))

def _to_lesson_days_text(days: str, lang: str = "uz") -> str:
    """Convert lesson days code to i18n label."""
    if not days:
        return days
    d = (days or "").strip().upper()
    if d == 'MWF':
        return t(lang, 'admin_days_mwf_label')
    if d == 'TTS':
        return t(lang, 'admin_days_tts_label')
    return days


async def show_students_list(message: Message, page: int = 0, search_query: str = ""):
    """Admin uchun chiroyli Students List"""
    state = get_admin_state(message.chat.id)
    state['step'] = 'students_list_view'
    state['data']['students_page'] = page
    state['data']['students_search'] = search_query

    lang = _admin_lang_from_message(message)
    admin_id = message.from_user.id
    all_users = get_all_users()
    all_users = _scope_users_for_admin(admin_id, all_users, login_type_filter=(1, 2))

    # Scope already applied:
    # - general admins: full list
    # - limited admins: own + shared students
    # Keep records visible even if not activated yet.
    
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

    total_pages = max(1, (total + per_page - 1) // per_page) if total else 1

    text = t(lang, "admin_students_list_title_with_page", page=page + 1, total=total_pages)

    keyboard = []
    row = []

    for i, student in enumerate(students, start=1):
        # Ma'lumotlarni boyitish
        subjects = get_student_subjects(student['id']) or ['—']
        teachers = get_student_teachers(student['id'])
        groups = get_user_groups(student['id'])
        try:
            diamonds = get_dcoins(student['id'])
        except Exception:
            logger.exception("get_dcoins failed for student_id=%s in show_students_list; using 0.0", student.get("id"))
            diamonds = 0.0

        teacher_names = ", ".join([f"{t['first_name']} {t['last_name']}" for t in teachers]) if teachers else "—"
        levels_line = _subject_levels_summary(student["id"], subjects)
        
        group_info = []
        for g in groups:
            days = _to_lesson_days_text(g.get('lesson_date', '—'), lang=lang)
            time = f"{g.get('lesson_start','?')[:5]}-{g.get('lesson_end','?')[:5]}"
            group_info.append(f"{g['name']} ({days} {time})")
        
        group_str = "\n   ".join(group_info) if group_info else "—"

        # Chiroyli blok
        text += (
            f"<b>{start + i}.</b> {student['first_name']} {student['last_name']}\n"
            f"   📚 {t(lang, 'admin_student_list_label_subject')}: {', '.join(subjects)}\n"
            f"   🎯 {t(lang, 'profile_subjects_levels_line')}: {levels_line}\n"
            f"   👨‍🏫 {t(lang, 'admin_student_list_label_teacher')}: {teacher_names}\n"
            f"   👥 {t(lang, 'admin_student_list_label_group')}: {group_str}\n"
            f"   💎 {t(lang, 'admin_student_list_label_dcoin')}: {diamonds}\n\n"
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
        nav.append(InlineKeyboardButton(text=t(lang, 'btn_prev'), callback_data=f"students_page_{page-1}"))
    if end < total:
        nav.append(InlineKeyboardButton(text=t(lang, 'btn_next'), callback_data=f"students_page_{page+1}"))
    
    if nav:
        keyboard.append(nav)
    keyboard.append([InlineKeyboardButton(text=t(lang, 'admin_btn_search_by_name'), callback_data="students_search_start")])
    keyboard.append([InlineKeyboardButton(text=t(lang, 'admin_btn_main_menu'), callback_data="admin_back_to_main")])

    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode='HTML')


async def run_admin_bot():
    global bot, student_notify_bot
    print("[STARTUP] admin_bot run_admin_bot() starting")
    if not ADMIN_BOT_TOKEN:
        raise RuntimeError("ADMIN_BOT_TOKEN is not set. Put it in .env (ADMIN_BOT_TOKEN=...) and retry.")
    if not STUDENT_BOT_TOKEN:
        raise RuntimeError("STUDENT_BOT_TOKEN is not set. Put it in .env (STUDENT_BOT_TOKEN=...) and retry.")
    bot = create_resilient_bot(ADMIN_BOT_TOKEN)
    student_notify_bot = create_resilient_bot(STUDENT_BOT_TOKEN)
    set_attendance_student_notify_bot(student_notify_bot)
    setup_admin_bot()
    print("[STARTUP] admin_bot setup_admin_bot() done")

    # Ensure D'coin schema before handlers start serving requests.
    try:
        ensure_subject_dcoin_schema()
        ensure_dcoin_schema_migrations()
        logger.info("D'coin schema ensured for admin bot startup")
    except Exception:
        logger.exception("Failed to ensure D'coin schema on admin startup")
    if not validate_dcoin_runtime_ready(context="admin_bot startup"):
        raise RuntimeError("Admin bot startup aborted: D'coin runtime schema is not ready")
    print("[STARTUP] admin_bot validate_dcoin_runtime_ready() ok")
    
    # Restore user sessions after bot restart
    try:
        restored_count = restore_sessions_on_startup()
        logger.info(f"🔄 Restored login sessions for {restored_count} users")
    except Exception as e:
        logger.error(f"Error restoring user sessions: {e}")
    
    # Attendance scheduler (Toshkent time)
    spawn_guarded_task(attendance_scheduler(bot, role="admin", admin_chat_ids=ALL_ADMIN_IDS), name="admin_attendance_scheduler")
    spawn_guarded_task(monthly_payment_scheduler(student_notify_bot), name="admin_monthly_payment_scheduler")
    spawn_guarded_task(overdue_penalty_scheduler(), name="admin_overdue_penalty_scheduler")
    
    logger.info("Admin bot started successfully")
    await run_bot_dispatcher(dp=dp, bot=bot, bot_name="admin", webhook_port=ADMIN_WEBHOOK_PORT)


@dp.error()
async def error_handler(event: types.ErrorEvent):
    """Global error handler for admin bot"""
    exc = event.exception
    logger.error(f"Error in admin bot: {exc}", exc_info=True)

    # 1) Write to log.txt (requested by admin for debugging)
    try:
        log_file = Path(__file__).resolve().parent / "log.txt"
        stack = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        with open(log_file, "a", encoding="utf-8") as f:
            f.write("\n" + "=" * 80 + "\n")
            f.write(f"Admin bot error: {repr(exc)}\n")
            f.write(stack)
            f.write("\n")
    except Exception:
        logger.exception("Failed to write admin bot error to log.txt")

    # 2) Notify admins (best-effort)
    try:
        if bot:
            update_info = getattr(event, "update", None)
            update_id = getattr(update_info, "update_id", None)
            short = f"Admin bot xatolik: {repr(exc)}"
            if update_id is not None:
                short += f" (update_id={update_id})"
            for aid in ADMIN_CHAT_IDS:
                await bot.send_message(int(aid), short)
    except Exception:
        logger.exception("Failed to notify admins about admin bot error")


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
    if bot is None:
        return
    setup_broadcast_handlers(dp, bot)


# === NEW GROUP CREATION FLOW (with teacher selection) ===
@dp.callback_query(lambda c: c.data == "group_create")
async def handle_group_create_start(callback: CallbackQuery):
    state = get_admin_state(callback.message.chat.id)
    lang = detect_lang_from_user(callback.from_user)
    state['step'] = 'ask_group_name'
    state['data'] = {}
    await callback.message.answer(t(lang, 'admin_auto_msg_46'), reply_markup=cancel_keyboard(lang))
    await callback.answer()


@dp.message(lambda m: get_admin_state(m.chat.id).get('step') == 'search_group_students')
async def handle_group_student_search_input(message: Message):
    """Handle search input for group students"""
    state = get_admin_state(message.chat.id)
    search_query = message.text.strip()
    state['data']['search_query'] = search_query
    state['data']['students_page'] = 0  # Reset to first page
    
    group_id = state['data']['group_id']
    mode = state['data'].get('group_student_ui_mode', 'add')
    if mode == 'remove':
        state['step'] = 'remove_student_from_group'
        await show_group_student_list_by_message(message, group_id, remove_mode=True)
    elif mode == 'teacher':
        state['step'] = 'edit_group_teacher'
        await show_group_student_list_by_message(message, group_id, show_for_teacher_change=True)
    else:
        state['step'] = 'add_student_to_group'
        await show_group_student_list_by_message(message, group_id)


async def show_group_student_list_by_message(message: Message, group_id: int, remove_mode: bool = False, show_for_teacher_change: bool = False):
    """Show group student list as a new message (for search results)"""
    state = get_admin_state(message.chat.id)
    lang = _admin_lang_from_message(message)
    admin_id = message.from_user.id
    search_query = state['data'].get('search_query', '')
    page = state['data'].get('students_page', 0)
    
    students = _students_for_group_picker(admin_id, search_query)
    
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
        title += t(lang, "admin_group_search_suffix", query=search_query)
    
    text = f"{title}\n\n"
    
    for i, student in enumerate(chunk, start=1):
        in_group_indicator = " ✅" if student['in_group'] else ""
        full_name = f"{student.get('first_name', '').strip()} {student.get('last_name', '').strip()}".strip()
        full_name = full_name or "—"
        text += (
            f"{i}. {full_name}{in_group_indicator}\n"
            f"   📚 {student.get('subject') or '—'}\n"
            f"   📱 {student.get('phone', '—') or '—'}\n"
            f"   🔑 {student.get('login_id', '—') or '—'}\n\n"
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
        nav_buttons.append(InlineKeyboardButton(text=t(lang, 'admin_btn_search_fullname'), callback_data=f"grp_search_students:{group_id}:name"))
    else:
        nav_buttons.append(InlineKeyboardButton(text=t(lang, 'admin_btn_search_fullname'), callback_data=f"grp_search_students:{group_id}:name"))
    
    # Pagination buttons
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text=t(lang, 'btn_prev'), callback_data=f"grp_students_page:{group_id}:{page-1}"))
    
    if end < total:
        nav_buttons.append(InlineKeyboardButton(text=t(lang, 'btn_next_arrow'), callback_data=f"grp_students_page:{group_id}:{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Back button
    keyboard.append([InlineKeyboardButton(text=t(lang, 'btn_back'), callback_data=f"group_detail_{group_id}")])
    
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")


@dp.message(lambda m: get_admin_state(m.chat.id).get('step') == 'ask_group_name')
async def handle_group_name(message: Message):
    state = get_admin_state(message.chat.id)
    lang = _admin_lang_from_message(message)
    state['data']['name'] = message.text.strip()
    state['step'] = 'ask_group_subject'
    await message.answer(t(lang, 'ask_group_subject'), reply_markup=_group_subject_keyboard(lang))


@dp.message(lambda m: get_admin_state(m.chat.id).get('step') == 'ask_group_level')
async def handle_group_level(message: Message):
    state = get_admin_state(message.chat.id)
    lang = _admin_lang_from_message(message)
    raw_level = message.text.strip()
    localized = {
        t(lang, "level_name_a1"): "A1",
        t(lang, "level_name_a2"): "A2",
        t(lang, "level_name_b1"): "B1",
        t(lang, "level_name_b2"): "B2",
        t(lang, "level_name_c1"): "C1",
    }
    level = localized.get(raw_level, raw_level.upper())
    if not level or not re.match(r'^[A-C][1-2]$', level):
        await message.answer(t(lang, 'group_level_invalid'))
        return

    state['data']['level'] = level
    state['step'] = 'ask_group_days'
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, 'admin_btn_lesson_days_mwf'), callback_data="group_days:MWF")],
        [InlineKeyboardButton(text=t(lang, 'admin_btn_lesson_days_tts'), callback_data="group_days:TTS")],
        [InlineKeyboardButton(text=t(lang, 'btn_cancel'), callback_data="cancel_group_creation")],
    ])
    await message.answer(t(lang, 'ask_group_days'), reply_markup=kb)


@dp.callback_query(lambda c: c.data.startswith("grp_subject_"))
async def handle_group_subject_pick_for_creation(callback: CallbackQuery):
    state = get_admin_state(callback.message.chat.id)
    if state.get('step') != 'ask_group_subject':
        await callback.answer()
        return
    lang = detect_lang_from_user(callback.from_user)
    subject = callback.data.split("_", 2)[2].strip().title()
    if subject not in ("English", "Russian"):
        await callback.answer(t(lang, "invalid_subject"), show_alert=True)
        return
    state['data']['subject'] = subject
    state['step'] = 'ask_group_level'
    kb = _group_level_keyboard_for_subject(subject, lang)
    ask = t(lang, 'ask_group_level_by_subject', subject=subject)
    try:
        await callback.message.edit_text(ask, reply_markup=kb)
    except Exception:
        await callback.message.answer(ask, reply_markup=kb)
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("group_level_pick:"))
async def handle_group_level_pick(callback: CallbackQuery):
    state = get_admin_state(callback.message.chat.id)
    step = state.get('step')
    if step not in ('ask_group_level', 'edit_group_level'):
        await callback.answer()
        return
    lang = detect_lang_from_user(callback.from_user)
    raw = callback.data.split(":", 1)[1].strip()
    if step == 'edit_group_level':
        gid = state['data'].get('edit_group_id')
        if not gid:
            await callback.answer()
            return
        grp = get_group(int(gid))
        subj = (grp.get('subject') or '') if grp else ''
    else:
        subj = (state.get("data") or {}).get("subject") or ""
    if subj.strip().title() == "Russian":
        from db import normalize_russian_group_level

        level = normalize_russian_group_level(raw)
        if not level:
            await callback.answer(t(lang, 'group_level_invalid'), show_alert=True)
            return
    else:
        level = raw.upper()
        if level not in ("A1", "A2", "B1", "B2", "C1"):
            await callback.answer(t(lang, 'group_level_invalid'), show_alert=True)
            return
    if step == 'edit_group_level':
        update_group_level(int(gid), level, sync_students=True)
        await callback.message.answer(t(lang, 'group_level_updated'))
        reset_admin_state(callback.message.chat.id)
        await callback.answer()
        return
    state['data']['level'] = level
    state['step'] = 'ask_group_days'
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, 'admin_btn_lesson_days_mwf'), callback_data="group_days:MWF")],
        [InlineKeyboardButton(text=t(lang, 'admin_btn_lesson_days_tts'), callback_data="group_days:TTS")],
        [InlineKeyboardButton(text=t(lang, 'btn_cancel'), callback_data="cancel_group_creation")],
    ])
    await callback.message.answer(t(lang, 'ask_group_days'), reply_markup=kb)
    await callback.answer()


# Teacher tanlash
@dp.callback_query(lambda c: c.data.startswith("group_teacher_select_"))
async def handle_group_teacher_select(callback: CallbackQuery):
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    teacher_id = int(callback.data.split("_")[-1])
    state = get_admin_state(callback.message.chat.id)
    
    group_id = state.get('data', {}).get('group_id') or state.get('data', {}).get('edit_group_id')
    
    if group_id:                     # ← mavjud guruh
        from db import update_group_teacher, update_group_subject
        teacher = get_user_by_id(teacher_id)
        update_group_teacher(group_id, teacher_id)
        lang = detect_lang_from_user(callback.from_user)
        if teacher:
            subj = (teacher.get('subject') or '').title()
            if subj:
                update_group_subject(int(group_id), subj)
            teacher_name = f"{teacher.get('first_name','')} {teacher.get('last_name','')}".strip()
        else:
            teacher_name = t(lang, "admin_unknown_teacher_label")
        await callback.message.edit_text(
            t(lang, "admin_teacher_assigned_to_group_confirm", teacher_name=teacher_name)
        )
        # state ni tozalash
        state['data'].pop('group_id', None)
        state['data'].pop('edit_group_id', None)
        state['step'] = None
    else:                            # ← yangi guruh
        state['data']['teacher_id'] = teacher_id
        await create_group_from_state(callback.message, state, owner_admin_id=callback.from_user.id)
    
    await callback.answer()


async def ask_group_teacher(message: Message, lang: str, state: dict):
    """Ask for teacher selection during group creation"""
    teachers = get_all_teachers()
    buttons = []
    for teacher in teachers:
        buttons.append([InlineKeyboardButton(
            text=f"👨‍🏫 {teacher['first_name']} {teacher['last_name']}", 
            callback_data=f"set_group_teacher_{teacher['id']}"
        )])
    
    # Add option to create without teacher
    buttons.append([InlineKeyboardButton(
        text=t(lang, "admin_btn_create_without_teacher"),
        callback_data="create_group_no_teacher"
    )])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    state['step'] = 'ask_teacher_for_group'
    await message.answer(t(lang, 'admin_auto_msg_49'), reply_markup=keyboard)


@dp.callback_query(lambda c: c.data.startswith("set_group_teacher_"))
async def save_group_with_teacher(callback: CallbackQuery):
    data = callback.data.split('_')
    teacher_id = int(data[-1])
    state = get_admin_state(callback.message.chat.id)
    
    # Set teacher for new group
    state['data']['teacher_id'] = teacher_id
    state['step'] = None
    
    # Create the group with teacher
    await create_group_from_state(callback.message, state, owner_admin_id=callback.from_user.id)
    
    # Get teacher name for confirmation
    teacher = get_user_by_id(teacher_id)
    lang = detect_lang_from_user(callback.from_user)
    if teacher:
        teacher_name = f"{teacher.get('first_name','')} {teacher.get('last_name','')}".strip()
    else:
        teacher_name = t(lang, "admin_unknown_teacher_label")

    await callback.answer(
        t(lang, "admin_teacher_assigned_to_group_callback", teacher_name=teacher_name)
    )


@dp.callback_query(lambda c: c.data == "create_group_no_teacher")
async def handle_group_no_teacher(callback: CallbackQuery):
    state = get_admin_state(callback.message.chat.id)
    state['data']['teacher_id'] = None
    state['step'] = None
    await create_group_from_state(callback.message, state, owner_admin_id=callback.from_user.id)
    await callback.answer()


async def create_group_from_state(message: Message, state: dict, owner_admin_id: int | None = None):
    data = state['data']
    lang = _admin_lang_from_message(message)
    if not data.get('name') or not data.get('level'):
        await message.answer(t(lang, 'admin_auto_msg_50'))
        return

    owner_admin_id = owner_admin_id if owner_admin_id is not None else message.from_user.id

    group_id = create_group(
        name=data['name'],
        teacher_id=data.get('teacher_id'),
        level=data['level'],
        subject=data.get('subject', 'English'),
        lesson_date=data.get('lesson_date', 'MWF'),
        lesson_start=data.get('lesson_start', '14:00'),
        lesson_end=data.get('lesson_end', '15:00'),
        tz='Asia/Tashkent',
        owner_admin_id=owner_admin_id,
    )

    teacher_name = t(lang, "none_short")
    if data.get('teacher_id'):
        teacher = get_user_by_id(data['teacher_id'])
        if teacher:
            teacher_name = f"{teacher.get('first_name','')} {teacher.get('last_name','')}".strip()
    await message.answer(
        t(
            lang,
            "admin_group_created_detailed",
            group_id=group_id,
            name=data['name'],
            level=data['level'],
            teacher_name=teacher_name,
        )
    )
    reset_admin_state(message.chat.id)


# ==================== O'QITUVCHINI ALMASHTIRISH ====================
@dp.callback_query(lambda c: c.data.startswith("group_edit_teacher_"))
async def handle_group_edit_teacher(callback: CallbackQuery):
    group_id = int(callback.data.split("_")[-1])
    admin_id = callback.from_user.id
    lang = detect_lang_from_user(callback.from_user)
    group = get_group(group_id)
    if not group:
        await callback.answer(t(lang, 'admin_auto_msg_42'))
        return
    if not _can_manage_group(admin_id, group):
        await callback.answer(t(lang, 'admin_auto_msg_20'), show_alert=True)
        return
    
    # ← BU QATORLARNI QO'SHING
    state = get_admin_state(callback.message.chat.id)
    state['data']['group_id'] = group_id   # <--- muhim!
    
    teachers = get_all_teachers()
    kb = create_group_teacher_selection_keyboard(teachers, lang)
    await callback.message.edit_text(t(lang, 'admin_auto_msg_59'), reply_markup=kb)
    await callback.answer()


# ==================== YANGI O'QUVCHI QO'SHISH ====================
@dp.callback_query(lambda c: c.data.startswith("group_add_student_"))
async def handle_group_add_student(callback: CallbackQuery):
    group_id = int(callback.data.split("_")[-1])
    admin_id = callback.from_user.id
    lang = detect_lang_from_user(callback.from_user)
    group = get_group(group_id)
    if not group:
        await callback.answer(t(lang, 'admin_auto_msg_42'))
        return
    if not _can_manage_group(admin_id, group):
        await callback.answer(t(lang, 'admin_auto_msg_20'), show_alert=True)
        return
    state = get_admin_state(callback.message.chat.id)
    state['adding_to_group'] = group_id
    state['step'] = 'add_student_to_group'
    state.setdefault('data', {})['group_id'] = group_id
    state['data']['students_page'] = 0
    state['data']['search_query'] = ""

    # Hozirgi guruhda bo'lmagan, admin scope ichidagi o'quvchilarni ko'rsatamiz
    all_users = _scope_users_for_admin(admin_id, get_all_users(), login_type_filter=(1, 2))
    group_users = {u['id'] for u in get_group_users(group_id)}
    available = [u for u in all_users if u['id'] not in group_users]

    if not available:
        await callback.message.edit_text(t(lang, 'admin_auto_msg_60'))
        await callback.answer()
        return

    await show_group_student_list(callback, group_id)
    await callback.answer()


# ==================== O'QUVCHINI CHIQARIB YUBORISH ====================
@dp.callback_query(lambda c: c.data.startswith("group_remove_student_"))
async def handle_group_remove_student(callback: CallbackQuery):
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    group_id = int(callback.data.split("_")[-1])
    admin_id = callback.from_user.id
    lang = detect_lang_from_user(callback.from_user)
    group = get_group(group_id)
    if not group:
        await callback.answer(t(lang, 'admin_auto_msg_42'))
        return
    if not _can_manage_group(admin_id, group):
        await callback.answer(t(lang, 'admin_auto_msg_20'), show_alert=True)
        return
    students = get_group_users(group_id)

    if not students:
        await callback.message.edit_text(t(lang, 'admin_auto_msg_61'))
        await callback.answer()
        return

    state = get_admin_state(callback.message.chat.id)
    state['step'] = 'remove_student_from_group'
    state.setdefault('data', {})['group_id'] = group_id
    state['data']['students_page'] = 0
    state['data']['search_query'] = ""
    await show_group_student_list(callback, group_id, remove_mode=True)
    await callback.answer()


# ==================== USER GROUP MANAGEMENT ====================
def _parse_two_ids_after_prefix(data: str, prefix: str) -> tuple[int, int] | None:
    """<prefix><group_id>_<user_id> — last underscore separates ids."""
    if not data.startswith(prefix):
        return None
    rest = data[len(prefix):]
    last_us = rest.rfind("_")
    if last_us <= 0:
        return None
    try:
        return int(rest[:last_us]), int(rest[last_us + 1:])
    except ValueError:
        return None


@dp.callback_query(lambda c: c.data.startswith("add_user_to_group_"))
async def handle_add_user_to_group(callback: CallbackQuery):
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    lang = detect_lang_from_user(callback.from_user)
    parsed = _parse_two_ids_after_prefix(callback.data, "add_user_to_group_")
    if not parsed:
        await callback.answer(t(lang, 'admin_auto_msg_51'))
        return
    group_id, user_id = parsed

    admin_id = callback.from_user.id
    if _is_limited_admin(admin_id):
        student = get_user_by_id(user_id)
        group = get_group(group_id)
        if not _can_manage_user(admin_id, student) or not _can_manage_group(admin_id, group):
            await callback.answer(t(lang, 'admin_auto_msg_20'), show_alert=True)
            return
    add_user_to_group(user_id, group_id)
    await _notify_student_group_assigned(user_id, group_id)
    await callback.answer(t(lang, 'admin_auto_msg_52'))
    await handle_group_select(callback)


@dp.callback_query(lambda c: c.data.startswith("remove_user_from_group_"))
async def handle_remove_user_from_group(callback: CallbackQuery):
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    lang = detect_lang_from_user(callback.from_user)
    parsed = _parse_two_ids_after_prefix(callback.data, "remove_user_from_group_")
    if not parsed:
        await callback.answer(t(lang, 'admin_auto_msg_51'))
        return
    group_id, user_id = parsed

    admin_id = callback.from_user.id
    if _is_limited_admin(admin_id):
        student = get_user_by_id(user_id)
        group = get_group(group_id)
        if not _can_manage_user(admin_id, student) or not _can_manage_group(admin_id, group):
            await callback.answer(t(lang, 'admin_auto_msg_20'), show_alert=True)
            return
    remove_user_from_group(user_id, group_id)
    await callback.answer(t(lang, 'admin_auto_msg_16'))
    await handle_group_select(callback)


async def show_group_student_list_for_remove(message: Message, group_id: int):
    lang = _admin_lang_from_message(message)
    students = get_group_users(group_id)
    if not students:
        await message.edit_text(t(lang, 'admin_auto_msg_62'))
        return
    kb = []
    for u in students:
        kb.append([InlineKeyboardButton(
            text=f"{u['first_name']} {u['last_name']} ({u.get('login_id','')})",
            callback_data=f"grp_remove_student:{group_id}:{u['id']}"
        )])
    await message.edit_text(t(lang, 'admin_auto_msg_63'), reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


async def show_group_student_list_for_add(message: Message, group_id: int):
    lang = _admin_lang_from_message(message)
    admin_id = message.from_user.id
    all_students = _scope_users_for_admin(
        admin_id,
        get_all_users(),
        login_type_filter=(1, 2),
    )
    group_ids = {u['id'] for u in get_group_users(group_id)}
    available = [u for u in all_students if u['id'] not in group_ids]

    if not available:
        await message.edit_text(t(lang, 'admin_auto_msg_64'))
        return

    kb = []
    for u in available[:20]:
        kb.append([InlineKeyboardButton(
            text=f"{u['first_name']} {u['last_name']}",
            callback_data=f"grp_add_student:{group_id}:{u['id']}"
        )])
    await message.edit_text(t(lang, 'admin_auto_msg_65'), reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


# ====================== TEACHERS LIST ======================
async def show_teachers_list(message: Message, page: int = 0, search_query: str = ""):
    """Chiroyli Teachers List (siz xohlagan formatda)"""
    lang = _admin_lang_from_message(message)
    state = get_admin_state(message.chat.id)
    state['step'] = 'teachers_list_view'
    state['data']['teachers_page'] = page
    state['data']['teachers_search'] = search_query

    admin_id = message.from_user.id
    teachers = _scope_users_for_admin(admin_id, get_all_teachers(), login_type_filter=(3,))

    # Hide soft-deleted profiles from the list view.
    if admin_id not in ADMIN_CHAT_IDS:
        teachers = [
            t
            for t in teachers
            if (t.get("telegram_id") is not None) and bool(t.get("access_enabled"))
        ]
    
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

    total_pages = max(1, (total + per_page - 1) // per_page) if total else 1
    text = t(lang, "admin_teachers_list_title_with_page", page=page + 1, total=total_pages) + "\n\n"

    keyboard = []
    row = []

    for i, teacher in enumerate(current_teachers, start=1):
        groups_count = get_teacher_groups_count(teacher['id'])
        students_count = get_teacher_total_students(teacher['id'])
        status_label = t(lang, "admin_status_blocked_label") if teacher.get("blocked") else t(lang, "admin_teacher_status_active_label")
        
        text += (
            f"<b>{start + i}.</b> {teacher['first_name']} {teacher['last_name']}\n"
            f"   📚 {t(lang, 'admin_teacher_list_label_subject')}: {teacher.get('subject', '—')}\n"
            f"   📞 {t(lang, 'admin_teacher_list_label_phone')}: {teacher.get('phone', '—')}\n"
            f"   🔑 {t(lang, 'admin_teacher_list_label_login')}: {teacher['login_id']}\n"
            f"   🛡 {t(lang, 'admin_teacher_list_label_status')}: {status_label}\n"
            f"   👥 {t(lang, 'admin_teacher_list_label_groups_students', groups=groups_count, students=students_count)}\n\n"
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
        nav.append(InlineKeyboardButton(text=t(lang, 'btn_prev'), callback_data=f"teachers_page_{page-1}"))
    if end < total:
        nav.append(InlineKeyboardButton(text=t(lang, 'btn_next_arrow'), callback_data=f"teachers_page_{page+1}"))
    
    if nav:
        keyboard.append(nav)
    keyboard.append([InlineKeyboardButton(text=t(lang, 'admin_btn_search_by_name'), callback_data="teachers_search_start")])
    keyboard.append([InlineKeyboardButton(text=t(lang, 'admin_btn_main_menu'), callback_data="admin_back_to_main")])

    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode='HTML')


# Qidiruvni boshlash
@dp.callback_query(lambda c: c.data == "teachers_search_start")
async def handle_teachers_search_start(callback: CallbackQuery):
    state = get_admin_state(callback.message.chat.id)
    state['step'] = 'teachers_search'
    lang = _admin_lang_from_callback(callback)
    await callback.message.answer(t(lang, 'admin_auto_msg_13'),
                                 reply_markup=cancel_keyboard(lang))
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
    lang = _admin_lang_from_callback(callback)

    if not teacher:
        await callback.answer(t(lang, 'admin_auto_msg_53'))
        return

    text, keyboard = build_admin_teacher_detail_reply(teacher, lang)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("teacher_delete_profile_") and "confirm_" not in (c.data or ""))
async def handle_teacher_delete_profile_prompt(callback: CallbackQuery):
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    lang = _admin_lang_from_callback(callback)
    teacher_id = int(callback.data.split("_")[-1])
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_yes"), callback_data=f"teacher_delete_profile_confirm_yes_{teacher_id}")],
            [InlineKeyboardButton(text=t(lang, "btn_no"), callback_data=f"teacher_delete_profile_confirm_no_{teacher_id}")],
        ]
    )
    await callback.message.answer(t(lang, "admin_confirm_delete_teacher_profile"), reply_markup=kb)
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("teacher_delete_profile_confirm_yes_"))
async def handle_teacher_delete_profile_yes(callback: CallbackQuery):
    if callback.from_user.id not in ALL_ADMIN_IDS:
        await callback.answer()
        return
    lang = _admin_lang_from_callback(callback)
    teacher_id = int(callback.data.split("_")[-1])
    teacher = get_user_by_id(teacher_id)
    if not teacher:
        await callback.answer(t(lang, 'admin_auto_msg_53'), show_alert=True)
        return
    if not _can_manage_user(callback.from_user.id, teacher):
        await callback.answer(t(lang, 'permission_denied_short'), show_alert=True)
        return
    from db import hard_delete_user_profile
    ok = hard_delete_user_profile(teacher_id)
    await callback.message.answer(t(lang, "admin_teacher_profile_deleted") if ok else t(lang, "operation_failed"))
    # If admin currently views the teachers list, re-render it.
    if ok:
        try:
            state = get_admin_state(callback.message.chat.id)
            if state.get("step") == "teachers_list_view":
                page = int(state.get("data", {}).get("teachers_page") or 0)
                search_query = str(state.get("data", {}).get("teachers_search") or "")
                await show_teachers_list(callback.message, page=page, search_query=search_query)
        except Exception:
            pass
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("teacher_delete_profile_confirm_no_"))
async def handle_teacher_delete_profile_no(callback: CallbackQuery):
    lang = _admin_lang_from_callback(callback)
    await callback.message.answer(t(lang, "operation_cancelled"))
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("t_toggle_daily_tests_"))
async def handle_toggle_daily_tests_permission(callback: CallbackQuery):
    teacher_id = int(callback.data.split("_")[-1])
    admin_id = callback.from_user.id
    lang = _admin_lang_from_callback(callback)

    teacher = get_user_by_id(teacher_id)
    if not teacher:
        await callback.answer(t(lang, 'admin_auto_msg_53'))
        return

    if not _can_manage_user(admin_id, teacher):
        await callback.answer(t(lang, 'permission_denied_short'), show_alert=True)
        return

    from db import set_daily_test_upload_permission
    current = bool(teacher.get('can_upload_daily_tests'))
    set_daily_test_upload_permission(teacher_id, not current)

    # Re-open detail page to reflect updated state.
    await handle_teacher_detail(callback)


@dp.callback_query(lambda c: c.data.startswith("t_toggle_ai_"))
async def handle_toggle_ai_permission(callback: CallbackQuery):
    teacher_id = int(callback.data.split("_")[-1])
    admin_id = callback.from_user.id
    lang = _admin_lang_from_callback(callback)

    teacher = get_user_by_id(teacher_id)
    if not teacher:
        await callback.answer(t(lang, 'admin_auto_msg_53'))
        return

    if not _can_manage_user(admin_id, teacher):
        await callback.answer(t(lang, 'permission_denied_short'), show_alert=True)
        return

    from db import set_teacher_ai_generation_permission
    current = bool(teacher.get('can_generate_ai'))
    set_teacher_ai_generation_permission(teacher_id, not current)

    # Re-open detail page to reflect updated state.
    await handle_teacher_detail(callback)


@dp.callback_query(lambda c: c.data.startswith("admin_ai_request_approve_"))
async def handle_admin_ai_request_approve(callback: CallbackQuery):
    teacher_id = int(callback.data.split("_")[-1])
    admin_id = callback.from_user.id
    lang = _admin_lang_from_callback(callback)

    teacher = get_user_by_id(teacher_id)
    if not teacher:
        await callback.answer(t(lang, 'admin_auto_msg_53'))
        return

    if not _can_manage_user(admin_id, teacher):
        await callback.answer(t(lang, 'permission_denied_short'), show_alert=True)
        return

    from db import set_teacher_ai_generation_permission
    set_teacher_ai_generation_permission(teacher_id, True)

    await callback.answer(t(lang, "admin_ai_access_approved_alert"))
    await handle_teacher_detail(callback)

    # Notify teacher (best-effort) — teacher's UI language, not admin's
    try:
        tid = teacher.get("telegram_id")
        if tid:
            t_lang = detect_lang_from_user(teacher)
            await bot.send_message(int(tid), t(t_lang, "admin_ai_access_approved_msg"))
    except Exception:
        pass


@dp.callback_query(lambda c: c.data.startswith("admin_ai_request_deny_"))
async def handle_admin_ai_request_deny(callback: CallbackQuery):
    teacher_id = int(callback.data.split("_")[-1])
    admin_id = callback.from_user.id
    lang = _admin_lang_from_callback(callback)

    teacher = get_user_by_id(teacher_id)
    if not teacher:
        await callback.answer(t(lang, 'admin_auto_msg_53'))
        return

    if not _can_manage_user(admin_id, teacher):
        await callback.answer(t(lang, 'permission_denied_short'), show_alert=True)
        return

    from db import set_teacher_ai_generation_permission
    set_teacher_ai_generation_permission(teacher_id, False)

    await callback.answer(t(lang, "admin_ai_access_rejected_alert"))
    await handle_teacher_detail(callback)

    # Notify teacher (best-effort) — teacher's UI language, not admin's
    try:
        tid = teacher.get("telegram_id")
        if tid:
            t_lang = detect_lang_from_user(teacher)
            await bot.send_message(int(tid), t(t_lang, "admin_ai_access_rejected_msg"))
    except Exception:
        pass


@dp.callback_query(lambda c: c.data.startswith("teacher_daily_tests_history_"))
async def handle_teacher_daily_tests_history(callback: CallbackQuery):
    teacher_id = int(callback.data.split("_")[-1])
    admin_id = callback.from_user.id
    lang = _admin_lang_from_callback(callback)

    teacher = get_user_by_id(teacher_id)
    if not teacher:
        await callback.answer(t(lang, 'admin_auto_msg_53'))
        return

    if not _can_manage_user(admin_id, teacher):
        await callback.answer(t(lang, 'permission_denied_short'), show_alert=True)
        return

    from db import get_daily_test_history_for_teacher
    history = get_daily_test_history_for_teacher(teacher_id, days=14)

    lines = [
        t(
            lang,
            "teacher_daily_tests_history_admin_title",
            first_name=(teacher.get("first_name") or "").strip(),
            last_name=(teacher.get("last_name") or "").strip(),
        )
    ]
    if not history:
        lines.append(t(lang, 'teacher_daily_tests_history_empty'))
    else:
        avg_lbl = t(lang, "teacher_daily_tests_history_avg_label")
        for row in history:
            td = row.get('test_date')
            completed = row.get('completed_attempts') or 0
            correct_total = row.get('correct_total') or 0
            wrong_total = row.get('wrong_total') or 0
            unanswered_total = row.get('unanswered_total') or 0
            avg_net = row.get('avg_net_dcoins') or 0
            avg_net_str = f"{float(avg_net):+.2f}"
            lines.append(
                t(
                    lang,
                    "teacher_daily_tests_history_row_line",
                    td=td,
                    completed=completed,
                    correct_total=correct_total,
                    wrong_total=wrong_total,
                    unanswered_total=unanswered_total,
                    avg_label=avg_lbl,
                    avg_net=avg_net_str,
                )
            )

    await callback.message.edit_text("\n".join(lines), parse_mode="HTML")
    await callback.answer()


# ==================== TEACHER EDIT HANDLERS (SHORT PREFIXES) ====================

@dp.callback_query(lambda c: c.data.startswith("t_edit_fn_"))
async def handle_teacher_edit_first_name(callback: CallbackQuery):
    teacher_id = int(callback.data.split("_")[-1])
    state = get_admin_state(callback.message.chat.id)
    state['step'] = 'teach_edit_first'
    state['data']['teacher_id'] = teacher_id
    
    lang = detect_lang_from_user(callback.from_user)
    await callback.message.answer(t(lang, 'admin_auto_msg_54'), reply_markup=cancel_keyboard(lang))
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("t_edit_ln_"))
async def handle_teacher_edit_last_name(callback: CallbackQuery):
    teacher_id = int(callback.data.split("_")[-1])
    state = get_admin_state(callback.message.chat.id)
    state['step'] = 'teach_edit_last'
    state['data']['teacher_id'] = teacher_id
    
    lang = detect_lang_from_user(callback.from_user)
    await callback.message.answer(t(lang, 'admin_auto_msg_55'), reply_markup=cancel_keyboard(lang))
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("t_edit_ph_"))
async def handle_teacher_edit_phone(callback: CallbackQuery):
    teacher_id = int(callback.data.split("_")[-1])
    state = get_admin_state(callback.message.chat.id)
    state['step'] = 'teach_edit_phone'
    state['data']['teacher_id'] = teacher_id
    
    lang = detect_lang_from_user(callback.from_user)
    await callback.message.answer(t(lang, 'admin_auto_msg_56'), reply_markup=cancel_keyboard(lang))
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("t_reset_pw_"))
async def handle_teacher_reset_password(callback: CallbackQuery):
    teacher_id = int(callback.data.split("_")[-1])
    teacher = get_user_by_id(teacher_id)
    lang = _admin_lang_from_callback(callback)
    
    if not teacher:
        await callback.answer(t(lang, 'admin_auto_msg_44'))
        return
    
    # Reset password for an existing teacher record.
    # (This handler should not create a new user row.)
    import random
    import string

    new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    from db import get_conn
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET password = ?, password_used = 0 WHERE id = ?",
        (new_password, teacher_id),
    )
    conn.commit()
    conn.close()

    text = t(
        lang,
        "admin_teacher_password_reset_success_html",
        first_name=teacher.get("first_name") or "",
        last_name=teacher.get("last_name") or "",
        password=new_password,
        login_id=teacher.get("login_id") or "",
    )

    await callback.message.edit_text(text, parse_mode='HTML')
    await callback.answer(t(lang, 'admin_auto_msg_57'))

@dp.callback_query(lambda c: c.data == "teachers_list_view")
async def handle_teachers_list_view(callback: CallbackQuery):
    """Handle back to teachers list with standardized callback"""
    await show_teachers_list(callback.message)
    await callback.answer()
