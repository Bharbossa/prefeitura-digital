import sqlite3
import bcrypt
import os

db_path = r'c:\Users\55829\OneDrive\Desktop\Leopoldina.D\database\leopoldina.db'

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

if not os.path.exists(db_path):
    print(f"Error: {db_path} not found.")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

user_email = 'usuario@test.com'
user_nome = 'Cidadão de Teste'
user_cpf = '111.222.333-44'
new_hash = get_password_hash('user123')

# Try to update or insert
cursor.execute("SELECT id FROM usuarios WHERE email = ?", (user_email,))
user = cursor.fetchone()

if user:
    cursor.execute("UPDATE usuarios SET senha_hash = ?, tipo_usuario = 'cidadao' WHERE email = ?", (new_hash, user_email))
    print(f"Updated existing user {user_email}")
else:
    cursor.execute("INSERT INTO usuarios (nome, cpf, email, senha_hash, tipo_usuario) VALUES (?, ?, ?, ?, ?)", 
                  (user_nome, user_cpf, user_email, new_hash, 'cidadao'))
    print(f"Created new user {user_email}")

conn.commit()
conn.close()
print(f"Success: Citizen user ready with password 'user123'.")
