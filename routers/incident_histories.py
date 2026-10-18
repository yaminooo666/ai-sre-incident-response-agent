import models, schemas
from sqlalchemy.orm import Session
from database import get_db
from fastapi import APIRouter, Depends, HTTPException, status,UploadFile
from services import history_service


router = APIRouter(
    prefix="/incident_histories",      
    tags=["IncidentHistory"]        
)


@router.post("/",response_model=schemas.IncidentHistoryOut)
def create_incident_history(
    history_in:schemas.IncidentHistoryCreate,
    db:Session=Depends(get_db)
):
    history=history_service.create_incident_history(db,history_in)
    return history



@router.get("/",response_model=list[schemas.IncidentHistoryOut])
def get_incident_histories(
    db:Session=Depends(get_db)
):
    histories=history_service.list_incident_histories(db)
    return histories