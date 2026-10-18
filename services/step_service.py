import models, schemas
from fastapi import status, HTTPException
from services import audit_service
import constans as c
from tools import registry
from tools.executor import execute_tool
import json
from .tool_call_service import generate_tool_call
from services.trace_service import record_trace_event



def approve_step(db,step_id,approved):
    step=db.query(models.PlanStep).filter(models.PlanStep.id==step_id).first()
    
    if step is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="step not found"
        )

    
    incident = step.plan.incident
    if incident.status in (    
    c.INCIDENT_STATUS_RESOLVED,    
    c.INCIDENT_STATUS_MANUAL_FOLLOWUP):    
        raise HTTPException(        
        status_code=status.HTTP_409_CONFLICT,        
        detail="incident is no longer actionable"
        )


    plan = step.plan
    if plan.status == c.PLAN_STATUS_SUPERSEDED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="plan is no longer active"
        )

    
    if not step.approval_required:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="this step does not require approval"
        )

    if step.status != "waiting_approval":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="step is not waiting for approval"
        )
    
    if approved:
        step.status="approved"
    else:
        step.status="rejected"

    log=audit_service.create_audit_log(
        db,
        incident_id=step.plan.incident_id,
        actor_type="approver",
        action="step_approved" if approved else "step_rejected",
        detail=f"step {step.step_order} {'approved' if approved else 'rejected'}"
    )

    db.commit()
    db.refresh(step)
    return step






def sync_incident_status(db, incident_id):

    incident=db.query(models.Incident).filter(models.Incident.id==incident_id).first()
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="incident not found"
        )

    latest_plan=(
    db.query(models.Plan)
    .filter(models.Plan.incident_id == incident_id)
    .order_by(models.Plan.created_at.desc())
    .first()
)

    if not latest_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="new_plan not found"
        )

    steps=latest_plan.steps

    if not steps:
       raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="latest plan has no steps"
        )

    if any(step.status=="failed" for step in steps):
        incident.status=c.INCIDENT_STATUS_EXECUTION_FAILED
    elif any(step.action_type == "notify_owner" and step.status == "executed" for step in steps):
        incident.status= c.INCIDENT_STATUS_MANUAL_FOLLOWUP
    elif all(step.status == "executed" for step in steps):
        incident.status = c.INCIDENT_STATUS_VERIFYING
    else:
        incident.status = c.INCIDENT_STATUS_EXECUTING

    return incident 



def execute_step(db,step_id,run_id,restart_time=None):
    step=db.query(models.PlanStep).filter(models.PlanStep.id==step_id).first()

    
    if step is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="step not found"
        )


    incident = step.plan.incident
    if incident.status in (    
    c.INCIDENT_STATUS_RESOLVED,    
    c.INCIDENT_STATUS_MANUAL_FOLLOWUP):    
        raise HTTPException(        
        status_code=status.HTTP_409_CONFLICT,        
        detail="incident is no longer actionable"
        )


    plan = step.plan
    if plan.status == c.PLAN_STATUS_SUPERSEDED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="plan is no longer active"
        )


    if step.status == "executed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="step has already been executed"
        )

    if step.status == "rejected":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="rejected step cannot be executed"
        )

    if step.status == "failed":
        raise HTTPException(
            status_code=status.
            HTTP_400_BAD_REQUEST,
            detail="failed step cannot be executed directly"
        )
    
    incident=step.plan.incident
    if (
        (not step.approval_required and step.status=="pending")
         or (step.approval_required and step.status =="approved")
    ):
        try:
            name,validated_args = generate_tool_call(incident,step,restart_time)

        except Exception as e:
            step.status = c.STEP_STATUS_FAILED
            step.execution_result = f"call_tool_failed:{e}"
            audit_action="step_failed"

            record_trace_event(
            db=db,
            incident=incident,
            run_id=run_id,   
            event_type="tool_call_failed",    
            step_id=step.id,    
            plan_id=step.plan_id,    
            payload={        
            "expected_tool": step.action_type,    
            "error": str(e)
            }
        )


        else :

            record_trace_event(
            db=db,
            incident=incident,
            run_id=run_id,   
            event_type="tool_call_generated",    
            step_id=step.id,    
            plan_id=step.plan_id,    
            payload={        
            "tool_name": name,        
            "validated_ai_args": validated_args.model_dump()
            }
        )

            validated_args = validated_args.model_dump()
            validated_args["service_name"] = incident.service_name
            if name == c.ACTION_CHECK_METRICS and restart_time is not None:
                validated_args["restart_time"] = restart_time


            tool_result=execute_tool(
                    name,
                    **validated_args)

            if tool_result.success:
                step.status=c.STEP_STATUS_EXECUTED
                step.execution_result =json.dumps(
                    tool_result.result,
                    ensure_ascii=False,
                    default=str
                )
                audit_action="step_executed"


            else:
                step.status=c.STEP_STATUS_FAILED
                step.execution_result = tool_result.error
                audit_action="step_failed"


    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="step is not ready for execution"
        )



    if step.status == c.STEP_STATUS_EXECUTED:
        record_trace_event(
            db=db,
            incident=incident,
            run_id=run_id,   
            event_type="step_executed",    
            step_id=step.id,    
            plan_id=step.plan_id,    
            payload={
            "action_type": step.action_type,        
            "success": step.status == c.STEP_STATUS_EXECUTED  
            }
            )
    elif step.status == c.STEP_STATUS_FAILED:
        record_trace_event(
            db=db,
            incident=incident,
            run_id=run_id,   
            event_type="step_failed",    
            step_id=step.id,    
            plan_id=step.plan_id,    
            payload={
            "action_type": step.action_type,        
            "success": step.status == c.STEP_STATUS_EXECUTED  
            }
        )


    db.flush()

    sync_incident_status(db,step.plan.incident_id)

    audit_service.create_audit_log(
        db=db,
        incident_id=step.plan.incident_id,
        actor_type="system",
        action=audit_action,
        detail=f"step {step.step_order} : {step.execution_result}"
)

    db.commit()
    db.refresh(step)

    return step






def add_verification_step(db,step_id):
    restart_step=(
        db.query(models.PlanStep).
        filter(models.PlanStep.id==step_id).
        first()
        )

    if restart_step is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="restart_step not found"
        )

    if restart_step.action_type != c.ACTION_RESTART_SERVICE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="step is not a restart_service step"
        )

    plan=restart_step.plan
    
    steps=plan.steps
    ordered_steps = sorted(
            steps,
            key=lambda step: step.step_order,
            reverse=True
            )


    exist_verification = next(
        (
            step
            for step in ordered_steps
            if step.action_type==c.ACTION_CHECK_METRICS
            and step.step_order==restart_step.step_order+1
        ),
            None
        )

    if exist_verification:
        return exist_verification

    for step in ordered_steps:
        if step.step_order>restart_step.step_order:
            step.step_order+=1


    tool_config = registry.TOOLS[c.ACTION_CHECK_METRICS]

    if tool_config["approval_required"]:
        step_status = c.STEP_STATUS_WAITING_APPROVAL
    else:
        step_status = c.STEP_STATUS_PENDING


    check_step=models.PlanStep(
        step_order=restart_step.step_order+1,
        action_type=c.ACTION_CHECK_METRICS,
        action_desc="Verify service health metrics after restart",
        risk_level=tool_config["risk_level"],
        status=step_status,
        approval_required=tool_config["approval_required"],
        execution_result=None,
        plan=plan
    )
    db.add(check_step)
    db.flush()

    return check_step
   



