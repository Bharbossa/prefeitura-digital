import random
import string
from datetime import datetime, timezone, timedelta

def get_brasilia_time():
    """Returns the current naive time in Brasília (GMT-3)"""
    return datetime.now(timezone(timedelta(hours=-3))).replace(tzinfo=None)

def generate_protocol():
    """Generates a unique protocol number like COL-2026-XXXXX"""
    year = get_brasilia_time().year
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return f"COL-{year}-{random_str}"
