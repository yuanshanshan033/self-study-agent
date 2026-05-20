import os
from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

load_dotenv(dotenv_path=os.path.join(PROJECT_ROOT, ".env"))

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

SQLITE_PATH = os.getenv("SQLITE_PATH", os.path.join(PROJECT_ROOT, "data", "xiaohongshu.db"))
CHROMA_PATH = os.getenv("CHROMA_PATH", os.path.join(PROJECT_ROOT, "data", "chroma"))
USER_PROFILE_PATH = os.path.join(PROJECT_ROOT, "data", "user_profile.json")

CHROMA_SERVER_PORT = int(os.getenv("PYTHON_CHROMA_PORT", "5001"))

MAX_DAILY_LIKES = 15
MAX_DAILY_BOOKMARKS = 5
MAX_BROWSING_MINUTES = 60
FEED_COUNT_FOR_PROFILE = 50