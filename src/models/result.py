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
    is_shared_image: bool = False
    matched_rules: Optional[list] = None
    error_message: Optional[str] = None
    timestamp: Optional[datetime] = None
    share_link: Optional[str] = None
    share_link_error: Optional[str] = None
    
    def __post_init__(self):
        if self.matched_rules is None:
            self.matched_rules = []
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def __str__(self) -> str:
        return f"Result(question_id={self.question_id}, platform={self.platform_name}, status={self.status})"
