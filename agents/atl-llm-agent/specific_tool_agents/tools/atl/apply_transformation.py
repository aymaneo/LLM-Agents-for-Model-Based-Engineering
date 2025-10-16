import subprocess
from langchain.tools import BaseTool

from .generate_description import create_transformation_description

class ApplyTransformationTool(BaseTool):
    name: str
    description: str
    transformation_name: str
    
    def __init__(self, transformation_name):
        # Handle case when transformation_name is a tuple
        if isinstance(transformation_name, tuple) and len(transformation_name) > 1:
            transformation_name = transformation_name[1]  # Extract the string part
            
        description = create_transformation_description(transformation_name)
        super().__init__(
            name=f"apply_{transformation_name}_transformation_tool",
            description=f"{description}. Input should ONLY be the file path to be transformed.",
            transformation_name=transformation_name
        )

    def _run(self, input_str: str) -> str:
        if "https://" in input_str or "http://" in input_str:
            return "Error: Do NOT include any URLs. Input should ONLY be a file path."
        
        try:
            file_path = input_str.strip()
            command = [
                'curl', 
                f'localhost:8080/transformation/{self.transformation_name}/apply', 
                '-F', f'file=@{file_path}'
            ]
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            return f"Transformation {self.transformation_name} applied:\n{result.stdout}"
            
        except subprocess.CalledProcessError as e:
            return f"An error occurred while applying transformation: {e.stderr}"

