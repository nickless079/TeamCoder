import os
import sys
from typing import Dict, Any

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.models import *
def remove_docstrings(code: str) -> str:
    import re
    # Regex to find all triple-quoted strings (single or double)
    # It handles both multiline and single-line docstrings.
    docstring_regex = r'(\"\"\"(?:.|\n)*?\"\"\")|(\'\'\'(?:.|\n)*?\'\'\')'
    
    # Replace any found docstring with an empty string
    code_without_docstrings = re.sub(docstring_regex, '', code)
    
    return code_without_docstrings
class FormatChecker:
    def __init__(self, model: BaseModel, **kwargs: Any):
        """
        Initializes the FormatChecker.

        Args:
            model (BaseModel): The language model to use for checking.
            **kwargs: Additional keyword arguments.
        """
        self.model = model
    

    def check(self, problem_description: str, code: str) -> str:
        """
        Checks the format of the given code based on the problem description.

        Args:
            problem_description (str): The description of the problem.
            code (str): The code to check.

        Returns:
            str: The filtered and calibrated code from the language model.
        """
       
        code= remove_docstrings(code)
        print(f"Code after removing docstrings:\n\n{code}\n\n") 
        
        prompt = self._create_prompt(problem_description, code)
        print(f"FormatChecker prompt:\n\n{prompt}\n\n")
        # Requesting the language model for format checking.
        response = self.model.chat(prompt)
        print(f"FormatChecker response:\n\n{response}\n\n")
        # Process the response to extract the calibrated code.
        processed_result = self._process_response(response)
        
        return processed_result["code"]

    def _create_prompt(self, problem_description: str, code: str) -> str:
        """
        Creates the prompt for the language model.
        (To be implemented)
        """
        # Placeholder for prompt creation logic
        prompt= f"""
### ROLE & MISSION
You are a Code Logic Auditor. Your sole mission is to perform a "Say-Do" analysis on the provided Python code. You will answer one, and only one, question: **Does the executable code's logic faithfully implement the intent described in its accompanying inline comments (`# ...`)?**

### THE CODE UNDER REVIEW
This is the self-contained unit you must audit. It contains only executable code and inline comments. Your entire universe of analysis is confined to what is written *inside* this block.
<CODE_TO_AUDIT>
{code}
</CODE_TO_AUDIT>

---

### AUDIT PROTOCOL
1.  **Analyze Implementation Intent**: From any inline comments (`# ...`), extract the specific promises made about what a block of code is supposed to do.
2.  **Analyze Code Logic**: Analyze the actual executable code that follows a comment to determine its true behavior.
3.  **Identify Discrepancies**: Compare the intent from the comments with the actual code logic. Report **only** the mismatches where the code's behavior deviates from what its own comments describe.

---
### REQUIRED OUTPUT: The Audit Report (JSON)
{{
  "audit_summary": {{
    "is_consistent": "A boolean (true/false) indicating if the code is perfectly consistent with its inline comments.",
    "verdict": "A one-sentence summary of the finding. If no comments exist, state that consistency cannot be audited."
  }},
  "inconsistencies_found": [
    {{
      "comment_promise": "Quote the specific `#` comment that makes a promise.",
      "actual_code_logic": "Quote the block of code that the comment describes.",
      "discrepancy_analysis": "In one precise sentence, explain why the `actual_code_logic` does not fulfill the `comment_promise`. If consistent, this array should be empty."
    }}
  ]
}}
"""
        return [{"role": "user", "content": prompt}]
    


    def _process_response(self, response: str) -> Dict[str, Any]:
        """
        Process model response, extract code and explanation.
        Handles nested code blocks within <INFO> tags.
        
        Args:
            response: Model response
            
        Returns:
            Processed result containing code and explanation
        """
        import re
        
        code = ""
        explanation = response
        
        info_pattern = r'<INFO>(.*?)</INFO>'
        info_match = re.search(info_pattern, response, re.DOTALL)
        
        target_text = response
        if info_match:
            target_text = info_match.group(1).strip()
            explanation = response.replace(info_match.group(0), "").strip()

        # Try to extract code from markdown code blocks
        code_pattern = r'```(?:python|java|cpp|c\+\+|c|javascript|js|typescript|ts|go|rust|php|ruby|csharp|c#)?\s*(.*?)```'
        code_matches = re.findall(code_pattern, target_text, re.DOTALL)
        
        if code_matches:
            code = code_matches[0].strip()
            # Refine explanation by removing the code part from it
            if not info_match:
                explanation = response
                for match in re.findall(r'```(?:.|\n)*?```', response, re.DOTALL):
                    explanation = explanation.replace(match, "").strip()
        elif info_match:
            # If inside <INFO> but no markdown, the whole content is code
            code = target_text
        else:
            # Fallback for when there are no <INFO> tags and no markdown blocks
            lines = response.split('\n')
            code_lines = []
            in_code = False
            for line in lines:
                if line.strip().startswith('```'):
                    in_code = not in_code
                    continue
                if in_code or not (line.startswith('#') or line.startswith('>')):
                    code_lines.append(line)
            code = '\n'.join(code_lines).strip()

        return {
            "code": code,
            "explanation": explanation.strip(),
            "raw_response": response
        }
    
    

 

if __name__ == '__main__':
    # This is an example of how to use the FormatChecker
    # You need to initialize the model first
    # from src.models.Ollama import Ollama
    # model = Ollama(model="your-model-name")
    # checker = FormatChecker(model)
    # problem_desc = "Your problem description here."
    # code_to_check = "Your code here."
    # result = checker.check(problem_desc, code_to_check)
    # print(result)
    pass
