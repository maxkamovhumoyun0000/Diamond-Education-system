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

DEFAULT_DB_PATH = BASE_DIR / 'data' / 'diamond.db'
DEFAULT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
DATABASE_URL = os.getenv('DATABASE_URL', f'sqlite+aiosqlite:///{DEFAULT_DB_PATH}')

# For optional Redis caching in utils
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Allowed subjects
SUBJECTS = ['English', 'Russian']

ADMIN_CHAT_IDS = [int(x) for x in os.getenv('ADMIN_CHAT_IDS', '').split(',') if x.strip().isdigit()]
TEACHER_CHAT_IDS = [int(x) for x in os.getenv('TEACHER_CHAT_IDS', '').split(',') if x.strip().isdigit()]

# ================== SQLITE3 ==================
DB_PATH = str(BASE_DIR / "data" / "diamond.db")

# For one-time password generation
OTP_LENGTH = 6

# Basic login limits
MAX_LOGIN_ATTEMPTS = 3
