import os
from pathlib import Path
import json
from typing import List, Dict, Any
import pandas as pd
from datetime import datetime
from rag_atl_agent import ATLAgent  # Make sure this imports your corrected ATLAgent
from specific_tool_agents.atl_mcp_client import MCPClient
import asyncio
from langgraph.errors import GraphRecursionError

class EnhancedTransformationEvaluator:
    def __init__(self, dataset_path: str):
        """Initialize evaluator with dataset path"""
        self.dataset = self.load_dataset(dataset_path)
        self.evaluation_results = []
        self.client = None
        self.agent = None
        self.graph = None

    async def initialize_agent(self):
        """Initialize the agent and MCP client once"""
        if self.client is None:
            print("Connecting to MCP server...")
            self.client = MCPClient()
            server_script_path = "atl_agent/atl_mcp_server.py"
            await self.client.connect_to_server(server_script_path)
            
            print("Creating ATL agent...")
            self.agent = ATLAgent(self.client)
            
            print("Initializing RAG...")
            # This should now work with the corrected method name
            await self.agent.initialize_rag()
            
            print("Creating agent graph...")
            self.graph = await self.agent.create_agent()
            
            print("Agent initialized successfully with RAG enabled")

    async def cleanup(self):
        """Clean up resources"""
        if self.client:
            await self.client.cleanup()
            self.client = None
            self.agent = None
            self.graph = None

    def load_dataset(self, dataset_path: str) -> List[Dict]:
        """Load and parse the dataset JSON file"""
        with open(dataset_path, 'r') as f:
            data = json.load(f)
            examples = []
            # Load multi_tool first
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
        """Retrieve the first value from the dictionary."""
        if isinstance(agent_input_args, dict):
            return next(iter(agent_input_args.values()), '')
        return agent_input_args

    def refactor_tool_name(self, input_str: str) -> str:
        """Refactor tool names to match the agent's implementation."""
        input_str = input_str.lower()

        if '.apply_tool' in input_str:
            transformation_name = input_str.split('.')[0]
            return f"apply_{transformation_name}_transformation_tool"
        elif '.get_tool' in input_str:
            transformation_name = input_str.split('.')[0]
            return f"list_transformation_{transformation_name}_tool"

        return input_str

    async def predict_atl_agent_answer(self, example: dict) -> Dict[str, Any]:
        """Run prediction for a single example using the already initialized agent"""
        
        if self.graph is None:
            raise RuntimeError("Agent not initialized. Call initialize_agent() first.")

        input_query = example["instruction"]
        messages = [{"role": "user", "content": input_query}]
        RECURSION_LIMIT = 21

        try:
            start_time = datetime.now()
            result = await self.graph.ainvoke(
                {"messages": messages, "selected_tools": []},
                {"recursion_limit": RECURSION_LIMIT}
            )
            duration = (datetime.now() - start_time).total_seconds()
            print(f"Completed in {duration:.2f} seconds")

            if not isinstance(result, dict):
                result = {"messages": []}
                
            return result
            
        except GraphRecursionError:
            print("Recursion limit reached")
            return {"messages": [], "error": "Max iterations reached"}
        except Exception as e:
            print(f"Error: {str(e)}")
            return {"messages": [], "error": str(e)}

    def evaluate_single_run(self, example: Dict, agent_response: Dict) -> Dict:
        """Evaluate a single run comparing agent response to reference"""
        agent_answer = []
        # Extract tool calls from messages
        for message in agent_response.get("messages", []):
            if hasattr(message, "tool_calls") and message.tool_calls:
                for tool_call in message.tool_calls:
                    agent_answer.append({
                        "tool_name": tool_call["name"].lower(),
                        "arguments": self.get_input_value(tool_call["args"])
                    })

        reference_apis = example["relevant_apis"]
        total_score = 0
        max_score = len(reference_apis)
        matched_tools = []
        unmatched_tools = []
        used_predictions = set()

        # Format tools for output
        tools_called = [f"{call['tool_name']}({call['arguments']})" for call in agent_answer]
        tools_called_str = " | ".join(tools_called) if tools_called else "No tools called"
        
        expected_tools = [f"{self.refactor_tool_name(api['api_name'])}({api['arguments']})" for api in reference_apis]
        expected_tools_str = " | ".join(expected_tools)

        print("\nTools Called:", tools_called_str)
        print("Expected Tools:", expected_tools_str)

        # Compare tool calls
        for ref_api in reference_apis:
            matched = False
            for i, pred_api in enumerate(agent_answer):
                if i in used_predictions:
                    continue

                ref_tool = self.refactor_tool_name(ref_api["api_name"])
                pred_tool = pred_api["tool_name"]

                # Allow case-insensitive and partial matches for tool names and arguments
                if ref_tool == pred_tool:
                    if self.args_match(ref_api["arguments"], pred_api["arguments"]):
                        total_score += 1
                        matched_tools.append(pred_api)
                        used_predictions.add(i)
                        matched = True
                        break

            if not matched:
                unmatched_tools.append(ref_api)

        score = total_score / max_score if max_score > 0 else 0

        return {
            "instruction": example["instruction"],
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

    async def evaluate_all(self) -> tuple:
        """Evaluate all examples and return results"""
        print("\nInitializing agent...")
        try:
            await self.initialize_agent()
        except Exception as e:
            print(f"Failed to initialize agent: {e}")
            raise e
        
        print("\nRunning agent predictions...")
        
        total_examples = len(self.dataset)
        
        try:
            for i, example in enumerate(self.dataset, 1):
                print(f"\n{'='*80}")
                print(f"Processing example {i}/{total_examples} ({(i/total_examples*100):.1f}%)")
                print(f"Type: {example['type']}, Level: {example['level']}")
                print(f"Instruction: {example['instruction']}")
                print(f"{'='*80}")
                
                response = await self.predict_atl_agent_answer(example)
                result = self.evaluate_single_run(example, response)
                self.evaluation_results.append(result)
                
                print(f"\nScore: {result['score']:.2f}")
                    
        except Exception as e:
            print(f"Error during evaluation: {str(e)}")
            raise e
        finally:
            # Clean up resources
            await self.cleanup()

        return self.get_results_dataframe()

    def get_results_dataframe(self) -> tuple:
        """Convert evaluation results to a DataFrame and calculate summary stats"""
        if not self.evaluation_results:
            print("No evaluation results to process")
            return pd.DataFrame(), {}
            
        df = pd.DataFrame(self.evaluation_results)
        
        summary_stats = {
            "total_examples": len(df),
            "average_score": round(df["score"].mean() * 100, 2),
            "perfect_matches": len(df[df["score"] == 1.0]),
            "failed_matches": len(df[df["score"] == 0.0]),
            "partial_matches": len(df[(df["score"] > 0.0) & (df["score"] < 1.0)]),
        }
        
        # Add type-specific accuracy if we have both types
        if "single_tool" in df["type"].values:
            single_tool_scores = df[df["type"] == "single_tool"]["score"]
            summary_stats["single_tool_accuracy"] = round(single_tool_scores.mean() * 100, 2)
        
        if "multi_tool" in df["type"].values:
            multi_tool_scores = df[df["type"] == "multi_tool"]["score"]
            summary_stats["multi_tool_accuracy"] = round(multi_tool_scores.mean() * 100, 2)
        
        # Add level-specific accuracy
        if "level" in df.columns:
            summary_stats["by_level"] = {
                f"level_{level}": round(score * 100, 2)
                for level, score in df.groupby("level")["score"].mean().items()
            }
        
        # Save results
        output_dir = Path.cwd() / "evaluation_results"
        print(f"\nResults will be saved in: {output_dir.absolute()}")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        results_path = output_dir / f"enhanced_all_transformation_evaluation_{timestamp}.csv"
        df.to_csv(results_path, index=False)
        print(f"Results saved to: {results_path}")
        
        summary_path = output_dir / f"enhanced_all_transformation_summary_{timestamp}.json"
        with open(summary_path, 'w') as f:
            json.dump(summary_stats, f, indent=4, sort_keys=True)
        print(f"Summary saved to: {summary_path}")
        
        return df, summary_stats

async def evaluate_tool_filtering_by_rag():
    """Main evaluation function"""
    
    if 'PROJECT_ROOT' in os.environ:
        root_dir = os.environ['PROJECT_ROOT']
    else:
        root_dir = os.getcwd()
        
    file_path = os.path.join(root_dir, 'dataset.json')
    dataset_path = Path(file_path)
    
    if not dataset_path.exists():
        print(f"Error: Dataset file not found at {dataset_path}")
        return None, None
           
    print(f"Starting evaluation with dataset: {dataset_path}")
    
    evaluator = EnhancedTransformationEvaluator(dataset_path)
    results_df, summary_stats = await evaluator.evaluate_all()
    return results_df, summary_stats