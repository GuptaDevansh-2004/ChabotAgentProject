import re
from dataclasses import dataclass
from typing import List, Tuple, Union, Dict, Set, Any


class TextProcessor:
    """Provide utilities tools for operations related to text"""
    
    @staticmethod
    def normalize_content(content: str) -> str:
        """
        Normalize content by:
        1. Collapsing multiple spaces or tabs into a single space
        2. Stripping leading/trailing spaces on each line
        3. Removing empty lines
        """
        # Collapse multiple spaces or tabs into one
        content = re.sub(r"[ \t]+", " ", content)
        # Strip leading/trailing spaces on each line, preserving newline
        content = re.sub(r"[ \t]+$", "", content, flags=re.MULTILINE)
        content = re.sub(r"^[ \t]+", "", content, flags=re.MULTILINE)
        # Replace multiple consecutive newlines with a single newline
        content = re.sub(r"\n{2,}", "\n", content)
        return content