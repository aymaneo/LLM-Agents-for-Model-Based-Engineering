import subprocess
from langchain.tools import BaseTool

from specific_tool_agents.tools.atl.generate_description import generate_get_tool_description

class GetTransformationByNameTool(BaseTool):
    name: str
    description: str
    transformation_name: str

    def __init__(self, transformation_name):
        # Handle case when transformation_name is a tuple
        if isinstance(transformation_name, tuple) and len(transformation_name) > 1:
            transformation_name = transformation_name[1]  # Extract the string part
        
        description = generate_get_tool_description(transformation_name)
        super().__init__(
            name=f"list_transformation_{transformation_name}_tool",
            description=f"{description}. Input can be empty or the transformation name.",
            transformation_name=transformation_name
        )


    def _run(self, input_str: str = "") -> str:  # Added input parameter
        """Run the tool with the given input."""
        try:
            command = ['curl', '-X', 'GET', f'localhost:8080/transformation/{self.transformation_name}']
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            return f"The transformation '{self.transformation_name}':\n{result.stdout} successfully fetched."
        except subprocess.CalledProcessError as e:
            return f"An error occurred while fetching the transformation: {e.stderr}"