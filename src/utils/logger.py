import logging
import os
from pathlib import Path
from typing import Optional


class Logger:
    _instance: Optional['Logger'] = None
    _logger: Optional[logging.Logger] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def setup(self, 
              log_dir: str = "logs",
              log_file: str = "evaluation.log",
              level: str = "INFO",
              format_str: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s") -> None:
        if self._logger is not None:
            return
            
        self._logger = logging.getLogger("AI_Evaluation")
        self._logger.setLevel(getattr(logging, level.upper()))
        
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path / log_file, encoding='utf-8')
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(logging.Formatter(format_str))
        
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, level.upper()))
        console_handler.setFormatter(logging.Formatter(format_str))
        
        self._logger.addHandler(file_handler)
        self._logger.addHandler(console_handler)
    
    def get_logger(self) -> logging.Logger:
        if self._logger is None:
            self.setup()
        return self._logger
    
    def info(self, message: str) -> None:
        self.get_logger().info(message)
    
    def warning(self, message: str) -> None:
        self.get_logger().warning(message)
    
    def error(self, message: str) -> None:
        self.get_logger().error(message)
    
    def debug(self, message: str) -> None:
        self.get_logger().debug(message)


logger = Logger()