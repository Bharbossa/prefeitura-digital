import firebase_admin
from firebase_admin import credentials, firestore
import os

# Mode: 'firestore' or 'sqlite'
DB_MODE = "sqlite"
db = None

# Initialize Firebase Admin
def initialize_firebase():
    global DB_MODE
    key_path = "serviceAccountKey.json"
    if os.path.exists(key_path):
        try:
            cred = credentials.Certificate(key_path)
            if not firebase_admin._apps:
                firebase_admin.initialize_app(cred)
            DB_MODE = "firestore"
            return firestore.client()
        except Exception:
            DB_MODE = "sqlite"
            return None
    else:
        # Check if we are in Google Cloud environment
        if os.getenv("K_SERVICE"): # Standard Cloud Run env var
            if not firebase_admin._apps:
                firebase_admin.initialize_app()
            DB_MODE = "firestore"
            return firestore.client()
        else:
            DB_MODE = "sqlite"
            return None

db = initialize_firebase()
