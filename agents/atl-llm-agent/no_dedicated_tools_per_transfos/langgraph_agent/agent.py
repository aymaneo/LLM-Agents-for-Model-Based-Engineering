from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent
from config.config import API_PASSWORD, API_USER, BASE_URL, OLLAMA_MAX_RETRIES, OLLAMA_MODEL, OLLAMA_TEMPERATURE
from no_dedicated_tools_per_transfos.tools.atl.apply_transformation import ApplyTransformationTool
from no_dedicated_tools_per_transfos.tools.atl.get_transformation_by_name import GetTransformationByNameTool
from no_dedicated_tools_per_transfos.langgraph_agent.prompts.system_prompt import SYSTEM_PROMPT

#no_dedicated_tools_per_transfos
def create_atl_agent():

    #Initialize LLM
    client_kwargs = {
    "auth": (API_USER, API_PASSWORD)  
        }
    
    llm = ChatOllama(
    model=OLLAMA_MODEL,
    temperature=OLLAMA_TEMPERATURE,
    max_retries=OLLAMA_MAX_RETRIES,
    base_url=BASE_URL,
    client_kwargs=client_kwargs,
    num_predict= 500
    )

    # Initialize tools
    tools = [
        ApplyTransformationTool(), 
        GetTransformationByNameTool() 
    ]

    # Create the LangGraph agent with the system prompt
    agent_executor = create_react_agent(
        llm,
        tools,
        state_modifier=SYSTEM_PROMPT, 
    )
    agent_executor.step_timeout= 100
    return agent_executor