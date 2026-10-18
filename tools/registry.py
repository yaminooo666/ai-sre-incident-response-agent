from .query_logs import query_logs
from .check_metrics import check_metrics
from .restart_service import restart_service
import constans as c
from .tool_call_schemas import QueryLogsArgs,CheckMetricsArgs,RestartServiceArgs


TOOLS= {
    "query_logs": {
        "function": query_logs,
        "args_model": QueryLogsArgs,
        "risk_level": c.RISK_LOW,
        "approval_required": False,
        "requires_verification": False,
        "description": "Query recent logs for a service with optional filtering."
    },

    "check_metrics": {
        "function": check_metrics,
        "args_model":CheckMetricsArgs,
        "risk_level": c.RISK_LOW,
        "approval_required": False,
        "requires_verification": False,
        "description":"Check selected health metrics for a service within a recent time window and report abnormal values."
    },

    "restart_service": {
        "function": restart_service,
        "args_model": RestartServiceArgs,
        "risk_level": c.RISK_HIGH,
        "approval_required": True,
        "requires_verification": True,
        "verification_tool": c.ACTION_CHECK_METRICS,
        "description":"Restart a service to recover from a suspected service failure. This action changes service state and requires approval."
    }

}


CONTROL_ACTIONS = {    
    c.ACTION_NOTIFY_OWNER: {        
        "risk_level": c.RISK_LOW,        
        "approval_required": False
        }
}

VALID_ACTION_TYPES = set(TOOLS) | set(CONTROL_ACTIONS)