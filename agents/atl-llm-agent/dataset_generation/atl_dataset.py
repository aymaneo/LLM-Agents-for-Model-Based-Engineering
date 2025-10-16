from langsmith import Client
import json
from langgraph.errors import GraphRecursionError


import json

def load_dataset(dataset_name: str):
    client = Client()
    
    # Check if the dataset exists
    if client.has_dataset(dataset_name=dataset_name):
        print(f"Dataset '{dataset_name}' already exists.")
        return client.read_dataset(dataset_name=dataset_name)

    # Create a new dataset
    dataset = client.create_dataset(
        dataset_name=dataset_name,
        description=f"Dataset for {dataset_name}"
    )
    print(f"Created new dataset: {dataset_name}")
    
    # Load JSON data from the specified file
    file_name = f"{dataset_name}.json"
    with open(file_name, 'r') as file:
        data = json.load(file)
    
    # Function to add examples to the dataset
    def add_examples(tool_type):
        for item in data.get(tool_type, []):
            example = {
                "inputs": {"input": item["instruction"]},
                "outputs": {"output": {"api_calls": item["relevant_apis"]}}
            }
            try:
                client.create_example(
                    inputs=example["inputs"],
                    outputs=example["outputs"],
                    dataset_id=dataset.id
                )
                print(f"Added {tool_type} example: {item['instruction'][:50]}...")
            except Exception as e:
                print(f"Error adding {tool_type} example: {str(e)}")
    
    # Add examples for both single_tool and multi_tool
    add_examples("single_tool")
    add_examples("multi_tool")
    
    print("\nDataset creation completed.")
    return dataset
def run_dataset_examples(agent, dataset):
    client = Client()
    examples = list(client.list_examples(dataset_id=dataset.id))  # Convert the generator to a list
    
    for example in examples: 
        # Format the input for LangGraph's expected schema
        config = {"configurable": {"thread_id": "test-thread"}}
        messages = [("human", example.inputs["input"])]
        
        RECURSION_LIMIT = 2 * 10 + 1  

        try:
            # Invoke the agent with the recursion limit
            result = agent.invoke({"messages": messages}, {"recursion_limit": RECURSION_LIMIT})
        except GraphRecursionError:
            # Handle the recursion limit being reached
            result = {"output": "Max iterations are reached. Agent stopped processing further."}

        if not isinstance(result, dict):
            result = {"output": result}
        
        # Print the results
        print(f"\nInput: {example.inputs['input']}")
        print(f"Expected API calls: {example.outputs['output']['api_calls']}")
        print(f"Agent result: {result['output']}\n")