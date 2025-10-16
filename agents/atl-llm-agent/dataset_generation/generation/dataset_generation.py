
import json
import os
import random
from collections import defaultdict
from typing import List, Dict, Any, Tuple

def try_generate_instruction(template: Dict, transformation: Dict, total_usage_counts: Dict[str, int]) -> Tuple[Dict, bool]:
    """Try to generate an instruction from a template and transformation. Returns (instruction, success)."""
    instruction = template["instruction"]
    level = template["level"]
    pattern = template["pattern"]
    new_instruction = None
    
    # Debug output
    # print(f"Trying template: Level {level}, Pattern {pattern}")
    # print(f"With transformation: {transformation['name']}")
    
    if pattern == "apply":
        if not transformation["source_models"]:
            # print(f"Skipping {transformation['name']} - no source models")
            return None, False
            
        if level == 1:
            if "$transformation_name" in instruction and "$path" in instruction:
                new_instruction = instruction.replace("$transformation_name", transformation["name"])
                new_instruction = new_instruction.replace("$path", transformation["source_models"][0])
                return {
                    "level": level,
                    "pattern": "apply",
                    "instruction": new_instruction,
                    "relevant_apis": [{
                        "api_name": f"{transformation['name']}.apply_tool",
                        "arguments": transformation["source_models"][0]
                    }]
                }, True
                
        elif level == 2:
            if all(x in instruction for x in ["$input_metamodel_name", "$output_metamodel_name", "$path"]):
                # Check if transformation has input_metamodels and output_metamodels
                if not transformation["input_metamodels"] or not transformation["output_metamodels"]:
                    # print(f"Skipping {transformation['name']} - missing metamodels for level 2")
                    return None, False
                
                # Double-check debug info
                # print(f"input_metamodels: {transformation['input_metamodels']}")
                # print(f"output_metamodels: {transformation['output_metamodels']}")
                
                new_instruction = instruction.replace("$input_metamodel_name", 
                                                   transformation["input_metamodels"][0])
                new_instruction = new_instruction.replace("$output_metamodel_name", 
                                                       transformation["output_metamodels"][0])
                new_instruction = new_instruction.replace("$path", transformation["source_models"][0])
                return {
                    "level": level,
                    "pattern": "apply",
                    "instruction": new_instruction,
                    "relevant_apis": [{
                        "api_name": f"{transformation['name']}.apply_tool",
                        "arguments": transformation["source_models"][0]
                    }]
                }, True
                
        elif level == 3:
            if "$output_metamodel_name" in instruction and "$path" in instruction:
                if not transformation["output_metamodels"]:
                    # print(f"Skipping {transformation['name']} - no output metamodels for level 3")
                    return None, False
                    
                new_instruction = instruction.replace("$output_metamodel_name", 
                                                   transformation["output_metamodels"][0])
                new_instruction = new_instruction.replace("$path", transformation["source_models"][0])
                return {
                    "level": level,
                    "pattern": "apply",
                    "instruction": new_instruction,
                    "relevant_apis": [{
                        "api_name": f"{transformation['name']}.apply_tool",
                        "arguments": transformation["source_models"][0]
                    }]
                }, True
                
    elif pattern == "get":
        if level == 1:
            if "$transformation_name" in instruction:
                new_instruction = instruction.replace("$transformation_name", transformation["name"])
                return {
                    "level": level,
                    "pattern": "get",
                    "instruction": new_instruction,
                    "relevant_apis": [{
                        "api_name": f"{transformation['name']}.get_tool",
                        "arguments": ""
                    }]
                }, True
        elif level == 2:
            if all(x in instruction for x in ["$input_metamodel_name", "$output_metamodel_name"]):
                if not transformation["input_metamodels"] or not transformation["output_metamodels"]:
                    # print(f"Skipping {transformation['name']} - missing metamodels for level 2 get")
                    return None, False
                    
                new_instruction = instruction.replace("$input_metamodel_name", 
                                                  transformation["input_metamodels"][0])
                new_instruction = new_instruction.replace("$output_metamodel_name", 
                                                      transformation["output_metamodels"][0])
                return {
                    "level": level,
                    "pattern": "get",
                    "instruction": new_instruction,
                    "relevant_apis": [{
                        "api_name": f"{transformation['name']}.get_tool",
                        "arguments": ""
                    }]
                }, True
        elif level == 3:
            if "$output_metamodel_name" in instruction and "$path" in instruction:
                if not transformation["output_metamodels"] or not transformation["source_models"]:
                    # Missing required attributes
                    return None, False
                    
                new_instruction = instruction.replace("$output_metamodel_name", 
                                                   transformation["output_metamodels"][0])
                new_instruction = new_instruction.replace("$path", 
                                                       transformation["source_models"][0])
                return {
                    "level": level,
                    "pattern": "get",
                    "instruction": new_instruction,
                    "relevant_apis": [{
                        "api_name": f"{transformation['name']}.get_tool",
                        "arguments": ""
                    }]
                }, True
    
    return None, False   

