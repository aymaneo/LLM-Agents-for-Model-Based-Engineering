import subprocess
from langchain.tools import BaseTool

class ListAllTransformationsTool(BaseTool):
    name: str = "curl_all_transformations_tool"
    description: str = "Retrieves a complete list of all available transformations with their detailed configurations"

    def _run(self, query: str) -> str:
        try:
            result = subprocess.run(['curl', '-X', 'GET', 'localhost:8080/transformations/enabled'], 
                                    capture_output=True, text=True, check=True)
            return f"Available transformations:\n{result.stdout}"
        except subprocess.CalledProcessError as e:
            return f"An error occurred while fetching transformations: {e.stderr}"
