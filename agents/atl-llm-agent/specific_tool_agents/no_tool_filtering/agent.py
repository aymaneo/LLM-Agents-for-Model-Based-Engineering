import json
import subprocess
from langchain_ollama import ChatOllama
from specific_tool_agents.tools.atl.apply_transformation import ApplyTransformationTool
from specific_tool_agents.tools.atl.get_input_metamodel import ExtractInputMetamodelName
from specific_tool_agents.tools.atl.get_transformation_by_name import GetTransformationByNameTool
from langgraph.prebuilt import create_react_agent
from langchain_ollama import ChatOllama
from config.config import API_PASSWORD, API_USER, BASE_URL, OLLAMA_MAX_RETRIES, OLLAMA_MODEL, OLLAMA_TEMPERATURE
from specific_tool_agents.no_tool_filtering.prompts.system_prompt import SYSTEM_PROMPT
import sys


def create_atl_agent():

    client_kwargs = {
    "auth": (API_USER, API_PASSWORD)  
}
    llm = ChatOllama(
    model=OLLAMA_MODEL,
    temperature=OLLAMA_TEMPERATURE,
    max_retries=OLLAMA_MAX_RETRIES,
    base_url=BASE_URL,
    client_kwargs=client_kwargs,
    num_predict = 500
)

    result = subprocess.run(['curl', '-X', 'GET', 'localhost:8080/transformations/enabled'], 
                          capture_output=True, text=True, check=True)
    transformations = json.loads(result.stdout)
    transformation_names = [t["name"] for t in transformations]
    tools = []
    for i, name in enumerate(transformation_names):
        # add just 13 tools
        if i > 6:
            break
        tools.extend([
        GetTransformationByNameTool(name), 
        ApplyTransformationTool(name)
        ])

    tool_names = [tool.__class__.__name__ for tool in tools]
    
    tools.extend([ExtractInputMetamodelName()])
   # Create the LangGraph agent with the system prompt
    agent_executor = create_react_agent(
        llm,
        tools,
        state_modifier=SYSTEM_PROMPT.format(
            tools= tools,
            tool_names=tool_names
        ),
    )
    return agent_executor