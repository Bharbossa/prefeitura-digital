import random
import string
from datetime import datetime

def generate_protocol():
    """Generates a unique protocol number like COL-2026-XXXXX"""
    year = datetime.now().year
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return f"COL-{year}-{random_str}"
