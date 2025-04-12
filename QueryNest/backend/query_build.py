import os
import requests
import json
from typing import Optional, Dict, Any, List
import re

# Environment variable for API key
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

def clean_code_block(code: str) -> str:
    """Clean and extract code from potential markdown code blocks."""
    # Remove markdown code block markers if present
    code = re.sub(r'^```\w*\n|```$', '', code, flags=re.MULTILINE)
    return code.strip()

def extract_code_blocks(text: str) -> List[Dict[str, str]]:
    """Extract code blocks and their languages from text."""
    # Match markdown code blocks with optional language
    pattern = r'```(\w*)\n(.*?)```'
    matches = re.findall(pattern, text, re.DOTALL)
    
    result = []
    for lang, code in matches:
        result.append({
            "language": lang.lower() if lang else "unknown",
            "code": code.strip()
        })
    
    # If no code blocks found but text contains code-like content
    if not result and any(keyword in text for keyword in ['function', 'class', 'import', 'def', 'return']):
        # Try to guess the language and extract as a single block
        if 'def ' in text or 'import ' in text and ('self' in text or ':' in text):
            language = "python"
        elif 'function' in text or 'const' in text or 'var' in text or 'let' in text:
            language = "javascript"
        elif 'public class' in text or 'public static void' in text:
            language = "java"
        else:
            language = "unknown"
            
        result.append({
            "language": language,
            "code": text.strip()
        })
    
    return result

def generate_code(description: str, language: Optional[str] = None) -> Dict[str, Any]:
    """Generate code based on a text description."""
    if not description:
        return {"success": False, "error": "Empty description", "code": ""}
    
    # Try to determine programming language if not specified
    if not language:
        language_indicators = {
            "python": ["python", "django", "flask", "pandas", "numpy"],
            "javascript": ["javascript", "js", "node", "react", "angular", "vue"],
            "java": ["java", "spring", "android"],
            "cpp": ["c++", "cpp"],
            "csharp": ["c#", "csharp", ".net"],
        }
        
        description_lower = description.lower()
        for lang, indicators in language_indicators.items():
            if any(indicator in description_lower for indicator in indicators):
                language = lang
                break
        
        if not language:
            # Default to Python if no language detected
            language = "python"
    
    # Prepare the message for code generation
    prompt = f"""Generate code in {language} that accomplishes the following:
{description}

Return only the code without explanations or comments, formatted with proper syntax.
"""

    try:
        # Try using OpenAI API if key is available
        if OPENAI_API_KEY:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENAI_API_KEY}"
            }
            
            payload = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "You are a code generation assistant that produces clean, efficient code without explanations."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 2000
            }
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                generated_text = result["choices"][0]["message"]["content"]
                
                # Extract code blocks
                code_blocks = extract_code_blocks(generated_text)
                
                if code_blocks:
                    return {
                        "success": True,
                        "language": code_blocks[0]["language"] or language,
                        "code": code_blocks[0]["code"],
                        "all_code_blocks": code_blocks if len(code_blocks) > 1 else []
                    }
                else:
                    # If no code blocks found, return the entire text as code
                    return {
                        "success": True,
                        "language": language,
                        "code": clean_code_block(generated_text)
                    }
            else:
                error_message = f"API error: {response.status_code}"
                return {"success": False, "error": error_message, "code": ""}
        
        # Fallback to template-based approach if no API key
        return generate_code_templates(description, language)
        
    except Exception as e:
        error_message = f"Error generating code: {str(e)}"
        return {"success": False, "error": error_message, "code": ""}

def generate_code_templates(description: str, language: str) -> Dict[str, Any]:
    """Generate simple code templates based on description for different languages."""
    description_lower = description.lower()
    
    # Detect if it's a function, class or API
    is_function = any(kw in description_lower for kw in ["function", "method", "calculate", "compute"])
    is_class = any(kw in description_lower for kw in ["class", "object", "model"])
    is_api = any(kw in description_lower for kw in ["api", "endpoint", "route", "server"])
    
    function_name = "process_data"
    if "sort" in description_lower:
        function_name = "sort_data"
    elif "filter" in description_lower:
        function_name = "filter_data"
    elif "search" in description_lower:
        function_name = "search_data"
    
    if language == "python":
        if is_api:
            code = f"""from fastapi import FastAPI

app = FastAPI()

@app.get("/api/data")
async def get_data():
    # Implementation based on: {description}
    return {{"message": "Data processed successfully"}}

@app.post("/api/data")
async def create_data(data: dict):
    # Process the data
    return {{"message": "Data created successfully"}}
"""
        elif is_class:
            code = f"""class DataProcessor:
    def __init__(self):
        self.data = []
        
    def process(self, input_data):
        # Implementation based on: {description}
        result = input_data  # Replace with actual processing
        self.data.append(result)
        return result
"""
        else:
            code = f"""def {function_name}(data):
    # Implementation based on: {description}
    result = data  # Replace with actual implementation
    return result

# Example usage
if __name__ == "__main__":
    test_data = ["sample", "data", "to", "process"]
    result = {function_name}(test_data)
    print(result)
"""
    
    elif language == "javascript":
        if is_api:
            code = f"""const express = require('express');
const app = express();
app.use(express.json());

// {description}
app.get('/api/data', (req, res) => {
  // Implementation logic here
  res.json({ message: 'Data processed successfully' });
});

app.post('/api/data', (req, res) => {
  const data = req.body;
  // Process the data
  res.json({ message: 'Data created successfully' });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
"""
        elif is_class:
            code = f"""class DataProcessor {
  constructor() {
    this.data = [];
  }
  
  process(inputData) {
    // Implementation based on: {description}
    const result = inputData;  // Replace with actual processing
    this.data.push(result);
    return result;
  }
}

// Example usage
const processor = new DataProcessor();
const result = processor.process(['sample', 'data']);
console.log(result);
"""
        else:
            code = f"""function {function_name}(data) {{
  // Implementation based on: {description}
  const result = data;  // Replace with actual implementation
  return result;
}}

// Example usage
const testData = ['sample', 'data', 'to', 'process'];
const result = {function_name}(testData);
console.log(result);
"""
    
    else:  # Default to Python if language not supported
        code = f"""# Code generation for {language} is not fully supported
# Here's a Python implementation instead:

def {function_name}(data):
    # Implementation based on: {description}
    result = data  # Replace with actual implementation
    return result
"""
    
    return {
        "success": True,
        "language": language,
        "code": code,
        "note": "Generated from template. Customize implementation as needed."
    }
