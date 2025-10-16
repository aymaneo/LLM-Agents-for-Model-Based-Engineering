import json
import os
from typing import List, Dict, Any
import pandas as pd
from datetime import datetime
from pathlib import Path
from langgraph.errors import GraphRecursionError
from ..agent import create_atl_agent

class LangGraphToolUsageEvaluator:
    def __init__(self, dataset_path: str):
        """Initialize evaluator with dataset path"""
        self.dataset = self.load_dataset(dataset_path)
        self.evaluation_results = []

    def load_dataset(self, dataset_path: str) -> Dict:
        """Load and parse the dataset JSON file"""
        with open(dataset_path, 'r') as f:
            data = json.load(f)
            # Flatten single_tool and multi_tool into one list
            all_examples = []
            
            for example in data.get("multi_tool", []):
                example["type"] = "multi_tool"
                all_examples.append(example)
            for example in data.get("single_tool", []):
                example["type"] = "single_tool"
                all_examples.append(example)
            return all_examples


    def normalize_args(self, args: Any) -> Any:
        """Normalize input arguments for comparison"""
        # Handle dictionary cases first (from original)
        if isinstance(args, dict):
            if "input_str" in args:
                return args["input_str"].split(',')
            if "query" in args:
                return args["query"]
            return args  # Return the dict if no special handling needed
            
        # Handle list cases
        if isinstance(args, list):
            return [str(arg).strip().strip("'\"") for arg in args]
            
        # Handle string cases
        if isinstance(args, str):
            # Check if string represents a list
            if args.startswith('[') and args.endswith(']'):
                try:
                    args_list = eval(args)
                    return [str(arg).strip().strip("'\"") for arg in args_list]
                except:
                    pass
            # Handle comma-separated strings
            if ',' in args:
                return [part.strip().strip("'\"") for part in args.split(',')]
            return str(args).strip().strip("'\"")
                
        return str(args).strip().strip("'\"")

    def args_match(self, ref_args: Any, pred_args: Any) -> bool:
        """Compare arguments after normalization"""
        ref_normalized = self.normalize_args(ref_args)
        pred_normalized = self.normalize_args(pred_args)
        
        # Convert to list if either is a list
        if isinstance(ref_normalized, list) or isinstance(pred_normalized, list):
            if not isinstance(ref_normalized, list):
                ref_normalized = [ref_normalized]
            if not isinstance(pred_normalized, list):
                pred_normalized = [pred_normalized]
            
            # Compare lists after sorting
            return sorted(ref_normalized) == sorted(pred_normalized)
        
        # If both are dicts, compare them directly
        if isinstance(ref_normalized, dict) and isinstance(pred_normalized, dict):
            return ref_normalized == pred_normalized
            
        return ref_normalized == pred_normalized

    def extract_tool_calls(self, agent_response: Dict) -> List[Dict]:
        """Extract tool calls from LangGraph agent response"""
        tool_calls = []
        
        # Handle messages format from LangGraph
        for message in agent_response.get("messages", []):
            if hasattr(message, "tool_calls") and message.tool_calls:
                for tool_call in message.tool_calls:
                    tool_calls.append({
                        "tool_name": tool_call["name"],
                        "arguments": tool_call["args"]
                    })
        
        return tool_calls

    def evaluate_single_run(self, example: Dict, agent_response: Dict) -> Dict:
        """Evaluate a single run comparing agent response to reference"""
        agent_tool_calls = self.extract_tool_calls(agent_response)
        reference_apis = example["relevant_apis"]

        total_score = 0
        max_score = len(reference_apis)
        matched_tools = []
        unmatched_tools = []
        matched_pairs = []  # Track which predictions matched which references

        # Format tools called for CSV
        tools_called = [f"{call['tool_name']}({call['arguments']})" for call in agent_tool_calls]
        tools_called_str = " | ".join(tools_called) if tools_called else "No tools called"
        
        # Format expected tools for comparison
        expected_tools = [f"{api['api_name']}({api['arguments']})" for api in reference_apis]
        expected_tools_str = " | ".join(expected_tools)

        for ref_api in reference_apis:
            matched = False
            for i, pred_api in enumerate(agent_tool_calls):
                if ref_api["api_name"] == pred_api["tool_name"]:
                    if self.args_match(ref_api["arguments"], pred_api["arguments"]):
                        total_score += 1
                        matched_tools.append(pred_api)
                        matched_pairs.append((ref_api, pred_api))
                        matched = True
                        break
            
            if not matched:
                unmatched_tools.append(ref_api)

        score = total_score / max_score if max_score > 0 else 0

        # Add detailed matching information
        matching_details = []
        for ref, pred in matched_pairs:
            matching_details.append(f"Matched: {ref['api_name']}({ref['arguments']}) with {pred['tool_name']}({pred['arguments']})")

        return {
            "instruction": example["instruction"],
            "type": example.get("type", "unknown"),
            "level": example.get("level", 0),
            "score": score,
            "total_tools_expected": max_score,
            "total_tools_matched": total_score,
            "tools_called": tools_called_str,
            "expected_tools": expected_tools_str,
            "matching_details": " | ".join(matching_details) if matching_details else "No matches",
            "matched_tools": matched_tools,
            "unmatched_tools": unmatched_tools,
            "timestamp": datetime.now().isoformat()
        }


    def predict_atl_agent_answer(self, example: dict) -> Dict[str, Any]:
        """Run prediction for a single example using ATL agent with LangGraph"""
        agent = create_atl_agent()
        input_query = example["instruction"]
        messages = [("human", input_query)]
        RECURSION_LIMIT = 2 * 10 + 1

        try:
            result = agent.invoke({"messages": messages}, {"recursion_limit": RECURSION_LIMIT})
            if not isinstance(result, dict):
                result = {"output": result}
        except GraphRecursionError:
            result = {"output": "Max iterations are reached. Agent stopped processing further."}
            
        return result

    def evaluate_all(self) -> tuple:
        """Evaluate all examples and return results"""
        print("\nRunning agent predictions...")
        total_examples = len(self.dataset)
        
        for i, example in enumerate(self.dataset, 1):
            progress_percent = (i/total_examples*100)
            try:
                print(f"\nEvaluating example ({progress_percent:.1f}%): {example['instruction']}")
                response = self.predict_atl_agent_answer(example)
                result = self.evaluate_single_run(example, response)
                self.evaluation_results.append(result)
            except Exception as e:
                print(f"Error processing example: {str(e)}")
                continue

        return self.get_results_dataframe()

    def get_results_dataframe(self) -> tuple:
        """Convert evaluation results to a DataFrame and calculate summary stats"""
        df = pd.DataFrame(self.evaluation_results)
        
        # Calculate summary statistics with formatted values
        summary_stats = {
            "total_examples": len(df),
            "average_score": round(df["score"].mean() * 100, 2),
            "perfect_matches": len(df[df["score"] == 1.0]),
            "failed_matches": len(df[df["score"] == 0.0]),
            "partial_matches": len(df[(df["score"] > 0.0) & (df["score"] < 1.0)]),
            "single_tool_accuracy": round(df[df["type"] == "single_tool"]["score"].mean() * 100, 2),
            "multi_tool_accuracy": round(df[df["type"] == "multi_tool"]["score"].mean() * 100, 2),
            "by_level": {
                f"level_{level}": round(score * 100, 2)
                for level, score in df.groupby("level")["score"].mean().items()
            }
        }
        
        # Save results
        output_dir = Path.cwd() / "evaluation_results"
        print(f"\nResults will be saved in: {output_dir.absolute()}")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save detailed results to CSV
        results_path = output_dir / f"langgraph_tool_evaluation_{timestamp}.csv"
        df.to_csv(results_path, index=False)
        
        # Save summary stats to JSON
        summary_path = output_dir / f"langgraph_summary_stats_{timestamp}.json"
        # Save formatted JSON with proper indentation and percentage values
        with open(summary_path, 'w') as f:
            json.dump(summary_stats, f, indent=4, sort_keys=True)
            
        
        return df, summary_stats

def evaluate_no_dedicated_tools():
    """Main evaluation function for ATL LangGraph agent"""
    
    if 'PROJECT_ROOT' in os.environ:
        root_dir = os.environ['PROJECT_ROOT']
    file_path = os.path.join(root_dir, 'dataset_generation', 'generation', 'atl_agent_dataset.json')


    dataset_path = Path(file_path)
        
    print("\nStarting atl LangGraph evaluation...")
    try:
        evaluator = LangGraphToolUsageEvaluator(dataset_path)
        results_df, summary_stats = evaluator.evaluate_all()
        return results_df, summary_stats
    except Exception as e:
        print(f"Evaluation failed: {str(e)}")
        return None, None