def try_generate_multi_instruction(template: Dict, trans1: Dict, trans2: Dict) -> Tuple[Dict, bool]:
    """Try to generate a multi-tool instruction. Returns (instruction, success)."""
    instruction = template["instruction"]
    pattern = template["pattern"]
    level = template["level"]
    
    if pattern == "get, get":
        if level == 1:
            if all(x in instruction for x in ["$transformation_name1", "$transformation_name2"]):
                new_instruction = instruction.replace("$transformation_name1", trans1["name"])
                new_instruction = new_instruction.replace("$transformation_name2", trans2["name"])
                return {
                    "level": level,
                    "pattern": "get, get",
                    "instruction": new_instruction,
                    "relevant_apis": [
                        {"api_name": f"{trans1['name']}.get_tool", "arguments": ""},
                        {"api_name": f"{trans2['name']}.get_tool", "arguments": ""}
                    ]
                }, True
        elif level == 2:
            if all(x in instruction for x in ["$input_metamodel_name1", "$output_metamodel_name1",
                                          "$input_metamodel_name2", "$output_metamodel_name2"]):
                if (not trans1["input_metamodels"] or not trans1["output_metamodels"] or
                    not trans2["input_metamodels"] or not trans2["output_metamodels"]):
                    return None, False
                    
                new_instruction = instruction.replace("$input_metamodel_name1", trans1["input_metamodels"][0])
                new_instruction = new_instruction.replace("$output_metamodel_name1", trans1["output_metamodels"][0])
                new_instruction = new_instruction.replace("$input_metamodel_name2", trans2["input_metamodels"][0])
                new_instruction = new_instruction.replace("$output_metamodel_name2", trans2["output_metamodels"][0])
                return {
                    "level": level,
                    "pattern": "get, get",
                    "instruction": new_instruction,
                    "relevant_apis": [
                        {"api_name": f"{trans1['name']}.get_tool", "arguments": ""},
                        {"api_name": f"{trans2['name']}.get_tool", "arguments": ""}
                    ]
                }, True
        # Added support for level 3 "get, get" pattern
        elif level == 3:
            if all(x in instruction for x in ["$path1", "$output_metamodel_name1",
                                              "$path2", "$output_metamodel_name2"]):
                if (not trans1["output_metamodels"] or not trans1["source_models"] or
                    not trans2["output_metamodels"] or not trans2["source_models"]):
                    return None, False
                    
                new_instruction = instruction.replace("$path1", trans1["source_models"][0])
                new_instruction = new_instruction.replace("$output_metamodel_name1", trans1["output_metamodels"][0])
                new_instruction = new_instruction.replace("$path2", trans2["source_models"][0])
                new_instruction = new_instruction.replace("$output_metamodel_name2", trans2["output_metamodels"][0])
                return {
                    "level": level,
                    "pattern": "get, get",
                    "instruction": new_instruction,
                    "relevant_apis": [
                        {"api_name": f"{trans1['name']}.get_tool", "arguments": ""},
                        {"api_name": f"{trans2['name']}.get_tool", "arguments": ""}
                    ]
                }, True
                   
    elif pattern == "get, apply":
        if not trans2["source_models"]:
            return None, False
            
        if level == 1:
            if all(x in instruction for x in ["$transformation_name1", "$transformation_name2", "$path2"]):
                new_instruction = instruction.replace("$transformation_name1", trans1["name"])
                new_instruction = new_instruction.replace("$transformation_name2", trans2["name"])
                new_instruction = new_instruction.replace("$path2", trans2["source_models"][0])
                return {
                    "level": level,
                    "pattern": "get, apply",
                    "instruction": new_instruction,
                    "relevant_apis": [
                        {"api_name": f"{trans1['name']}.get_tool", "arguments": ""},
                        {"api_name": f"{trans2['name']}.apply_tool", "arguments": trans2["source_models"][0]}
                    ]
                }, True
        elif level == 2:
            if all(x in instruction for x in ["$input_metamodel_name1", "$output_metamodel_name1",
                                            "$path2", "$input_metamodel_name2", "$output_metamodel_name2"]):
                if (not trans1["input_metamodels"] or not trans1["output_metamodels"] or
                    not trans2["input_metamodels"] or not trans2["output_metamodels"]):
                    return None, False
                    
                new_instruction = instruction.replace("$input_metamodel_name1", trans1["input_metamodels"][0])
                new_instruction = new_instruction.replace("$output_metamodel_name1", trans1["output_metamodels"][0])
                new_instruction = new_instruction.replace("$input_metamodel_name2", trans2["input_metamodels"][0])
                new_instruction = new_instruction.replace("$output_metamodel_name2", trans2["output_metamodels"][0])
                new_instruction = new_instruction.replace("$path2", trans2["source_models"][0])
                return {
                    "level": level,
                    "pattern": "get, apply",
                    "instruction": new_instruction,
                    "relevant_apis": [
                        {"api_name": f"{trans1['name']}.get_tool", "arguments": ""},
                        {"api_name": f"{trans2['name']}.apply_tool", "arguments": trans2["source_models"][0]}
                    ]
                }, True
        # Added support for level 3 "get, apply" pattern
        elif level == 3:
            if all(x in instruction for x in ["$path1", "$output_metamodel_name1",
                                              "$path2", "$output_metamodel_name2"]):
                if (not trans1["output_metamodels"] or not trans1["source_models"] or
                    not trans2["output_metamodels"] or not trans2["source_models"]):
                    return None, False
                    
                new_instruction = instruction.replace("$path1", trans1["source_models"][0])
                new_instruction = new_instruction.replace("$output_metamodel_name1", trans1["output_metamodels"][0])
                new_instruction = new_instruction.replace("$path2", trans2["source_models"][0])
                new_instruction = new_instruction.replace("$output_metamodel_name2", trans2["output_metamodels"][0])
                return {
                    "level": level,
                    "pattern": "get, apply",
                    "instruction": new_instruction,
                    "relevant_apis": [
                        {"api_name": f"{trans1['name']}.get_tool", "arguments": ""},
                        {"api_name": f"{trans2['name']}.apply_tool", "arguments": trans2["source_models"][0]}
                    ]
                }, True
                    
    elif pattern == "apply, apply":
        if not (trans1["source_models"] and trans2["source_models"]):
            return None, False
            
        if level == 1:
            if all(x in instruction for x in ["$transformation_name1", "$transformation_name2",
                                            "$path1", "$path2"]):
                new_instruction = instruction.replace("$transformation_name1", trans1["name"])
                new_instruction = new_instruction.replace("$transformation_name2", trans2["name"])
                new_instruction = new_instruction.replace("$path1", trans1["source_models"][0])
                new_instruction = new_instruction.replace("$path2", trans2["source_models"][0])
                return {
                    "level": level,
                    "pattern": "apply, apply",
                    "instruction": new_instruction,
                    "relevant_apis": [
                        {"api_name": f"{trans1['name']}.apply_tool", "arguments": trans1["source_models"][0]},
                        {"api_name": f"{trans2['name']}.apply_tool", "arguments": trans2["source_models"][0]}
                    ]
                }, True
                
        elif level == 2:
            if all(x in instruction for x in ["$input_metamodel_name1", "$output_metamodel_name1",
                                            "$input_metamodel_name2", "$output_metamodel_name2",
                                            "$path1", "$path2"]):
                if (not trans1["input_metamodels"] or not trans1["output_metamodels"] or
                    not trans2["input_metamodels"] or not trans2["output_metamodels"]):
                    return None, False
                    
                new_instruction = instruction.replace("$input_metamodel_name1", trans1["input_metamodels"][0])
                new_instruction = new_instruction.replace("$output_metamodel_name1", trans1["output_metamodels"][0])
                new_instruction = new_instruction.replace("$input_metamodel_name2", trans2["input_metamodels"][0])
                new_instruction = new_instruction.replace("$output_metamodel_name2", trans2["output_metamodels"][0])
                new_instruction = new_instruction.replace("$path1", trans1["source_models"][0])
                new_instruction = new_instruction.replace("$path2", trans2["source_models"][0])
                return {
                    "level": level,
                    "pattern": "apply, apply",
                    "instruction": new_instruction,
                    "relevant_apis": [
                        {"api_name": f"{trans1['name']}.apply_tool", "arguments": trans1["source_models"][0]},
                        {"api_name": f"{trans2['name']}.apply_tool", "arguments": trans2["source_models"][0]}
                    ]
                }, True
        elif level == 3:
            if all(x in instruction for x in ["$output_metamodel_name1", "$output_metamodel_name2",
                                            "$path1", "$path2"]):
                if not trans1["output_metamodels"] or not trans2["output_metamodels"]:
                    return None, False
                    
                new_instruction = instruction.replace("$output_metamodel_name1", trans1["output_metamodels"][0])
                new_instruction = new_instruction.replace("$output_metamodel_name2", trans2["output_metamodels"][0])
                new_instruction = new_instruction.replace("$path1", trans1["source_models"][0])
                new_instruction = new_instruction.replace("$path2", trans2["source_models"][0])
                return {
                    "level": level,
                    "pattern": "apply, apply",
                    "instruction": new_instruction,
                    "relevant_apis": [
                        {"api_name": f"{trans1['name']}.apply_tool", "arguments": trans1["source_models"][0]},
                        {"api_name": f"{trans2['name']}.apply_tool", "arguments": trans2["source_models"][0]}
                    ]
                }, True
                
    elif pattern == "apply, get":
        if not trans1["source_models"]:
            return None, False
            
        if level == 1:
            if all(x in instruction for x in ["$transformation_name1", "$transformation_name2", "$path1"]):
                new_instruction = instruction.replace("$transformation_name1", trans1["name"])
                new_instruction = new_instruction.replace("$transformation_name2", trans2["name"])
                new_instruction = new_instruction.replace("$path1", trans1["source_models"][0])
                return {
                    "level": level,
                    "pattern": "apply, get",
                    "instruction": new_instruction,
                    "relevant_apis": [
                        {"api_name": f"{trans1['name']}.apply_tool", "arguments": trans1["source_models"][0]},
                        {"api_name": f"{trans2['name']}.get_tool", "arguments": ""}
                    ]
                }, True
        elif level == 2:
            if all(x in instruction for x in ["$input_metamodel_name1", "$output_metamodel_name1",
                                          "$input_metamodel_name2", "$output_metamodel_name2",
                                          "$path1"]):
                if (not trans1["input_metamodels"] or not trans1["output_metamodels"] or
                    not trans2["input_metamodels"] or not trans2["output_metamodels"]):
                    return None, False
                    
                new_instruction = instruction.replace("$input_metamodel_name1", trans1["input_metamodels"][0])
                new_instruction = new_instruction.replace("$output_metamodel_name1", trans1["output_metamodels"][0])
                new_instruction = new_instruction.replace("$input_metamodel_name2", trans2["input_metamodels"][0])
                new_instruction = new_instruction.replace("$output_metamodel_name2", trans2["output_metamodels"][0])
                new_instruction = new_instruction.replace("$path1", trans1["source_models"][0])
                return {
                    "level": level,
                    "pattern": "apply, get",
                    "instruction": new_instruction,
                    "relevant_apis": [
                        {"api_name": f"{trans1['name']}.apply_tool", "arguments": trans1["source_models"][0]},
                        {"api_name": f"{trans2['name']}.get_tool", "arguments": ""}
                    ]
                }, True
            
        # Added support for level 3 "apply, get" pattern
        elif level == 3:
            if all(x in instruction for x in ["$path1", "$output_metamodel_name1",
                                              "$path2", "$output_metamodel_name2"]):
                if (not trans1["output_metamodels"] or not trans1["source_models"] or
                    not trans2["output_metamodels"] or not trans2["source_models"]):
                    return None, False
                    
                new_instruction = instruction.replace("$path1", trans1["source_models"][0])
                new_instruction = new_instruction.replace("$output_metamodel_name1", trans1["output_metamodels"][0])
                new_instruction = new_instruction.replace("$path2", trans2["source_models"][0])
                new_instruction = new_instruction.replace("$output_metamodel_name2", trans2["output_metamodels"][0])
                return {
                    "level": level,
                    "pattern": "apply, get",
                    "instruction": new_instruction,
                    "relevant_apis": [
                        {"api_name": f"{trans1['name']}.apply_tool", "arguments": trans1["source_models"][0]},
                        {"api_name": f"{trans2['name']}.get_tool", "arguments": ""}
                    ]
                }, True
            
    return None, False

