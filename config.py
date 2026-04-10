import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Try to load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / '.env')
except Exception:
    pass

ADMIN_BOT_TOKEN = os.getenv('ADMIN_BOT_TOKEN')
TEACHER_BOT_TOKEN = os.getenv('TEACHER_BOT_TOKEN')
STUDENT_BOT_TOKEN = os.getenv('STUDENT_BOT_TOKEN')
SUPPORT_BOT_TOKEN = os.getenv('SUPPORT_BOT_TOKEN')


# Require PostgreSQL DATABASE_URL
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL or not DATABASE_URL.strip().lower().startswith(('postgresql://', 'postgres://')):
    raise RuntimeError('DATABASE_URL must be set and must start with postgresql:// or postgres://')




# For optional Redis caching in utils
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Allowed subjects
SUBJECTS = ['English', 'Russian']

# General admins: full visibility/control across all data and modules.
ADMIN_CHAT_IDS = [int(x) for x in os.getenv('ADMIN_CHAT_IDS', '').split(',') if x.strip().isdigit()]
TEACHER_CHAT_IDS = [int(x) for x in os.getenv('TEACHER_CHAT_IDS', '').split(',') if x.strip().isdigit()]

# Support lesson booking "NEW BOOKING" notifications: ALL_ADMIN_IDS (main + limited) via SUPPORT_BOT_TOKEN (student_bot).
# See student_bot._support_booking_notify_admin_ids()

# Limited admins (only manage their own students/groups).
# Set in .env as:
#   DiamondAdmin1=...
#   DiamondAdmin2=...
_limited_1 = (
    os.getenv('DiamondAdmin1')
    or os.getenv('DiamondAmind1')  # backward compatibility for common typo
    or os.getenv('DIAMOND_ADMIN_1')
)
_limited_2 = os.getenv('DiamondAdmin2') or os.getenv('DIAMOND_ADMIN_2')
LIMITED_ADMIN_CHAT_IDS = [int(x) for x in (_limited_1, _limited_2) if x and str(x).strip().isdigit()]

# All admins (main + limited) — can access admin bot; scoping applied per role
ALL_ADMIN_IDS = list(dict.fromkeys(ADMIN_CHAT_IDS + LIMITED_ADMIN_CHAT_IDS))


def limited_admin_label(admin_id: int) -> str:
    """
    Friendly label for limited admins in UI.
    Uses order in LIMITED_ADMIN_CHAT_IDS:
      [0] -> DiamondAdmin1
      [1] -> DiamondAdmin2
    Fallback: "Admin {id}"
    """
    try:
        aid = int(admin_id)
    except Exception:
        return f"Admin {admin_id}"
    if LIMITED_ADMIN_CHAT_IDS:
        if len(LIMITED_ADMIN_CHAT_IDS) >= 1 and aid == int(LIMITED_ADMIN_CHAT_IDS[0]):
            return "DiamondAdmin1"
        if len(LIMITED_ADMIN_CHAT_IDS) >= 2 and aid == int(LIMITED_ADMIN_CHAT_IDS[1]):
            return "DiamondAdmin2"
    return f"Admin {aid}"

# Diamondvoy: full DB wipe (PostgreSQL) after secret confirmation — set in .env only, never commit real values.
DIAMONDVOY_DB_RESET_SECRET = (os.getenv("DIAMONDVOY_DB_RESET_SECRET") or "").strip()

# ================== SQLITE3 ==================
# Allow explicit DB path from .env for stable multi-bot deployments.
DB_PATH = os.getenv('DB_PATH', str(BASE_DIR / "data" / "diamond.db"))

# For one-time password generation
OTP_LENGTH = 6

# Basic login limits
MAX_LOGIN_ATTEMPTS = 3
# Student bot: optional forced channel subscription (see force_subscribe.py)
def _env_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


FORCE_SUBSCRIBE = _env_bool("FORCE_SUBSCRIBE", "false")
_force_ch = os.getenv("FORCE_SUBSCRIBE_CHANNEL_ID", "").strip()
try:
    FORCE_SUBSCRIBE_CHANNEL_ID: int | None = int(_force_ch) if _force_ch else None
except ValueError:
    FORCE_SUBSCRIBE_CHANNEL_ID = None
FORCE_SUBSCRIBE_CHANNEL_URL = os.getenv(
    "FORCE_SUBSCRIBE_CHANNEL_URL",
    "https://t.me/diamond_education1",
).strip()

# Runtime transport mode
USE_WEBHOOK = _env_bool("USE_WEBHOOK", "false")
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "").strip()
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "").strip()
WEBHOOK_PATH_PREFIX = os.getenv("WEBHOOK_PATH_PREFIX", "tg").strip() or "tg"
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "0.0.0.0").strip() or "0.0.0.0"

# Per-bot webhook ports (safe defaults when bots run as separate services)
ADMIN_WEBHOOK_PORT = int(os.getenv("ADMIN_WEBHOOK_PORT", "8081"))
TEACHER_WEBHOOK_PORT = int(os.getenv("TEACHER_WEBHOOK_PORT", "8082"))
STUDENT_WEBHOOK_PORT = int(os.getenv("STUDENT_WEBHOOK_PORT", "8083"))
SUPPORT_WEBHOOK_PORT = int(os.getenv("SUPPORT_WEBHOOK_PORT", "8084"))

