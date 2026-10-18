from services.plan_service import generate_plan
import constans as c
from tools import registry
import json
import models
from services import audit_service
from services.step_service import execute_step, add_verification_step
from services.plan_service import re_evaluate_plan,retrieve_evidence
from services.retrieval_service import retrieve_histories,retrieve_runbooks,rerank_histories,rerank_runbooks
from services.trace_service import record_trace_event
from uuid import uuid4
from datetime import datetime



def run_agent(db,incident):

    if incident.status in(
    c.INCIDENT_STATUS_RESOLVED,
    c.INCIDENT_STATUS_MANUAL_FOLLOWUP):
        return "incident already resolved or manual_followup"

    run_id = str(uuid4())

    runbooks, histories = retrieve_evidence(db, incident)

    record_trace_event(
        db=db,
        incident=incident,
        run_id = run_id,
        event_type="retrieval_completed",
        payload={
            "runbook_ids": [r.id for r in runbooks],
            "history_ids": [h.id for h in histories]
        }
    )


    if not incident.plans:
        plan=generate_plan(db,incident.id,runbooks,histories)

        record_trace_event(
        db=db,
        incident=incident,
        run_id = run_id,
        event_type="plan_generated",
        plan_id=plan.id,
        payload={
            "step_ids": [s.id for s in plan.steps],
            "actions":[s.action_type for s in plan.steps]
        }
    )
    else:
        plan=(db.query(models.Plan).
        filter(models.Plan.incident_id==incident.id 
        , models.Plan.status == c.PLAN_STATUS_GENERATED).
        order_by(models.Plan.created_at.desc()).
        first())

        if plan is None:
            incident.status = c.INCIDENT_STATUS_MANUAL_FOLLOWUP

            audit_service.create_audit_log(
                db=db,
                incident_id=incident.id,
                actor_type="system",
                action="active_plan_missing",            
                detail="incident has plan history but no active plan"
                )

            record_trace_event(
                 db=db,
                incident=incident,
                run_id=run_id,   
                event_type="active_plan_missing",          
                payload={
                "plan_ids": [p.id for p in incident.plans]
                }
            )
            db.commit()
            return




    i=0
    while i<10:
        step=get_next_step(plan)
        steps=plan.steps

        i+=1

        if step is None:
            plan_id = plan.id
            if all(s.status == c.STEP_STATUS_EXECUTED for s in steps):
                incident.status=c.INCIDENT_STATUS_MANUAL_FOLLOWUP

                audit_service.create_audit_log(
                        db=db,
                        incident_id=incident.id,
                        actor_type="system",
                        action="incident_manual_followup",
                        detail="all steps executed but not resolved"
                )

                record_trace_event(
                        db=db,
                        incident=incident,
                        run_id=run_id,   
                        event_type="no_next_step",       
                        plan_id=plan_id,    
                        payload={
                        "reason": "all_steps_executed_but_not_resolved"
                        }
                    )
            elif any(s.status == c.STEP_STATUS_FAILED for s in steps):
                incident.status=c.INCIDENT_STATUS_MANUAL_FOLLOWUP

                audit_service.create_audit_log(
                        db=db,
                        incident_id=incident.id,
                        actor_type="system",
                        action="incident_manual_followup",
                        detail="have step failed"
                    )
                record_trace_event(
                        db=db,
                        incident=incident,
                        run_id=run_id,   
                        event_type="no_next_step",    
                        plan_id=plan_id,    
                        payload={
                        "reason": "failed_step_present",    
                        "failed_step_ids": [        
                            s.id for s in steps        
                            if s.status == c.STEP_STATUS_FAILED
                        ]
                        }
                    )
            
            db.commit()
            break 

        if step.status==c.STEP_STATUS_WAITING_APPROVAL:#等于跳出agent循环 变为人工审批
            record_trace_event(
                    db=db,
                    incident=incident,
                    run_id=run_id,   
                    event_type="approval_waiting",    
                    step_id=step.id,    
                    plan_id=step.plan_id,    
                    payload={
                    "action_type": step.action_type
                    }
                )
            
            db.commit()
            break

        if step.status==c.STEP_STATUS_REJECTED:
            incident.status=c.INCIDENT_STATUS_MANUAL_FOLLOWUP

            audit_service.create_audit_log(
                    db=db,
                    incident_id=incident.id,
                    actor_type="agent",
                    action="incident_manual_followup",
                    detail="rejected step triggered manual followup"
                )
            record_trace_event(
                db=db,
                incident=incident,
                run_id=run_id,   
                event_type="rejected_step_encountered",    
                step_id=step.id,    
                plan_id=step.plan_id,    
                payload={
                "action_type": step.action_type,        
                "status": step.status
                }
            )

            db.commit()
            break

        if step.action_type == c.ACTION_NOTIFY_OWNER:
            incident.status=c.INCIDENT_STATUS_MANUAL_FOLLOWUP
            step.status = c.STEP_STATUS_EXECUTED

            audit_service.create_audit_log(
                    db=db,
                    incident_id=incident.id,
                    actor_type="agent",
                    action="incident_manual_followup",
                    detail="control action notify_owner triggered manual followup"
                )
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

            db.commit()
            break



        restart_time = None
        for p in incident.plans:
            for s in p.steps:
                if s.action_type == c.ACTION_RESTART_SERVICE and s.status == c.STEP_STATUS_EXECUTED:
                    exe_re = s.execution_result
                    exe_re = json.loads(exe_re)

                    tamp = exe_re.get("last_restart_at")
                    if not tamp:
                        raise ValueError(
                        f"Executed restart step {s.id} missing last_restart_at"
                    )

                    tamp = datetime.fromisoformat(tamp)

                    if restart_time is None:
                        restart_time = tamp
                    else:
                        restart_time = max(restart_time , tamp) 


        execute_step(db,step.id,run_id,restart_time)


        tool_config = registry.TOOLS[step.action_type]

        if (
            step.status==c.STEP_STATUS_EXECUTED
            and tool_config.get("requires_verification",False)
        ):
            add_verification_step(db,step.id)

            record_trace_event(
            db=db,
            incident=incident,
            run_id=run_id,   
            event_type="add_verification",    
            step_id=step.id,    
            plan_id=step.plan_id,    
            payload={
            "source_action": step.action_type,    
            "verification_tool": tool_config["verification_tool"]
            }
        )
            continue


        result=re_evaluate_plan(incident, plan, steps,runbooks,histories)

        record_trace_event(
            db=db,
            incident=incident,
            run_id=run_id,   
            event_type="re_evaluate",    
            step_id=step.id,    
            plan_id=step.plan_id,    
            payload={
            "decision": result.decision,
            "trigger": "post_step_execution"
            }
        )

        if result.decision == "resolved":
            allow, next_action, reason = evaluate_resolution(steps)

            record_trace_event(
            db=db,
            incident=incident,
            run_id=run_id,   
            event_type="evaluate_resolution", 
            plan_id= plan.id,
            payload={
            "allow": allow,
            "reason": reason,
            "next_action": next_action
            }
        )

            if allow:
                incident.status = c.INCIDENT_STATUS_RESOLVED
                
                audit_service.create_audit_log(
                db=db,
                incident_id=incident.id,
                actor_type="agent",
                action="incident_resolved",
                detail=reason
            )
                db.commit()

                break

            if next_action == "continue":
                continue

            if next_action == "wait_for_approval":
                next_step = None
                for s in steps:
                    if s.status == c.STEP_STATUS_WAITING_APPROVAL:
                        next_step = s
                        break
                
                if next_step is not None:
                    record_trace_event(
                        db=db,
                        incident=incident,
                        run_id=run_id,   
                        event_type="approval_waiting",
                        step_id=next_step.id,    
                        plan_id=next_step.plan_id,    
                        payload={
                        "action_type": next_step.action_type
                        }
                    )
                else:
                    incident.status = c.INCIDENT_STATUS_MANUAL_FOLLOWUP

                    audit_service.create_audit_log(
                        db=db,
                        incident_id=incident.id,
                        actor_type="system",
                        action="incident_manual_followup",
                        detail="wait_for_approval returned but no waiting approval step found"
                    )

                    record_trace_event(
                        db=db,
                        incident=incident,
                        run_id=run_id,   
                        event_type="approval_state_inconsistent",  
                        plan_id=plan.id,    
                        payload={
                        "reason": "wait_for_approval returned but no waiting approval step found"
                        }
                    )

                db.commit()
                break

            if next_action == "re_evaluate":
                result = re_evaluate_plan(
                    incident,
                    plan,
                    steps,
                    runbooks,
                    histories,
                    system_feedback=reason,
                    allow_resolved=False
                )
                record_trace_event(
                db=db,
                incident=incident,
                run_id=run_id,   
                event_type="re_evaluate",    
                step_id=step.id,    
                plan_id=step.plan_id,    
                payload={
                "decision": result.decision,
                "trigger": "resolution_guard"
                }
            )
                

            elif next_action == "manual_followup":
                incident.status = c.INCIDENT_STATUS_MANUAL_FOLLOWUP

                audit_service.create_audit_log(
                    db=db,
                    incident_id=incident.id,
                    actor_type="agent",
                    action="incident_manual_followup",
                    detail=reason
                )


                db.commit()
                break

            elif next_action == "system_error":
                incident.status = c.INCIDENT_STATUS_MANUAL_FOLLOWUP

                audit_service.create_audit_log(
                    db=db,
                    incident_id=incident.id,
                    actor_type="system",
                    action="resolution_validation_failed",
                    detail=reason
                )

                db.commit()
                break
    


        if result.decision=="continue":
            continue

        elif result.decision=="modify_plan":
            old_plan = plan
            plan=create_revised_plan(db,incident,result,old_plan)
            steps=plan.steps

            record_trace_event(
            db=db,
            incident=incident,
            run_id=run_id,   
            event_type="modify_plan", 
            plan_id= plan.id,
            payload={
            "step_ids":[s.id for s in steps],
            "actions": [s.action_type for s in steps],
            "previous_plan_id":old_plan.id
            }
        )


        elif result.decision=="manual_followup":
            incident.status=c.INCIDENT_STATUS_MANUAL_FOLLOWUP

            audit_service.create_audit_log(
                db=db,
                incident_id=incident.id,
                actor_type="agent",
                action="incident_manual_followup",
                detail=result.reason
            )

            db.commit()
            break
                
    
    else:
        incident.status=c.INCIDENT_STATUS_MANUAL_FOLLOWUP

        audit_service.create_audit_log(
        db=db,
        incident_id=incident.id,
        actor_type="system",
        action="agent_iteration_limit_reached",
        detail="Agent reached the maximum iteration limit without resolving the incident"
    )

        record_trace_event(
        db=db,
        incident=incident,
        run_id=run_id,
        event_type="iteration_limit_reached",
        plan_id=plan.id,
        payload={
            "max_iterations": 10,
            "incident_status": c.INCIDENT_STATUS_MANUAL_FOLLOWUP
        }
    )
        db.commit()

   



