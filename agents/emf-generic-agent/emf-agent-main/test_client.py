import asyncio
import sys
import json
from typing import Optional, Dict, List, Any
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class EMFMCPTestClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.current_session_id: Optional[str] = None
        self.created_objects: Dict[str, List[Any]] = {}

    async def connect_to_server(self, server_script_path: str):
        """Connect to the EMF MCP server using stdio transport."""
        server_params = StdioServerParameters(command="python", args=[server_script_path])
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        await self.session.initialize()
        print("Connected to EMF MCP server")

    async def call_tool(self, name: str, args: dict = None):
        """Call a tool and return the result content."""
        try:
            result = await self.session.call_tool(name, args or {})
            content = result.content[0].text if result.content else "No content"
            print(f"\nCalling {name}:")
            print(content)
            return content
        except Exception as e:
            print(f"Error calling {name}: {e}")
            return None

    async def test_complete_workflow(self, metamodel_path: str):
        """Test the complete workflow from session creation to object manipulation."""
        print("Starting complete workflow test")
        
        # Start a new metamodel session
        session_result = await self.call_tool("start_metamodel_session", 
                                            {"metamodel_file_path": metamodel_path})
        if session_result:
            session_data = json.loads(session_result)
            self.current_session_id = session_data.get('sessionId')
            session_short = self.current_session_id[:8]
            print(f"Session ID: {session_short}")

        # Get session information
        await self.call_tool("get_session_info", {"session_id": self.current_session_id})
        
        # Create test objects
        print("\nCreating objects...")
        family_result = await self.call_tool(f"create_family_{session_short}")
        father_result = await self.call_tool(f"create_member_{session_short}")
        mother_result = await self.call_tool(f"create_member_{session_short}")
        son_result = await self.call_tool(f"create_member_{session_short}")
        
        # Extract object IDs from creation results
        family_id = self.extract_id(family_result)
        father_id = self.extract_id(father_result) 
        mother_id = self.extract_id(mother_result)
        son_id = self.extract_id(son_result)
        
        print(f"Created: Family({family_id}), Father({father_id}), Mother({mother_id}), Son({son_id})")

        # List all objects in the session
        await self.call_tool("list_session_objects", {"session_id": self.current_session_id})

        # Update object features
        print("\nUpdating object features...")
        if all([family_id, father_id, mother_id, son_id]):
            # Set individual names
            await self.call_tool(f"update_member_firstName_{session_short}", 
                               {"object_id": str(father_id), "value": "John"})
            await self.call_tool(f"update_member_firstName_{session_short}", 
                               {"object_id": str(mother_id), "value": "Jane"})
            await self.call_tool(f"update_member_firstName_{session_short}", 
                               {"object_id": str(son_id), "value": "Junior"})
            
            # Establish family relationships
            await self.call_tool(f"update_family_father_{session_short}", 
                               {"object_id": str(family_id), "value": str(father_id)})
            await self.call_tool(f"update_family_mother_{session_short}", 
                               {"object_id": str(family_id), "value": str(mother_id)})
            await self.call_tool(f"update_family_sons_{session_short}", 
                               {"object_id": str(family_id), "value": str(son_id)})
            
            # Set family surname
            await self.call_tool(f"update_family_lastName_{session_short}", 
                               {"object_id": str(family_id), "value": "Smith"})

        # Show final state of all objects
        print("\nFinal state of objects:")
        await self.call_tool("list_session_objects", {"session_id": self.current_session_id})

        # Test list functionality
        print("\nTesting list functionality...")
        await self.call_tool(f"update_family_father_{session_short}", {"object_id": "list"})

    def extract_id(self, result_text: str) -> Any:
        """Extract object ID from the creation result text."""
        if not result_text:
            return None
        try:
            lines = result_text.split('\n')
            for line in lines:
                if 'ID:' in line:
                    id_part = line.split('ID:')[1].split('(')[0].strip()
                    # Try to convert to integer if possible
                    try:
                        return int(id_part)
                    except:
                        return id_part
        except:
            pass
        return None

    async def cleanup(self):
        """Clean up resources and close connections."""
        try:
            await self.exit_stack.aclose()
        except Exception as e:
            print(f"Cleanup error: {e}")

async def main():
    if len(sys.argv) < 2:
        print("Usage: python test_client.py <mcp_server.py> [metamodel_file]")
        sys.exit(1)

    server_path = sys.argv[1]
    metamodel_path = sys.argv[2] if len(sys.argv) > 2 else "/Users/zakariahachm/Documents/Phd_Zakaria/EmfServer/uploads/Family.ecore"
    
    client = EMFMCPTestClient()
    
    try:
        await client.connect_to_server(server_path)
        await client.test_complete_workflow(metamodel_path)
        print("\nTesting completed successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
    print("Exiting test client.")
    sys.exit(0)
# End of test_client.py
