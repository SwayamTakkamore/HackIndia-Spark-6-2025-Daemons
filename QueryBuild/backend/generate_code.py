from .llm_wrapper import query_llm
import re
import os
from typing import Tuple, Optional

def clean_code(code_text: str, language: str) -> str:
    """Clean LLM output to extract only executable code.
    
    Args:
        code_text: Raw output from LLM
        language: Target programming language
        
    Returns:
        Cleaned code text with only executable content
    """
    # Remove markdown code blocks and language specifiers
    code_text = re.sub(r'```(?:[\w\+\#]*\s*)?(.*?)```', r'\1', code_text, flags=re.DOTALL)
    
    # Remove common explanatory prefixes
    prefixes = [
        r'^(?:Here is|Here\'s)(?: the)?(?: code| solution)?.*?:',
        r'^The (?:code|solution) (?:is|would be):',
        r'^You can use this (?:code|implementation):',
        r'^This (?:code|solution) (?:implements|solves):'
    ]
    for pattern in prefixes:
        code_text = re.sub(pattern, '', code_text, flags=re.IGNORECASE|re.MULTILINE)
    
    lines = code_text.split('\n')
    clean_lines = []
    
    for line in lines:
        stripped = line.strip()
        
        # Skip various non-code patterns
        if (re.match(r'^\d+\.\s+`.*`\s*-\s*', stripped) or  # Numbered explanations
            re.match(r'^Here\'s.*:|^In this.*:|^This is.*:', stripped) or  # Explanations
            stripped.lower().startswith(('note:', 'example:', 'solution:', 'output:')) or
            stripped.lower().endswith(('code:', 'solution:')) or
            stripped.lower() in ['python:', 'c++:', 'cpp:', 'java:', 'javascript:', 'c#:', 'c:']):
            continue
            
        clean_lines.append(line)
    
    # Remove leading/trailing whitespace and empty lines
    cleaned = '\n'.join(clean_lines).strip()
    
    return cleaned

def get_file_extension(language: str) -> str:
    """Get the correct file extension for the specified language.
    
    Args:
        language: Programming language name
        
    Returns:
        File extension with leading dot
    """
    extensions = {
        "python": ".py",
        "py": ".py",
        "cpp": ".cpp",
        "c++": ".cpp",
        "c": ".c",
        "java": ".java",
        "javascript": ".js",
        "js": ".js",
        "csharp": ".cs",
        "c#": ".cs",
        "typescript": ".ts",
        "ts": ".ts",
        "go": ".go",
        "rust": ".rs",
        "ruby": ".rb",
        "swift": ".swift",
        "kotlin": ".kt",
        "scala": ".scala"
    }
    return extensions.get(language.lower(), ".txt")  # Default to .txt if unknown

def analyze_query(problem_statement: str) -> Tuple[str, str]:
    """Use NLP to analyze the query and extract language and actual task.
    
    Args:
        problem_statement: User's input query
        
    Returns:
        Tuple of (detected_language, extracted_task)
    """
    # Use a more structured prompt for Mistral
    analysis_prompt = f"""Analyze this programming query and extract:
1. The programming language being requested (python, c, cpp, java, javascript, csharp, typescript, go, rust, ruby, swift, kotlin, scala)
2. The core programming task

Query: "{problem_statement}"

Respond in this exact format:
LANGUAGE|||language_name
TASK|||task_description

If no language can be determined, respond with:
LANGUAGE|||unknown
"""
    
    analysis = query_llm(analysis_prompt)
    
    # Default values
    language = "unknown"
    task = problem_statement
    
    # Parse the response
    for line in analysis.split('\n'):
        if line.startswith("LANGUAGE|||"):
            detected_lang = line.split("|||")[1].strip().lower()
            language_mapping = {
                "c++": "cpp",
                "c sharp": "csharp", 
                "c#": "csharp",
                "js": "javascript",
                "ts": "typescript",
                "golang": "go"
            }
            language = language_mapping.get(detected_lang, detected_lang)
        elif line.startswith("TASK|||"):
            task = line.split("|||")[1].strip()
            
    print(f"Analysis complete - Language: '{language}', Task: '{task}'")
    if language == "unknown":
        raise ValueError("Could not determine programming language from query. Please specify the language explicitly.")
        language = "python"  # Default to Python if unknown
    return language, task
    
    

