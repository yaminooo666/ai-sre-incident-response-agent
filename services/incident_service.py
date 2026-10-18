import models, schemas
from fastapi import status, HTTPException
from . import audit_service
import constans as c
from tools.mock_store import create_abnormal_metrics,METRIC_STORE



def create_incident(db,incident_in):

    if not incident_in.title.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="title cannot be empty" 
            )
    

    if not incident_in.service_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="service_name cannot be empty"
        )

    if not incident_in.alert_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="alert_type cannot be empty"
        )

    if not incident_in.created_by:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="created_by cannot be empty"
        )

    new_incident=models.Incident(
        title=incident_in.title.strip(),
        service_name=incident_in.service_name.strip(),
        alert_type=incident_in.alert_type.strip(),
        severity=incident_in.severity,
        description=incident_in.description.strip(),
        created_by=incident_in.created_by.strip(),
        status=c.INCIDENT_STATUS_PENDING_ANALYSIS
    )

    db.add(new_incident)
    db.flush()
    
    log=audit_service.create_audit_log(
        db,
        new_incident.id,
        actor_type="user",
        action="incident_created",
        detail=f"incident created by {new_incident.created_by}"
        )

    db.commit()

    new_metrics = create_abnormal_metrics()
    METRIC_STORE.clear()
    METRIC_STORE.update(new_metrics)

    return new_incident





def get_incident_detail(db,incident_id):
    incident=(
        db.query(models.Incident).
        filter(models.Incident.id==incident_id).
        first()
        )
    
    
    plans=(
        db.query(models.Plan).
        filter(models.Plan.incident_id==incident_id).
        order_by(models.Plan.created_at.asc()).
        all()
    )

    audit_logs=(
        db.query(models.AuditLog).
        filter(models.AuditLog.incident_id==incident_id).
        order_by(models.AuditLog.created_at.asc()).
        all()
    )

    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="incident not found"
        )

    result={
        "incident":incident,
        "plans":plans,
        "audit_logs":audit_logs
    }

    return result

