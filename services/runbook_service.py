import models, schemas
from fastapi import status,HTTPException



def create_runbook(db,runbook_in):
    title = runbook_in.title.strip()
    service_name = runbook_in.service_name.strip()
    alert_type = runbook_in.alert_type.strip()
    content = runbook_in.content.strip()
    
    if not title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="title cannot be empty" 
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

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="content cannot be empty"
        )

    runbook=models.Runbook(
        title = title,
        service_name = service_name,
        alert_type = alert_type,
        content = content
    )
    db.add(runbook)
    db.commit()
    db.refresh(runbook)
    return runbook



def list_runbooks(db):
    runbooks=db.query(models.Runbook).all()

    return runbooks