def validate_code_content(code: str, language: str) -> bool:
    """Validate that the code appears to be in the correct language.
    
    Args:
        code: The generated code
        language: Expected language
        
    Returns:
        True if code appears valid for the language
    """
    language = language.lower()
    if language == "unknown":
        language = "python"
    code_lower = code.lower()
    
    validation_patterns = {
        "python": [
            r'^import\s|^from\s|^def\s|^class\s',
            r'^\s*(?:if|for|while|def|class)\s',
            r'print\('
        ],
        "c": [
            r'#include\s*<',
            r'int\s+main\s*\(',
            r'printf\s*\('
        ],
        "cpp": [
            r'#include\s*<',
            r'int\s+main\s*\(',
            r'std::',
            r'cout\s*<<'
        ],
        "java": [
            r'class\s+\w+',
            r'public\s+(?:static\s+)?void\s+main\s*\(',
            r'System\.out\.print'
        ],
        "javascript": [
            r'function\s+\w+\s*\(',
            r'const\s+\w+\s*=',
            r'console\.log\s*\(',
            r'export\s+(?:default\s+)?\w+'
        ],
        "csharp": [
            r'using\s+System',
            r'class\s+\w+',
            r'Console\.Write(?:Line)?\s*\('
        ]
    }
    
    patterns = validation_patterns.get(language, [])
    if not patterns:
        return True  # Can't validate unknown languages
    
    return any(re.search(pattern, code_lower) for pattern in patterns)

def generate_code_file(
    problem_statement: str,
    language: Optional[str] = None,
    save_path: Optional[str] = None,
    max_retries: int = 3
) -> str:
    """Generate code file in the specified language.
    
    Args:
        problem_statement: The problem to solve
        language: Optional specific language (if None, will detect)
        save_path: Optional file path (defaults to 'solution.{ext}')
        max_retries: Number of times to retry if validation fails
        
    Returns:
        Path to the generated file
    """
    # First, analyze the query to detect language and extract task
    detected_language, task = analyze_query(problem_statement)
    
    # Use provided language if specified, otherwise use detected language
    language = language or detected_language
    
    # Determine the correct file extension
    extension = get_file_extension(language)
    
    # Set default save path if not provided
    if not save_path:
        save_path = f"solution{extension}"
    else:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
        # Ensure the path has the correct extension
        base_path = os.path.splitext(save_path)[0]
        save_path = f"{base_path}{extension}"
    
    print(f"Generating {language} code for: {task}")
    
    # Construct a Mistral-optimized prompt
    prompt = f"""You are an expert {language} programmer. Write complete, executable code to solve this problem:

Problem: {task}

Requirements:
1. Write ONLY valid {language} code that solves the problem
2. Include all necessary imports/dependencies
3. Include all required functions/classes
4. Use proper syntax and indentation
5. DO NOT include any explanations, comments outside code, or markdown
6. DO NOT include example usage or test cases
7. DO NOT include any text that isn't valid {language} code

The first and last lines of your response must be valid {language} code.

Begin your response immediately with the code:"""
    
    retries = 0
    while retries < max_retries:
        # Query the LLM with increased token limit
        code = query_llm(prompt, max_tokens=2048)
        clean_code_output = clean_code(code, language)
        
        # Validate the code
        if validate_code_content(clean_code_output, language):
            break
            
        retries += 1
        print(f"Validation failed, retry {retries}/{max_retries}")
    else:
        print(f"Warning: Could not validate {language} code after {max_retries} attempts")
    
    # Write to file
    with open(save_path, 'w', encoding='utf-8') as f:
        f.write(clean_code_output)
    
    print(f"Code generated at {save_path}")
    return save_path