from typing import List, Dict, Any, Annotated, TypedDict
from langchain_ollama import ChatOllama
import json
import re
from atl_mcp_server.atl_mcp_server import get_transformation_names
from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from specific_tool_agents.atl_mcp_client import MCPClient
from config.config import API_PASSWORD, API_USER, OLLAMA_MODEL, OLLAMA_TEMPERATURE, OLLAMA_MAX_RETRIES, BASE_URL
from prompts.system_prompt import SYSTEM_PROMPT
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_mcp_adapters.tools import load_mcp_tools


TOOLS_PER_BATCH = 6
MAX_TRANSFORMATIONS = 12  # Limit to first 12 transformations

class State(TypedDict):
    messages: Annotated[list, add_messages]
    selected_tools: list[str]
    metamodel_name: str | None
    file_paths: list[dict]

class ATLAgent:

    def __init__(self, client: MCPClient):
        client_kwargs = {
            "auth": (API_USER, API_PASSWORD)
        }
        self.client = client
        self.model = ChatOllama(
            model=OLLAMA_MODEL,
            temperature=OLLAMA_TEMPERATURE,
            max_retries=OLLAMA_MAX_RETRIES,
            base_url=BASE_URL,
            client_kwargs=client_kwargs,
            num_predict=500
        )
        self.tool_registry = {}

    async def analyze_input(self, state: State) -> State:
        """Analyze input to extract file paths and metamodels."""
        message = state["messages"][-1].content
        state["metamodel_name"] = None
        state["file_paths"] = []
        session = await self.client.get_session()
        
        has_file_path = any(ext in message.lower() for ext in ['.xmi', '.ecore', '.atl'])
        if has_file_path:
            file_path_prompt = f"""Extract the file paths from this text and return ONLY a JSON object with this exact format: {{"file_paths": [paths_here]}}
    Do not include any additional text, explanations, or formatting - just the JSON object.
    Text to analyze: {message}"""
            
            try:
                response = self.model.invoke(file_path_prompt).content.strip()
                json_str = response.replace('```json', '').replace('```', '').strip()
                file_paths_data = json.loads(json_str)
                file_paths = file_paths_data.get("file_paths", [])

                for file_path in file_paths:
                    try:
                        result = await session.call_tool("extract_input_metamodel_name", {"file_path": file_path})
                        if isinstance(result.content, str):
                            file_info = {
                                "path": file_path,
                                "metamodel": result.content
                            }
                            state["file_paths"].append(file_info)
                            if state["metamodel_name"] is None:
                                state["metamodel_name"] = result
                    except Exception as e:
                        print(f"Error extracting metamodel for {file_path}: {str(e)}")
                        continue
            except Exception as e:
                print(f"Error analyzing input: {str(e)}")
        return state

    async def select_tools(self, state: State) -> State:
        """Select tools based on the input analysis."""
        # if not state["file_paths"]:
        #     return state

        session = await self.client.get_session()
        transformation_names = get_transformation_names()[:MAX_TRANSFORMATIONS]
        response = await session.list_tools()
        available_tools = [{
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        } for tool in response.tools]

        scored_tools = []
        for i in range(0, len(transformation_names), TOOLS_PER_BATCH):
            batch = transformation_names[i:i + TOOLS_PER_BATCH]
            batch_scored_tools = self.evaluate_tools_batch(
                state["messages"][-1].content,
                state["file_paths"],
                batch,
                available_tools
            )
            scored_tools.extend(batch_scored_tools)

        scored_tools.sort(key=lambda x: x["relevance_score"], reverse=True)
        top_tools = scored_tools[:10]
        selected_tool_names = [tool["tool_name"] for tool in top_tools]
        
        selected_tool_ids = []
        for name in selected_tool_names:
            selected_tool_ids.extend([f"list_transformation_{name}_tool", f"apply_{name}_transformation_tool"])

        if not selected_tool_ids and transformation_names and state["file_paths"]:
            for file_info in state["file_paths"]:
                metamodel = file_info["metamodel"].lower()
                matching_tool = next((name for name in transformation_names if metamodel in name.lower()), None)
                tool_name = matching_tool if matching_tool else transformation_names[0]
                selected_tool_ids.extend([f"list_transformation_{name}_tool", f"apply_{name}_transformation_tool"])

        state["selected_tools"] = selected_tool_ids
        return state

    def evaluate_tools_batch(self, user_message: str, file_paths: List[Dict], names_batch: List[str], available_tools: List[Dict]) -> List[Dict]:
        """Evaluate a batch of tool names and return them with relevance scores"""
        tools_list = "\n".join([
            f"Tool {i+1}:\n- Name: {f'{name}'}\n- Description: {next((tool['description'] for tool in available_tools if tool['name'] == f'apply_{name}_transformation_tool'), 'No description available')}\n"
            for i, name in enumerate(names_batch)
        ])

        context = ""
        if file_paths:
            context = "\nInput Source Metamodels:\n"
            metamodels = [f"{f.get('metamodel', 'Unknown')}" for f in file_paths]
            context += ", ".join(metamodels)
            context += "\nCRITICAL: Only use transformations where these metamodels (if they exists) are the input/source model in the transformation description.\n"
        else:
            context = "No input files detected. Analyzing user request directly.\n"

        prompt = f'''System: You are a tool selection expert. Your task is to analyze transformation tools and select those that are directly relevant to the user's request. 
**The provided context is CRUCIAL in determining which tools are relevant.** The selection should be based primarily on the input metamodels and the user's request.

User Request:
"{user_message}"

Based on this information context: 
{context}

Choose one or more tools from the available list according to the following instructions, and assign them a relevance score from 0 to 5 (where 5 is most relevant):
{tools_list}

Selection Instructions:
1. **Extract the input metamodel(s) from the context.**  
2. **ONLY choose tools that have this extracted metamodel as their source.**  
3. If no tools match the extracted metamodel, return an empty response.  
4. Input_model of the tool description **must** match the extracted metamodel. 
5. You may choose multiple tools if they all transform the extracted input metamodel.  
6. If no input metamodel is provided, analyze the user's request directly.  

Scoring Rules:
- 5: Essential for this task, perfectly matches the user's need
- 4: Very relevant, highly useful for the task
- 3: Relevant, would be helpful
- 2: Somewhat relevant
- 1: Minimally relevant
- 0: Not relevant at all (don't include these in your response)

Response Format:
Return a JSON object with tool numbers as keys and their relevance scores as values, like this:
{{
"1": 5,
"3": 4,
"5": 3
}}

DO NOT include tools with a score of 0.
DO NOT add any explanation or extra text.
ONLY return the JSON object.'''

        response = self.model.invoke(prompt).content.strip()
        
        try:
            json_pattern = r'\{.*\}'
            match = re.search(json_pattern, response, re.DOTALL)
            scored_tools = json.loads(match.group()) if match else {}
            
            result = []
            for tool_idx_str, score in scored_tools.items():
                try:
                    tool_idx = int(tool_idx_str) - 1
                    if 0 <= tool_idx < len(names_batch):
                        result.append({
                            "tool_name": names_batch[tool_idx],
                            "relevance_score": score
                        })
                except ValueError:
                    continue
                    
            return sorted(result, key=lambda x: x["relevance_score"], reverse=True)
        except Exception as e:
            print(f"Error parsing tool scores: {str(e)}")
            return []

    async def agent(self, state: State) -> State:
        """Process the state using the selected tools."""
        session = await self.client.get_session()
        response = await session.list_tools()
        
        # Format tools properly for the LLM
        base_tools = [{
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.inputSchema
        } for tool in response.tools if tool.name == "extract_input_metamodel_name"]
        
        selected_tools = [{
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.inputSchema
        } for tool in response.tools if tool.name in state["selected_tools"]]
        
        all_tools = base_tools + selected_tools
        
        # Create tool info for the prompt
        tools_info = "\n".join([f"- {tool['name']}: {tool['description']}" for tool in all_tools])
        
        context = ""
        if state["file_paths"]:
            context = "\nInput Source Metamodels:\n"
            metamodels = [f"{f.get('metamodel', 'Unknown')}" for f in state["file_paths"]]
            context += ", ".join(metamodels)
            context += "\nCRITICAL: Only use transformations where these metamodels are the input/source model in the transformation description.\n"
        
        full_prompt = f"{SYSTEM_PROMPT}\n\nAvailable tools:\n{tools_info}{context}"
        state["messages"].insert(0, {"role": "system", "content": full_prompt})

        # Bind tools to the model
        llm_with_tools = self.model.bind_tools(all_tools)
        
        # Process the state
        return {"messages": [llm_with_tools.invoke(state["messages"])]}

    async def create_agent(self):
        """Run the agent's chat loop"""
        session = await self.client.get_session()
        # Create the graph
        builder = StateGraph(State)
        builder.add_node("analyze_input", self.analyze_input)
        builder.add_node("select_tools", self.select_tools)
        builder.add_node("agent", self.agent)
        
        # Create tools from MCP tools
        tools = await load_mcp_tools(session)
        builder.add_node("tools", ToolNode(tools=tools))

        builder.add_edge(START, "analyze_input")
        builder.add_edge("analyze_input", "select_tools")
        builder.add_edge("select_tools", "agent")
        builder.add_conditional_edges("agent", tools_condition, path_map=["tools", "__end__"])
        builder.add_edge("tools", "agent")

        return builder.compile()


 