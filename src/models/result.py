from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class Result:
    question_id: str
    platform_name: str
    question_text: str
    answer: str
    status: str  # "success", "error", "timeout"
    screenshot_path: Optional[str] = None
    matched_rules: Optional[list] = None
    error_message: Optional[str] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.matched_rules is None:
            self.matched_rules = []
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def __str__(self) -> str:
        return f"Result(question_id={self.question_id}, platform={self.platform_name}, status={self.status})"