def get_next_step(plan):
    steps=sorted(plan.steps,key=lambda step:step.step_order)
    
    for step in steps:
        if step.status=="failed" or step.status=="executed":
            continue

        return step
    return None
    






def create_revised_plan(db,incident,result,old_plan):
    steps=result.new_steps

    ai_steps = []
    for index,ai_step in enumerate(steps,start=1):

        if ai_step.action_type not in registry.VALID_ACTION_TYPES:
            raise ValueError(f"unsupported action: {ai_step.action_type}")

        if ai_step.action_type in registry.TOOLS:
            tool_config=registry.TOOLS.get(ai_step.action_type)
        else:
            tool_config = registry.CONTROL_ACTIONS.get(ai_step.action_type)

        if tool_config is None:
            raise ValueError(f"unsupported action: {ai_step.action_type}")

        risk_level=tool_config["risk_level"]
        approval_required=tool_config["approval_required"]

        if approval_required:
            status=c.STEP_STATUS_WAITING_APPROVAL
        else: status=c.STEP_STATUS_PENDING

        ai_steps.append(
            {
                "step_order": index,        
                "action_type": ai_step.action_type,        
                "action_desc": ai_step.action_desc,        
                "risk_level": risk_level,        
                "approval_required": approval_required,        
                "status": status
            }
        )
    
    
    
    new_plan=models.Plan(
        incident_id=incident.id,
        diagnosis = result.updated_diagnosis,
        evidence_summary = result.updated_evidence_summary,
        status = c.PLAN_STATUS_GENERATED
    )
    db.add(new_plan)
    db.flush()

    for ai_step in ai_steps:

        step = models.PlanStep(
        plan_id=new_plan.id,
        step_order= ai_step["step_order"],
        action_type=ai_step["action_type"],
        action_desc=ai_step["action_desc"],
        risk_level=ai_step["risk_level"],
        approval_required=ai_step["approval_required"],
        status=ai_step["status"],
        execution_result=None
        )   
        db.add(step)


    incident.status=c.INCIDENT_STATUS_PLAN_GENERATED

    audit_service.create_audit_log(
        db=db,
        incident_id=incident.id,
        actor_type="agent",
        action=c.AUDIT_ACTION_PLAN_REVISED,
        detail=result.reason
    )

    old_plan.status = c.PLAN_STATUS_SUPERSEDED
    
    db.commit()
    db.refresh(new_plan)
    return new_plan




    


