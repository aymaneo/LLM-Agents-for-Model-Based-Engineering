import logging
import sys
import os
import json
import subprocess
from mcp.server.fastmcp import FastMCP
from typing import List

# Constants
ATL_SERVER_BASE = "http://localhost:8080"

# Set up logging to stderr as required by MCP
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger('transformation_generic_mcp_server')

# Initialize the MCP server
mcp = FastMCP("transformation_server")

def create_transformation_description(transformation_name):
    """Create a description for a specific transformation by extracting metamodel names from paths."""
    try:
        result = subprocess.run(['curl', '-X', 'GET', 'localhost:8080/transformations/enabled'], 
                              capture_output=True, text=True, check=True)
        transformations = json.loads(result.stdout)
        # Find the transformation with the specified name
        transformation = next((t for t in transformations if t["name"] == transformation_name), None)
        
        if not transformation:
            return f"Transformation {transformation_name} not found"
        
        # Extract input model name
        input_path = transformation["input_metamodels"][0]["path"]
        input_model = input_path.split("/")[-1].replace(".ecore", "")
        
        # Extract output model name
        output_path = transformation["output_metamodels"][0]["path"]
        output_model = output_path.split("/")[-1].replace(".ecore", "")
        
        # Create and return the formatted description
        return f"This transformation takes: {input_model} model as input and produces {output_model} model"
    except Exception as e:
        logger.warning(f"Could not create description for transformation {transformation_name}: {e}")
        return f"{transformation_name}: Description unavailable"

def generate_get_tool_description(transformation_name):
    """Generate description for the get transformation tool."""
    try:
        result = subprocess.run(['curl', '-X', 'GET', 'localhost:8080/transformations/enabled'], 
                              capture_output=True, text=True, check=True)
        transformations = json.loads(result.stdout)
        # Find the transformation with the specified name
        transformation = next((t for t in transformations if t["name"] == transformation_name), None)
        
        if not transformation:
            return f"Transformation {transformation_name} not found"
        
        # Extract input model name
        input_path = transformation["input_metamodels"][0]["path"]
        input_model = input_path.split("/")[-1].replace(".ecore", "")
        
        # Extract output model name
        output_path = transformation["output_metamodels"][0]["path"]
        output_model = output_path.split("/")[-1].replace(".ecore", "")
        
        # Create and return the formatted description
        return f"The transformation {transformation_name} that transforms: {input_model} model into {output_model} model."
    except Exception as e:
        logger.warning(f"Could not create get tool description for transformation {transformation_name}: {e}")
        return f"{transformation_name}: Description unavailable"

def create_description_with_transformations(base_description: str) -> str:
    """Create tool description that includes available transformation names and their purposes."""
    try:
        result = subprocess.run(['curl', '-X', 'GET', 'localhost:8080/transformations/enabled'], 
                              capture_output=True, text=True, check=True)
        transformations = json.loads(result.stdout)
        
        transformation_descriptions = []
        
        # Add UMLActivityDiagram2MsProject description at the beginning
        transformation_descriptions.append("UMLActivityDiagram2MsProject: This transformation takes: UMLDI model as input and produces MsProject model")
        
        for transformation in transformations:
            name = transformation["name"]
            # Skip if it's UMLActivityDiagram2MsProject since we already added it
            if name == "UMLActivityDiagram2MsProject":
                continue
            description = create_transformation_description(name)
            transformation_descriptions.append(f"{name}: {description}")
        
        if transformation_descriptions:
            transformations_list = ". ".join(transformation_descriptions)
            return f"{base_description} Available transformations: {transformations_list}."
        else:
            return f"{base_description} (No transformations available)"
    except Exception as e:
        return f"{base_description} (Error retrieving transformation details: {e})"

def create_get_tool_description() -> str:
    """Create description for the get transformation tool that includes all available transformations."""
    try:
        result = subprocess.run(['curl', '-X', 'GET', 'localhost:8080/transformations/enabled'], 
                              capture_output=True, text=True, check=True)
        transformations = json.loads(result.stdout)
        
        transformation_descriptions = []
        
        # Add UMLActivityDiagram2MsProject description at the beginning
        transformation_descriptions.append("The transformation UMLActivityDiagram2MsProject that transforms: UMLDI model into MsProject model.")
        
        for transformation in transformations:
            name = transformation["name"]
            # Skip if it's UMLActivityDiagram2MsProject since we already added it
            if name == "UMLActivityDiagram2MsProject":
                continue
            description = generate_get_tool_description(name)
            transformation_descriptions.append(description)
        
        if transformation_descriptions:
            transformations_list = ". ".join(transformation_descriptions)
            return f"Retrieves detailed information about a single transformation by providing its name. Input should be the exact transformation name as a string. Available transformations: {transformations_list}."
        else:
            return "Retrieves detailed information about a single transformation by providing its name. Input should be the exact transformation name as a string. (No transformations available)"
    except Exception as e:
        return f"Retrieves detailed information about a single transformation by providing its name. Input should be the exact transformation name as a string. (Error retrieving transformation details: {e})"

@mcp.tool(
    name="curl_apply_transformation_tool",
    description=create_description_with_transformations("Executes a transformation on a specified file. Input must be provided in the format: 'transformation_name,file_path' (note the comma separator).")
)
async def apply_transformation_tool(input_str: str) -> str:
    """Apply a transformation to a specified file."""
    if "https://" in input_str or "http://" in input_str:
        return "Error: Do NOT include any URLs. Input should ONLY be in the format 'transformation_name,file_path'."
    
    try:
        parts = input_str.split(',')
        if len(parts) != 2:
            return "Error: Input MUST have exactly two parts separated by a comma. Format: 'transformation_name,file_path'."
        
        transformation_name = parts[0].strip() 
        file_path = parts[1].strip()

        # Check if file exists
        if not os.path.exists(file_path):
            return f"Error: File not found at {file_path}"

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
    except Exception as e:
        return f"An error occurred: {str(e)}"

@mcp.tool(
    name="curl_transformation_by_Name_tool",
    description=create_get_tool_description()
)
async def get_transformation_by_name_tool(query: str) -> str:
    """Get detailed information about a transformation by its name."""
    try:
        query = query.strip()
        identifier = query
        
        command = ['curl', '-X', 'GET', f'localhost:8080/transformation/{identifier}']
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return f"The transformation with '{identifier}':\n{result.stdout}"
    except subprocess.CalledProcessError as e:
        return f"An error occurred while fetching the transformation: {e.stderr} :\n{command}"
    except Exception as e:
        return f"An error occurred: {str(e)}"


if __name__ == "__main__":
    try:
        logger.info("Starting transformation MCP server...")
        mcp.run(transport='stdio')
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        sys.exit(1)