def generate_single_tool_instructions_by_level(templates: Dict[str, List[Dict]], 
                                             transformations: List[Dict],
                                             target_per_level: int,
                                             total_usage_counts: Dict[str, int],
                                             template_usage_counts: Dict[str, int]) -> Dict[int, List[Dict]]:
    """Generate single tool instructions with 200 per level."""
    
    result = {1: [], 2: [], 3: []}
    max_attempts = len(templates["single_tool"]) * len(transformations) * 20
    
    # Group templates by level and pattern
    templates_by_level_pattern = defaultdict(list)
    for template in templates["single_tool"]:
        key = (template["level"], template["pattern"])
        templates_by_level_pattern[key].append(template)
    
    # Print available templates summary
    print("\nAvailable Single Tool Templates:")
    for (level, pattern), tmpl_list in templates_by_level_pattern.items():
        print(f"Level {level}, Pattern {pattern}: {len(tmpl_list)} templates")
    
    # Check transformations for required attributes
    valid_transformations_for_level2 = []
    for t in transformations:
        if t["source_models"] and t["input_metamodels"] and t["output_metamodels"]:
            valid_transformations_for_level2.append(t)
    
    print(f"\nValid transformations for level 2: {len(valid_transformations_for_level2)} out of {len(transformations)}")
    for t in valid_transformations_for_level2:
        print(f"  - {t['name']}")
    
    # Process each level
    for level in [1, 2, 3]:
        attempts = 0
        
        # Process each pattern available for this level
        # MODIFIED: Include both "get" and "apply" patterns for all levels
        level_patterns = set(pattern for (lvl, pattern) in templates_by_level_pattern.keys() if lvl == level)
        
        if not level_patterns:
            print(f"Warning: No templates for level {level}")
            continue
            
        patterns = list(level_patterns)  # Use available patterns from templates
        
        for pattern in patterns:
            key = (level, pattern)
            level_pattern_templates = templates_by_level_pattern[key]
            
            if not level_pattern_templates:
                print(f"Warning: No templates for level {level}, pattern {pattern}")
                continue
                
            # Target for this pattern (divide evenly between patterns)
            pattern_target = target_per_level // len(patterns)
            pattern_result = []
            
            print(f"\nGenerating level {level}, pattern {pattern}: target {pattern_target} instructions")
            
            # Use each template at least once if possible
            for template in level_pattern_templates:
                if len(pattern_result) >= pattern_target:
                    break
                    
                if template_usage_counts[template["instruction"]] > 0:
                    continue
                    
                # Select appropriate transformations for this level and pattern
                usable_transformations = []
                if level == 2:
                    usable_transformations = valid_transformations_for_level2
                else:
                    usable_transformations = [t for t in transformations if t["source_models"] or pattern == "get"]
                
                if not usable_transformations:
                    print(f"Warning: No valid transformations for level {level}, pattern {pattern}")
                    break
                
                # Sort by usage count
                usable_transformations = sorted(usable_transformations, key=lambda x: total_usage_counts[x["name"]])
                
                # Try each transformation
                success = False
                for transformation in usable_transformations:
                    instruction, success = try_generate_instruction(template, transformation, total_usage_counts)
                    if success:
                        pattern_result.append(instruction)
                        template_usage_counts[template["instruction"]] += 1
                        total_usage_counts[transformation["name"]] += 1
                        break
                
                if not success:
                    print(f"Failed to use template: {template['instruction'][:50]}...")
            
            # Fill remaining slots with balanced transformation usage
            inner_attempts = 0
            max_inner_attempts = max_attempts
            
            while len(pattern_result) < pattern_target and inner_attempts < max_inner_attempts:
                inner_attempts += 1
                
                # Use templates with lowest usage
                template_counts = {t["instruction"]: template_usage_counts[t["instruction"]] 
                                for t in level_pattern_templates}
                sorted_templates = sorted(level_pattern_templates, 
                                       key=lambda x: template_counts[x["instruction"]])
                
                if not sorted_templates:
                    print(f"No templates available for level {level}, pattern {pattern}")
                    break
                    
                template = sorted_templates[0]
                
                # Select appropriate transformations
                if level == 2:
                    usable_transformations = valid_transformations_for_level2
                else:
                    usable_transformations = [t for t in transformations if t["source_models"] or pattern == "get"]
                
                if not usable_transformations:
                    print(f"No valid transformations for level {level}, pattern {pattern}")
                    break
                
                # Use transformation with lowest usage
                sorted_transformations = sorted(usable_transformations, key=lambda x: total_usage_counts[x["name"]])
                
                success = False
                for transformation in sorted_transformations[:5]:  # Try top 5 least used transformations
                    instruction, success = try_generate_instruction(template, transformation, total_usage_counts)
                    if success:
                        pattern_result.append(instruction)
                        template_usage_counts[template["instruction"]] += 1
                        total_usage_counts[transformation["name"]] += 1
                        break
                
                # Print progress every 10 instructions
                if len(pattern_result) % 10 == 0 and len(pattern_result) > 0:
                    print(f"Progress: {len(pattern_result)}/{pattern_target} instructions for level {level}, pattern {pattern}")
            
            # Add pattern results to level results
            result[level].extend(pattern_result)
            print(f"Generated {len(pattern_result)}/{pattern_target} instructions for level {level}, pattern {pattern}")
        
        print(f"Total for level {level}: {len(result[level])}/{target_per_level}")
        
        # If we still don't have enough instructions, try to reuse templates
        if len(result[level]) < target_per_level:
            print(f"Need {target_per_level - len(result[level])} more instructions for level {level}.")
            print("Will reuse templates to reach target count.")
            
            all_level_templates = []
            for pattern in patterns:
                key = (level, pattern)
                if key in templates_by_level_pattern:
                    all_level_templates.extend(templates_by_level_pattern[key])
            
            # If we still have templates available
            if all_level_templates:
                attempts = 0
                max_fill_attempts = max_attempts * 2
                
                while len(result[level]) < target_per_level and attempts < max_fill_attempts:
                    attempts += 1
                    
                    # Choose random template and transformation
                    template = random.choice(all_level_templates)
                    pattern = template["pattern"]
                    
                    # Select transformations based on level
                    if level == 2:
                        usable_transformations = valid_transformations_for_level2
                    else:
                        usable_transformations = [t for t in transformations if t["source_models"] or pattern == "get"]
                    
                    if not usable_transformations:
                        continue
                    
                    # Choose transformation with lowest usage
                    transformation = min(usable_transformations, key=lambda x: total_usage_counts[x["name"]])
                    
                    instruction, success = try_generate_instruction(template, transformation, total_usage_counts)
                    if success:
                        result[level].append(instruction)
                        template_usage_counts[template["instruction"]] += 1
                        total_usage_counts[transformation["name"]] += 1
                        
                        if len(result[level]) % 10 == 0:
                            print(f"Fill progress: {len(result[level])}/{target_per_level} for level {level}")
                
                print(f"After filling: {len(result[level])}/{target_per_level} for level {level}")
    
    return result

