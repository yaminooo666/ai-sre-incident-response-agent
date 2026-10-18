import models, schemas
from fastapi import status, HTTPException
import constans as c






def record_trace_event(
    db,
    incident,
    run_id,
    event_type,
    plan_id=None,
    step_id=None,
    payload=None
):

    if payload is None:
        payload = {}

    trace = models.TraceEvent(
        incident_id = incident.id,
        run_id = run_id,
        step_id = step_id,
        plan_id = plan_id,
        event_type = event_type,
        payload = payload
    )

    db.add(trace)
    return trace
