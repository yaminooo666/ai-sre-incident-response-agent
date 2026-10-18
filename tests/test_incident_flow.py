import sys
from pathlib import Path


sys.path.append(str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from main import app
from services import plan_service
import constans as c
from types import SimpleNamespace
from tools.run_agent import evaluate_resolution
from datetime import datetime ,timedelta


client = TestClient(app)

def test_create_incident():
    payload = {
        "title": "payment high error rate",
        "service_name": "payment-service",
        "alert_type": "high_error_rate",
        "severity": 3,
        "description": "Payment service error rate increased sharply.",
        "created_by": "test_user"
    }

    response = client.post("/incidents/", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == payload["title"]
    assert data["status"] == c.INCIDENT_STATUS_PENDING_ANALYSIS


def test_generate_plan_creates_steps():
    payload = {
        "title": "payment high error rate",
        "service_name": "payment-service",
        "alert_type": "high_error_rate",
        "severity": 3,
        "description": "Payment service error rate increased sharply.",
        "created_by": "test_user"
    }

    create_response = client.post("/incidents/", json=payload)
    assert create_response.status_code == 200

    incident_data = create_response.json()
    incident_id = incident_data["id"]

    plan_response = client.post(f"/incidents/{incident_id}/generate-plan")
    assert plan_response.status_code == 200

    plan_data = plan_response.json()
    assert "diagnosis" in plan_data
    assert len(plan_data["steps"]) > 0

    detail_response = client.get(f"/incidents/{incident_id}")
    assert detail_response.status_code == 200

    detail_data = detail_response.json()
    assert len(detail_data["plans"]) > 0
    assert any(log["action"] == c.INCIDENT_STATUS_PLAN_GENERATED for log in detail_data["audit_logs"])


def test_approve_and_execute_high_risk_step(monkeypatch):
    def fake_build_plan_content(incident, runbooks, histories):
        return (
            "测试 diagnosis",
            "测试 evidence_summary",
            [
                {
                    "step_order": 1,
                    "action_type": "query_logs",
                    "action_desc": "检查最近错误日志",
                    "risk_level": "low",
                    "status": "pending",
                    "approval_required": False,
                    "execution_result": None,
                },
                {
                    "step_order": 2,
                    "action_type": "restart_service",
                    "action_desc": "重启异常服务实例",
                    "risk_level": "high",
                    "status": "waiting_approval",
                    "approval_required": True,
                    "execution_result": None,
                },
            ],
            "ai",
        )

    monkeypatch.setattr(plan_service, "build_plan_content", fake_build_plan_content)


    payload = {
        "title": "payment high error rate",
        "service_name": "payment-service",
        "alert_type": "high_error_rate",
        "severity": 3,
        "description": "Payment service error rate increased sharply.",
        "created_by": "test_user"
    }
    
    create_response = client.post("/incidents/", json=payload)
    assert create_response.status_code == 200

    incident_data = create_response.json()
    incident_id = incident_data["id"]

    plan_response = client.post(f"/incidents/{incident_id}/generate-plan")
    assert plan_response.status_code == 200

    plan_data = plan_response.json()
    assert "diagnosis" in plan_data
    assert len(plan_data["steps"]) > 0

    steps=plan_data["steps"]
    new_step = next((step for step in steps if step["approval_required"]==True),None)
    print(steps)
    assert new_step is not None, steps

    step_id=new_step["id"]
    approve_response=client.post(f"/steps/{step_id}/approve",json={"approved": True})
    assert approve_response.status_code == 200

    approve_data = approve_response.json()
    assert approve_data["status"] == "approved"

    execute_response=client.post(f"/steps/{step_id}/execute")
    assert execute_response.status_code == 200

    execute_data = execute_response.json()
    assert execute_data["status"] == "executed"
    assert execute_data["execution_result"] is not None




def test_incident_resolved_after_all_steps_executed(monkeypatch):
    def fake_build_plan_content(incident, runbooks, histories):
        return (
            "测试 diagnosis",
            "测试 evidence_summary",
            [
                {
                    "step_order": 1,
                    "action_type": "query_logs",
                    "action_desc": "检查最近错误日志",
                    "risk_level": "low",
                    "status": "pending",
                    "approval_required": False,
                    "execution_result": None,
                },
                {
                    "step_order": 2,
                    "action_type": "restart_service",
                    "action_desc": "重启异常服务实例",
                    "risk_level": "high",
                    "status": "waiting_approval",
                    "approval_required": True,
                    "execution_result": None,
                },
            ],
            "ai",
        )

    monkeypatch.setattr(plan_service, "build_plan_content", fake_build_plan_content)

    payload = {
        "title": "payment high error rate",
        "service_name": "payment-service",
        "alert_type": "high_error_rate",
        "severity": 3,
        "description": "Payment service error rate increased sharply.",
        "created_by": "test_user"
    }

    create_response = client.post("/incidents/", json=payload)
    assert create_response.status_code == 200

    incident_data = create_response.json()
    incident_id = incident_data["id"]

    plan_response = client.post(f"/incidents/{incident_id}/generate-plan")
    assert plan_response.status_code == 200

    plan_data = plan_response.json()
    steps = plan_data["steps"]
    assert len(steps) == 2

    low_risk_step = next((step for step in steps if step["approval_required"] is False), None)
    high_risk_step = next((step for step in steps if step["approval_required"] is True), None)

    assert low_risk_step is not None
    assert high_risk_step is not None

    low_execute_response = client.post(f"/steps/{low_risk_step['id']}/execute")
    assert low_execute_response.status_code == 200

    approve_response = client.post(
        f"/steps/{high_risk_step['id']}/approve",
        json={"approved": True}
    )
    assert approve_response.status_code == 200

    high_execute_response = client.post(f"/steps/{high_risk_step['id']}/execute")
    assert high_execute_response.status_code == 200

    detail_response = client.get(f"/incidents/{incident_id}")
    assert detail_response.status_code == 200

    detail_data = detail_response.json()
    assert detail_data["incident"]["status"] == c.INCIDENT_STATUS_RESOLVED




