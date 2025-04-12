from nbformat import v4 as nbf
from .llm_wrapper import query_llm
import re

def clean_code(code_text):
    """Clean LLM output to extract only executable Python code."""
    # Remove markdown code blocks
    code_text = re.sub(r'```python\s*|\s*```', '', code_text)
    
    # Remove explanatory text that may be at the beginning/end
    lines = code_text.split('\n')
    clean_lines = []
    in_code_block = False
    
    for line in lines:
        # Skip lines with explanatory numbering (1., 2., etc.)
        if re.match(r'^\d+\.\s+`.*`\s*-\s*', line):
            continue
        
        # Skip lines that are clearly explanations and not code
        if re.match(r'^Here\'s.*:|^In this.*:|^This is.*:', line):
            continue
            
        # Skip lines starting with common explanation markers
        if line.strip().startswith(('Note:', 'Example:', 'Solution:')):
            continue
            
        clean_lines.append(line)
    
    return '\n'.join(clean_lines)

def generate_notebook(problem_statement, save_path):
    nb = nbf.new_notebook()
    
    # Use LLM to generate components with explicit instructions for executable code
    libraries_prompt = f"""Given the problem statement: '{problem_statement}', 
    provide ONLY executable Python import statements for the 5-8 most important libraries needed.
    Do NOT include explanations, just valid Python code that can be executed directly."""
    
    libraries_code = query_llm(libraries_prompt)
    libraries_code = clean_code(libraries_code)
    
    # Add an explanation in markdown before the code
    libraries_explanation_prompt = f"""Given the problem statement: '{problem_statement}', 
    briefly explain in 2-3 sentences why these libraries would be useful."""
    libraries_explanation = query_llm(libraries_explanation_prompt)
    
    data_processing_prompt = f"""Given the problem statement: '{problem_statement}', 
    write ONLY executable Python code to load and preprocess the data.
    Include code comments but NO explanatory text. The code should be ready to run in a Jupyter notebook."""
    
    data_processing_code = query_llm(data_processing_prompt)
    data_processing_code = clean_code(data_processing_code)
    
    model_prompt = f"""Given the problem statement: '{problem_statement}', 
    write ONLY executable Python code to build and train an appropriate model.
    Include code comments but NO explanatory text or markdown. The code should be ready to run in a Jupyter notebook."""
    
    model_code = query_llm(model_prompt)
    model_code = clean_code(model_code)
    
    evaluation_prompt = f"""Given the problem statement: '{problem_statement}', 
    write ONLY executable Python code to evaluate the model and visualize results.
    Include code comments but NO explanatory text. The code should be ready to run in a Jupyter notebook."""
    
    evaluation_code = query_llm(evaluation_prompt)
    evaluation_code = clean_code(evaluation_code)
    
    nb.cells = [
        nbf.new_markdown_cell(f"# Project Notebook\n\n## Problem Statement:\n{problem_statement}"),
        nbf.new_markdown_cell("## Step 1: Import Libraries\n\n" + libraries_explanation),
        nbf.new_code_cell(libraries_code),
        nbf.new_markdown_cell("## Step 2: Load and Preprocess Data"),
        nbf.new_code_cell(data_processing_code),
        nbf.new_markdown_cell("## Step 3: Build and Train Model"),
        nbf.new_code_cell(model_code),
        nbf.new_markdown_cell("## Step 4: Evaluate and Visualize Results"),
        nbf.new_code_cell(evaluation_code),
    ]
    
    with open(save_path, 'w', encoding='utf-8') as f:
        import nbformat
        nbformat.write(nb, f)
    return save_path
