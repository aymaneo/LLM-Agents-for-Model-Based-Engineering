# LLM-based Agents for Model-to-Model
Transformation in ATL

## Description

This repository contains artifacts for the paper *"Towards LLM Agents for Model-Based Engineering:  A Case in Transformation SelectionL,"* to be submitted at SAM 2025.

This project implements an agentic system for Model-Based Engineering (MBE) workflows, focusing on ATL (ATL Transformation Language) transformations. Built with LangGraph, the system optimizes tool selection and execution through various agent architectures.

##  Features

- Multiple agent architectures for comparison
- Intelligent tool selection and parameter optimization
- Built-in performance metrics and evaluation.
- Real-time execution monitoring
- Flexible tool integration system

##  Prerequisites

- Python 3.8+
- ATL Server running
- The Ollama server is running. We used a local LLaMA model running on a machine with the following configuration:
  - **CPU:** AMD EPYC 7452 32-Core Processor
  - **RAM:** 32GB
  - **GPU:** RTX 3090

##  Installation

1. Download the repository

```bash
cd ATL-LLM-agent
```

2. Set up virtual environment

```bash
python -m venv venv
source venv/bin/activate  # Linux/MacOS
.\venv\Scripts\activate   # Windows
```

3. Install dependencies

```bash
pip install -r requirements.txt
```

##  Project Structure

Run this command to see the full project structure:

```bash
tree -I 'venv|__pycache__|*.pyc|.git' --dirsfirst
```

##  Usage

To run the project:

1. Ensure all prerequisites are installed and running (ATL Server and Ollama)

2. Configure your model parameters in `config/config.py`

   Set up the following environment variables before running the project:

   - `OLLAMA_MODEL`: Name of the Ollama model to use for inference
   - `OLLAMA_TEMPERATURE`: Temperature setting for model generation (controls randomness)
   - `OLLAMA_MAX_RETRIES`: Maximum number of retry attempts for Ollama API calls.

3. Run the main script:

```bash
python main.py
```

This will:

- ###### Generate two datasets for evaluating different variation of agents.

- ###### Launch the evaluation process for different agent architectures.

- ###### Output results to the `evaluation_results` directory.



- #### Using Pre-generated Datasets

  If you want to skip dataset generation, you can use the pre-generated datasets located at: **dataset_generation/generation/test_dataset**

  To do this:

  1. Comment out the following dataset generation code in the main file:

     ```python
     # Patterns generation
     generate_evenly_balanced_dataset()
     # First dataset generation
     generate()
     # Second dataset generation 
     transform()
     ```

  2. Update the file paths in each evaluation script to use the pre-generated datasets:

     - Find the last function in each evaluation script
     - Change paths like this:

     From:

     ```python
     file_path = os.path.join(root_dir, 'dataset_generation', 'generation', 'atl_agent_dataset.json')
     ```

     To:

     ```python
     file_path = os.path.join(root_dir, 'dataset_generation', 'generation', 'test_dataset', 'atl_agent_dataset.json')
     ```

  #### Customizing Evaluation

  - To skip specific evaluations, simply comment out the corresponding script calls in `main.py`

  ##### Adjusting Tool Numbers for Evaluation

  Note that we evaluated these tool numbers: 20, 24, 30, 50, 70, 90, and 110. The evaluation process requires manually changing the tool number in the code for each evaluation run.

  ##### For the No tool filtering Agent

  Modify the file `specific_tool_agents/no_tool_filtering/agent.py`:

  ```python
  for i, name in enumerate(transformation_names):
     if i > 6:  # Change this number to control how many transformations to include
         break
     tools.extend([
     GetTransformationByNameTool(name), 
     ApplyTransformationTool(name)
     ])
  ```

  The relationship is: 6 transformations = 12 tools, and so on.

  ##### For the Transformation Agent

  Modify the file `specific_tool_agents/transformation_agent/agent.py`:

  ```python
  MAX_TRANSFORMATIONS = 12  # Change this number to control how many transformation
  ```

  #### Viewing Evaluation Results

  - Pre-computed evaluation results are stored in the `evaluation_results` folder
  - These results are maintained for transparency, traceability and reproducibility of the paper results.
  - You can inspect the raw data in CSV or JSON format.
  - Note that in the evaluation results, you will see that we separated the Level 3 evaluation. This is because in the original dataset we used, we didn't have the pattern retrieval functionality for Level 3, so we added it later to maintain consistency and fairness. This issue is fixed in the current version.

  #### Regenerating Visualization Plots

  To reproduce the evaluation charts from the paper:

  ```python
  python process.py
  ```

  This script extract data from evaluation results we got and diplay them in the chart.
  The visualizations will be saved to the `plots` folder.

##  ATL MCP Servers

The ATL MCP Server is located in this path`atl_mcp_server/atl_mcp_server.py` , You can also find the mcp server used in the running example here: ` atl_mcp_server/copilot_mcp_server.py`


##  Agent Architectures and Evaluation

The system evaluates tool usage and calling patterns in multiple agent architectures:

- **Langgraph no dedicated tool per transformation**: Graph-based agent architecture using LangGraph
- **Langgraph no tool filtering agent**: Specialized agent for ATL transformations without tool filtering
- **ATL Transformation Agent**: Advanced version with improved reasoning and an LLM as a tool filtering.
- **ATL Transformation Agent**: Same previous version but using tool filtering by RAG.


### Evaluation Logic

The evaluation process is based on extracting the agent's response and checking:

1. If the correct tool is called
2. If the correct arguments are passed to the tool

A test is considered successful only when both the tool and arguments match the expected values. Otherwise, it's marked as a failure. This evaluation methodology allows for precise measurement of the agent's ability to understand instructions and correctly select and parameterize tools.