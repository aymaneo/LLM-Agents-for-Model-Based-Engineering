import subprocess
from langchain.tools import BaseTool

# Apply transformation to the class
class ApplyTransformationTool(BaseTool):
    name: str = "curl_apply_transformation_tool"
    description: str = "Executes a transformation on a specified file. Input must be provided in the format: 'transformation_name,file_path' (note the comma separator)."

    def _run(self, input_str: str) -> str:
        if "https://" in input_str or "http://" in input_str:
            return "Error: Do NOT include any URLs. Input should ONLY be in the format 'transformation_name,file_path'."
        
        try:
            parts = input_str.split(',')
            if len(parts) != 2:
                return "Error: Input MUST have exactly two parts separated by a comma. Format: 'transformation_name,file_path'."
            
            transformation_name = parts[0].strip() 
            file_path = parts[1].strip()

            command = [
                'curl', 
                f'localhost:8080/transformation/{transformation_name}/apply', 
                '-F', f'IN=@{file_path}'
            ]

            result = subprocess.run(command, capture_output=True, text=True, check=True)
            # Return raw output without formatting
            return result.stdout
        except subprocess.CalledProcessError as e:
            return f"An error occurred while applying transformation: {e.stderr}"