import models, schemas
from fastapi import status
from typing import Literal
from pydantic import BaseModel, Field
from services.llm_client import client
from config import settings
from . import audit_service
import constans as c
from fastapi import HTTPException
from services.ai_schemas import (
    AIGeneratedStep,
    AIGeneratedPlan,
    ReEvaluationResult
)
from tools import registry
from tools.registry import TOOLS,VALID_ACTION_TYPES,CONTROL_ACTIONS
from services.retrieval_service import retrieve_histories,retrieve_runbooks,rerank_histories,rerank_runbooks


def retrieve_evidence(db, incident):

    service_name = incident.service_name
    runbooks = db.query(models.Runbook).filter(models.Runbook.service_name==service_name).all()
    histories = db.query(models.IncidentHistory).filter(models.IncidentHistory.service_name==service_name).all()

    incident_text = []
   
    incident_text.append(incident.alert_type if incident.alert_type is not None else "")
    incident_text.append(incident.title if incident.title is not None else "")
    incident_text.append(incident.description if incident.description is not None else "")

    incident_text = "\n".join(incident_text)

    histories = retrieve_histories(incident_text,histories,10)
    runbooks = retrieve_runbooks(incident_text,runbooks,10)

    histories = rerank_histories(incident_text, histories, 3)
    runbooks = rerank_runbooks(incident_text, runbooks, 3)

    return runbooks,histories





def _format_runbooks(runbooks):
    if not runbooks:
        return "No matched runbooks."
    return "\n\n".join(
        f"Runbook {i+1}:\nTitle: {rb.title}\nService: {rb.service_name}\nAlert Type: {rb.alert_type}\nContent: {rb.content}"
        for i, rb in enumerate(runbooks)
    )

def _format_histories(histories):
    if not histories:
        return "No similar incident histories."
    return "\n\n".join(
        f"History {i+1}:\nTitle: {h.incident_title}\nService: {h.service_name}\nAlert Type: {h.alert_type}\n"
        f"Problem: {h.problem_summary}\nResolution: {h.resolution_summary}\nOutcome: {h.outcome}"
        for i, h in enumerate(histories)
    )

def _format_executed_steps(steps):
    step_detail=[]

    for step in steps:
        if step.status in ("executed","failed"):
            step_detail.append(f"step_order:{step.step_order},"
                            f" action_type:{step.action_type},"
                            f"status:{step.status},"
                            f" execution_result:{step.execution_result}")
    return "\n".join(step_detail)


def _format_plan_steps(steps):
    if not steps:
        return "No plan steps."

    return "\n".join(
        f"{step.step_order}. {step.action_type}: "
        f"{step.action_desc} (status={step.status})"
        for step in sorted(steps, key=lambda s: s.step_order)
    )




