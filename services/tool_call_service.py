from tools.convert_tools import create_tool_config,create_tool_declarations_bundle
from tools.registry import TOOLS
from services.llm_client import client
from config import settings
from google.genai import types
import constans as c



def generate_tool_call(incident, step, restart_time = None):
    
    tool_config = create_tool_config(step)
    declarations_tool = create_tool_declarations_bundle()

    
    prompt = f"""
    
    Generate exactly ONE function call for the current PlanStep.
    Do not generate parallel function calls.
    Do not call the same function more than once.

    Current incident:
    - title: {incident.title}
    - service_name: {incident.service_name}
    - alert_type: {incident.alert_type}
    - severity: {incident.severity}
    - description: {incident.description}

    Current step:
    - action_type: {step.action_type}
    - action_desc: {step.action_desc}

    """
    if (restart_time is not None
    and step.action_type == c.ACTION_CHECK_METRICS):
        prompt += f"""
        Verification context:
        - This metrics check is part of post-restart verification.
        - The service was restarted at: {restart_time}
        - Choose appropriate metrics and a recent time window to verify service recovery.
        """
    response=client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[declarations_tool],
                tool_config=tool_config
            )
        )
        
    function_calls = response.function_calls

    if not function_calls:
        raise ValueError("Gemini returned no function call")
    if len(function_calls) != 1:
        raise ValueError("Gemini returned multiple function calls")

    function_call = function_calls[0]


    if not function_call.name:
        raise ValueError("Function call has no name")
    if function_call.name not in TOOLS:
        raise ValueError(
            f"Unsupported tool: {function_call.name}"
    )
    if function_call.name != step.action_type:
        raise ValueError(        
            f"Tool call mismatch: expected {step.action_type}, "        
            f"got {function_call.name}"
        )
    

    validated_args = validate_tool_call_args(function_call)

    return function_call.name,validated_args
        
    
        


def validate_tool_call_args(function_call):

    args_model = TOOLS.get(function_call.name)["args_model"]

    validated_args = args_model.model_validate(
            function_call.args
    )
    return validated_args
