import models, schemas
from fastapi import status, HTTPException




def create_incident_history(db,history_in):

    incident_title = history_in.incident_title.strip()
    service_name = history_in.service_name.strip()
    alert_type = history_in.alert_type.strip()
    problem_summary = history_in.problem_summary.strip()
    resolution_summary = history_in.resolution_summary.strip()
    outcome = history_in.outcome.strip()

    if not incident_title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="incident_title cannot be empty" 
            )
    
    if not service_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="service_name cannot be empty"
        )

    if not alert_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="alert_type cannot be empty"
        )

    if not problem_summary:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="problem_summary cannot be empty"
        )

    if not resolution_summary:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="resolution_summary cannot be empty"
        )

    if not outcome:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="outcome cannot be empty"
        )

    history=models.IncidentHistory(
        incident_title=incident_title,
        service_name=service_name,
        alert_type=alert_type,
        severity=history_in.severity,
        problem_summary=problem_summary,
        resolution_summary=resolution_summary,
        outcome=outcome
    )
    db.add(history)
    db.commit()
    db.refresh(history)

    return history



def list_incident_histories(db):
    histories=db.query(models.IncidentHistory).all()

    return histories