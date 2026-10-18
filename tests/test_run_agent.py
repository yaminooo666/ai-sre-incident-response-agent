import json
import models
import pytest
import constans as c

from types import SimpleNamespace
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from services import step_service, plan_service
import tools.run_agent as agent_module
from tools import registry




@pytest.fixture
def db(tmp_path):

    test_url = f"sqlite:///{tmp_path / 'test.db'}"

    test_engine = create_engine(
        test_url,
        connect_args={"check_same_thread": False}
    )

    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine
    )

    Base.metadata.create_all(bind=test_engine)

    with TestingSessionLocal() as session:
        yield session

    test_engine.dispose()





def test_run_agent_healthy(db, monkeypatch):

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
        status=c.STEP_STATUS_PENDING,
        approval_required=False
    )

    db.add_all([incident, plan, step])
    db.commit()



    def fake_execute_tool(action_type, service_name):
        assert action_type == c.ACTION_CHECK_METRICS
        assert service_name == "test_service"

        return SimpleNamespace(
            success=True,
            result={
                "timestamp": 1,
                "abnormal_reasons": []
            },
            error=None
        )

    monkeypatch.setattr(
        step_service,
        "execute_tool",
        fake_execute_tool
    )


    def fake_re_evaluate(*args, **kwargs):
        return SimpleNamespace(
            decision="resolved",
            reason="Service metrics are healthy"
        )

    monkeypatch.setattr(
        agent_module,
        "re_evaluate_plan",
        fake_re_evaluate
    )

    agent_module.run_agent(db, incident)

    saved_incident = db.get(models.Incident, incident.id)
    assert saved_incident.status == c.INCIDENT_STATUS_RESOLVED

    saved_step = db.get(models.PlanStep, step.id)
    assert saved_step.status == c.STEP_STATUS_EXECUTED

    saved_log = (
    db.query(models.AuditLog)
    .filter(
        models.AuditLog.incident_id == incident.id,
        models.AuditLog.action == "incident_resolved"
    )
    .first()
    )
    assert saved_log is not None






def test_run_agent_restart_verified(db, monkeypatch):

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
        diagnosis="Need to restart",
        evidence_summary="Test evidence",
        status="generated"
    )

    step = models.PlanStep(
        step_order=1,
        action_type=c.ACTION_RESTART_SERVICE,
        action_desc="restart",
        risk_level= registry.TOOLS[c.ACTION_RESTART_SERVICE]["risk_level"],
        status=c.STEP_STATUS_APPROVED,
        approval_required=True,
        plan=plan
)

    db.add_all([incident, plan, step])
    db.commit()

    def fake_execute_tool(action_type, service_name):
        assert service_name == "test_service"

        if action_type == c.ACTION_RESTART_SERVICE:
            return SimpleNamespace(
                success=True,
                result={
                    "service_name": service_name,
                    "current_status": "running",
                    "restart_count": 1
                },
                error=None
            )

        if action_type == c.ACTION_CHECK_METRICS:
            return SimpleNamespace(
                success=True,
                result={
                    "timestamp": 1,
                    "abnormal_reasons": []
                },
                error=None
            )

        pytest.fail(f"Unexpected tool: {action_type}")


    monkeypatch.setattr(
            step_service,
            "execute_tool",
            fake_execute_tool
        )

    def fake_re_evaluate(*args, **kwargs):
        return SimpleNamespace(
            decision="resolved",
            reason="Service metrics are healthy"
        )

    monkeypatch.setattr(
        agent_module,
        "re_evaluate_plan",
        fake_re_evaluate
    )


    agent_module.run_agent(db,incident)
    
    next_step = (
        db.query(models.PlanStep)
        .filter(
            models.PlanStep.step_order==2,
            models.PlanStep.action_type== c.ACTION_CHECK_METRICS,
            models.PlanStep.plan_id == plan.id
        )
        .first()
    )

    assert next_step is not None

    saved_incident = db.get(models.Incident, incident.id)
    assert saved_incident.status == c.INCIDENT_STATUS_RESOLVED

    saved_step = db.get(models.PlanStep, next_step.id)
    assert saved_step.status == c.STEP_STATUS_EXECUTED

    saved_restart = db.get(models.PlanStep, step.id)
    assert saved_restart.status == c.STEP_STATUS_EXECUTED

    saved_log = (
    db.query(models.AuditLog)
    .filter(
        models.AuditLog.incident_id == incident.id,
        models.AuditLog.action == "incident_resolved"
    )
    .first()
    )
    assert saved_log is not None





