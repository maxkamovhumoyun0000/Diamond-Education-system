import asyncio
import logging
from datetime import datetime, timedelta
import re
import pytz

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from db import get_conn, get_group, get_group_users, add_attendance, get_user_by_id, get_user_by_telegram
from i18n import t, detect_lang_from_user
from logging_config import get_logger

logger = get_logger(__name__)

TZ = pytz.timezone("Asia/Tashkent")
PAGE_SIZE = 10


def now_tashkent():
    return datetime.now(TZ)


def _today_str():
    return now_tashkent().strftime("%Y-%m-%d")


def ensure_session(group_id: int, date_str: str):
    """Create attendance session if not exists, return session row dict."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO attendance_sessions (group_id, date) VALUES (?, ?)",
        (group_id, date_str),
    )
    conn.commit()
    cur.execute("SELECT * FROM attendance_sessions WHERE group_id=? AND date=?", (group_id, date_str))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def set_notified(session_id: int, field: str):
    if field not in (
        "notified_admin",
        "notified_teacher",
        "notified_admin_pre",
        "notified_admin_post",
        "notified_teacher_pre",
        "notified_teacher_post",
    ):
        return
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"UPDATE attendance_sessions SET {field}=1 WHERE id=?", (session_id,))
    conn.commit()
    conn.close()


def set_session_opened(session_id: int, opened_by: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE attendance_sessions SET opened_by=?, opened_at=CURRENT_TIMESTAMP, status='open' WHERE id=?",
        (opened_by, session_id),
    )
    conn.commit()
    conn.close()


def set_session_closed(session_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE attendance_sessions SET status='closed', closed_at=CURRENT_TIMESTAMP WHERE id=?", (session_id,))
    conn.commit()
    conn.close()


def get_session(session_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM attendance_sessions WHERE id=?", (session_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_group_sessions(group_id: int):
    """Get all attendance sessions for a group, ordered by date descending"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM attendance_sessions 
        WHERE group_id=? 
        ORDER BY date DESC
    """, (group_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_attendance_map(group_id: int, date_str: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT user_id, status FROM attendance WHERE group_id=? AND date=?", (group_id, date_str))
    rows = cur.fetchall()
    conn.close()
    return {r["user_id"]: r["status"] for r in rows}


def build_attendance_keyboard(session_id: int, group_id: int, date_str: str, page: int):
    users = get_group_users(group_id)
    total = len(users)
    start = page * PAGE_SIZE
    end = min(total, start + PAGE_SIZE)
    slice_users = users[start:end]

    status_map = get_attendance_map(group_id, date_str)

    rows = []
    for u in slice_users:
        uid = u["id"]
        st = (status_map.get(uid) or "").lower()
        prefix = "✅ " if st == "present" else ("❌ " if st == "absent" else "⚪ ")
        name_btn = InlineKeyboardButton(text=prefix + f"{u.get('first_name','')} {u.get('last_name','')}", callback_data="att_noop")
        present_btn = InlineKeyboardButton(text="✅", callback_data=f"att_mark_{session_id}_{uid}_Present_{page}")
        absent_btn = InlineKeyboardButton(text="❌", callback_data=f"att_mark_{session_id}_{uid}_Absent_{page}")
        rows.append([name_btn, present_btn, absent_btn])

    nav = []
    if start > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"att_page_{session_id}_{page-1}"))
    if end < total:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"att_page_{session_id}_{page+1}"))
    if nav:
        rows.append(nav)

    # Language for teacher/admin is decided at send-time; button label defaults to Uzbek
    rows.append([InlineKeyboardButton(text=t('uz', 'attendance_finish_btn'), callback_data=f"att_finish_{session_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def send_attendance_panel(bot, chat_id: int, session_id: int, group_id: int, date_str: str, page: int = 0):
    group = get_group(group_id)
    # Try to detect language from recipient if they exist in users table
    u = get_user_by_telegram(str(chat_id))
    lang = detect_lang_from_user(u or {})
    title = t(lang, 'attendance_title', group=group.get('name', 'Guruh'), date=date_str)
    kb = build_attendance_keyboard(session_id, group_id, date_str, page)
    await bot.send_message(chat_id, title, reply_markup=kb)


def can_teacher_manage_group(teacher_user: dict, group: dict) -> bool:
    return teacher_user and teacher_user.get("login_type") == 3 and group and group.get("teacher_id") == teacher_user.get("id")


async def attendance_scheduler(bot, role: str, admin_chat_ids=None):
    """
    role: 'admin' or 'teacher'
    - admin: notify ADMIN_CHAT_IDS
    - teacher: notify each group's teacher telegram_id
    """
    admin_chat_ids = admin_chat_ids or []
    while True:
        try:
            now = now_tashkent()
            today = now.strftime("%Y-%m-%d")
            cur_time = now.strftime("%H:%M")
            weekday = now.weekday()  # 0=Mon ... 6=Sun

            conn = get_conn()
            cur = conn.cursor()
            # Fetch all groups that have a schedule; we will decide per-group if today is a lesson day
            cur.execute("SELECT * FROM groups WHERE lesson_start IS NOT NULL AND lesson_end IS NOT NULL")
            groups = [dict(r) for r in cur.fetchall()]
            conn.close()

            for g in groups:
                # Decide if this group has lesson today
                lesson_date = (g.get("lesson_date") or "").strip()
                has_today = False
                if lesson_date:
                    # Explicit calendar date
                    if re.match(r"^\d{4}-\d{2}-\d{2}$", lesson_date):
                        has_today = (lesson_date == today)
                    else:
                        code = lesson_date.upper()
                        if code == "ODD":
                            # Mon/Wed/Fri
                            has_today = weekday in (0, 2, 4)
                        elif code == "EVEN":
                            # Tue/Thu/Sat
                            has_today = weekday in (1, 3, 5)
                if not has_today:
                    continue

                start = (g.get("lesson_start") or "")[:5]
                end = (g.get("lesson_end") or "")[:5]
                if not start or not end:
                    continue

                # Build timezone-aware datetimes for comparisons
                try:
                    start_naive = datetime.strptime(f"{today} {start}", "%Y-%m-%d %H:%M")
                    end_naive = datetime.strptime(f"{today} {end}", "%Y-%m-%d %H:%M")
                    start_dt = TZ.localize(start_naive)
                    end_dt = TZ.localize(end_naive)
                except Exception:
                    continue
                pre_dt = start_dt - timedelta(minutes=10)

                # Only operate around the lesson window (pre to end)
                if not (pre_dt <= now <= end_dt):
                    continue

                session = ensure_session(g["id"], today)
                if not session or session.get("status") == "closed":
                    continue

                # Pre-notify: 10 minutes before start until start
                if pre_dt <= now < start_dt:
                    if role == "admin":
                        if not session.get("notified_admin_pre"):
                            for admin_id in admin_chat_ids:
                                try:
                                    admin_lang = 'uz'
                                    await bot.send_message(
                                        admin_id,
                                        t(admin_lang, 'attendance_pre_notify', group=g.get('name'), start=start, end=end),
                                    )
                                    await send_attendance_panel(bot, admin_id, session["id"], g["id"], today, 0)
                                except Exception:
                                    logger.exception("Admin attendance pre-notify failed")
                            set_notified(session["id"], "notified_admin_pre")

                    if role == "teacher":
                        if not session.get("notified_teacher_pre"):
                            teacher = get_user_by_id(g.get("teacher_id")) if g.get("teacher_id") else None
                            if teacher and teacher.get("telegram_id"):
                                try:
                                    tid = int(teacher["telegram_id"])
                                    t_lang = detect_lang_from_user(teacher)
                                    await bot.send_message(
                                        tid,
                                        t(t_lang, 'attendance_pre_notify', group=g.get('name'), start=start, end=end),
                                    )
                                    await send_attendance_panel(bot, tid, session["id"], g["id"], today, 0)
                                except Exception:
                                    logger.exception("Teacher attendance pre-notify failed")
                                set_notified(session["id"], "notified_teacher_pre")

                # Post-notify: at/after start until end (so if bot restarts, it still notifies)
                if start_dt <= now <= end_dt:
                    if role == "admin":
                        if not session.get("notified_admin_post") and not session.get("notified_admin"):
                            for admin_id in admin_chat_ids:
                                try:
                                    admin_lang = 'uz'
                                    await bot.send_message(
                                        admin_id,
                                        t(admin_lang, 'attendance_post_notify', group=g.get('name'), start=start, end=end),
                                    )
                                    await send_attendance_panel(bot, admin_id, session["id"], g["id"], today, 0)
                                except Exception:
                                    logger.exception("Admin attendance post-notify failed")
                            set_notified(session["id"], "notified_admin_post")
                            # legacy flag for backward compatibility with old DBs/logic
                            set_notified(session["id"], "notified_admin")

                    if role == "teacher":
                        if not session.get("notified_teacher_post") and not session.get("notified_teacher"):
                            teacher = get_user_by_id(g.get("teacher_id")) if g.get("teacher_id") else None
                            if teacher and teacher.get("telegram_id"):
                                try:
                                    tid = int(teacher["telegram_id"])
                                    t_lang = detect_lang_from_user(teacher)
                                    await bot.send_message(
                                        tid,
                                        t(t_lang, 'attendance_post_notify', group=g.get('name'), start=start, end=end),
                                    )
                                    await send_attendance_panel(bot, tid, session["id"], g["id"], today, 0)
                                except Exception:
                                    logger.exception("Teacher attendance post-notify failed")
                                set_notified(session["id"], "notified_teacher_post")
                                set_notified(session["id"], "notified_teacher")

        except Exception:
            logger.exception("attendance_scheduler loop error")

        await asyncio.sleep(30)

