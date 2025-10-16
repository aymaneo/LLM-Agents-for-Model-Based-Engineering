import subprocess
from langchain.tools import BaseTool

class GetTransformationByNameTool(BaseTool):
    name: str = "curl_transformation_by_Name_tool"
    description: str = "Retrieves detailed informations about a single transformation by providing its name. Input should be the exact transformation name as a string"

    def _run(self, query: str) -> str:
        try:
            query = query.strip()
          
            identifier = query
            
            command = ['curl', '-X', 'GET', f'localhost:8080/transformation/{identifier}']
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            return f"The transformation with '{identifier}':\n{result.stdout}"
        except subprocess.CalledProcessError as e:
            return f"An error occurred while fetching the transformation: {e.stderr} :\n{command}"
             