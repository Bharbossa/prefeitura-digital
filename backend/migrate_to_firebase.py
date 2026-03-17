import sqlite3
import firebase_admin
from firebase_admin import credentials, firestore
import os

# CONFIGURATION
# You need to download your service account key from Firebase Console:
# Project Settings -> Service Accounts -> Generate new private key
SERVICE_ACCOUNT_KEY = 'serviceAccountKey.json' 
DB_PATH = r'../database/leopoldina.db'

def migrate():
    if not os.path.exists(SERVICE_ACCOUNT_KEY):
        print(f"Error: {SERVICE_ACCOUNT_KEY} not found.")
        print("Please place your Firebase Service Account JSON file in the backend folder.")
        return

    # Initialize Firebase
    cred = credentials.Certificate(SERVICE_ACCOUNT_KEY)
    firebase_admin.initialize_app(cred)
    db_firestore = firestore.client()

    # Connect to SQLite
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    tables = {
        'usuarios': 'usuarios',
        'secretarias': 'secretarias',
        'admins_secretaria': 'admin_secretarias',
        'ocorrencias': 'ocorrencias',
        'respostas': 'respostas'
    }

    for table_name, collection_name in tables.items():
        print(f"Migrating table: {table_name} to collection: {collection_name}...")
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        
        batch = db_firestore.batch()
        count = 0
        
        for row in rows:
            doc_data = dict(row)
            doc_id = str(doc_data.pop('id'))
            
            doc_ref = db_firestore.collection(collection_name).document(doc_id)
            batch.set(doc_ref, doc_data)
            count += 1
            
            if count % 400 == 0: # Firestore batch limit is 500
                batch.commit()
                batch = db_firestore.batch()
        
        batch.commit()
        print(f"Successfully migrated {count} documents to collection '{table}'.")

    conn.close()
    print("Migration finished!")

if __name__ == "__main__":
    migrate()
