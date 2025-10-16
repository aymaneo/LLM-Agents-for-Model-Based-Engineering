import json
import subprocess


def create_transformation_description(transformation_name):
    
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
    return f"Input metamodel: {input_model}, Output metamodel:  {output_model} .This tool takes : {input_model} model as input and produces {output_model} model."


def generate_get_tool_description(transformation_name):
    
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
    return f"This tool display the details of the transformation {transformation_name} that transforms: {input_model} model into  {output_model} model."


