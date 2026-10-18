import models, schemas
from sqlalchemy.orm import Session
from database import get_db
from fastapi import APIRouter, Depends, HTTPException, status,UploadFile
from services import runbook_service


router = APIRouter(
    prefix="/runbooks",      
    tags=["Runbook"]        
)


@router.post("/",response_model=schemas.RunbookOut)
def create_runbook(
    runbook_in:schemas.RunbookCreate,
    db:Session=Depends(get_db)
):
    runbook=runbook_service.create_runbook(db,runbook_in)
    return runbook



@router.get("/",response_model=list[schemas.RunbookOut])
def get_runbooks(
    db:Session=Depends(get_db)
):
    runbooks=runbook_service.list_runbooks(db)
    return runbooks