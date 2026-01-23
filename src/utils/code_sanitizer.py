import re
from typing import Optional

def sanitize_code_prefix(code: Optional[str]) -> str:
    """
    Remove unwanted leading think tags like:
    <think>\n\n</think>\n\n
    and similar variants (allowing flexible whitespace).
    """
    if not code:
        return code or ""
    pattern = r"^\s*<think>\s*</think>\s*"
    return re.sub(pattern, "", code, count=1, flags=re.IGNORECASE) 