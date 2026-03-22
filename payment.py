"""
Payment management module
Handles payment history export and cleanup functions
"""

import io
from typing import Tuple
from datetime import datetime, timedelta
import pytz
from openpyxl import Workbook

from db import get_conn, ensure_monthly_payments_table, _ym_now, DB_WRITE_LOCK


def export_payment_history_to_xlsx() -> Tuple[io.BytesIO, str]:
    """Export last 3 months of payment history to Excel with group information"""
    conn = get_conn()
    cur = conn.cursor()
    
    # Calculate date 3 months ago
    now = datetime.now(pytz.timezone("Asia/Tashkent"))
    three_months_ago = now - timedelta(days=90)
    three_months_ago_str = three_months_ago.strftime('%Y-%m')
    
    # Get payment history for last 3 months with group information
    cur.execute("""
        SELECT mp.*, 
               u.first_name, u.last_name, u.login_id,
               u.phone, u.telegram_id,
               g.name as group_name, g.level as group_level
        FROM monthly_payments mp
        JOIN users u ON mp.user_id = u.id
        LEFT JOIN user_groups ug ON u.id = ug.user_id
        LEFT JOIN groups g ON ug.group_id = g.id
        WHERE mp.ym >= ? 
        ORDER BY mp.ym DESC, u.first_name, u.last_name
    """, (three_months_ago_str,))
    
    payment_data = cur.fetchall()
    conn.close()
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Payment History"
    
    # Headers
    headers = [
        'Month', 'Student ID', 'First Name', 'Last Name', 
        'Phone', 'Telegram ID', 'Group Name', 'Group Level',
        'Payment Status', 'Payment Date', 'Notification Days'
    ]
    ws.append(headers)
    
    # Data
    for row in payment_data:
        payment_status = "✅ To'langan" if row['paid'] else "❌ To'lanmagan"
        notification_days = row['notified_days'] or "-"
        
        ws.append([
            row['ym'],
            row['login_id'],
            row['first_name'],
            row['last_name'],
            row['phone'] or '-',
            row['telegram_id'] or '-',
            row['group_name'] or '-',
            row['group_level'] or '-',
            payment_status,
            row['paid_at'] or '-',
            notification_days
        ])
    
    # Auto-adjust column widths
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
    return bio, f'payment_history_{now.strftime("%Y-%m-%d")}.xlsx'


def cleanup_old_payment_history():
    """Delete payment records older than 3 months"""
    conn = get_conn()
    cur = conn.cursor()
    
    # Calculate date 3 months ago
    now = datetime.now(pytz.timezone("Asia/Tashkent"))
    three_months_ago = now - timedelta(days=90)
    three_months_ago_str = three_months_ago.strftime('%Y-%m')
    
    # Delete old payment records
    cur.execute("DELETE FROM monthly_payments WHERE ym < ?", (three_months_ago_str,))
    
    deleted_count = cur.rowcount
    conn.commit()
    conn.close()
    
    return deleted_count


def get_payment_history_for_student(student_id: int, months: int = 3) -> list:
    """Get payment history for a specific student"""
    conn = get_conn()
    cur = conn.cursor()
    
    # Calculate date N months ago
    now = datetime.now(pytz.timezone("Asia/Tashkent"))
    months_ago = now - timedelta(days=30 * months)
    months_ago_str = months_ago.strftime('%Y-%m')
    
    cur.execute("""
        SELECT mp.*, g.name as group_name, g.level as group_level
        FROM monthly_payments mp
        LEFT JOIN user_groups ug ON mp.user_id = ug.user_id
        LEFT JOIN groups g ON ug.group_id = g.id
        WHERE mp.user_id = ? AND mp.ym >= ?
        ORDER BY mp.ym DESC
    """, (student_id, months_ago_str))
    
    result = [dict(row) for row in cur.fetchall()]
    conn.close()
    return result


