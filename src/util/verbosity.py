import os
from dotenv import load_dotenv

load_dotenv()

def _get_log_verbosity():
    try:
        return max(0, int(os.getenv('LOG_VERBOSITY', '1')))
    except Exception:
        print("Invalid LOG_VERBOSITY in .env, defaulting to 1")
        return 1

LOG_VERBOSITY = _get_log_verbosity()