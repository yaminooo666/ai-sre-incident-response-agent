import constans as c
from types import SimpleNamespace
from tools.run_agent import evaluate_resolution
from fastapi import status, HTTPException
from services.step_service import execute_step,approve_step
from tools import registry




def test_plan_supereded():
    plan = SimpleNamespace(
        status = c.PLAN_STATUS_SUPERSEDED
    )
    step = SimpleNamespace(
        status = c.STEP_STATUS_WAITING_APPROVAL,
        plan = plan
    )
    incident = SimpleNamespace(

    )

    with pytest.raises(HTTPException) as exc_info:
        approve_step(db,step.id,True)
    assert exc_info.value.status_code == 409

    with pytest.raises(HTTPException) as exc_info:
        execute_step(db,step.id,run_id)
    assert exc_info.value.status_code == 409
    