def generate_multi_tool_instructions_by_level(templates: Dict[str, List[Dict]], 
                                           transformations: List[Dict],
                                           target_per_level: int,
                                           total_usage_counts: Dict[str, int],
                                           template_usage_counts: Dict[str, int]) -> Dict[int, List[Dict]]:
    """Generate multi-tool instructions with 200 per level."""
    result = {1: [], 2: [], 3: []}
    max_attempts = len(templates["multi_tool"]) * len(transformations) * 20
    
    # Group templates by level and pattern
    templates_by_level_pattern = defaultdict(list)
    for template in templates["multi_tool"]:
        key = (template["level"], template["pattern"])
        templates_by_level_pattern[key].append(template)
    
    # Print available templates summary
    print("\nAvailable Multi Tool Templates:")
    for (level, pattern), tmpl_list in templates_by_level_pattern.items():
        print(f"Level {level}, Pattern {pattern}: {len(tmpl_list)} templates")
    
    # Check transformations for level 2 requirements
    valid_transformations_for_level2 = []
    for t in transformations:
        if t["source_models"] and t["input_metamodels"] and t["output_metamodels"]:
            valid_transformations_for_level2.append(t)
    
    # Process each level
    for level in [1, 2, 3]:
        attempts = 0
        
        # Get all valid patterns for this level
        level_patterns = set(pattern for (lvl, pattern) in templates_by_level_pattern.keys() if lvl == level)
        if not level_patterns:
            print(f"Warning: No templates for level {level}")
            continue
            
        # Target per pattern
        pattern_target = target_per_level // len(level_patterns)
        
        # Process each pattern
        for pattern in level_patterns:
            key = (level, pattern)
            level_pattern_templates = templates_by_level_pattern[key]
            
            if not level_pattern_templates:
                print(f"Warning: No templates for level {level}, pattern {pattern}")
                continue
                
            print(f"\nGenerating level {level}, pattern {pattern}: target {pattern_target} instructions")
            pattern_result = []
            
            # Use each template at least once
            for template in level_pattern_templates:
                if len(pattern_result) >= pattern_target:
                    break
                    
                if template_usage_counts[template["instruction"]] > 0:
                    continue
                    
                # Try with different transformation pairs
                for i, trans1 in enumerate(transformations):
                    if len(pattern_result) >= pattern_target:
                        break
                        
                    # Skip transformations without required attributes for level 2
                    if level == 2:
                        if not (trans1["source_models"] and trans1["input_metamodels"] and trans1["output_metamodels"]):
                            continue
                    
                    for trans2 in transformations[i+1:]:
                        if trans1["name"] == trans2["name"]:
                            continue
                            
                        # Skip transformations without required attributes for level 2
                        if level == 2:
                            if not (trans2["source_models"] and trans2["input_metamodels"] and trans2["output_metamodels"]):
                                continue
                                
                        instruction, success = try_generate_multi_instruction(template, trans1, trans2)
                        if success:
                            pattern_result.append(instruction)
                            template_usage_counts[template["instruction"]] += 1
                            total_usage_counts[trans1["name"]] += 1
                            total_usage_counts[trans2["name"]] += 1
                            break
                            
                    if template_usage_counts[template["instruction"]] > 0:
                        break
            
            # Fill remaining slots
            inner_attempts = 0
            max_inner_attempts = max_attempts
            
            while len(pattern_result) < pattern_target and inner_attempts < max_inner_attempts:
                inner_attempts += 1
                
                # Choose template with lowest usage
                template_counts = {t["instruction"]: template_usage_counts[t["instruction"]] 
                                for t in level_pattern_templates}
                sorted_templates = sorted(level_pattern_templates, 
                                       key=lambda x: template_counts[x["instruction"]])
                
                if not sorted_templates:
                    print(f"No templates available for level {level}, pattern {pattern}")
                    break
                    
                template = sorted_templates[0]
                
                # Choose transformations with lowest usage
                sorted_transformations = sorted(transformations, key=lambda x: total_usage_counts[x["name"]])
                
                if len(sorted_transformations) < 2:
                    print(f"Not enough transformations for level {level}")
                    break
                
                # Try pairs starting with lowest usage
                success = False
                for i in range(min(10, len(sorted_transformations))):
                    if success:
                        break
                        
                    trans1 = sorted_transformations[i]
                    
                    # Skip if transformation doesn't meet level 2 requirements
                    if level == 2 and (not trans1["source_models"] or not trans1["input_metamodels"] or not trans1["output_metamodels"]):
                        continue
                        
                    for j in range(i+1, min(20, len(sorted_transformations))):
                        trans2 = sorted_transformations[j]
                        
                        if trans1["name"] == trans2["name"]:
                            continue
                            
                        # Skip if transformation doesn't meet level 2 requirements
                        if level == 2 and (not trans2["source_models"] or not trans2["input_metamodels"] or not trans2["output_metamodels"]):
                            continue
                            
                        instruction, success = try_generate_multi_instruction(template, trans1, trans2)
                        if success:
                            pattern_result.append(instruction)
                            template_usage_counts[template["instruction"]] += 1
                            total_usage_counts[trans1["name"]] += 1
                            total_usage_counts[trans2["name"]] += 1
                            break
                
                # Print progress every 10 instructions
                if len(pattern_result) % 10 == 0 and len(pattern_result) > 0:
                    print(f"Progress: {len(pattern_result)}/{pattern_target} for level {level}, pattern {pattern}")
            
            # Add pattern results to level results
            result[level].extend(pattern_result)
            print(f"Generated {len(pattern_result)}/{pattern_target} instructions for level {level}, pattern {pattern}")
            
        print(f"Total for level {level}: {len(result[level])}/{target_per_level}")
        
        # If we still don't have enough, reuse templates to fill
        if len(result[level]) < target_per_level:
            print(f"Need {target_per_level - len(result[level])} more instructions for level {level}.")
            print("Will reuse templates to reach target count.")
            
            # Collect all templates for this level
            all_level_templates = []
            for pattern in level_patterns:
                all_level_templates.extend(templates_by_level_pattern[(level, pattern)])
            
            if all_level_templates:
                fill_attempts = 0
                max_fill_attempts = max_attempts * 2
                
                while len(result[level]) < target_per_level and fill_attempts < max_fill_attempts:
                    fill_attempts += 1
                    
                    # Select template and sort transformations by usage
                    template = random.choice(all_level_templates)
                    sorted_transformations = sorted(transformations, key=lambda x: total_usage_counts[x["name"]])
                    
                    if len(sorted_transformations) < 2:
                        break
                    
                    # Try pairs until success
                    for i in range(len(sorted_transformations) - 1):
                        success = False
                        trans1 = sorted_transformations[i]
                        
                        # Skip if transformation doesn't meet level 2 requirements
                        if level == 2 and (not trans1["source_models"] or not trans1["input_metamodels"] or not trans1["output_metamodels"]):
                            continue
                            
                        for j in range(i+1, len(sorted_transformations)):
                            trans2 = sorted_transformations[j]
                            
                            if trans1["name"] == trans2["name"]:
                                continue
                                
                            # Skip if transformation doesn't meet level 2 requirements
                            if level == 2 and (not trans2["source_models"] or not trans2["input_metamodels"] or not trans2["output_metamodels"]):
                                continue
                                
                            instruction, success = try_generate_multi_instruction(template, trans1, trans2)
                            if success:
                                result[level].append(instruction)
                                template_usage_counts[template["instruction"]] += 1
                                total_usage_counts[trans1["name"]] += 1
                                total_usage_counts[trans2["name"]] += 1
                                break
                                
                        if success:
                            break
                            
                    # Print progress occasionally
                    if len(result[level]) % 10 == 0:
                        print(f"Fill progress: {len(result[level])}/{target_per_level} for level {level}")
                
                print(f"After filling: {len(result[level])}/{target_per_level} for level {level}")
    
    return result