def get_payment_stats_by_group(group_id: int, months: int = 3) -> dict:
    """Get payment statistics for a specific group"""
    conn = get_conn()
    cur = conn.cursor()
    
    # Calculate date N months ago
    now = datetime.now(pytz.timezone("Asia/Tashkent"))
    months_ago = now - timedelta(days=30 * months)
    months_ago_str = months_ago.strftime('%Y-%m')
    
    cur.execute("""
        SELECT 
            COUNT(*) as total_students,
            SUM(CASE WHEN mp.paid = 1 THEN 1 ELSE 0 END) as paid_students,
            SUM(CASE WHEN mp.paid = 0 THEN 1 ELSE 0 END) as unpaid_students,
            mp.ym
        FROM monthly_payments mp
        JOIN user_groups ug ON mp.user_id = ug.user_id
        WHERE ug.group_id = ? AND mp.ym >= ?
        GROUP BY mp.ym
        ORDER BY mp.ym DESC
    """, (group_id, months_ago_str))
    
    result = [dict(row) for row in cur.fetchall()]
    conn.close()
    return result


def set_month_paid(user_id: int, ym: str | None = None, group_id: int | None = None, subject: str | None = None, paid: bool = True):
    """Mark monthly payment status per user-group for a given month."""
    ym = ym or _ym_now()
    ensure_monthly_payments_table()
    with DB_WRITE_LOCK:
        conn = get_conn()
        cur = conn.cursor()
        if paid:
            cur.execute(
                '''
                INSERT INTO monthly_payments(user_id, ym, group_id, subject, paid, paid_at)
                VALUES(?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id, ym, group_id) DO UPDATE SET paid=1, paid_at=CURRENT_TIMESTAMP, subject=COALESCE(excluded.subject, subject)
                ''',
                (user_id, ym, group_id, subject),
            )
        else:
            cur.execute(
                '''
                INSERT INTO monthly_payments(user_id, ym, group_id, subject, paid, paid_at)
                VALUES(?, ?, ?, ?, 0, NULL)
                ON CONFLICT(user_id, ym, group_id) DO UPDATE SET paid=0, paid_at=NULL, subject=COALESCE(excluded.subject, subject)
                ''',
                (user_id, ym, group_id, subject),
            )
        conn.commit()
        conn.close()
    from db import _cleanup_old_monthly_payments
    _cleanup_old_monthly_payments(retention_months=4)


def is_month_paid(user_id: int, ym: str | None = None, group_id: int | None = None) -> bool:
    ym = ym or _ym_now()
    ensure_monthly_payments_table()
    conn = get_conn()
    cur = conn.cursor()
    if group_id is None:
        cur.execute("SELECT paid FROM monthly_payments WHERE user_id=? AND ym=?", (user_id, ym))
    else:
        cur.execute("SELECT paid FROM monthly_payments WHERE user_id=? AND ym=? AND group_id=?", (user_id, ym, group_id))
    row = cur.fetchone()
    conn.close()
    return bool(row["paid"]) if row else False


def was_notified_on_day(user_id: int, day: int, ym: str | None = None) -> bool:
    ym = ym or _ym_now()
    ensure_monthly_payments_table()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT notified_days FROM monthly_payments WHERE user_id=? AND ym=?", (user_id, ym))
    row = cur.fetchone()
    conn.close()
    if not row or not row["notified_days"]:
        return False
    days = str(row["notified_days"]).split(",")
    return str(day) in days


def mark_notified_day(user_id: int, day: int, ym: str | None = None):
    ym = ym or _ym_now()
    ensure_monthly_payments_table()
    with DB_WRITE_LOCK:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT notified_days FROM monthly_payments 
            WHERE user_id = ? AND ym = ?
        """, (user_id, ym))
        row = cur.fetchone()
        if row and row["notified_days"]:
            days = str(row["notified_days"]).split(",")
            if str(day) not in days:
                days.append(str(day))
            new_days = ",".join(days)
            cur.execute("""
                UPDATE monthly_payments SET notified_days = ?
                WHERE user_id = ? AND ym = ?
            """, (new_days, user_id, ym))
        else:
            cur.execute("""
                INSERT OR REPLACE INTO monthly_payments (user_id, ym, notified_days)
                VALUES (?, ?, ?)
            """, (user_id, ym, str(day)))
        conn.commit()
        conn.close()


