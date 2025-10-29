import os
import json
import requests

def apply_transformation(transformation_id_or_name: str, input_files_dict: dict) -> None:
    API_BASE_URL = "http://localhost:8080"
    
    # First validate all files exist and are not directories
    for input_name, file_path in input_files_dict.items():
        if not os.path.exists(file_path):
            print(f"Error: File does not exist: {file_path}")
            return
        if os.path.isdir(file_path):
            print(f"Error: Path is a directory, not a file: {file_path}")
            return
            
    try:
        files = {}
        file_handles = []  # Keep track of opened files       
        try:
            # Open all files first
            for input_name, file_path in input_files_dict.items():
                f = open(file_path, 'rb')
                file_handles.append(f)  # Save the handle to close later
                files[input_name] = f
                
            # Send the request
            response = requests.post(
                f"{API_BASE_URL}/transformation/{transformation_id_or_name}/apply",
                files=files,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.text
                output_dir = "transformation_results"
                os.makedirs(output_dir, exist_ok=True)
                output_file = os.path.join(output_dir, f"result_{transformation_id_or_name}.xmi")
                
                with open(output_file, 'w') as f:
                    f.write(result)
                print(f"Transformation successful! Result saved to: {output_file}")
            else:
                print(f"Error: ")
                
        except requests.exceptions.RequestException as e:
            print(f"Request error for {transformation_id_or_name}: {str(e)}")
            
        finally:
            # Make sure to close all opened files
            for f in file_handles:
                f.close()
                
    except Exception as e:
        print(f"Error processing {transformation_id_or_name}: {str(e)}") 
def main():

    script_dir = os.path.dirname(os.path.abspath(__file__))
    transformation_dirs = []
    for dirpath, dirnames, filenames in os.walk(script_dir):
        if 'config.json' in filenames:
            transformation_dirs.append(dirpath)

    # Sort directories alphabetically
    transformation_dirs.sort()
    for dirpath in transformation_dirs:
        try:
            with open(os.path.join(dirpath, 'config.json')) as f:
                config = json.load(f)

            configs = [config] if isinstance(config, dict) else config
            for cfg in configs:
                try:
                    name = cfg.get('name')
                    input_metamodels = cfg.get('input_metamodels', [])
                    sample_models = cfg.get('sample_models', [])

                    for model in sample_models:
                        try:
                            source_files = model.get('source', [])
                            if source_files:
                                if isinstance(source_files, str):
                                    source_files = [source_files]
                                
                                # Create a dictionary mapping input names to their files
                                input_files_dict = {}
                                for idx, source in enumerate(source_files):
                                    if idx < len(input_metamodels):
                                        source_path = os.path.join(dirpath, source.replace('./', ''))
                                        input_name = input_metamodels[idx]['name']
                                        input_files_dict[input_name] = source_path
                              
                                print(f"\nTrying to apply transformation {name} with inputs:")
                                   
                                try:
                                    apply_transformation(name, input_files_dict)
                                except Exception as e:
                                    print(f"Failed to apply transformation {name}: {e}")
                                    continue
                        except Exception as e:
                            print(f"Error with model for {name}: {e}")
                            continue
                except Exception as e:
                    print(f"Error processing config for transformation: {e}")
                    continue
        except Exception as e:
            print(f"Error reading config in {dirpath}: {e}")
            continue

    print("All transformations processed")
    print("finished")

if __name__ == "__main__":
    main()