def generate():
    """Main function to generate the balanced dataset."""
    # Load template data
    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Create path relative to the script
    file_path1 = os.path.join(script_dir, 'evenly_balanced_instructions.json')
    file_path2 = os.path.join(script_dir, '6_transformations.json')

    with open(file_path1, 'r') as f:
        templates = json.load(f)
    
    # Load transformation data
    with open(file_path2, 'r') as f:
        transformations = json.load(f)
    
    # Verify transformation data
    print("\nTransformation Data Analysis:")
    for i, t in enumerate(transformations):
        print(f"{i+1}. {t['name']}:")
        print(f"   - Source models: {len(t['source_models'])}")
        print(f"   - Input metamodels: {len(t['input_metamodels'])}")
        print(f"   - Output metamodels: {len(t['output_metamodels'])}")
    
    # Print initial template counts
    print("\nTemplate Counts:")
    print(f"Single tool templates: {len(templates['single_tool'])}")
    print(f"Multi tool templates: {len(templates['multi_tool'])}")
    
    # Target count per level
    target_per_level = 200
    
    # Initialize counters
    total_usage_counts = defaultdict(int)
    template_usage_counts = defaultdict(int)
    
    # Generate instructions with 200 per level
    single_result_by_level = generate_single_tool_instructions_by_level(
        templates, transformations, target_per_level, total_usage_counts, template_usage_counts
    )
    
    multi_result_by_level = generate_multi_tool_instructions_by_level(
        templates, transformations, target_per_level, total_usage_counts, template_usage_counts
    )
    
    # Flatten results
    single_result = []
    for level in [1, 2, 3]:
        single_result.extend(single_result_by_level[level])
    
    multi_result = []
    for level in [1, 2, 3]:
        multi_result.extend(multi_result_by_level[level])
    
    # Print summary statistics
    print("\n--- SUMMARY ---")
    print(f"\nTotal single tool instructions: {len(single_result)}")
    for level in [1, 2, 3]:
        print(f"Level {level}: {len(single_result_by_level[level])}")
    
    print(f"\nTotal multi tool instructions: {len(multi_result)}")
    for level in [1, 2, 3]:
        print(f"Level {level}: {len(multi_result_by_level[level])}")
    
    print("\nTransformation usage:")
    for trans in sorted(transformations, key=lambda x: total_usage_counts[x["name"]]):
        print(f"{trans['name']}: {total_usage_counts[trans['name']]} times")
    
    # For each level, analyze pattern distribution
    print("\nSingle Tool Pattern Distribution:")
    for level in [1, 2, 3]:
        pattern_counts = defaultdict(int)
        for instr in single_result_by_level[level]:
            pattern_counts[instr["pattern"]] += 1
        
        print(f"Level {level}:")
        for pattern, count in pattern_counts.items():
            print(f"  {pattern}: {count}")
    
    print("\nMulti Tool Pattern Distribution:")
    for level in [1, 2, 3]:
        pattern_counts = defaultdict(int)
        for instr in multi_result_by_level[level]:
            pattern_counts[instr["pattern"]] += 1
        
        print(f"Level {level}:")
        for pattern, count in pattern_counts.items():
            print(f"  {pattern}: {count}")
    
    # Create the output structure
    output = {
        "single_tool": single_result,
        "multi_tool": multi_result
    }
    
    # Save to file
    path = './dataset_generation/generation'
    with open(os.path.join(path,'atl_balanced_level_instructions.json'), 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=4)
    
    print("\nInstructions saved to 'atl_balanced_level_instructions.json'")
    
    # Return total counts for verification
    return {
        "single_tool_total": len(single_result),
        "single_tool_by_level": {level: len(instructions) for level, instructions in single_result_by_level.items()},
        "multi_tool_total": len(multi_result),
        "multi_tool_by_level": {level: len(instructions) for level, instructions in multi_result_by_level.items()},
    }

