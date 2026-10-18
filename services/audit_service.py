import models, schemas
from fastapi import status, HTTPException



def create_audit_log(db, incident_id, actor_type, action, detail):
    log=models.AuditLog(
        incident_id=incident_id,
        actor_type=actor_type,
        action=action,
        detail=detail
        )
    
    db.add(log)
    return log
