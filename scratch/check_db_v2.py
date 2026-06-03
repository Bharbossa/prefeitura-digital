import psycopg2
db_url = 'postgresql://neondb_owner:npg_9gGs8ZPRMUnS@ep-wild-river-ancnt251-pooler.c-6.us-east-1.aws.neon.tech/neondb?sslmode=require'
conn = psycopg2.connect(db_url)
cursor = conn.cursor()
cursor.execute("SELECT id, protocolo, anexo FROM agendamentos WHERE tipo = 'Concurso' ORDER BY id DESC LIMIT 5")
rows = cursor.fetchall()
for r in rows:
    print(f'ID: {r[0]} | Prot: {r[1]} | Anexo: {r[2]}')
