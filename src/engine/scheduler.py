import asyncio
from typing import List, Dict, Any
from src.models.question import Question
from src.models.result import Result
from src.engine.rate_limiter import RateLimiter
from src.utils.logger import logger


class Scheduler:
    def __init__(self, adapters: List[Any], rate_limiter: RateLimiter):
        self.adapters = adapters
        self.rate_limiter = rate_limiter
        self.results: List[Result] = []
        # 为每个适配器创建一个锁
        self._adapter_locks = {adapter.name: asyncio.Lock() for adapter in adapters}
    
    async def process_question(self, question: Question, adapter: Any) -> Result:
        logger.info(f"开始处理问题 {question.id}，平台: {adapter.name}")
        
        # 获取该适配器的锁
        adapter_lock = self._adapter_locks[adapter.name]
        
        async with adapter_lock:  # 确保同一适配器同一时间只处理一个问题
            try:
                result_data = await self.rate_limiter.execute_with_limit(
                    adapter.process, question
                )
                
                result = Result(
                    question_id=question.id,
                    platform_name=adapter.name,
                    question_text=question.text,
                    answer=result_data["answer"],
                    status=result_data["status"],
                    screenshot_path=result_data["screenshot_path"],
                    is_shared_image=result_data.get("is_shared_image", False),
                    error_message=result_data["error_message"],
                    share_link=result_data.get("share_link"),
                    share_link_error=result_data.get("share_link_error")
                )
                
                logger.info(f"问题 {question.id} 在 {adapter.name} 处理完成，状态: {result.status}")
                return result
                
            except Exception as e:
                logger.error(f"处理问题 {question.id} 时发生错误: {str(e)}")
                return Result(
                    question_id=question.id,
                    platform_name=adapter.name,
                    question_text=question.text,
                    answer="",
                    status="error",
                    error_message=str(e)
                )
    
    async def process_all_questions(self, questions: List[Question]) -> List[Result]:
        logger.info(f"开始处理 {len(questions)} 个问题")
        
        tasks = []
        for question in questions:
            for adapter in self.adapters:
                task = self.process_question(question, adapter)
                tasks.append(task)
        
        self.results = await asyncio.gather(*tasks)
        logger.info(f"所有问题处理完成，共生成 {len(self.results)} 个结果")
        
        return self.results
    
    async def process_sequentially(self, questions: List[Question]) -> List[Result]:
        logger.info(f"开始顺序处理 {len(questions)} 个问题")
        
        self.results = []
        for question in questions:
            for adapter in self.adapters:
                result = await self.process_question(question, adapter)
                self.results.append(result)
        
        logger.info(f"顺序处理完成，共生成 {len(self.results)} 个结果")
        return self.results
    
    def get_results(self) -> List[Result]:
        return self.results
    
    def get_success_rate(self) -> float:
        if not self.results:
            return 0.0
        successful = sum(1 for r in self.results if r.status == "success")
        return successful / len(self.results)
