import json
import os
import requests
from typing import List, Dict, Set
from dataclasses import dataclass
from tqdm import tqdm
from dataset_generation.seeds.multi_tool_seeds import MultiToolSeeds, Seed
from urllib.parse import urlparse
from dataset_generation.seeds.single_tool_seeds import SingleToolSeeds
import math

# Import configuration
try:
    from config.config import (
        BASE_URL,
        API_USER,
        API_PASSWORD,
        OLLAMA_MODEL,
        OLLAMA_TEMPERATURE
    )
except ImportError:
    print("Error: Could not import configuration. Make sure config.py exists and is properly set up.")

@dataclass
class InstructionGroup:
    level: int
    pattern: str
    instructions: List[Dict]

class PlaceholderValidator:
    @staticmethod
    def validate_single_tool(instruction: str, pattern: str, level: int) -> bool:
            instruction_lower = instruction.lower()
            
            # Removed the rejection of level 3 get pattern
            
            if pattern == 'get':
                if level == 1:
                    # Level 1 get: needs transformation name
                    return '$transformation_name' in instruction_lower
                elif level == 2:
                    # Level 2 get: needs ONLY input and output metamodel names
                    return ('$input_metamodel_name' in instruction_lower and 
                        '$output_metamodel_name' in instruction_lower and
                        '$transformation_name' not in instruction_lower)  # Explicitly check absence
                elif level == 3:
                    # Level 3 get: needs ONLY path and output metamodel name
                    return ('$path' in instruction_lower and
                        '$output_metamodel_name' in instruction_lower and
                        '$transformation_name' not in instruction_lower and
                        '$input_metamodel_name' not in instruction_lower)  # Check no other placeholders
                    
            elif pattern == 'apply':
                if level == 1:
                    # Level 1 apply: needs path and transformation name
                    return ('$path' in instruction_lower and 
                        '$transformation_name' in instruction_lower)
                elif level == 2:
                    # Level 2 apply: needs ONLY path, input and output metamodel names
                    return ('$path' in instruction_lower and
                        '$input_metamodel_name' in instruction_lower and 
                        '$output_metamodel_name' in instruction_lower and
                        '$transformation_name' not in instruction_lower)  # Explicitly check absence
                elif level == 3:
                    # Level 3 apply: needs ONLY path and output metamodel name
                    return ('$path' in instruction_lower and
                        '$output_metamodel_name' in instruction_lower and
                        '$transformation_name' not in instruction_lower and  # Check no other placeholders
                        '$input_metamodel_name' not in instruction_lower)
            
            return False

    @staticmethod
    def validate_multi_tool(instruction: str, pattern: str, level: int) -> bool:
        instruction_lower = instruction.lower()
        patterns = pattern.split(', ')
        
        if len(patterns) != 2:
            return False
            
        # Level 1 validations
        if level == 1:
            if pattern == 'get, get':
                # Both tasks need transformation names
                return ('$transformation_name1' in instruction_lower and 
                       '$transformation_name2' in instruction_lower)
                       
            elif pattern == 'get, apply':
                # First task needs transformation name
                # Second task needs path and transformation name
                return ('$transformation_name1' in instruction_lower and
                       '$path2' in instruction_lower and
                       '$transformation_name2' in instruction_lower)
                       
            elif pattern == 'apply, get':
                # First task needs path and transformation name
                # Second task needs transformation name
                return ('$path1' in instruction_lower and
                       '$transformation_name1' in instruction_lower and
                       '$transformation_name2' in instruction_lower)
                       
            elif pattern == 'apply, apply':
                # Both tasks need path and transformation name
                return ('$path1' in instruction_lower and
                       '$transformation_name1' in instruction_lower and
                       '$path2' in instruction_lower and
                       '$transformation_name2' in instruction_lower)
                       
        # Level 2 validations
        elif level == 2:
            if pattern == 'get, get':
                # Both tasks need input and output metamodel names
                return ('$input_metamodel_name1' in instruction_lower and
                       '$output_metamodel_name1' in instruction_lower and
                       '$input_metamodel_name2' in instruction_lower and
                       '$output_metamodel_name2' in instruction_lower)
                       
            elif pattern == 'get, apply':
                # First task needs input and output metamodel names
                # Second task needs path, input and output metamodel names
                return ('$input_metamodel_name1' in instruction_lower and
                    '$output_metamodel_name1' in instruction_lower and
                    '$path2' in instruction_lower and
                    '$input_metamodel_name2' in instruction_lower and
                    '$output_metamodel_name2' in instruction_lower)
                       
            elif pattern == 'apply, get':
                # First task needs path, input and output metamodel names
                # Second task needs input and output metamodel names
               return ('$path1' in instruction_lower and
                    '$input_metamodel_name1' in instruction_lower and
                    '$output_metamodel_name1' in instruction_lower and
                    '$input_metamodel_name2' in instruction_lower and
                    '$output_metamodel_name2' in instruction_lower)
                       
            elif pattern == 'apply, apply':
                # Both tasks need path, input and output metamodel names
                return ('$path1' in instruction_lower and
                       '$input_metamodel_name1' in instruction_lower and
                       '$output_metamodel_name1' in instruction_lower and
                       '$path2' in instruction_lower and
                       '$input_metamodel_name2' in instruction_lower and
                       '$output_metamodel_name2' in instruction_lower)
                       
        # Level 3 validations - Added all patterns for level 3
        elif level == 3:
            if pattern == 'apply, apply':
                # Both tasks need path and output metamodel name
                return ('$path1' in instruction_lower and
                       '$output_metamodel_name1' in instruction_lower and
                       '$path2' in instruction_lower and
                       '$output_metamodel_name2' in instruction_lower)
            elif pattern == 'get, apply':
                # First task needs path and output metamodel name
                # Second task needs path and output metamodel name
                return ('$path1' in instruction_lower and
                       '$output_metamodel_name1' in instruction_lower and
                       '$path2' in instruction_lower and
                       '$output_metamodel_name2' in instruction_lower)
            elif pattern == 'apply, get':
                # First task needs path and output metamodel name
                # Second task needs path and output metamodel name
                return ('$path1' in instruction_lower and
                       '$output_metamodel_name1' in instruction_lower and
                       '$path2' in instruction_lower and
                       '$output_metamodel_name2' in instruction_lower)
            elif pattern == 'get, get':
                # Both tasks need path and output metamodel name
                return ('$path1' in instruction_lower and
                       '$output_metamodel_name1' in instruction_lower and
                       '$path2' in instruction_lower and
                       '$output_metamodel_name2' in instruction_lower)
        
        return False

