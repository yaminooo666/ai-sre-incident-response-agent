from pydantic import BaseModel, Field
from typing import Literal, Optional



class AIGeneratedStep(BaseModel):
    action_type: str = Field(
        description=(
            "Tool action name. Must exactly match one of the currently available "
            "registered tools provided in the prompt. Do not invent new tool names."
        )
    )

    action_desc: str = Field(
        description=(
            "Concrete and concise description of what this step will do and why it "
            "is relevant to the current incident. Must be grounded in available evidence."
        )
    )

    risk_level: Literal["low", "medium", "high"] = Field(
        description=(
            "Risk level of executing the step: low for read-only observational actions, "
            "medium for limited-impact actions, and high for actions that may change "
            "service state or affect production."
        )
    )

    approval_required: bool = Field(
        description=(
            "Whether human approval is required before execution. "
            "Use true for high-risk or state-changing actions, and false for safe "
            "read-only observational actions."
        )
    )

class AIGeneratedPlan(BaseModel):
    diagnosis: str
    evidence_summary: str
    steps: list[AIGeneratedStep]

class ReEvaluationResult(BaseModel):
    decision:Literal[
        "continue",
        "modify_plan",
        "manual_followup",
        "resolved"
    ]
    reason:str
    new_steps:Optional[list[AIGeneratedStep]]=None
    updated_diagnosis: Optional[str] = None
    updated_evidence_summary: Optional[str] = None

