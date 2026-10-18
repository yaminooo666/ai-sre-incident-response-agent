import constans as c
from types import SimpleNamespace
from tools.run_agent import evaluate_resolution
import json
from tools import registry




def test_resolution_healthy():

    result={
        "timestamp": 1,
        "cpu_usage": 80,
        "memory_usage": 80,
        "error_rate": 0.05,
        "latency_ms": 999,
        "abnormal_reasons":[]
    }

    execution_result=json.dumps(result)

    step = SimpleNamespace(
        step_order=1,
        action_type=c.ACTION_CHECK_METRICS,
        status=c.STEP_STATUS_EXECUTED,
        execution_result=execution_result
    )

    steps =[step]

    allowed, next_action, reason = evaluate_resolution(steps)

    assert allowed is True
    assert next_action == "resolved"



def test_resolution_unhealthy():

    result={
        "timestamp": 1,
        "cpu_usage": 90,
        "memory_usage": 80,
        "error_rate": 0.05,
        "latency_ms": 999,
        "abnormal_reasons":[]
    }

    result["abnormal_reasons"].append(
        f"CPU usage is {result.get('cpu_usage')}"
    )

    execution_result=json.dumps(result)

    step = SimpleNamespace(
        step_order=1,
        action_type=c.ACTION_CHECK_METRICS,
        status=c.STEP_STATUS_EXECUTED,
        execution_result=execution_result
    )

    steps =[step]

    allowed, next_action, reason = evaluate_resolution(steps)

    assert allowed is False
    assert next_action == "re_evaluate"



def test_resolution_missing_verification():

    step = SimpleNamespace(
        step_order=1,
        action_type=c.ACTION_RESTART_SERVICE,
        status=c.STEP_STATUS_EXECUTED,
        execution_result=[]
    )
    steps=[step]

    allowed, next_action, reason = evaluate_resolution(steps)

    assert allowed is False
    assert next_action == "system_error"




def test_resolution_restart_verified():
    
    step1 = SimpleNamespace(
        step_order=1,
        action_type=c.ACTION_RESTART_SERVICE,
        status=c.STEP_STATUS_EXECUTED,
        execution_result=[]
    )

    execution_result= {
        "timestamp": 1,
        "cpu_usage": 80,
        "memory_usage": 80,
        "error_rate": 0.05,
        "latency_ms": 999,
        "abnormal_reasons":[]
    }
    execution_result=json.dumps(execution_result)

    step2 = SimpleNamespace(
        step_order=2,
        action_type=c.ACTION_CHECK_METRICS,
        status=c.STEP_STATUS_EXECUTED,
        execution_result=execution_result
    )

    steps=[step1,step2]
    allowed, next_action, reason = evaluate_resolution(steps)

    assert allowed is True
    assert next_action == "resolved"
