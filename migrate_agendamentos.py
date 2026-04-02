import sys
sys.path.append('.')
from backend.app.database import engine
from sqlalchemy import text

def add_columns():
    with engine.begin() as conn:
        print("Migrating agendamentos table...")
        
        # Add protocolo
        conn.execute(text("ALTER TABLE agendamentos ADD COLUMN IF NOT EXISTS protocolo VARCHAR(20);"))
        
        # Add motivo
        conn.execute(text("ALTER TABLE agendamentos ADD COLUMN IF NOT EXISTS motivo TEXT;"))
        
        # Add acompanhante
        conn.execute(text("ALTER TABLE agendamentos ADD COLUMN IF NOT EXISTS acompanhante VARCHAR(100);"))
        
        # Add cartao_sus
        conn.execute(text("ALTER TABLE agendamentos ADD COLUMN IF NOT EXISTS cartao_sus VARCHAR(50);"))
        
        # Add anexo
        conn.execute(text("ALTER TABLE agendamentos ADD COLUMN IF NOT EXISTS anexo VARCHAR(255);"))
        
        # Add criado_em
        conn.execute(text("ALTER TABLE agendamentos ADD COLUMN IF NOT EXISTS criado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW();"))
        
        print("Success! Columns have been ensured.")

if __name__ == "__main__":
    add_columns()
