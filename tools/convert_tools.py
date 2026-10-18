from tools.registry import TOOLS
from google.genai import types



def convert_tool(action_type):
    result = {
        "name":None,
        "description":None,
        "parameters":None
        }

    name = action_type
    args_model = TOOLS[action_type]["args_model"]
    parameters = args_model.model_json_schema()
    description = TOOLS[action_type]["description"]

    result["name"] = name
    result["parameters"] = parameters
    result["description"] = description

    return result



def create_declarations():
    available_tools = TOOLS

    sum_declarations = []
    final = []

    for action_type in available_tools:
        result = convert_tool(action_type)
        sum_declarations.append(result)

    for declaration in sum_declarations:
        final.append(types.FunctionDeclaration(
            name = declaration["name"],
            description=declaration["description"],
            parameters_json_schema = declaration["parameters"]
        ))

   
    return final


def create_tool_declarations_bundle():

    declarations = create_declarations()

    tools = types.Tool(
        function_declarations=declarations
    )
    return tools


def create_tool_config(step):
    function_config = types.FunctionCallingConfig(
        mode = "ANY",
        allowed_function_names = [step.action_type]
    )

    tool_config = types.ToolConfig(
        function_calling_config=function_config
    )

    return tool_config