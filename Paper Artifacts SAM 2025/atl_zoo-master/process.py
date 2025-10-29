import os
import json
from pathlib import Path

def get_transformation_details():
    # Liste pour stocker les détails des transformations
    transformation_details = []
    
    # Récupérer le répertoire de travail actuel (dossier racine)
    root_dir = Path.cwd()
    
    # Parcourir tous les dossiers
    for dirpath, _, filenames in os.walk(root_dir):
        # Vérifier si le fichier config.json existe dans le dossier actuel
        if 'config.json' in filenames:
            config_path = Path(dirpath) / 'config.json'
            try:
                # Lire et analyser le fichier config.json
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    
                # Extraire les détails des transformations activées
                for item in config_data:
                    if item.get('enabled') == "True":
                        name = item.get('name')
                        
                        # Garder uniquement le nom du métamodèle sans ".ecore"
                        input_metamodels = [
                            Path(mm['path']).stem for mm in item.get('input_metamodels', [])
                        ]
                        output_metamodels = [
                            Path(mm['path']).stem for mm in item.get('output_metamodels', [])
                        ]
                        
                        # Convertir les chemins des sources en absolu
                        source_models = [
                            str((Path(dirpath) / source).resolve())
                            for sample in item.get('sample_models', [])
                            for source in sample.get('source', [])
                        ]
                        
                        if name:
                            transformation_details.append({
                                "name": name,
                                "input_metamodels": input_metamodels,
                                "output_metamodels": output_metamodels,
                                "source_models": source_models
                            })
            except json.JSONDecodeError:
                print(f"Erreur lors de l'analyse JSON dans {config_path}")
            except Exception as e:
                print(f"Erreur lors du traitement de {config_path} : {str(e)}")
    
    return transformation_details

# Exécuter la fonction et enregistrer les résultats dans un fichier JSON
if __name__ == "__main__":
    details = get_transformation_details()
    
    # Définir le chemin du fichier de sortie
    output_file = Path.cwd() / "output.json"
    
    # Écrire les détails dans le fichier JSON
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(details, f, indent=4, ensure_ascii=False)
        print(f"Détails des transformations enregistrés dans {output_file}")
    except Exception as e:
        print(f"Erreur lors de l'écriture du fichier : {str(e)}")
