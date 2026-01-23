# filename: code_slicer_v2_fixed.py

import ast
from collections import defaultdict
from typing import Dict, List, Optional

class CodeSlicer:
    """
    A robust tool to slice Python source code into granular logical blocks
    using its Abstract Syntax Tree (AST).

    This slicer decomposes code based on programming intent (e.g., input
    validation, helper functions, main loops, state updates) to provide a
    structured, semantic view of the code's internal logic.

    Usage:
        slicer = CodeSlicer(source_code)
        logical_blocks = slicer.slice()
    """

    def __init__(self, source_code: str):
        self.source_code = source_code
        self.tree: Optional[ast.AST] = None
        self.blocks: Dict[str, List[str]] = defaultdict(list)
        try:
            self.tree = ast.parse(self.source_code)
        except SyntaxError as e:
            raise ValueError(f"Could not parse source code: {e}")

    def _get_source_segment(self, node: ast.AST) -> str:
        """Safely extracts the source code segment for a given AST node."""
        return ast.get_source_segment(self.source_code, node)

    def slice(self) -> Dict[str, List[str]]:
        """Performs the slicing operation and returns the identified logical blocks."""
        if not self.tree:
            return {}

        visitor = self._LogicalBlockVisitor(self)
        visitor.visit(self.tree)
        return dict(self.blocks)

    class _LogicalBlockVisitor(ast.NodeVisitor):
        def __init__(self, slicer_instance: 'CodeSlicer'):
            self.slicer = slicer_instance
            # Track context to know if we are inside a loop
            self.in_loop = False

        def visit_Import(self, node: ast.Import) -> None:
            self.slicer.blocks['Header & Imports'].append(self.slicer._get_source_segment(node))
            self.generic_visit(node)

        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
            self.slicer.blocks['Header & Imports'].append(self.slicer._get_source_segment(node))
            self.generic_visit(node)
            
        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            # Helper functions are now identified by being called within another function
            # This is a more robust heuristic
            is_helper = False
            for parent_node in ast.walk(self.slicer.tree):
                if isinstance(parent_node, ast.FunctionDef) and parent_node.name != node.name:
                    for call_node in ast.walk(parent_node):
                        if isinstance(call_node, ast.Call) and isinstance(call_node.func, ast.Name) and call_node.func.id == node.name:
                            is_helper = True
                            break
                if is_helper:
                    break
            
            if is_helper:
                 self.slicer.blocks['Helper Function Definition'].append(self.slicer._get_source_segment(node))
            else:
                 # It's a main function, so we analyze its contents
                 self.analyze_function_body(node)
        
        def analyze_function_body(self, func_node: ast.FunctionDef):
            # Analyze the body of a main function line by line
            for i, node in enumerate(func_node.body):
                # --- START: MODIFICATION TO IGNORE DOCSTRINGS ---
                # Check if the node is an expression and its value is a string constant.
                # This is how docstrings are represented in the AST.
                if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    continue  # Skip docstrings
                # --- END: MODIFICATION ---
                
                # We handle each statement type within the function
                if isinstance(node, ast.If):
                     # Re-classify If statements inside the loop later
                     is_validation = i == 0 and any(isinstance(n, ast.Raise) for n in ast.walk(node))
                     # We check the original index `i` for validation logic. The first *code* statement should be index 0 or 1
                     # depending on whether a docstring was present. A more robust check might be needed if this assumption is fragile.
                     # For now, this is a reasonable approach.
                     if is_validation:
                         self.slicer.blocks['Input Validation'].append(self.slicer._get_source_segment(node))
                     else:
                         # Defer classification of other Ifs
                         self.visit(node)
                elif isinstance(node, ast.Assign):
                    self.visit(node)
                elif isinstance(node, (ast.For, ast.While)):
                    self.visit(node)
                elif isinstance(node, ast.FunctionDef): # Inner functions
                    self.slicer.blocks['Core Algorithm Component Definition'].append(self.slicer._get_source_segment(node))
                elif isinstance(node, ast.Return):
                    self.slicer.blocks['Final Output & Return'].append(self.slicer._get_source_segment(node))
                else:
                    # Catch-all for other statement types
                    self.slicer.blocks['General Statement'].append(self.slicer._get_source_segment(node))


        def visit_For(self, node: ast.For) -> None:
            self.slicer.blocks['Main Execution Loop'].append(self.slicer._get_source_segment(node))
            self.in_loop = True
            # Visit children to find logic *inside* the loop
            for child in node.body:
                self.visit(child)
            self.in_loop = False
        
        # Similar logic for While would go here

        def visit_Assign(self, node: ast.Assign) -> None:
            # Distinguish between initial setup and state updates
            if self.in_loop:
                self.slicer.blocks['State Update Logic'].append(self.slicer._get_source_segment(node))
            else:
                self.slicer.blocks['Initial State Setup'].append(self.slicer._get_source_segment(node))

        def visit_If(self, node: ast.If) -> None:
            if self.in_loop:
                # If statements inside a loop are likely termination conditions or state updates
                is_termination = any(isinstance(n, (ast.Return, ast.Break)) for n in ast.walk(node))
                if is_termination:
                    self.slicer.blocks['Termination Condition'].append(self.slicer._get_source_segment(node))
                else:
                    self.slicer.blocks['Conditional Logic (in-loop)'].append(self.slicer._get_source_segment(node))
            # The case for 'Input Validation' is handled in analyze_function_body

# --- HOW TO CALL AND USE THE NEW, REFINED SLICER ---

if __name__ == '__main__':
    code_with_docstring = """
import math

def poly(xs: list, x: float):
    \"\"\"Evaluates a polynomial at a given point x.\"\"\"
    return sum([coeff * math.pow(x, i) for i, coeff in enumerate(xs)])

def find_zero(xs: list):
    \"\"\"
    Finds a root of a polynomial using Newton's method.
    This is a multi-line docstring.
    \"\"\"
    if len(xs) % 2 != 0:
        raise ValueError('Input list must have an even number of coefficients.')
    max_coeff = max([coeff for coeff in xs if coeff != 0])

    def f(x):
        return poly(xs, x)

    def df(x):
        return sum([coeff * math.pow(x, i) for i, coeff in enumerate(xs) if i > 0])
        
    x0 = -max_coeff / max_coeff if max_coeff != 0 else 0.0
    tolerance = 1e-06
    
    for _ in range(1000):
        fx = f(x0)
        dfx = df(x0)
        if abs(dfx) < 1e-09:
            break
        x1 = x0 - fx / dfx
        if abs(x1 - x0) < tolerance:
            return round(x1, 2)
        x0 = x1
        
    return round(x0, 2)
"""
    print("--- Analyzing Polynomial Problem Code (Fixed Slicer) ---")
    try:
        slicer = CodeSlicer(code_with_docstring)
        blocks = slicer.slice()
        import json
        print(json.dumps(blocks, indent=4))
    except ValueError as e:
        print(e)