from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class Question:
    id: str
    text: str
    category: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __str__(self) -> str:
        return f"Question(id={self.id}, text={self.text[:50]}..., category={self.category})"