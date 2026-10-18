import models, schemas
from sqlalchemy.orm import Session
from database import get_db
from fastapi import APIRouter, Depends, HTTPException, status,UploadFile
from services import incident_service,plan_service,audit_service
from tools.run_agent import run_agent


router = APIRouter(
    prefix="/incidents",      
    tags=["Incident"]        
)

@router.post("/{incident_id}/run")
def run_incident(
    incident_id:int,
    db:Session=Depends(get_db)
):
    incident = db.query(models.Incident).filter(models.Incident.id==incident_id).first()
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="incident not found"
        )

    run_agent(db,incident)

    return {"incident_id":incident.id,"status":incident.status}



@router.post("/",response_model=schemas.IncidentOut)
def create_incident(
    incident_in:schemas.IncidentCreate,
    db:Session=Depends(get_db)
):
    incident=incident_service.create_incident(db,incident_in)
    return incident


@router.get("/{incident_id}",response_model=schemas.IncidentDetailOut)
def get_incident(
    incident_id:int,
    db:Session=Depends(get_db)
):
    incident_detail=incident_service.get_incident_detail(db,incident_id)
    return incident_detail



@router.post("/{incident_id}/generate-plan",response_model=schemas.PlanOut)
def generate_plan(
    incident_id:int,
    db:Session=Depends(get_db)
):
    plan=plan_service.generate_plan(db,incident_id)
    return plan



@router.get("/{incident_id}/trace",response_model=list[schemas.TraceEventOut])
def get_trace(
    incident_id:int,
    db:Session=Depends(get_db)
):
    traces = (
        db.
        query(models.TraceEvent).
        filter(models.TraceEvent.incident_id == incident_id).
        order_by(models.TraceEvent.created_at.asc()).
        all()
    )

    return traces