def evaluate_resolution(steps):
      
        
        if not steps:
            return False, "re_evaluate", "no plan steps available"

        if any((step.action_type==c.ACTION_NOTIFY_OWNER 
            and step.status==c.STEP_STATUS_EXECUTED) for step in steps):
             return False, "manual_followup", "notify_owner has already been executed"

        if any(step.status == c.STEP_STATUS_REJECTED for step in steps):
            return False, "manual_followup", "step status is rejected"

        if any(step.status == c.STEP_STATUS_FAILED for step in steps):
            return False, "re_evaluate", "step status is failed"
        
        if any(step.status in(c.STEP_STATUS_PENDING,c.STEP_STATUS_APPROVED) for step in steps):
            return False, "continue", "step status need execute"

        if any(step.status == c.STEP_STATUS_WAITING_APPROVAL for step in steps):
            return False, "wait_for_approval", "step status need approve"

        if any(step.status!=c.STEP_STATUS_EXECUTED for step in steps):
            return False, "system_error", "all steps need execute"

        
        verification_steps = []
        for step in steps:
            if registry.TOOLS[step.action_type]["requires_verification"]:
                verification_step = next(
                    (s
                    for s in steps
                    if (s.step_order==step.step_order+1
                    and s.action_type==c.ACTION_CHECK_METRICS)
                    ),
                    None
                )

                if verification_step is None:
                    return False, "system_error", "no verification steps available"

                if verification_step.execution_result is None:
                    return False, "system_error", "executed verification step has no execution result"
                
                verification_steps.append(verification_step)
        


        latest_verification_order = (
            max(step.step_order for step in verification_steps)
            if verification_steps
            else None
        )
        for step in steps:
            
            if step.action_type != c.ACTION_CHECK_METRICS:        
                continue
           
            if (
                latest_verification_order is not None 
                and step.step_order < latest_verification_order
            ):
                continue

            if step.execution_result is None:
                return False, "system_error", "executed metrics step has no execution result"

            result=json.loads(step.execution_result)

            if result["abnormal_reasons"]:
                return False, "re_evaluate", "metrics shows the incident is still abnormal"

        
        if all(step.action_type!=c.ACTION_CHECK_METRICS for step in steps):
            return False, "re_evaluate", "no plan step in check metrics"

        return True, "resolved", "all resolution conditions are satisfied"