import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

# Render sets RENDER=true in its environment; treat that (or explicit prod flag) as production.
IS_PRODUCTION = os.getenv('RENDER') == 'true' or os.getenv('FLASK_ENV') == 'production'

_FORBIDDEN_DEFAULTS = {
    '', 'dev-secret-key-change-in-production',
    'your-secret-key-here-change-in-production', 'change-me-in-production',
}

def _require_in_prod(name: str) -> str:
    val = os.getenv(name, '')
    if IS_PRODUCTION and val in _FORBIDDEN_DEFAULTS:
        raise RuntimeError(f'{name} must be set to a real value in production')
    return val

class Config:
    # Flask
    SECRET_KEY = _require_in_prod('SECRET_KEY') or 'dev-secret-key-change-in-production'

    # Session cookies
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = IS_PRODUCTION  # localhost runs over http
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)

    # CSRF: workout pages stay open for 90+ minutes; never expire the token mid-session
    WTF_CSRF_TIME_LIMIT = None

    # Supabase
    SUPABASE_URL = os.getenv('SUPABASE_URL', '')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')              # anon key: browser OAuth only
    SUPABASE_SERVICE_KEY = _require_in_prod('SUPABASE_SERVICE_KEY')  # server data access

    # Cron auth
    CRON_SECRET = _require_in_prod('CRON_SECRET')

    # Google OAuth (configure later)
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '')

    # Anthropic API (for AI-generated exercise cues)
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')

    # YouTube Data API (for exercise demo videos)
    YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY', '')