def re_evaluate_plan(incident, plan, steps,runbooks,histories,system_feedback=None,allow_resolved=True):
    available_tools=list(TOOLS.keys())

    allowed_decisions =[
    "continue",
    "modify_plan",
    "manual_followup"]

    if allow_resolved:
        allowed_decisions.append("resolved")

    feedback_text = system_feedback or "No additional system feedback."
    
    try:
        prompt = f"""
    You are an incident response planner.

    Current incident:
    - title: {incident.title}
    - service_name: {incident.service_name}
    - alert_type: {incident.alert_type}
    - severity: {incident.severity}
    - description: {incident.description}

    Original plan:
    -diagnosis: {plan.diagnosis}
    -evidence_summary: {plan.evidence_summary}
    -steps: {_format_plan_steps(plan.steps)}

    Matched runbooks:
    {_format_runbooks(runbooks)}

    Matched incident histories:
    {_format_histories(histories)}

    Available tools:
    {available_tools}

    Executed tool result:
    {_format_executed_steps(steps)} 

    allowed_decisions:
    {allowed_decisions}

    System feedback:
    {feedback_text}

    allow_resolved:
    {allow_resolved}

    Re-evaluate based on this feedback and the existing execution evidence.

    Re-evaluate the incident and decide the next action.

    Rules:
        1.根据 Incident、原始 Plan、已执行 Tool Results、Evidence、Available Tools,以及 System feedback（如果有）选择一个 decision。
        2.decision must be one of:{allowed_decisions}
        3.必须给出reason讲述为什么这样做
        4.If the execution results are insufficient, do not mark the task as resolved directly.
        5.Fabricating non-existent tools is prohibited.
        6.If a tool fails, choose continue only if the remaining steps in the current
        plan are still useful and safe despite the failure. Otherwise choose
        modify_plan or manual_followup.
        7.The task can be marked as resolved only when sufficient evidence proves that the issue has been recovered.
        8. 只有当 decision == modify_plan 时才允许返回 new_steps。
        9. new_steps 中每个 action_type 必须来自 Available tools。
       
    """
        response=client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_json_schema": ReEvaluationResult.model_json_schema(),
            }
        )
        result=ReEvaluationResult.model_validate_json(response.text)

        if result.decision not in allowed_decisions:
            raise ValueError("unsupported decision")

        if result.decision=="modify_plan":
            if not result.new_steps:
                raise ValueError("modify_plan requires new_steps")

            if not result.updated_diagnosis:
                raise ValueError("modify_plan requires updated_diagnosis")

            if not result.updated_evidence_summary:
                raise ValueError("modify_plan requires updated_evidence_summary")

            for step in result.new_steps:
                if step.action_type not in VALID_ACTION_TYPES:
                    raise ValueError(f"unsupported tool in new_steps: {step.action_type}")
        
        else:
            result.new_steps=None

        return result

    except Exception as e:
        print(f"re_evaluate_plan fallback because of error: {e}")

        return ReEvaluationResult(
        decision="manual_followup",
        reason=f"AI re-evaluation failed: {e}",
        new_steps=None
    )






def build_fallback_plan_content(runbooks, histories):
    diagnosis="AI generation failed or no strong evidence found. Generated a conservative fallback plan."
    evidence_summary=f"Matched {len(runbooks)} runbooks and {len(histories)} similar incident histories."
    steps_data = [
        {
            "step_order": 1,
            "action_type": "query_logs",
            "action_desc": "检查最近的错误日志。",
            "risk_level": "low",
            "status": "pending",
            "approval_required": False,
            "execution_result": None,
        },
        {
            "step_order": 2,
            "action_type": "check_metrics",
            "action_desc": "检查服务指标是否异常。",
            "risk_level": "low",
            "status": "pending",
            "approval_required": False,
            "execution_result": None,
        },
        {
            "step_order": 3,
            "action_type": "notify_owner",
            "action_desc": "通知负责人进行人工排查。",
            "risk_level": "medium",
            "status": "waiting_approval",
            "approval_required": True,
            "execution_result": None,
        },
    ]

    return diagnosis,evidence_summary,steps_data




