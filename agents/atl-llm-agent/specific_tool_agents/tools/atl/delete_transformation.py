import subprocess
from langchain.tools import BaseTool


class DeleteTransformationTool(BaseTool):

    name: str 
    description: str 
    transformation_name: str

    def __init__(self,transformation_name):
        super().__init__(
            name=f"delete_transformation_{transformation_name}_tool",
            description=f"Delete the transformation with the name {transformation_name} ",
            transformation_name = transformation_name
        )

    def _run(self, query: str) -> str:
        try:
            command = ['curl', '-X', 'DELETE', f'localhost:8080/transformation/{self.transformation_name}']
            result = subprocess.run(command,capture_output=True, text=True, check=True)
            return f"Transformation {self.transformation_name} deleted successfully:\n{result.stdout}"
        except subprocess.CalledProcessError as e:
            return f"An error occurred while deleting transformation {self.transformation_name}: {e.stderr}"
        

