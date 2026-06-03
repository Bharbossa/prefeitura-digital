import sqlite3

def fix_jeff():
    conn = sqlite3.connect('backend/sql_app.db')
    c = conn.cursor()
    
    # 1. Get the ID for "SECRETARIA MUNICIPAL DE CULTURA E ESPORTES"
    c.execute("SELECT id, nome FROM secretarias WHERE nome LIKE '%CULTURA%'")
    cultura_row = c.fetchone()
    
    if not cultura_row:
        print("Secretaria de Cultura não encontrada.")
        return
        
    cultura_id = cultura_row[0]
    print(f"ID da Cultura e Esportes: {cultura_id}")
    
    # 2. Find Jeff
    c.execute("SELECT id, email, secretaria_id FROM admin_secretarias WHERE email='jefftenocava@gmail.com'")
    jeff_row = c.fetchone()
    
    if not jeff_row:
        print("Jeff não encontrado.")
        return
        
    print(f"Atualizando jefftenocava@gmail.com de secretaria {jeff_row[2]} para {cultura_id}")
    
    # 3. Update Jeff
    c.execute("UPDATE admin_secretarias SET secretaria_id = ? WHERE email='jefftenocava@gmail.com'", (cultura_id,))
    conn.commit()
    print("Atualizado com sucesso!")
    conn.close()

if __name__ == "__main__":
    fix_jeff()
