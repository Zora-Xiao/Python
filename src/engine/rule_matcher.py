import re
from typing import List
from src.models.rule import Rule
from src.models.result import Result
from src.utils.logger import logger


class RuleMatcher:
    def __init__(self, rules: List[Rule]):
        self.rules = sorted(rules, key=lambda r: r.priority, reverse=True)
    
    def match(self, answer: str) -> List[str]:
        matched_labels = []
        
        for rule in self.rules:
            if self._match_rule(answer, rule):
                matched_labels.append(rule.label)
                logger.debug(f"规则 {rule.name} 匹配成功，标签: {rule.label}")
        
        return matched_labels
    
    def _match_rule(self, answer: str, rule: Rule) -> bool:
        if rule.type == "keyword":
            return self._match_keywords(answer, rule.keywords)
        elif rule.type == "regex":
            return self._match_regex(answer, rule.pattern)
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
    
    def apply_rules(self, result: Result) -> Result:
        if result.status == "success":
            matched_labels = self.match(result.answer)
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
            "rule_matches": {}
        }
        
        for result in results:
            if result.status == "success":
                stats["success"] += 1
            else:
                stats["error"] += 1
            
            for label in result.matched_rules:
                if label not in stats["rule_matches"]:
                    stats["rule_matches"][label] = 0
                stats["rule_matches"][label] += 1
        
        return stats