class BalancedJSONWriter:
    def __init__(self, filename: str):
        self.filename = filename
        
        # Updated structure to store instructions - including Level 3 get for single tool
        self.single_tool_instructions = {
            1: {"get": [], "apply": []},
            2: {"get": [], "apply": []},
            3: {"get": [], "apply": []}  # Added "get" for level 3
        }
        
        # Updated structure for multi-tool - adding more patterns for level 3
        self.multi_tool_instructions = {
            1: {"get, get": [], "get, apply": [], "apply, get": [], "apply, apply": []},
            2: {"get, get": [], "get, apply": [], "apply, get": [], "apply, apply": []},
            3: {"get, get": [], "get, apply": [], "apply, get": [], "apply, apply": []}  # Added all patterns for level 3
        }
        
        self.seen_instructions = {
            "single_tool": set(),
            "multi_tool": set()
        }
        
        # Calculate target counts (33 per level, evenly distributed across patterns)
        self.target_counts = self._calculate_target_counts()
        
    def _calculate_target_counts(self) -> Dict:
        """Calculate how many instructions we need for each level/pattern to achieve the balanced distribution"""
        targets = {
            "single_tool": {},
            "multi_tool": {}
        }
        
        # For single tool: 33 instructions per level, divided among patterns
        for level in [1, 2]:
            # 2 patterns (get, apply) for levels 1 and 2
            pattern_count = 33 // 2  # ~17 per pattern (with potential rounding)
            targets["single_tool"][level] = {"get": pattern_count, "apply": pattern_count}
            
            # Adjust to make sure we get exactly 33 per level
            remainder = 33 - (pattern_count * 2)
            if remainder > 0:
                targets["single_tool"][level]["apply"] += remainder
        
        # Level 3 now has both get and apply patterns
        targets["single_tool"][3] = {"get": 33 // 2, "apply": 33 // 2}
        # Handle remainder
        remainder = 33 - (33 // 2 * 2)
        if remainder > 0:
            targets["single_tool"][3]["apply"] += remainder
        
        # For multi tool: 33 instructions per level, divided among patterns
        for level in [1, 2]:
            # 4 patterns for levels 1 and 2
            pattern_count = 33 // 4  # ~8 per pattern
            targets["multi_tool"][level] = {
                "get, get": pattern_count,
                "get, apply": pattern_count,
                "apply, get": pattern_count,
                "apply, apply": pattern_count
            }
            
            # Adjust to make sure we get exactly 33 per level
            remainder = 33 - (pattern_count * 4)
            if remainder > 0:
                # Distribute remainder across patterns
                patterns = ["get, get", "get, apply", "apply, get", "apply, apply"]
                for i in range(remainder):
                    targets["multi_tool"][level][patterns[i]] += 1
        
        # Level 3 now has all 4 patterns
        pattern_count = 33 // 4
        targets["multi_tool"][3] = {
            "get, get": pattern_count,
            "get, apply": pattern_count,
            "apply, get": pattern_count,
            "apply, apply": pattern_count
        }
        
        # Adjust for level 3 multi-tool
        remainder = 33 - (pattern_count * 4)
        if remainder > 0:
            patterns = ["get, get", "get, apply", "apply, get", "apply, apply"]
            for i in range(remainder):
                targets["multi_tool"][3][patterns[i]] += 1
        
        return targets
        
    def add_instruction(self, instruction: Dict, tool_type: str) -> bool:
        """Add an instruction if we still need more for this level/pattern"""
        level = instruction["level"]
        pattern = instruction["pattern"]
        
        if tool_type == "single_tool":
            target = self.target_counts["single_tool"][level][pattern]
            current = len(self.single_tool_instructions[level][pattern])
            
            if current < target:
                self.single_tool_instructions[level][pattern].append(instruction)
                return True
                
        else:  # multi_tool
            target = self.target_counts["multi_tool"][level][pattern]
            current = len(self.multi_tool_instructions[level][pattern])
            
            if current < target:
                self.multi_tool_instructions[level][pattern].append(instruction)
                return True
                
        return False  # Didn't add because we already have enough
        
    def get_level_pattern_count(self, level: int, pattern: str, tool_type: str) -> int:
        """Get the current count of instructions for a level/pattern"""
        if tool_type == "single_tool":
            return len(self.single_tool_instructions[level][pattern])
        else:
            return len(self.multi_tool_instructions[level][pattern])
            
    def get_target_count(self, level: int, pattern: str, tool_type: str) -> int:
        """Get the target count for a level/pattern"""
        return self.target_counts[tool_type][level][pattern]
            
    def is_level_complete(self, level: int, tool_type: str) -> bool:
        """Check if a level has all its required instructions"""
        if tool_type == "single_tool":
            patterns = self.single_tool_instructions[level].keys()
            for pattern in patterns:
                current = len(self.single_tool_instructions[level][pattern])
                target = self.target_counts["single_tool"][level][pattern]
                if current < target:
                    return False
            return True
        else:
            patterns = self.multi_tool_instructions[level].keys()
            for pattern in patterns:
                current = len(self.multi_tool_instructions[level][pattern])
                target = self.target_counts["multi_tool"][level][pattern]
                if current < target:
                    return False
            return True
            
    def is_complete(self, tool_type: str) -> bool:
        """Check if we have all required instructions for a tool type"""
        if tool_type == "single_tool":
            levels = [1, 2, 3]
        else:
            levels = [1, 2, 3]
            
        for level in levels:
            if not self.is_level_complete(level, tool_type):
                return False
                
        return True
        
    def get_total_count(self, tool_type: str) -> int:
        """Get the total number of instructions collected for a tool type"""
        total = 0
        
        if tool_type == "single_tool":
            for level in [1, 2, 3]:
                for pattern in self.single_tool_instructions[level].keys():
                    total += len(self.single_tool_instructions[level][pattern])
        else:
            for level in [1, 2, 3]:
                for pattern in self.multi_tool_instructions[level].keys():
                    total += len(self.multi_tool_instructions[level][pattern])
                    
        return total
    
    def save_to_file(self) -> bool:
        """Save the generated instructions to file"""
        print("\nPreparing to save instructions...")
        
        # Flatten all instructions for single tool
        single_tool_flat = []
        for level in [1, 2, 3]:
            for pattern in self.single_tool_instructions[level]:
                single_tool_flat.extend(self.single_tool_instructions[level][pattern])
        
        # Flatten all instructions for multi tool
        multi_tool_flat = []
        for level in [1, 2, 3]:
            for pattern in self.multi_tool_instructions[level]:
                multi_tool_flat.extend(self.multi_tool_instructions[level][pattern])
        
        # Create the final data structure
        data = {
            "single_tool": single_tool_flat,
            "multi_tool": multi_tool_flat
        }
        
        # Write to the main file
        path = './dataset_generation/generation'
        with open(os.path.join(path,self.filename), 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        # Write detailed data for analysis
        path = './dataset_generation/generation'
        with open(os.path.join(path, 'instruction_groups_detailed.json'), 'w', encoding='utf-8') as f:
            detailed_data = {
                "single_tool": {
                    f"level_{level}_{pattern}": self.single_tool_instructions[level][pattern]
                    for level in [1, 2, 3]
                    for pattern in self.single_tool_instructions[level]
                },
                "multi_tool": {
                    f"level_{level}_{pattern}": self.multi_tool_instructions[level][pattern]
                    for level in [1, 2, 3]
                    for pattern in self.multi_tool_instructions[level]
                }
            }
            json.dump(detailed_data, f, indent=2)
        
        # Print summary
        print("\nSuccessfully saved:")
        print(f"Single tool instructions: {len(single_tool_flat)}")
        print(f"Multi tool instructions: {len(multi_tool_flat)}")
        print(f"Total instructions: {len(single_tool_flat) + len(multi_tool_flat)}")
        
        # Print distribution
        print("\nSingle Tool Distribution:")
        for level in [1, 2, 3]:
            level_total = sum(len(self.single_tool_instructions[level][pattern]) for pattern in self.single_tool_instructions[level])
            print(f"Level {level}: {level_total} instructions")
            for pattern in self.single_tool_instructions[level]:
                count = len(self.single_tool_instructions[level][pattern])
                target = self.target_counts["single_tool"][level][pattern]
                print(f"  Pattern '{pattern}': {count}/{target} instructions")
        
        print("\nMulti Tool Distribution:")
        for level in [1, 2, 3]:
            level_total = sum(len(self.multi_tool_instructions[level][pattern]) for pattern in self.multi_tool_instructions[level])
            print(f"Level {level}: {level_total} instructions")
            for pattern in self.multi_tool_instructions[level]:
                count = len(self.multi_tool_instructions[level][pattern])
                target = self.target_counts["multi_tool"][level][pattern]
                print(f"  Pattern '{pattern}': {count}/{target} instructions")
        
        return True

class EvenlyBalancedInstructionGenerator:
    def __init__(self):
        self.model_name = OLLAMA_MODEL
        self.base_url = "http://localhost:11434"
        #self.auth = (API_USER, API_PASSWORD) if API_USER and API_PASSWORD else None
        self.temperature = OLLAMA_TEMPERATURE
        self.writer = BalancedJSONWriter('evenly_balanced_instructions.json')
        self.validator = PlaceholderValidator()

    def _check_server_connection(self) -> bool:
        try:
            response = requests.get(self.base_url, timeout=10)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"Failed to connect to Ollama server: {str(e)}")
            return False
        

    
    def _call_ollama(self, prompt: str, max_retries=3, backoff_factor=2) -> str:
        """
        Call Ollama API with retry logic to handle connection issues.
        
        Args:
            prompt: The prompt to send to Ollama
            max_retries: Maximum number of retry attempts
            backoff_factor: Factor to increase wait time between retries
            
        Returns:
            Response string from Ollama or empty string if all retries fail
        """
        import time
        
        if not self._check_server_connection():
            print("Warning: Could not establish connection to Ollama server.")
            # Don't immediately exit, try to proceed with retries
        
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "temperature": self.temperature
        }
        
        for retry in range(max_retries + 1):
            try:
                print(f"Attempt {retry + 1}/{max_retries + 1} to call Ollama...")
                
                # Increase timeout for larger payloads
                response = requests.post(url, json=payload, timeout=60)
                response.raise_for_status()
                return response.json()["response"]
                
            except requests.exceptions.Timeout:
                wait_time = backoff_factor ** retry
                print(f"Request timed out. Waiting {wait_time} seconds before retrying...")
                time.sleep(wait_time)
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 401:
                    print("Authentication failed. Please check your API credentials.")
                    return ""
                elif e.response.status_code == 404:
                    print(f"Model '{self.model_name}' not found. Please check if the model is available on the server.")
                    return ""
                elif e.response.status_code >= 500:
                    # Server errors (5xx) may be temporary, worth retrying
                    wait_time = backoff_factor ** retry
                    print(f"Server error: {e}. Waiting {wait_time} seconds before retrying...")
                    time.sleep(wait_time)
                else:
                    print(f"HTTP Error: {e}")
                    return ""
                    
            except requests.exceptions.ConnectionError as e:
                wait_time = backoff_factor ** retry
                print(f"Connection error: {e}. Waiting {wait_time} seconds before retrying...")
                time.sleep(wait_time)
                
            except Exception as e:
                print(f"Error calling Ollama: {e}")
                return ""
        
        print("All retry attempts failed. Returning empty response.")
        return ""

    def _create_single_tool_prompt(self, seed: Seed) -> str:
        """Create a prompt for generating single tool instructions with clear semantic distinction between get/apply."""
        prompt = (
            f"Generate variations of this instruction while preserving its exact meaning and pattern.\n"
            f"Level: {seed.level}\n"
            f"Pattern: {seed.pattern}\n\n"
            f"Original instruction: {seed.instruction}\n\n"
            "Requirements:\n"
            "1. Generate 40 unique variations\n"
            "2. Each variation must be a natural language instruction (not paths or commands)\n"
            "3. Use diverse vocabulary and sentence structures\n"
            "4. Avoid repetitive phrasings\n"
            "5. Keep all placeholders exactly as they appear\n"
            "6. Do not use any additional placeholders\n"
        )
        
        # Add pattern-specific requirements with clear semantic distinction
        if seed.pattern == 'get':
            # For GET operations - focus on SHOWING, DISPLAYING, RETRIEVING information
            if seed.level == 1:
                prompt += "7. Must include $transformation_name\n"
                prompt += "8. Focus on retrieving, showing, or displaying configuration information\n"
                prompt += "9. ALWAYS use verbs like 'show', 'display', 'retrieve', 'get', 'view', or 'see' at the beginning\n"
                prompt += "10. NEVER use words like 'transform', 'convert', or 'apply' that imply active transformation\n"
            elif seed.level == 2:
                prompt += "7. Must include ONLY $input_metamodel_name and $output_metamodel_name\n"
                prompt += "8. DO NOT use $transformation_name placeholder\n"
                prompt += "9. Focus on retrieving, showing, or displaying configuration information about model-to-model transformation\n"
                prompt += "10. ALWAYS use verbs like 'show', 'display', 'retrieve', 'get', 'view', or 'see' at the beginning\n"
                prompt += "11. NEVER use words like 'transform', 'convert', or 'apply' that imply active transformation\n"
            elif seed.level == 3:
                prompt += "7. Must include ONLY $path and $output_metamodel_name\n"
                prompt += "8. DO NOT use any other placeholders ($transformation_name, $input_metamodel_name)\n"
                prompt += "9. Focus on retrieving, showing, or displaying information about a transformation to the target model\n"
                prompt += "10. ALWAYS use verbs like 'show', 'display', 'retrieve', 'get', 'view', or 'see' at the beginning\n"
                prompt += "11. NEVER use words like 'transform', 'convert', or 'apply' that imply active transformation\n"
        else:  # apply
            # For APPLY operations - focus on TRANSFORMING, CONVERTING, APPLYING transformations
            if seed.level == 1:
                prompt += "7. Must include $path and $transformation_name\n"
                prompt += "8. Focus on actively applying or executing the transformation\n"
                prompt += "9. ALWAYS use verbs like 'transform', 'convert', 'apply', 'execute', or 'run' at the beginning\n"
                prompt += "10. NEVER use words like 'show', 'display', or 'get' that imply only retrieving information\n"
            elif seed.level == 2:
                prompt += "7. Must include ONLY $path, $input_metamodel_name, and $output_metamodel_name\n"
                prompt += "8. DO NOT use $transformation_name placeholder\n"
                prompt += "9. Focus on actively executing the model transformation process\n"
                prompt += "10. ALWAYS use verbs like 'transform', 'convert', 'apply', 'execute', or 'run' at the beginning\n"
                prompt += "11. NEVER use words like 'show', 'display', or 'get' that imply only retrieving information\n"
            elif seed.level == 3:
                prompt += "7. Must include ONLY $path and $output_metamodel_name\n"
                prompt += "8. DO NOT use any other placeholders ($transformation_name, $input_metamodel_name)\n"
                prompt += "9. Focus on actively executing the target model transformation\n"
                prompt += "10. ALWAYS use verbs like 'transform', 'convert', 'apply', 'execute', or 'run' at the beginning\n"
                prompt += "11. NEVER use words like 'show', 'display', or 'get' that imply only retrieving information\n"
                    
        prompt += "\nExamples of good variations:\n"
        
        if seed.pattern == 'get':
            # GET operation examples with clear "showing" semantics
            if seed.level == 1:
                prompt += "- Show me the detailed configuration for the $transformation_name transformation\n"
                prompt += "- Display all settings for the $transformation_name transformation\n"
                prompt += "- Retrieve the complete configuration of the $transformation_name transformation\n"
            elif seed.level == 2:
                prompt += "- Show me how to convert a $input_metamodel_name model into a $output_metamodel_name model\n"
                prompt += "- Display the configuration for transforming $input_metamodel_name to $output_metamodel_name\n"
                prompt += "- View the transformation settings from $input_metamodel_name to $output_metamodel_name\n"
            elif seed.level == 3:
                prompt += "- Show me how to convert the model at $path to $output_metamodel_name format\n"
                prompt += "- Display the transformation details for converting $path to $output_metamodel_name\n"
                prompt += "- View the conversion process from $path to $output_metamodel_name\n"
        else:  # apply
            # APPLY operation examples with clear "transforming" semantics
            if seed.level == 1:
                prompt += "- Transform $path using the $transformation_name process\n"
                prompt += "- Convert the model at $path by applying the $transformation_name transformation\n"
                prompt += "- Execute the $transformation_name transformation on $path\n"
            elif seed.level == 2:
                prompt += "- Transform the $input_metamodel_name model at $path into a $output_metamodel_name model\n"
                prompt += "- Convert the model at $path from $input_metamodel_name to $output_metamodel_name\n"
                prompt += "- Execute the transformation of $path from $input_metamodel_name to $output_metamodel_name\n"
            elif seed.level == 3:
                prompt += "- Transform the model at $path to $output_metamodel_name format\n"
                prompt += "- Convert the given $path into a $output_metamodel_name model\n"
                prompt += "- Apply the transformation to $path to create a $output_metamodel_name model\n"
                    
        prompt += "\nReturn only the variations, one per line, without numbering or additional text."
        return prompt

    def _create_multi_tool_prompt(self, seed: Seed) -> str:
        """Create a prompt for generating multi-tool instructions with clear semantic distinction between get/apply."""
        prompt = (
            f"Generate variations of this multi-tool instruction while preserving its exact meaning and pattern.\n"
            f"Level: {seed.level}\n"
            f"Pattern: {seed.pattern}\n\n"
            f"Original instruction: {seed.instruction}\n\n"
            "Requirements:\n"
            "1. Generate 40 unique variations\n"
            "2. Each variation must be a natural language instruction\n"
            "3. Use diverse vocabulary and sentence structures\n"
            "4. Keep the sequence of operations clear\n"
            "5. Never use numbering (1., 2., etc.)\n"
            "6. Use connecting words (then, after, once, etc.) to link the operations\n"
            "7. Keep all numbered placeholders exactly as they appear\n"
        )
        
        patterns = seed.pattern.split(', ')
        
        # Add additional semantic requirements based on patterns
        prompt += "\nCritical semantic requirements:\n"
        
        for i, pattern in enumerate(patterns, 1):
            if pattern == 'get':
                # GET operations must use verbs related to showing/displaying
                prompt += f"- For operation {i} (GET operation): ALWAYS use verbs like 'show', 'display', 'retrieve', 'get', 'view' or 'see'\n"
                prompt += f"- For operation {i}: NEVER use words like 'transform', 'convert', or 'apply' that imply active transformation\n"
            else:  # apply
                # APPLY operations must use verbs related to transforming/converting
                prompt += f"- For operation {i} (APPLY operation): ALWAYS use verbs like 'transform', 'convert', 'apply', 'execute', or 'run'\n"
                prompt += f"- For operation {i}: NEVER use words like 'show', 'display', or 'get' that imply only retrieving information\n"
        
        # Add level and pattern specific examples
        prompt += "\nExamples of good variations:"
        
        if seed.level == 1:
            if seed.pattern == "get, get":
                prompt += "\n- Show me the settings for $transformation_name1 then display the configuration for $transformation_name2"
                prompt += "\n- Retrieve the configuration of $transformation_name1 followed by viewing the settings of $transformation_name2"
            elif seed.pattern == "get, apply":
                prompt += "\n- Display the configuration of $transformation_name1 then transform $path2 using $transformation_name2"
                prompt += "\n- After showing me the settings for $transformation_name1, apply $transformation_name2 to $path2"
            elif seed.pattern == "apply, get":
                prompt += "\n- Transform $path1 with $transformation_name1 and then display the $transformation_name2 configuration"
                prompt += "\n- Apply $transformation_name1 to $path1 then show me the settings for $transformation_name2"
            elif seed.pattern == "apply, apply":
                prompt += "\n- Transform $path1 using $transformation_name1 then convert $path2 using $transformation_name2"
                prompt += "\n- Apply $transformation_name1 to $path1 followed by executing $transformation_name2 on $path2"
                
        elif seed.level == 2:
            if seed.pattern == "get, get":
                prompt += "\n- Show the configuration for transforming $input_metamodel_name1 to $output_metamodel_name1 then display the settings for converting $input_metamodel_name2 to $output_metamodel_name2"
                prompt += "\n- View how to transform $input_metamodel_name1 to $output_metamodel_name1 and then see the process for $input_metamodel_name2 to $output_metamodel_name2"
            elif seed.pattern == "get, apply":
                prompt += "\n- Show me the configuration for $input_metamodel_name1 to $output_metamodel_name1 conversion then transform $path2 from $input_metamodel_name2 to $output_metamodel_name2"
                prompt += "\n- Display how to convert $input_metamodel_name1 to $output_metamodel_name1 then apply the transformation to $path2 from $input_metamodel_name2 to $output_metamodel_name2"
            elif seed.pattern == "apply, get":
                prompt += "\n- Transform $path1 from $input_metamodel_name1 to $output_metamodel_name1 then show the configuration for converting $input_metamodel_name2 to $output_metamodel_name2"
                prompt += "\n- Convert $path1 from $input_metamodel_name1 to $output_metamodel_name1 then display transformation details for $input_metamodel_name2 to $output_metamodel_name2"
            elif seed.pattern == "apply, apply":
                prompt += "\n- Transform $input_metamodel_name1 model at $path1 to $output_metamodel_name1 then convert the $input_metamodel_name2 model at $path2 to $output_metamodel_name2"
                prompt += "\n- Apply transformation to $path1 from $input_metamodel_name1 to $output_metamodel_name1 then execute conversion on $path2 from $input_metamodel_name2 to $output_metamodel_name2"
        
        elif seed.level == 3:
            if seed.pattern == "get, get":
                prompt += "\n- Show me how to transform $path1 to $output_metamodel_name1 then display the process for converting $path2 to $output_metamodel_name2"
                prompt += "\n- View the transformation configuration for $path1 to $output_metamodel_name1 and then see how to convert $path2 to $output_metamodel_name2"
            elif seed.pattern == "get, apply":
                prompt += "\n- Show me how to transform $path1 to $output_metamodel_name1 then convert $path2 to $output_metamodel_name2"
                prompt += "\n- Display the transformation details for $path1 to $output_metamodel_name1 then apply the conversion to $path2 creating a $output_metamodel_name2 model"
            elif seed.pattern == "apply, get":
                prompt += "\n- Transform $path1 to $output_metamodel_name1 then show me how to convert $path2 to $output_metamodel_name2"
                prompt += "\n- Convert $path1 to $output_metamodel_name1 then display the transformation process for $path2 to $output_metamodel_name2"
            elif seed.pattern == "apply, apply":
                prompt += "\n- Transform $path1 to $output_metamodel_name1 then convert $path2 to $output_metamodel_name2"
                prompt += "\n- Apply transformation to $path1 creating a $output_metamodel_name1 model then execute conversion on $path2 to generate a $output_metamodel_name2 model"
        
        # Add level-specific requirements
        prompt += self._add_level_requirements(seed.level, seed.pattern)
        
        prompt += "\nReturn only the variations, one per line, without numbering or additional text."
        return prompt

    def _add_level_requirements(self, level: int, pattern: str) -> str:
        reqs = "\nAdditional requirements for placeholders:\n"
        patterns = pattern.split(', ')
        
        if level == 1:
            for i, p in enumerate(patterns, 1):
                if p == 'get':
                    reqs += f"- For task {i}: Must include $transformation_name{i}\n"
                else:  # apply
                    reqs += f"- For task {i}: Must include $path{i} and $transformation_name{i}\n"
        
        elif level == 2:
            for i, p in enumerate(patterns, 1):
                if p == 'get':
                    reqs += f"- For task {i}: Must include $input_metamodel_name{i} and $output_metamodel_name{i}\n"
                else:  # apply
                    reqs += f"- For task {i}: Must include $path{i}, $input_metamodel_name{i}, and $output_metamodel_name{i}\n"
        
        elif level == 3:
            # Updated requirements for level 3 patterns
            for i, p in enumerate(patterns, 1):
                if p == 'get' or p == 'apply':
                    reqs += f"- For task {i}: Must include $path{i} and $output_metamodel_name{i}\n"
                    reqs += f"- For task {i}: DO NOT use any other placeholders ($transformation_name{i}, $input_metamodel_name{i})\n"
        
        return reqs
    

    def generate_instructions(self, seeds: List[Seed], tool_type: str) -> None:
        """Generate instructions with a balanced distribution"""
        # Process each level first to get an even distribution
        for level in [1, 2, 3]:
            level_seeds = [seed for seed in seeds if seed.level == level]
            
            # Skip if we already have all instructions for this level
            if self.writer.is_level_complete(level, tool_type):
                print(f"Level {level} for {tool_type} is already complete.")
                continue
                
            print(f"\nGenerating {tool_type} instructions for level {level}...")
            
            # Process seeds until we complete the level
            while not self.writer.is_level_complete(level, tool_type):
                for seed in level_seeds:
                    # No longer skip level 3 get pattern
                        
                    # Skip patterns that are already complete
                    pattern = seed.pattern
                    current = self.writer.get_level_pattern_count(level, pattern, tool_type)
                    target = self.writer.get_target_count(level, pattern, tool_type)
                    
                    if current >= target:
                        continue
                        
                    # Process the seed to generate variations
                    print(f"Generating {tool_type} level {level}, pattern '{pattern}': {current}/{target}")
                    self._process_seed(seed, tool_type)
                    
                    # Check if we're done with this pattern
                    new_current = self.writer.get_level_pattern_count(level, pattern, tool_type)
                    if new_current >= target:
                        print(f"Completed {tool_type} level {level}, pattern '{pattern}': {new_current}/{target}")
                        
            # Print completion message for the level
            print(f"All {tool_type} instructions for level {level} complete!")
            
        # Print final stats
        total = self.writer.get_total_count(tool_type)
        print(f"\nTotal {tool_type} instructions generated: {total}/100")

    def _process_seed(self, seed: Seed, tool_type: str) -> None:
        """Process a single seed to generate variations with semantic validation and fallback options."""
        level = seed.level
        pattern =seed.pattern  
        
        # Skip if we already have enough instructions for this pattern
        current = self.writer.get_level_pattern_count(level, pattern, tool_type)
        target = self.writer.get_target_count(level, pattern, tool_type)
        
        if current >= target:
            return
        
        print(f"Processing seed: Level {level}, Pattern '{pattern}'")
        print(f"Original instruction: {seed.instruction}")
        
        # Create prompt based on tool type
        if tool_type == "single_tool":
            prompt = self._create_single_tool_prompt(seed)
        else:
            prompt = self._create_multi_tool_prompt(seed)
            
        if not prompt:  # Empty prompt
            print("Warning: Empty prompt generated. Skipping this seed.")
            return
        
        # Try to generate with Ollama first
        response = self._call_ollama(prompt)
        
        # If Ollama fails, use a fallback approach
        if not response:
            print("Ollama failed to generate responses. Using fallback manual variations.")
        else:
            # Parse Ollama response
            variations = [line.strip() for line in response.split('\n') if line.strip()]
        
        # Validate and add variations
        added_count = 0
        rejected_count = 0
        
        for var in variations:
            # Skip processing if we've reached the target
            if self.writer.get_level_pattern_count(level, pattern, tool_type) >= target:
                break
                
            normalized_var = ' '.join(var.lower().split())
            
            # Skip if we've seen this variation before
            if normalized_var in self.writer.seen_instructions[tool_type]:
                continue
                
            # First validate placeholders
            if tool_type == "single_tool":
                is_valid = self.validator.validate_single_tool(var, pattern, level)
            else:
                is_valid = self.validator.validate_multi_tool(var, pattern, level)
                
            if is_valid:
                    instruction = {
                        "instruction": var,
                        "level": level,
                        "pattern": pattern
                    }
                    
                    # Try to add it
                    if self.writer.add_instruction(instruction, tool_type):
                        self.writer.seen_instructions[tool_type].add(normalized_var)
                        added_count += 1
              
            else:
                rejected_count += 1
        
        print(f"Added {added_count} new instructions, rejected {rejected_count} for placeholder issues.")
        
        # If we still need more instructions, try to generate more through manual approach
        if added_count == 0 and self.writer.get_level_pattern_count(level, pattern, tool_type) < target:
            print(f"Could not generate any valid instructions. Using more aggressive fallback approach...")
            
            # Use a more aggressive approach to generate variations
            more_variations = self._generate_aggressive_fallback(seed, pattern, level, tool_type)
            
            # Process these additional variations
            more_added = 0
            for var in more_variations:
                if self.writer.get_level_pattern_count(level, pattern, tool_type) >= target:
                    break
                    
                normalized_var = ' '.join(var.lower().split())
                
                if normalized_var in self.writer.seen_instructions[tool_type]:
                    continue
                    
                # Validate again
                if tool_type == "single_tool":
                    is_valid = self.validator.validate_single_tool(var, pattern, level)
                else:
                    is_valid = self.validator.validate_multi_tool(var, pattern, level)
                    
                if is_valid and self._validate_instruction_semantics(var, pattern, level):
                    instruction = {
                        "instruction": var,
                        "level": level,
                        "pattern": pattern
                    }
                    
                    if self.writer.add_instruction(instruction, tool_type):
                        self.writer.seen_instructions[tool_type].add(normalized_var)
                        more_added += 1
            
            print(f"Fallback approach added {more_added} additional instructions")
            added_count += more_added
        
        print(f"Total added: {added_count} new instructions for level {level}, pattern '{pattern}'")
        print(f"Current count: {self.writer.get_level_pattern_count(level, pattern, tool_type)}/{target}")


def generate_evenly_balanced_dataset():
        """Generate a balanced dataset with exactly 33 instructions per level, evenly distributed across patterns"""
        print("\nStarting evenly balanced instruction generation...")
        print("Target: 100 instructions per tool type, 33 per level, even pattern distribution")
        
        try:
            # Get seeds - fix the spacing issues in patterns
            single_tool_seeds = SingleToolSeeds.get_seeds()
            multi_tool_seeds = MultiToolSeeds.get_seeds()
            
            # Initialize the generator
            generator = EvenlyBalancedInstructionGenerator()
            
            # Track progress to allow for resuming
            progress = {"single_tool": False, "multi_tool": False}
            progress_file = "generation_progress.json"
            
            # Try to load progress if it exists
            try:
                if os.path.exists(progress_file):
                    with open(progress_file, 'r') as f:
                        progress = json.load(f)
                    print(f"Loaded progress: {progress}")
            except Exception as e:
                print(f"Could not load progress file: {e}")
            
            # Generate single-tool instructions if not already completed
            if not progress["single_tool"]:
                print("\nGenerating single-tool instructions...")
                try:
                    generator.generate_instructions(single_tool_seeds, "single_tool")
                    progress["single_tool"] = True
                    # Save progress
                    with open(progress_file, 'w') as f:
                        json.dump(progress, f)
                except Exception as e:
                    print(f"Error generating single-tool instructions: {e}")
                    # Continue to multi-tool anyway
            else:
                print("\nSkipping single-tool instructions (already completed)")
            
            # Generate multi-tool instructions if not already completed
            if not progress["multi_tool"]:
                print("\nGenerating multi-tool instructions...")
                try:
                    generator.generate_instructions(multi_tool_seeds, "multi_tool")
                    progress["multi_tool"] = True
                    # Save progress
                    with open(progress_file, 'w') as f:
                        json.dump(progress, f)
                except Exception as e:
                    print(f"Error generating multi-tool instructions: {e}")
            else:
                print("\nSkipping multi-tool instructions (already completed)")
            
            # Save the results even if not all were generated
            try:
                result = generator.writer.save_to_file()
                if result:
                    print("\nSuccessfully saved instructions to file.")
                    
                    # If both steps completed, remove the progress file
                    if progress["single_tool"] and progress["multi_tool"]:
                        if os.path.exists(progress_file):
                            os.remove(progress_file)
                            print("Generation completed successfully. Progress file removed.")
                    
                    return True
                else:
                    print("\nFailed to save instructions to file.")
                    return False
            except Exception as e:
                print(f"\nError saving results to file: {e}")
                return False
                
        except Exception as e:
            print(f"Unexpected error during dataset generation: {e}")
            return False