def build_plan_content(incident, runbooks, histories):
    available_tools=list(TOOLS.keys())
    try:
        prompt = f"""
    You are an incident response planner.

    Current incident:
    - title: {incident.title}
    - service_name: {incident.service_name}
    - alert_type: {incident.alert_type}
    - severity: {incident.severity}
    - description: {incident.description}

    Matched runbooks:
    {_format_runbooks(runbooks)}

    Matched incident histories:
    {_format_histories(histories)}

    Available tools:
    {available_tools}

    Generate a concise incident response plan.

    Rules:
    1. Return 2 to 4 steps.
    2.请用简体中文输出 diagnosis、evidence_summary 和 action_desc。
    3. action_type must be selected only from Available tools above.
    4. High-risk actions must set approval_required=true.
    5. Low-risk observational actions should usually set approval_required=false.
    6. Do not invent unsupported tools.
    7. Keep evidence_summary concise and grounded in the provided evidence.
    8. risk_level must be one of: low, medium, high.
    9. approval_required must be a boolean.
    10.risk_level should be low for read-only observational actions, medium for limited-impact actions, and high for actions that may change service state or affect production.
    11.不能把没有出现在 Runbook / History 里的事实说成证据
    12.如果没有匹配证据，要明确说明证据不足
    13.History 的 resolution 只能作为历史经验，不能证明当前 Incident 已经恢复
        """
        response=client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_json_schema": AIGeneratedPlan.model_json_schema(),
            }
        )

        ai_plan=AIGeneratedPlan.model_validate_json(response.text)
        steps_data=[]

        for index,step in enumerate(ai_plan.steps,start=1):

            if step.action_type not in available_tools:
                original_action_type = step.action_type
                step.action_type="notify_owner"
                step.action_desc=f"模型生成了未支持动作 {original_action_type}，已降级为通知负责人。"
                step.approval_required = True
                step.risk_level = "medium"

            step_status = "waiting_approval" if step.approval_required else "pending"

            steps_data.append(
                {
                "step_order":index,
                "action_type":step.action_type,
                "action_desc":step.action_desc,
                "risk_level":step.risk_level,
                "status":step_status,
                "approval_required":step.approval_required,
                "execution_result":None
                }
            )
           


        if len(steps_data)<1:
            diagnosis, evidence_summary, steps_data = build_fallback_plan_content(runbooks, histories)
            plan_source = "fallback"
            return diagnosis, evidence_summary, steps_data, plan_source
        if len(steps_data)>4:
            steps_data=steps_data[:4]

        plan_source="ai"

        return ai_plan.diagnosis,ai_plan.evidence_summary,steps_data, plan_source

    except Exception as e:
        print(f"build_plan_content fallback because of error: {e}")
        diagnosis, evidence_summary, steps_data = build_fallback_plan_content(runbooks, histories)
        plan_source="fallback"
        return diagnosis, evidence_summary, steps_data , plan_source




def generate_plan(db,incident_id,runbooks,histories):
    incident=db.query(models.Incident).filter(models.Incident.id==incident_id).first()

    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="incident not found"
        )
        
    diagnosis,evidence_summary,steps_data,plan_source=build_plan_content(incident,runbooks,histories)

    if not steps_data:
        raise ValueError("generated plan has no steps")

    unsupported_tools=[
        step_data["action_type"]
        for step_data in steps_data
        if step_data["action_type"] not in VALID_ACTION_TYPES
    ]

    if unsupported_tools:
        raise ValueError(
        f"unsupported tools: {unsupported_tools}"
    )
    
    plan=models.Plan( 
        incident_id=incident_id, 
        diagnosis = diagnosis, 
        evidence_summary = evidence_summary, 
        status = c.PLAN_STATUS_GENERATED 
        )

    db.add(plan)
    db.flush()



    for index, step_data in enumerate(steps_data, start=1):

        action_type = step_data["action_type"]

        if action_type not in VALID_ACTION_TYPES:    
            raise ValueError(f"unsupported action: {action_type}")
        if action_type in registry.TOOLS:
            tool_config=TOOLS.get(action_type)
        else:
            tool_config = CONTROL_ACTIONS.get(action_type)



        if tool_config is None:
            raise ValueError(
                f"unsupported action: {action_type}"
            )

        risk_level=tool_config["risk_level"]
        approval_required=tool_config["approval_required"]

        if approval_required:
            step_status = c.STEP_STATUS_WAITING_APPROVAL
        else:
            step_status = c.STEP_STATUS_PENDING


        step = models.PlanStep(
            plan_id=plan.id,
            step_order=index,
            action_type=action_type,
            action_desc=action_type,
            risk_level=risk_level,
            status=step_status,
            approval_required=approval_required,
            execution_result=None
        )
        db.add(step)

    incident.status = c.INCIDENT_STATUS_PLAN_GENERATED

    audit_service.create_audit_log(
        db,
        incident_id,
        actor_type="agent", 
        action=c.INCIDENT_STATUS_PLAN_GENERATED, 
        detail=f"plan generated for incident {incident_id} using {plan_source}"
    )

    db.commit()
    db.refresh(plan)

    return plan


