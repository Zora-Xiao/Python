import re
from typing import List
from src.models.rule import Rule
from src.models.result import Result
from src.utils.logger import logger


class RuleMatcher:
    def __init__(self, rules: List[Rule]):
        self.rules = sorted(rules, key=lambda r: r.priority, reverse=True)
    
    def match(self, answer: str, question: str = "") -> List[str]:
        matched_labels = []
        
        for rule in self.rules:
            if self._match_rule(answer, rule, question):
                matched_labels.append(rule.label)
                logger.debug(f"规则 {rule.name} 匹配成功，标签: {rule.label}")
        
        return matched_labels
    
    def _match_rule(self, answer: str, rule: Rule, question: str = "") -> bool:
        if rule.type == "keyword":
            return self._match_keywords(answer, rule.keywords)
        elif rule.type == "regex":
            return self._match_regex(answer, rule.pattern)
        elif rule.type == "length":
            return self._match_length(answer, rule.min_length, rule.max_length)
        elif rule.type == "quality":
            return self._match_quality(answer, rule.quality_keywords, rule.quality_type)
        elif rule.type == "relevance":
            return self._match_relevance(answer, question, rule.relevance_keywords)
        return False
    
    def _match_keywords(self, answer: str, keywords: List[str]) -> bool:
        if not keywords:
            return False
        
        answer_lower = answer.lower()
        return any(keyword.lower() in answer_lower for keyword in keywords)
    
    def _match_regex(self, answer: str, pattern: str) -> bool:
        if not pattern:
            return False
        
        try:
            return bool(re.search(pattern, answer, re.IGNORECASE))
        except re.error as e:
            logger.error(f"正则表达式匹配失败: {pattern}, 错误: {str(e)}")
            return False
    
    def _match_length(self, answer: str, min_length: int = None, max_length: int = None) -> bool:
        answer_stripped = answer.strip()
        length = len(answer_stripped)
        
        if min_length is not None and length < min_length:
            return False
        
        if max_length is not None and length > max_length:
            return False
        
        return True
    
    def _match_quality(self, answer: str, quality_keywords: List[str], quality_type: str) -> bool:
        if not quality_keywords or not quality_type:
            return False
        
        answer_lower = answer.lower()
        
        if quality_type == "positive":
            return any(keyword.lower() in answer_lower for keyword in quality_keywords)
        elif quality_type == "negative":
            return any(keyword.lower() in answer_lower for keyword in quality_keywords)
        
        return False
    
    def _match_relevance(self, answer: str, question: str, relevance_keywords: List[str]) -> bool:
        if not answer or not question:
            return False
        
        answer_lower = answer.lower()
        question_lower = question.lower()
        
        if relevance_keywords:
            for keyword in relevance_keywords:
                if keyword.lower() in question_lower and keyword.lower() in answer_lower:
                    return True
            return False
        
        question_words = set(question_lower.split())
        answer_words = set(answer_lower.split())
        
        if len(question_words) == 0:
            return False
        
        overlap = question_words & answer_words
        
        return len(overlap) > 0
    
    def apply_rules(self, result: Result) -> Result:
        if result.status == "success":
            matched_labels = self.match(result.answer, result.question_text)
            result.matched_rules = matched_labels
            logger.info(f"结果 {result.question_id}-{result.platform_name} 匹配规则: {matched_labels}")
        
        return result
    
    def apply_rules_to_results(self, results: List[Result]) -> List[Result]:
        logger.info(f"开始对 {len(results)} 个结果应用规则")
        
        for result in results:
            self.apply_rules(result)
        
        logger.info("规则应用完成")
        return results
    
    def get_statistics(self, results: List[Result]) -> dict:
        stats = {
            "total": len(results),
            "success": 0,
            "error": 0,
            "timeout": 0,
            "rule_matches": {},
            "quality_stats": {
                "positive": 0,
                "negative": 0,
                "neutral": 0
            }
        }
        
        for result in results:
            if result.status == "success":
                stats["success"] += 1
            elif result.status == "error":
                stats["error"] += 1
            elif result.status == "timeout":
                stats["timeout"] += 1
            
            for label in result.matched_rules:
                if label not in stats["rule_matches"]:
                    stats["rule_matches"][label] = 0
                stats["rule_matches"][label] += 1
                
                if "正面" in label:
                    stats["quality_stats"]["positive"] += 1
                elif "负面" in label:
                    stats["quality_stats"]["negative"] += 1
        
        stats["quality_stats"]["neutral"] = stats["success"] - stats["quality_stats"]["positive"] - stats["quality_stats"]["negative"]
        
        return stats