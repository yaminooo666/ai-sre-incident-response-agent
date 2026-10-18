from pydantic import BaseModel,ConfigDict,Field
from typing import List,Any
from datetime import datetime
from typing import Optional


class IncidentCreate(BaseModel):
    title:str
    service_name:str
    alert_type:str
    severity:int
    description:str
    created_by:str


class IncidentOut(BaseModel):
    id:int
    title:str
    service_name:str
    alert_type:str
    severity:int
    description:str
    status:str
    created_by:str
    created_at:datetime
    updated_at:datetime

    model_config = ConfigDict(from_attributes=True)


class RunbookCreate(BaseModel):
    title: str
    service_name: str
    alert_type: str
    content: str


class RunbookOut(BaseModel):
    id: int
    title: str
    service_name: str
    alert_type: str
    content: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)



class IncidentHistoryCreate(BaseModel):
    incident_title: str
    service_name: str
    alert_type: str
    severity: int
    problem_summary: str
    resolution_summary: str
    outcome: str
    


class IncidentHistoryOut(BaseModel):
    id: int
    incident_title: str
    service_name: str
    alert_type: str
    severity: int
    problem_summary: str
    resolution_summary: str
    outcome: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)




class PlanStepOut(BaseModel):
    id:int
    step_order:int
    action_type:str
    action_desc:str
    risk_level:str
    status:str
    approval_required:bool
    execution_result:Optional[str]=None

    model_config = ConfigDict(from_attributes=True)



class PlanOut(BaseModel):
    id:int
    incident_id:int
    diagnosis:str
    evidence_summary:str
    status:str
    created_at:datetime
    steps: List[PlanStepOut]

    model_config = ConfigDict(from_attributes=True)


class AuditLogOut(BaseModel):
    id:int
    actor_type:str
    action:str
    detail:str
    created_at:datetime

    model_config = ConfigDict(from_attributes=True)


class IncidentDetailOut(BaseModel):
    incident: IncidentOut
    plans: List[PlanOut]
    audit_logs: List[AuditLogOut]

    model_config = ConfigDict(from_attributes=True)



class StepApprovalRequest(BaseModel):
    approved: bool



class TraceEventOut(BaseModel):
    id: int
    incident_id: int
    run_id: str
    step_id: Optional[int]=None
    plan_id: Optional[int]=None
    event_type: str
    payload: dict[str,Any]= Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)