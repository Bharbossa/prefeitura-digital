from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.schema import FileStorage

router = APIRouter()

@router.get("/{file_id}")
def get_file(file_id: str, db_sql: Session = Depends(get_db)):
    """
    Recupera um arquivo salvo no banco de dados e o envia como resposta binária.
    Isso substitui o armazenamento efêmero local.
    """
    file_record = db_sql.query(FileStorage).filter(FileStorage.id == file_id).first()
    
    if not file_record:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")
        
    return Response(content=file_record.data, media_type=file_record.content_type)
