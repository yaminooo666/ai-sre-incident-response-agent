from pydantic import BaseModel
from typing import Optional,Any

class ToolExecutionResult(BaseModel):
    success: bool
    result: Any = None
    error: Optional[str] = None