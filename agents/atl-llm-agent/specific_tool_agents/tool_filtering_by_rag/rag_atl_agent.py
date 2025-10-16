from typing import Annotated, TypedDict
from langchain_ollama import ChatOllama
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OllamaEmbeddings
from langchain_core.documents import Document
import json
from atl_mcp_server.atl_mcp_server import get_transformation_names
from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from specific_tool_agents.atl_mcp_client import MCPClient
from config.config import API_PASSWORD, API_USER, OLLAMA_MODEL, OLLAMA_TEMPERATURE, OLLAMA_MAX_RETRIES, BASE_URL
from  specific_tool_agents.transformation_agent.prompts.system_prompt import SYSTEM_PROMPT
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_mcp_adapters.tools import load_mcp_tools


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
            max_retries=OLLAMA_MAX_RETRIES
            #base_url="https://ollama.kher.nl"
            #client_kwargs=client_kwargs,
            #num_predict=500
        )
        self.tool_registry = {}
        
        # Initialize RAG components
        self.embeddings = OllamaEmbeddings(
            model=OLLAMA_MODEL
            #base_url="https://ollama.kher.nl"
        )
        self.vector_store = None

    async def initialize_rag(self):  # ← CHANGED: Removed underscore from method name
        """Initialize the RAG vector store with transformation tools."""
        try:
            print("Initializing RAG...")  # Added logging
            # Get tools with descriptions from MCP client
            session = await self.client.get_session()
            response = await session.list_tools()
            available_tools = {tool.name: tool for tool in response.tools}
            
            transformation_names = get_transformation_names()
            documents = []
            
            # Create documents for each transformation tool
            for name in transformation_names:
                # Get descriptions for both list and apply tools
                list_tool_name = f"list_transformation_{name}_tool"
                apply_tool_name = f"apply_{name}_transformation_tool"
                
                descriptions = []
                if list_tool_name in available_tools:
                    descriptions.append(available_tools[list_tool_name].description)
                if apply_tool_name in available_tools:
                    descriptions.append(available_tools[apply_tool_name].description)
                
                # Combine descriptions
                combined_description = " ".join(descriptions) if descriptions else f"Transformation tool for {name}"
                
                # Create document content that includes the tool name and descriptions
                content = f"Tool: {name}\nTransformation: {name}\nName: {name}\nDescription: {combined_description}"
                
                # Create metadata for better retrieval
                metadata = {
                    "tool_name": name,
                    "apply_tool": f"apply_{name}_transformation_tool",
                    "list_tool": f"list_transformation_{name}_tool"
                }
                
                doc = Document(
                    page_content=content,
                    metadata=metadata
                )
                documents.append(doc)
            
            # Create vector store
            if documents:
                self.vector_store = FAISS.from_documents(documents, self.embeddings)
                print(f"RAG initialized successfully with {len(documents)} transformation tools")
            else:
                raise Exception("No transformation tools found for RAG initialization")
                
        except Exception as e:
            print(f"Failed to initialize RAG: {str(e)}")
            raise e 

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
        """Select tools using RAG-based retrieval - limited to exactly 10 tools."""
        if self.vector_store is None:
            print("Vector store not initialized")
            raise RuntimeError("RAG not initialized. Vector store is None.")

        try:
            # Prepare search query
            user_message = state["messages"][-1].content
            search_query = user_message
            
            # Enhanced search query with metamodel information
            if state["file_paths"]:
                metamodels = [f.get('metamodel', 'Unknown') for f in state["file_paths"]]
                search_query = f"{user_message} {' '.join(metamodels)}"
            
            print(f"RAG search query: {search_query}")
            
            # Perform similarity search
            retrieved_docs = self.vector_store.similarity_search(
                search_query, 
                k=5 
            )
            
            print(f"RAG found {len(retrieved_docs)} relevant documents")
            
            # Extract tool names from retrieved documents (limited to first 10)
            selected_tool_names = []
            for doc in retrieved_docs[:10]: 
                tool_name = doc.metadata.get("tool_name")
                if tool_name and tool_name not in selected_tool_names:
                    selected_tool_names.append(tool_name)
            
            # Create exactly 10 tool IDs for the selected tools (5 transformations * 2 tools each)
            selected_tool_ids = []
            for name in selected_tool_names[:10]:  # 
                selected_tool_ids.extend([
                    f"list_transformation_{name}_tool", 
                    f"apply_{name}_transformation_tool"
                ])
            
            # If RAG didn't find relevant tools, fail
            if not selected_tool_ids:
                print("RAG search returned no relevant tools")
                raise RuntimeError("RAG search returned no relevant tools.")
            
            # Filter tools based on metamodel compatibility if file paths exist
            if state["file_paths"]:
                try:
                    session = await self.client.get_session()
                    response = await session.list_tools()
                    available_tools = {tool.name: tool for tool in response.tools}
                    
                    compatible_tools = []
                    metamodels = [f.get('metamodel', '').lower() for f in state["file_paths"]]
                    
                    for tool_id in selected_tool_ids:
                        if tool_id in available_tools:
                            tool = available_tools[tool_id]
                            description = tool.description.lower()
                            
                            # Check if any metamodel is mentioned in the tool description
                            if any(metamodel in description for metamodel in metamodels if metamodel):
                                compatible_tools.append(tool_id)
                    
                    # Use compatible tools if found, otherwise use original selection
                    if compatible_tools:
                        # Limit to 10 tools even after filtering
                        selected_tool_ids = compatible_tools[:10]
                        print(f"Filtered to {len(selected_tool_ids)} metamodel-compatible tools")
                    else:
                        # Ensure we don't exceed 10 tools
                        selected_tool_ids = selected_tool_ids[:10]
                        
                except Exception as e:
                    print(f"Error filtering tools by metamodel: {str(e)}")
                    # Ensure we don't exceed 10 tools
                    selected_tool_ids = selected_tool_ids[:10]
            else:
                # Ensure we don't exceed 10 tools
                selected_tool_ids = selected_tool_ids[:10]
            
            state["selected_tools"] = selected_tool_ids
            print(f"RAG selected exactly {len(selected_tool_ids)} tools: {selected_tool_ids}")
            
        except Exception as e:
            print(f"Error in RAG tool selection: {str(e)}")
            raise e
        
        return state

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
        """Create the agent's graph"""
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
