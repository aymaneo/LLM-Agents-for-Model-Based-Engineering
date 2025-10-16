import subprocess
from langchain.tools import BaseTool

class GetTransformationName(BaseTool):
    name: str = "get_transformation_name"
    description: str = "Retrieves the name of a transformation based on matching input and output metamodel names. Accepts input as {'input_str': 'DSL, KM3'}. Nested formats like are not allowed. "

    def _run(self, **kwargs) -> str:
        try:
            # Extract the value from the dictionary if kwargs is not empty
            if kwargs:
                # Use the first key-value pair in kwargs
                query = next(iter(kwargs.values()))
            else:
                return "Error: No input provided."
            
            # Ensure the query is a stripped string
            query = str(query).strip()
            queryList = query.split(",")
            
            # Validate that we have two parts: inputMetamodel and outputMetamodel
            if len(queryList) != 2:
                return "Error: Input must contain exactly two comma-separated metamodel names, e.g., 'inputMetamodel, outputMetamodel'."
            
            inputMetamodel = queryList[0].strip()
            outputMetamodel = queryList[1].strip()
            
            # Construct the curl command
            command = [
                'curl',
                f'localhost:8080/transformation/hasTransformation?inputMetamodel={inputMetamodel}.ecore&outputMetamodel={outputMetamodel}.ecore'
            ]
            
            # Run the command
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            return f"{result.stdout}"
        
        except subprocess.CalledProcessError as e:
            return f"An error occurred while fetching the transformation: {e.stderr} :\n{command}"
        except Exception as e:
            return f"An unexpected error occurred: {str(e)}"
