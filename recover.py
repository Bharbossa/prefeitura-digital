import psycopg2
import sys

try:
    conn = psycopg2.connect(
        host="c-6.us-east-1.aws.neon.tech",
        database="neondb",
        user="neondb_owner",
        password="npg_9gGs8ZPRMUnS",
        sslmode="require",
        options="project=ep-wild-river-ancnt251@2026-07-07T14:00:00Z"
    )
    cur = conn.cursor()
    cur.execute("SELECT * FROM agendamentos WHERE protocolo = 'COL-2026-OH4C9'")
    row = cur.fetchone()
    if row:
        colnames = [desc[0] for desc in cur.description]
        data = dict(zip(colnames, row))
        print("FOUND:")
        print(data)
    else:
        print("NOT FOUND")
except Exception as e:
    print(f"ERROR: {e}")
