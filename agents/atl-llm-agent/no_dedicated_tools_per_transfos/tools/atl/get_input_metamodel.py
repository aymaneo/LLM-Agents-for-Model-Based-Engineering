import re
from langchain.tools import BaseTool

class ExtractInputMetamodelName(BaseTool):
    name: str = "extract_input_metamodel_name"
    description: str = "Extracts the metamodel name from an XMI file. The input should be exactly a file path to an XMI file. Returns the metamodel name (like 'Class', 'Grafcet', 'ECORE', or 'KM3')."


    def _run(self, **kwargs) -> str:
        try:
            # Extract the file path from kwargs
            if kwargs:
                file_path = next(iter(kwargs.values()))
            else:
                return "Error: No file path provided."

            # Ensure the file path is a string and strip any leading/trailing whitespace
            file_path = str(file_path).strip()

            # Open and read the file content
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()

            # Extract the metamodel name from the content
            metamodel_name = self._extract_from_content(content)

            if metamodel_name:
                return f"Successfully extracted metamodel name: {metamodel_name}"
            else:
                return "Could not extract metamodel name from the file."

        except FileNotFoundError:
            return f"Error: File not found at path: {file_path}"
        except Exception as e:
            return f"An error occurred while processing the file: {str(e)}"


    def _extract_from_content(self, content: str) -> str:
        # First try to find simple xmlns="MetamodelName" pattern
        simple_xmlns_pattern = r'xmlns="([^"]*)"'
        match = re.search(simple_xmlns_pattern, content)
        if match:
            return match.group(1)

        # If not found, look for xmlns:prefix pattern
        complex_xmlns_pattern = r'xmlns:(\w+)="([^"]*)"'
        matches = re.findall(complex_xmlns_pattern, content)
        
        # Filter out common XML namespaces
        filtered_matches = [
            (prefix, url) for prefix, url in matches 
            if not prefix in ['xmi', 'xsi']  # Exclude standard XML namespaces
        ]
        
        if filtered_matches:
            # Get the first relevant namespace prefix (e.g., 'ecore' or 'km3')
            metamodel_prefix = filtered_matches[0][0]
            
            # Look for the root element to confirm it's the main metamodel
            root_pattern = rf'<{metamodel_prefix}:\w+'
            if re.search(root_pattern, content):
                return metamodel_prefix.upper()  # Return uppercase version

        return None
    

