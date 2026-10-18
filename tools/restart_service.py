
from datetime import datetime
from fastapi import HTTPException, status
from tools.mock_store import METRIC_STORE




RESTART_STORE = {
    "payment-service": {
        "status": "unhealthy",
        "restart_count": 0,
        "last_restart_at": None
    }
}


def restart_service(service_name):
    service=RESTART_STORE.get(service_name)

    if service is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="service not found"
        )

    service["restart_count"]+=1
    previous_status=service["status"]
    service["status"]="running"
    service["last_restart_at"]=datetime.utcnow()

    record_post_restart_metrics(service_name)

    return {
        "service_name": service_name,
        "previous_status": previous_status,
        "current_status": service["status"],
        "restart_count": service["restart_count"],
        "last_restart_at":service["last_restart_at"]
    }




def record_post_restart_metrics(service_name):
    dict1 = {
            "timestamp": datetime.utcnow(),
            "cpu_usage": 45,
            "memory_usage": 62,
            "error_rate": 0.02,
            "latency_ms": 180
        }
    METRIC_STORE.setdefault(service_name, []).append(dict1)
