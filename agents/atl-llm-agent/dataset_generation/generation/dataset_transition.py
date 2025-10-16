import json
import os

def transform():
    # Charger le fichier JSON d'origine

    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, 'atl_balanced_level_instructions.json')

    with open(file_path, 'r') as f:

        data = json.load(f)

    # Fonction pour transformer les relevant_apis
    def transform_api(api):
        if api['api_name'].endswith('.get_tool'):
            name = api['api_name'].split('.')[0]
            api['api_name'] = f"curl_transformation_by_Name_tool"
            api['arguments'] = name
        elif api['api_name'].endswith('.apply_tool'):
            name = api['api_name'].split('.')[0]
            api['api_name'] = "curl_apply_transformation_tool"
            api['arguments'] = (name, api['arguments'])
        return api

    # Transformer les données
    transformed_data = {}
    for key, entries in data.items():
        transformed_data[key] = []
        for entry in entries:
            transformed_entry = {
                "instruction": entry["instruction"],
                "relevant_apis": [transform_api(api) for api in entry["relevant_apis"]],
                "level": entry.get("level", 2)  # Keep existing level or set to 2 if missing
            }
            transformed_data[key].append(transformed_entry)

    # Saved in a new json file
    with open('dataset_generation/generation/atl_agent_dataset.json', 'w') as f:
        json.dump(transformed_data, f, indent=4)

    print("Transformation is done. Results are saved in 'atl_agent_dataset.json'.")

