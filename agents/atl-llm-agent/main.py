from dataset_generation.generation.dataset_generation import generate
from dataset_generation.generation.dataset_transition import transform
from dataset_generation.generation.instruction_generator import generate_evenly_balanced_dataset
from no_dedicated_tools_per_transfos.langgraph_agent.evaluation.evaluator import evaluate_no_dedicated_tools
from specific_tool_agents.tool_filtering_by_rag.evaluator import evaluate_tool_filtering_by_rag
from specific_tool_agents.transformation_agent.evaluation.evaluator import evaluate_atl_transformation_agent
from specific_tool_agents.no_tool_filtering.evaluation.evaluator import  evaluate_atl_transformation_langgraph



if __name__ == "__main__":

    # Patterns generation
    generate_evenly_balanced_dataset()
    # First dataset generation
    generate()
    # Second dataset generation 
    transform() 
    # Evaluation process
    # No dedicated tools per transformation agent
    evaluate_no_dedicated_tools()
    # No tool filtering agent
    evaluate_atl_transformation_langgraph()
    # ATL transformation agent 
    evaluate_atl_transformation_agent()
    # tool filtering by RAG agent
    evaluate_tool_filtering_by_rag()

   