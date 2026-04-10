import asyncio
import logging
import os
import fcntl
import atexit
from datetime import datetime, timedelta
import pytz
from i18n import t
from db import init_db, set_bot_started_at_now
from migrations import run_all_migrations
from tests_seed import seed
from admin_bot import run_admin_bot
from student_bot import run_student_bot
from teacher_bot import run_teacher_bot
from support_lesson import run_support_bot

_LOCK_FD = None


def _acquire_single_instance_lock() -> bool:
    """
    Prevent running duplicate bot orchestrators on the same host.
    Duplicate polling processes cause TelegramConflictError.
    """
    global _LOCK_FD
    lock_path = "/tmp/diamond-bot-main.lock"
    _LOCK_FD = open(lock_path, "w")
    try:
        fcntl.flock(_LOCK_FD, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _LOCK_FD.write(str(os.getpid()))
        _LOCK_FD.flush()
        return True
    except BlockingIOError:
        return False


def _release_single_instance_lock():
    global _LOCK_FD
    try:
        if _LOCK_FD is not None:
            fcntl.flock(_LOCK_FD, fcntl.LOCK_UN)
            _LOCK_FD.close()
            _LOCK_FD = None
    except Exception:
        pass

async def cleanup_scheduler():
    """Run cleanup tasks every 48 hours"""
    while True:
        try:
            from auth import run_periodic_cleanup
            run_periodic_cleanup()
        except Exception as e:
            print(f"[SCHEDULER] Error in cleanup: {e}")
        
        # Wait 48 hours
        await asyncio.sleep(48 * 60 * 60)  # 48 hours in seconds


async def arena_questions_promote_scheduler():
    """Move arena_questions_bank rows older than 24h into daily_tests_bank (hourly)."""
    while True:
        try:
            from db import promote_expired_arena_questions_to_daily

            n = promote_expired_arena_questions_to_daily()
            if n:
                print(f"[SCHEDULER] arena_questions promoted to daily_tests_bank: {n}")
        except Exception as e:
            print(f"[SCHEDULER] arena_questions_promote_scheduler error: {e}")
        await asyncio.sleep(3600)


async def daily_arena_questions_promote_scheduler():
    """Move Daily Arena questions into daily_tests_bank after 3 hours (every 30 min)."""
    while True:
        try:
            from db import promote_expired_daily_arena_questions_to_daily

            n = promote_expired_daily_arena_questions_to_daily()
            if n:
                print(f"[SCHEDULER] daily_arena_questions promoted to daily_tests_bank: {n}")
        except Exception as e:
            print(f"[SCHEDULER] daily_arena_questions_promote_scheduler error: {e}")
        await asyncio.sleep(1800)


async def duel_questions_promote_scheduler():
    """Move finished Duel questions from tmp pools into daily_tests_bank after 3 hours."""
    while True:
        try:
            from db import promote_expired_duel_questions_tmp_to_daily

            n = promote_expired_duel_questions_tmp_to_daily()
            if n:
                print(f"[SCHEDULER] duel_questions promoted to daily_tests_bank: {n}")
        except Exception as e:
            print(f"[SCHEDULER] duel_questions_promote_scheduler error: {e}")
        await asyncio.sleep(1800)


async def diamondvoy_history_cleanup_scheduler():
    """Delete Diamondvoy history older than 30 days, once per 24h."""
    from db import delete_diamondvoy_history_older_than_days

    while True:
        try:
            n = delete_diamondvoy_history_older_than_days(30)
            if n:
                print(f"[SCHEDULER] diamondvoy_history cleanup: removed {n} row(s)")
        except Exception as e:
            print(f"[SCHEDULER] diamondvoy_history cleanup error: {e}")
        await asyncio.sleep(24 * 60 * 60)


async def daily_tests_scheduler():
    """
    Daily tests reminders + low-stock alerts.
    Times are in Asia/Tashkent:
      - 09:00: send daily test start
      - 14:00: reminder if not completed
      - 19:00: reminder if not completed
    """
    import pytz
    from datetime import datetime as dt
    from config import ALL_ADMIN_IDS
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    import student_bot as sb
    from db import (
        get_daily_test_reminder_candidates,
        mark_daily_test_notification_sent,
        count_available_daily_tests_global,
        mark_daily_test_stock_alert,
        get_teachers_with_daily_test_permission,
        get_user_by_telegram,
        ensure_daily_test_type_plan,
        cleanup_expired_daily_tests,
    )

    tz = pytz.timezone("Asia/Tashkent")
    thresholds = [200, 100, 80, 60, 40, 20]
    reminder_slots = {9: 0, 14: 1, 19: 2}

    last_checked: dict[tuple[str, int], bool] = {}
    last_daily_bank_cleanup_date: str | None = None

    while True:
        try:
            now = dt.now(tz)
            test_date = now.date().isoformat()

            # Wait until student bot initializes (it also initializes sb.admin_bot)
            if sb.bot is None:
                await asyncio.sleep(10)
                continue

            # Send reminders at fixed time (best-effort window)
            if now.minute == 0 and now.hour in reminder_slots:
                slot = reminder_slots[now.hour]
                key = (test_date, slot)
                if not last_checked.get(key):
                    last_checked[key] = True

                    plan_en = None
                    # At 09:00 create deterministic daily-test type plan once per day.
                    if now.hour == 9 and slot == 0:
                        try:
                            plan_en = ensure_daily_test_type_plan("English", test_date, total_questions=10)
                            ensure_daily_test_type_plan("Russian", test_date, total_questions=10)
                        except Exception:
                            plan_en = None

                    candidates = get_daily_test_reminder_candidates(test_date, slot)
                    if candidates:
                        for u in candidates:
                            if not mark_daily_test_notification_sent(u["id"], test_date, slot):
                                continue
                            if not u.get("telegram_id"):
                                continue
                            lang = (u.get("language") or "uz").lower()
                            if lang not in ("uz", "ru", "en"):
                                lang = "uz"
                            kb = InlineKeyboardMarkup(
                                inline_keyboard=[
                                    [
                                        InlineKeyboardButton(
                                            text=t(lang, "daily_test_start_btn"),
                                            callback_data="daily_test_start",
                                        )
                                    ]
                                ]
                            )
                            mix_line = ""
                            if plan_en:
                                mix_line = "\n\n" + t(
                                    lang,
                                    "daily_test_mix_line",
                                    rules=plan_en.get('grammar_rules_count', 0),
                                    sentence=plan_en.get('grammar_sentence_count', 0),
                                    find_mistake=plan_en.get('find_mistake_count', 0),
                                    error=plan_en.get('error_spotting_count', 0),
                                )
                            text = t(lang, "daily_test_reminder_text") + mix_line
                            await sb.bot.send_message(int(u["telegram_id"]), text, reply_markup=kb)

            # Expire used daily-test bank rows (Postgres only in db); once per local day, off-peak.
            if now.minute == 0 and now.hour == 3:
                dkey = now.date().isoformat()
                if last_daily_bank_cleanup_date != dkey:
                    last_daily_bank_cleanup_date = dkey
                    try:
                        removed = cleanup_expired_daily_tests(days=4)
                        if removed:
                            print(f"[SCHEDULER] daily_tests_bank cleanup: {removed} row(s)")
                    except Exception as e:
                        print(f"[SCHEDULER] cleanup_expired_daily_tests: {e}")

            # Low-stock alerts once per day during 09:00 check
            if now.minute == 0 and now.hour == 9:
                current_stock = count_available_daily_tests_global()
                if sb.admin_bot is None:
                    await asyncio.sleep(20)
                    continue
                teachers = get_teachers_with_daily_test_permission()
                teacher_chat_ids = [int(t["telegram_id"]) for t in teachers if t.get("telegram_id")]

                for th in thresholds:
                    if current_stock <= th:
                        if not mark_daily_test_stock_alert(subject="ALL", level="ALL", threshold=th):
                            continue

                        # Notify admins
                        for admin_id in ALL_ADMIN_IDS:
                            try:
                                alert_lang = "uz"
                                au = get_user_by_telegram(str(admin_id))
                                if au:
                                    alert_lang = (au.get("language") or "uz").lower()
                                if alert_lang not in ("uz", "ru", "en"):
                                    alert_lang = "uz"
                                await sb.admin_bot.send_message(
                                    int(admin_id),
                                    t(alert_lang, "daily_tests_stock_alert", current_stock=current_stock, threshold=th),
                                )
                            except Exception:
                                pass

                        # Notify permitted teachers
                        for teacher_id in teacher_chat_ids:
                            try:
                                tl = "uz"
                                tu = get_user_by_telegram(str(teacher_id))
                                if tu:
                                    tl = (tu.get("language") or "uz").lower()
                                if tl not in ("uz", "ru", "en"):
                                    tl = "uz"
                                await sb.admin_bot.send_message(
                                    int(teacher_id),
                                    t(tl, "daily_tests_stock_alert", current_stock=current_stock, threshold=th),
                                )
                            except Exception:
                                pass

        except Exception as e:
            print(f"[SCHEDULER] daily_tests_scheduler error: {e}")

        await asyncio.sleep(20)


async def holiday_cancel_scheduler():
    """Startupda 10 kunni tekshiradi, keyin har kuni 12:00 da +10-kunni tekshiradi."""
    tz = pytz.timezone("Asia/Tashkent")
    bootstrap_done = False
    last_sent_date: str | None = None
    while True:
        try:
            import admin_bot as ab
            now = datetime.now(tz)
            date_key = now.strftime("%Y-%m-%d")

            # Birinchi ishga tushishda: bugun + 10 kunni tekshiramiz.
            if not bootstrap_done and getattr(ab, "bot", None):
                await ab.send_daily_otmen_alerts(start_offset=0, days_count=11)
                bootstrap_done = True

            # Har kuni 12:00 da: faqat bugundan 10 kun keyingi bittani tekshiramiz.
            if now.hour == 12 and now.minute == 0 and last_sent_date != date_key and getattr(ab, "bot", None):
                await ab.send_daily_otmen_alerts(start_offset=10, days_count=1)
                last_sent_date = date_key
        except Exception as e:
            print(f"[SCHEDULER] holiday_cancel_scheduler error: {e}")

        await asyncio.sleep(20)


async def main():
    print("[STARTUP] init_db() starting")
    init_db()                    # diamond.db yaratadi
    print("[STARTUP] init_db() done")

    print("[STARTUP] run_all_migrations() starting")
    run_all_migrations()         # migratsiyalarni bajaradi
    print("[STARTUP] run_all_migrations() done")

    # Limit month navigation/scheduling to the actual bot startup moment.
    print("[STARTUP] set_bot_started_at_now()")
    set_bot_started_at_now()

    print("[STARTUP] seed() starting")
    seed()                       # test savollarini qo'shadi
    print("[STARTUP] seed() done")

    # === 60 KUNLIK TO'LIQ AVTOMATIK O'CHIRISH (startupda ham ishlaydi) ===
    from auth import cleanup_inactive_accounts
    deleted = cleanup_inactive_accounts()
    if deleted > 0:
        print(f"✅ Startup cleanup: {deleted} ta inactive akkaunt o'chirildi")

    async def _guard(name: str, coro):
        try:
            print(f"[STARTUP] {name} launching")
            return await coro
        except Exception as e:
            print(f"[STARTUP][ERROR] {name} crashed: {repr(e)}")
            return None

    # Start all bots and cleanup scheduler
    await asyncio.gather(
        _guard("admin_bot", run_admin_bot()),
        _guard("student_bot", run_student_bot()),
        _guard("teacher_bot", run_teacher_bot()),
        _guard("support_bot", run_support_bot()),
        _guard("cleanup_scheduler", cleanup_scheduler()),  # 48-hour cleanup scheduler
        _guard("daily_tests_scheduler", daily_tests_scheduler()),  # daily tests reminders + low-stock alerts
        _guard(
            "diamondvoy_history_cleanup_scheduler",
            diamondvoy_history_cleanup_scheduler(),
        ),
        _guard("holiday_cancel_scheduler", holiday_cancel_scheduler()),
        # _guard("arena_questions_promote_scheduler", arena_questions_promote_scheduler()),
        # _guard("daily_arena_questions_promote_scheduler", daily_arena_questions_promote_scheduler()),
        _guard("duel_questions_promote_scheduler", duel_questions_promote_scheduler()),
        return_exceptions=True,
    )

if __name__ == '__main__':
    if not _acquire_single_instance_lock():
        print("[STARTUP] Another main.py instance is already running. Exiting.")
        raise SystemExit(1)
    atexit.register(_release_single_instance_lock)
    asyncio.run(main())
