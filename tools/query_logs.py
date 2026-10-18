import models, schemas
from datetime import datetime ,timedelta
from fastapi import HTTPException, status


LOG_STORE = {
    "payment-service": [
        {
            "timestamp": datetime.utcnow() - timedelta(minutes=2),
            "level": "INFO",
            "message": "payment request started"
        },
        {
            "timestamp": datetime.utcnow() - timedelta(minutes=1),
            "level": "ERROR",
            "message": "database connection timeout"
        },
        {
            "timestamp": datetime.utcnow() - timedelta(minutes=20),
            "level": "ERROR",
            "message": "old payment failure"
        },
    ]
}

def query_logs(service_name,minutes,level,keyword=None):
   
    logs=LOG_STORE.get(service_name)
    cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
    matched_logs=[]

    if logs is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="logs not found"
        )

    for log in logs:
        if (log.get("level")==level 
        and log.get("timestamp")>=cutoff_time 
        and (keyword is None or keyword in log.get("message"))
        ):
            matched_logs.append(log)

    return matched_logs
        
    
    

