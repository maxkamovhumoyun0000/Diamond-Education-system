import asyncio
import logging
from datetime import timedelta
from db import init_db
from migrations import run_all_migrations
from tests_seed import seed
from admin_bot import run_admin_bot
from student_bot import run_student_bot
from teacher_bot import run_teacher_bot

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

async def main():
    init_db()                    # diamond.db yaratadi

    run_all_migrations()         # migratsiyalarni bajaradi

    seed()                       # test savollarini qo'shadi

    # === 60 KUNLIK TO'LIQ AVTOMATIK O'CHIRISH (startupda ham ishlaydi) ===
    from auth import cleanup_inactive_accounts
    deleted = cleanup_inactive_accounts()
    if deleted > 0:
        print(f"✅ Startup cleanup: {deleted} ta inactive akkaunt o'chirildi")

    # Start all bots and cleanup scheduler
    await asyncio.gather(
        run_admin_bot(),
        run_student_bot(),
        run_teacher_bot(),
        cleanup_scheduler(),  # 48-hour cleanup scheduler
    )

if __name__ == '__main__':
    asyncio.run(main())
