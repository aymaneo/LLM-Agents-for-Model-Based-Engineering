# ATL_Zoo


## 📜 Project Overview

This repository contains artifacts for the paper *"LLM-based Agents for Model-to-Model Transformation in ATL,"* to be submitted at MODELS 2025.

The **ATL Zoo** simplifies working with ATL transformations from the Eclipse ATL Zoo by creating standardized configuration files (`config.json`). These files encapsulate all the critical parameters associated with each transformation, enabling developers and users to seamlessly locate and manipulate ATL transformations.

## 📝 Problem Statement

The Eclipse ATL Zoo hosts numerous ATL transformations along with their related resources:

- **Input Metamodels**
- **Output Metamodels**
- **ATL Transformation Files (.atl)**
- **Source and Target Files** (used to test the transformations)

While the Zoo allows users to download these resources, it often lacks clear organization or direct access to all relevant parameters. This can make locating and using the correct components cumbersome and time-consuming.

## 💡 Solution

This project introduces a **configuration file (`config.json`)** for each ATL transformation. The file provides:

- Direct pointers to all the necessary parameters (metamodels, transformation files, source/target examples).
- An easy-to-navigate structure for developers and users.
- Simplified manipulation and testing of ATL transformations. 

## 🚀 Features

- **Standardized Configurations**: Each transformation has a `config.json` file detailing all associated resources.
- **Enhanced Usability**: Developers and users can quickly find and link all required components.
- **Facilitates Automation**: The structured format is ideal for scripts or tools that need to work with transformations.
- **Improves Accessibility**: Reduces the need for manual searching and setup.

- **Transformation Status**: The `enabled` flag indicates whether a transformation works correctly and generates the expected output. When set to "True", the transformation is validated and produces correct results. The user can filter just the working transformations.

Example of `config.json`File:

```json
[
    {
        "name": "Ant2Maven",
        "description": "",
        "compiler": "EMFVM",
        "input_metamodels": [
            {
                "name": "IN",
                "path": "./MM/Ant.ecore"
            }
        ],
        "output_metamodels": [
            {
                "name": "OUTMaven",
                "path": "./MM/MavenMaven.ecore"
            },
            {
                "name": "OUTProject",
                "path": "./MM/MavenProject.ecore"
            }
        ],
        "atlFile": "./transfo/Ant2Maven.atl",
        "sample_models": [
            {
                "source": [
                    "./example/build1Ant.xmi"
                ],
                "target": [
                    "./example/mavenFile.xmi",
                    "./example/ProjectFile.xmi"
                ]
            }
        ],
        "libraries": [],
        "enabled": "True"
    },
    {
        "name": "XML2Ant",
        "compiler": "EMFVM",
        "description": "",
        "input_metamodels": [
            {
                "name": "IN",
                "path": "./MM/XML.ecore"
            }
        ],
        "output_metamodels": [
            {
                "name": "OUT",
                "path": "./MM/Ant.ecore"
            }
        ],
        "atlFile": "./transfo/XML2Ant.atl",
        "sample_models": [
            {
                "source": [
                    "./example/build1.xmi"
                ],
                "target": [
                    "./example/build1Ant.xmi"
                ]
            }
        ],
        "libraries": [],
        "enabled": "True"
    }
]
```