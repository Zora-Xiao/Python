import asyncio
import random
import time
from typing import Optional
from src.utils.logger import logger


class RateLimiter:
    def __init__(self, 
                 max_requests_per_minute: int = 10,
                 min_interval: float = 2.0,
                 max_interval: float = 5.0,
                 exponential_backoff: bool = True,
                 max_retries: int = 3):
        self.max_requests_per_minute = max_requests_per_minute
        self.min_interval = min_interval
        self.max_interval = max_interval
        self.exponential_backoff = exponential_backoff
        self.max_retries = max_retries
        
        self.tokens = max_requests_per_minute
        self.last_update = time.time()
        self.lock = asyncio.Lock()
    
    async def acquire(self) -> bool:
        async with self.lock:
            now = time.time()
            elapsed = now - self.last_update
            
            self.tokens += elapsed * (self.max_requests_per_minute / 60.0)
            self.tokens = min(self.tokens, self.max_requests_per_minute)
            self.last_update = now
            
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            return False
    
    async def wait_with_backoff(self, retry_count: int = 0) -> None:
        if self.exponential_backoff:
            base_delay = self.min_interval * (2 ** retry_count)
            delay = min(base_delay, self.max_interval)
        else:
            delay = random.uniform(self.min_interval, self.max_interval)
        
        delay = min(delay, self.max_interval)
        logger.info(f"等待 {delay:.2f} 秒后重试...")
        await asyncio.sleep(delay)
    
    async def execute_with_limit(self, func, *args, **kwargs):
        retry_count = 0
        while retry_count <= self.max_retries:
            if await self.acquire():
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"执行失败: {str(e)}")
                    if retry_count < self.max_retries:
                        await self.wait_with_backoff(retry_count)
                        retry_count += 1
                    else:
                        raise
            else:
                await self.wait_with_backoff(retry_count)
                retry_count += 1
        
        raise Exception("超过最大重试次数")