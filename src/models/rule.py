from dataclasses import dataclass
from typing import List, Union, Optional


@dataclass
class Rule:
    id: str
    name: str
    type: str  # "keyword" or "regex"
    keywords: Optional[List[str]] = None
    pattern: Optional[str] = None
    priority: int = 1
    label: str = ""
    
    def __post_init__(self):
        if self.type == "keyword" and self.keywords is None:
            self.keywords = []
        if self.type == "regex" and self.pattern is None:
            self.pattern = ""
    
    def __str__(self) -> str:
        return f"Rule(id={self.id}, name={self.name}, type={self.type}, label={self.label})"