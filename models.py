from database import Base
from sqlalchemy import Column, Integer, String,ForeignKey,DateTime,Boolean,Text,Float
from datetime import datetime
from sqlalchemy.orm import relationship
from sqlalchemy import JSON

class Incident(Base):
    __tablename__ ="incidents"
    id=Column(Integer,primary_key=True,index=True)
    title=Column(String)
    service_name=Column(String)
    alert_type=Column(String)
    severity=Column(Integer)
    description=Column(Text)
    status=Column(String)
    created_by=Column(String)
    created_at=Column(DateTime,default=datetime.utcnow)
    updated_at=Column(DateTime,default=datetime.utcnow, onupdate=datetime.utcnow)

    plans=relationship("Plan",back_populates="incident")
    audit_logs=relationship("AuditLog",back_populates="incident")

class Plan(Base):
    __tablename__ ="plans"
    id=Column(Integer,primary_key=True,index=True)
    incident_id=Column(Integer,ForeignKey("incidents.id"))
    diagnosis=Column(Text)
    evidence_summary=Column(Text)
    status=Column(String)
    created_at=Column(DateTime,default=datetime.utcnow)

    incident=relationship("Incident",back_populates="plans")
    steps=relationship("PlanStep",back_populates="plan")

class PlanStep(Base):
    __tablename__ ="plan_steps"
    id=Column(Integer,primary_key=True,index=True)
    plan_id=Column(Integer,ForeignKey("plans.id"))
    step_order=Column(Integer)
    action_type=Column(String)
    action_desc=Column(Text)
    risk_level=Column(String)
    status=Column(String)
    approval_required=Column(Boolean,default=False)
    execution_result=Column(Text)
    created_at=Column(DateTime,default=datetime.utcnow)
    updated_at=Column(DateTime,default=datetime.utcnow, onupdate=datetime.utcnow)

    plan=relationship("Plan",back_populates="steps")
    

class Runbook(Base):
    __tablename__ ="runbooks"
    id=Column(Integer,primary_key=True,index=True)
    title=Column(String)
    service_name=Column(String)
    alert_type=Column(String)
    content=Column(Text)
    created_at=Column(DateTime,default=datetime.utcnow)
    updated_at=Column(DateTime,default=datetime.utcnow, onupdate=datetime.utcnow)


class IncidentHistory(Base):
    __tablename__ ="incident_histories"
    id=Column(Integer,primary_key=True,index=True)
    incident_title=Column(String)
    service_name=Column(String)
    alert_type=Column(String)
    severity=Column(Integer)
    problem_summary=Column(Text)
    resolution_summary=Column(Text)
    outcome=Column(String)
    created_at=Column(DateTime,default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ ="audit_logs"
    id=Column(Integer,primary_key=True,index=True)
    incident_id=Column(Integer,ForeignKey("incidents.id"))
    actor_type=Column(String)
    action=Column(String)
    detail=Column(Text)
    created_at=Column(DateTime,default=datetime.utcnow)

    incident=relationship("Incident",back_populates="audit_logs")





class TraceEvent(Base):
    __tablename__ ="trace_event"
    id=Column(Integer,primary_key=True,index=True)
    run_id=Column(String,nullable=False)
    incident_id=Column(Integer,ForeignKey("incidents.id"),nullable=False)
    step_id=Column(Integer,ForeignKey("plan_steps.id"))
    plan_id=Column(Integer,ForeignKey("plans.id"))
    event_type=Column(String,nullable=False)
    payload=Column(JSON,default=dict,nullable=False)
    created_at=Column(DateTime,default=datetime.utcnow,nullable=False)

