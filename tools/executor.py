from .schemas import ToolExecutionResult
from tools.registry import TOOLS


def execute_tool(action_type,**kwargs):
    tool_config=TOOLS.get(action_type)
   
    if tool_config is None:
        return ToolExecutionResult(
            success=False,
            error="unsupported tool"
        )

    tool=tool_config["function"]

    try:
        result=tool(**kwargs)
        return ToolExecutionResult(
            success=True,
            result=result
        )

    except Exception as e:
        return ToolExecutionResult(
            success=False,
            error=f"{e}"
        )
