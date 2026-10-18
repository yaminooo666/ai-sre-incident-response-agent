import models, schemas
from sqlalchemy.orm import Session
from database import get_db
from fastapi import APIRouter, Depends, HTTPException, status,UploadFile
from services import step_service,audit_service
import constans as c
from tools.run_agent import run_agent


router = APIRouter(
    prefix="/steps",      
    tags=["Step"]        
)


@router.post("/{step_id}/approve",response_model=schemas.PlanStepOut)
def approve_step(
    step_id:int,
    approval_in:schemas.StepApprovalRequest,
    db:Session=Depends(get_db)
):
    step=step_service.approve_step(db,step_id,approval_in.approved)
    incident=step.plan.incident

    
    run_agent(db,incident)
   
    db.commit()

    return step



@router.post("/{step_id}/execute",response_model=schemas.PlanStepOut)
def execute_step(
    step_id:int,
    db:Session=Depends(get_db)
):
    step=step_service.execute_step(db,step_id)
    return step
