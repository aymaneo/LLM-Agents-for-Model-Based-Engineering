import os
from pathlib import Path
import json
from typing import List, Dict, Any
import pandas as pd
from datetime import datetime
from ..agent import create_atl_agent

class ATLTransformationLangGraphEvaluator:
    def __init__(self, dataset_path: str):
        """Initialize evaluator with dataset path"""
        self.dataset = self.load_dataset(dataset_path)
        self.evaluation_results = []

    def load_dataset(self, dataset_path: str) -> List[Dict]:
        """Load and parse the dataset JSON file"""
        with open(dataset_path, 'r') as f:
            data = json.load(f)
            examples = []
            for example in data.get("multi_tool", []):
                example["type"] = "multi_tool"
                examples.append(example)
            for example in data.get("single_tool", []):
                example["type"] = "single_tool"
                examples.append(example)

            print(f"\nLoaded {len(examples)} examples:")
            print(f"- Multi-tool examples: {len(data.get('multi_tool', []))}")
            print(f"- Single-tool examples: {len(data.get('single_tool', []))}")
            return examples

    def normalize_args(self, args: Any) -> Any:
        """Normalize input arguments for comparison"""
        if isinstance(args, dict):
            if "input_str" in args:
                return args["input_str"].split(',')
            if "query" in args:
                return args["query"]
            return args
            
        if isinstance(args, list):
            return [str(arg).strip().strip("'\"") for arg in args]
            
        if isinstance(args, str):
            if args.startswith('[') and args.endswith(']'):
                try:
                    args_list = eval(args)
                    return [str(arg).strip().strip("'\"") for arg in args_list]
                except:
                    pass
            if ',' in args:
                return [part.strip().strip("'\"") for part in args.split(',')]
            return str(args).strip().strip("'\"")
                
        return str(args).strip().strip("'\"")

    def args_match(self, ref_args: Any, pred_args: Any) -> bool:
        """Compare arguments after normalization"""
        ref_normalized = self.normalize_args(ref_args)
        pred_normalized = self.normalize_args(pred_args)
        
        if isinstance(ref_normalized, list) or isinstance(pred_normalized, list):
            if not isinstance(ref_normalized, list):
                ref_normalized = [ref_normalized]
            if not isinstance(pred_normalized, list):
                pred_normalized = [pred_normalized]
            return sorted(ref_normalized) == sorted(pred_normalized)
        
        return ref_normalized == pred_normalized

    def get_input_value(self, agent_input_args):
        """Retrieve the first value from the dictionary"""
        if isinstance(agent_input_args, dict):
            return next(iter(agent_input_args.values()), '')
        return agent_input_args

    def refactor_tool_name(self, input_str: str) -> str:
        """Refactor tool names to match the agent's implementation."""
        if '.apply_tool' in input_str:
            transformation_name = input_str.split('.')[0]
            return f"apply_{transformation_name}_transformation_tool"
        elif '.get_tool' in input_str:
            transformation_name = input_str.split('.')[0]
            return f"list_transformation_{transformation_name}_tool"
        else:
            return input_str

    def predict_atl_agent_answer(self, example: dict) -> Dict[str, Any]:
        """Run prediction for a single example using ATL agent"""
        agent = create_atl_agent()
        input_query = example["instruction"]
        messages = [("human", input_query)]
        config = {"configurable": {"thread_id": "test-thread"}}
        
        try:
            start_time = datetime.now()
            result = agent.invoke({"messages": messages}, config)
            duration = (datetime.now() - start_time).total_seconds()
            print(f"Completed in {duration:.2f} seconds")
            
            if not isinstance(result, dict):
                result = {"messages": []}
        except Exception as e:
            print(f"Prediction error: {str(e)}")
            result = {"messages": []}
            
        return result

    def evaluate_all(self) -> tuple:
        """Evaluate all examples and return results"""
        print("\nRunning agent predictions...")
        
        total_examples = len(self.dataset)
        current_example = 0  # Track actual example number
        errors = 0
        
        for example in self.dataset:
            try:
                current_example += 1
                print(f"\n{'='*80}")
                print(f"Processing example {current_example}/{total_examples} ({(current_example/total_examples*100):.1f}%)")
                print(f"Type: {example.get('type', 'unknown')}, Level: {example.get('level', 'unknown')}")
                print(f"Instruction: {example.get('instruction', '')}")
                print(f"{'='*80}")
                
                response = self.predict_atl_agent_answer(example)
                if response and isinstance(response, dict):
                    result = self.evaluate_single_run(example, response)
                    if result:
                        self.evaluation_results.append(result)
                        print(f"Errors so far: {errors}")
                    else:
                        errors += 1
                        print(f"Error: Failed to evaluate example {current_example}")
                else:
                    errors += 1
                    print(f"Error: No valid response for example {current_example}")
                    
            except Exception as e:
                errors += 1
                print(f"Error processing example {current_example}: {str(e)}")
                continue

        if self.evaluation_results:
            return self.get_results_dataframe()
        print("No valid evaluation results")
        return None, None

    def evaluate_single_run(self, example: Dict, agent_response: Dict) -> Dict:
        """Evaluate a single run comparing agent response to reference"""
        try:
            # Ensure we have all required fields
            if not isinstance(example, dict) or 'level' not in example:
                print("Invalid example format")
                return None

            agent_answer = []
            for message in agent_response.get("messages", []):
                if hasattr(message, "tool_calls") and message.tool_calls:
                    for tool_call in message.tool_calls:
                        if isinstance(tool_call, dict) and "name" in tool_call and "args" in tool_call:
                            agent_answer.append({
                                "tool_name": tool_call["name"],
                                "arguments": tool_call["args"]
                            })

            reference_apis = example.get("relevant_apis", [])
            total_score = 0
            max_score = len(reference_apis)
            matched_tools = []
            unmatched_tools = []

            # Format tools outputs
            tools_called = [f"{call['tool_name']}({call['arguments']})" for call in agent_answer]
            tools_called_str = " | ".join(tools_called) if tools_called else "No tools called"
            
            expected_tools = [f"{api['api_name']}({api['arguments']})" for api in reference_apis]
            expected_tools_str = " | ".join(expected_tools)

            # Match tools
            for ref_api in reference_apis:
                matched = False
                for pred_api in agent_answer:
                    ref_tool = self.refactor_tool_name(ref_api["api_name"])
                    if ref_tool == pred_api["tool_name"]:
                        pred_value = self.get_input_value(pred_api["arguments"])
                        if self.args_match(ref_api["arguments"], pred_value):
                            total_score += 1
                            matched_tools.append(pred_api)
                            matched = True
                            break
                
                if not matched:
                    unmatched_tools.append(ref_api)

            score = total_score / max_score if max_score > 0 else 0
            print(f"Score: {score:.2f}")

            # Create result dictionary with safe gets
            return {
                "instruction": example.get("instruction", ""),
                "type": example.get("type", "unknown"),
                "level": example.get("level", 0),
                "score": score,
                "total_tools_expected": max_score,
                "total_tools_matched": total_score,
                "tools_called": tools_called_str,
                "expected_tools": expected_tools_str,
                "matched_tools": matched_tools,
                "unmatched_tools": unmatched_tools,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            print(f"Error in evaluate_single_run: {str(e)}")
            return None

    def get_results_dataframe(self) -> tuple:
        """Convert evaluation results to a DataFrame and calculate summary stats"""
        df = pd.DataFrame(self.evaluation_results)
        
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
        
        output_dir = Path.cwd() / "evaluation_results"
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        results_path = output_dir / f"langgraph_all_transformation_evaluation_{timestamp}.csv"
        df.to_csv(results_path, index=False)
        
        summary_path = output_dir / f"langgraph_all_transformation_summary_{timestamp}.json"
        with open(summary_path, 'w') as f:
            json.dump(summary_stats, f, indent=4, sort_keys=True)
        
        return df, summary_stats

def evaluate_atl_transformation_langgraph():
    """Main evaluation function"""

    if 'PROJECT_ROOT' in os.environ:
        root_dir = os.environ['PROJECT_ROOT']
    file_path = os.path.join(root_dir, 'dataset_generation', 'generation', 'atl_balanced_level_instructions.json')

    dataset_path = Path(file_path)
    
    print("\nStarting LangGraph atl transformation evaluation...")
    try:
        evaluator = ATLTransformationLangGraphEvaluator(dataset_path)
        results_df, summary_stats = evaluator.evaluate_all()
        return results_df, summary_stats
    except Exception as e:
        print(f"Evaluation failed: {str(e)}")
        return None, None