import constans as c
from types import SimpleNamespace
from tools.run_agent import evaluate_resolution
import json
from tools import registry
import models
from services import plan_service, step_service

from tests.test_run_agent import db
import tools.run_agent as agent_module



def test_re_evaluate_plan(monkeypatch):
    incident = models.Incident(
            title="Test incident",
            service_name="test_service",
            alert_type="high_latency",
            severity=2,
            description="Test description",
            status=c.INCIDENT_STATUS_PLAN_GENERATED,
            created_by="test"
        )

    plan = models.Plan(
        incident=incident,
        diagnosis="Need to check metrics",
        evidence_summary="Test evidence",
        status="generated"
    )

    step = models.PlanStep(
        plan=plan,
        step_order=1,
        action_type=c.ACTION_CHECK_METRICS,
        action_desc="Check service health",
        risk_level="low",
        status=c.STEP_STATUS_EXECUTED,
        execution_result=json.dumps({
            "abnormal_reasons": []
        }),
        approval_required=False
    )

    steps= [step]


    def fake_generate_content(**kwargs):
        return SimpleNamespace(
            text=json.dumps({
                "decision": "resolved",
                "reason": "Service metrics are healthy"
            })
        )
    monkeypatch.setattr(
        plan_service,
        "client",
        SimpleNamespace(
            models=SimpleNamespace(
                generate_content=fake_generate_content
            )
        )
    )

    result = plan_service.re_evaluate_plan(
        incident, plan, steps, [], []
)
    assert result.decision == "resolved"





def test_unhealthy_plan(db, monkeypatch):

    incident = models.Incident(
            title="Test incident",
            service_name="test_service",
            alert_type="high_latency",
            severity=2,
            description="Test description",
            status=c.INCIDENT_STATUS_PLAN_GENERATED,
            created_by="test"
        )

    plan = models.Plan(
        incident=incident,
        diagnosis="Need to check metrics",
        evidence_summary="Test evidence",
        status="generated"
    )

    step = models.PlanStep(
        plan=plan,
        step_order=1,
        action_type=c.ACTION_CHECK_METRICS,
        action_desc="Check service unhealth",
        risk_level="low",
        status=c.STEP_STATUS_PENDING,
        execution_result=None,
        approval_required=False
    )

    db.add_all([incident, plan, step])
    db.commit()



    def fake_execute_tool(action_type, service_name):
        assert action_type == c.ACTION_CHECK_METRICS
       
        return SimpleNamespace(
            success=True,
            result={
                "timestamp": 1,
                "abnormal_reasons": ["CPU usage is too high"]
            },
            error=None
        )
    monkeypatch.setattr(
        step_service,
        "execute_tool",
        fake_execute_tool
    )

    ai_calls = []

    def fake_re_evaluate(*args, **kwargs):
        ai_calls.append(kwargs)

        if kwargs.get("allow_resolved") is False:
            assert kwargs.get("system_feedback")

            return SimpleNamespace(
                decision = "manual_followup",
                reason = "CPU is still abnormal"
            )
        return SimpleNamespace(
            decision = "resolved",
            reason = "ai believes the incident is resolved"
        )
    monkeypatch.setattr(
        agent_module,
        "re_evaluate_plan",
        fake_re_evaluate
)

    agent_module.run_agent(db ,incident)

    saved_incident = db.get(models.Incident, incident.id)
    assert saved_incident.status == c.INCIDENT_STATUS_MANUAL_FOLLOWUP

    assert len(ai_calls) == 2
    assert ai_calls[1]["allow_resolved"] is False
    

    