import sqlite3
import bcrypt
import os

db_path = r'c:\Users\55829\OneDrive\Desktop\Leopoldina.D\database\leopoldina.db'

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# Ensure file exists
if not os.path.exists(db_path):
    print(f"Error: {db_path} not found.")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

admin_email = 'admin@leopoldina.gov.br'
new_hash = get_password_hash('admin123')

# Try to update existing user
cursor.execute("UPDATE usuarios SET senha_hash = ?, status = 'Ativo' WHERE email = ?", (new_hash, admin_email))
if cursor.rowcount == 0:
    # If not found, insert
    cursor.execute("INSERT INTO usuarios (nome, cpf, email, senha_hash, tipo_usuario, status) VALUES (?, ?, ?, ?, ?, ?)", 
                  ('Administrador Geral', '000.000.000-00', admin_email, new_hash, 'admin', 'Ativo'))

conn.commit()
conn.close()
print(f"Success: Password for {admin_email} reset to 'admin123'.")
