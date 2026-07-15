from dataclasses import dataclass
from typing import List, Union, Optional


@dataclass
class Rule:
    id: str
    name: str
    type: str  # "keyword", "regex", "length", "quality", "relevance"
    keywords: Optional[List[str]] = None
    pattern: Optional[str] = None
    priority: int = 1
    label: str = ""
    
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    
    quality_keywords: Optional[List[str]] = None
    quality_type: Optional[str] = None  # "positive" or "negative"
    
    relevance_keywords: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.type == "keyword" and self.keywords is None:
            self.keywords = []
        if self.type == "regex" and self.pattern is None:
            self.pattern = ""
        if self.type == "quality" and self.quality_keywords is None:
            self.quality_keywords = []
        if self.type == "relevance" and self.relevance_keywords is None:
            self.relevance_keywords = []
    
    def __str__(self) -> str:
        return f"Rule(id={self.id}, name={self.name}, type={self.type}, label={self.label})"