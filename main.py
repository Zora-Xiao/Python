# 在导入任何模块之前设置环境变量，解决Node.js v24与Playwright的EPIPE兼容性问题
import os
os.environ['PLAYWRIGHT_TRANSPORT'] = 'websocket'

import asyncio
import yaml
from pathlib import Path
from src.models.question import Question
from src.models.rule import Rule
from src.adapters.doubao import DoubaoAdapter
from src.adapters.yuanbao import YuanbaoAdapter
from src.adapters.qwen import QwenAdapter
from src.adapters.ernie import ErnieAdapter
from src.adapters.deepseek import DeepseekAdapter
from src.engine.rate_limiter import RateLimiter
from src.engine.scheduler import Scheduler
from src.engine.rule_matcher import RuleMatcher
from src.exporter.excel_exporter import ExcelExporter
from src.utils.logger import logger
from src.utils.screenshot import ScreenshotTool


class AIEvaluationTool:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self._setup_logger()
        self.questions = self._load_questions()
        self.rules = self._load_rules()
        self.adapters = self._load_adapters()
        self.rate_limiter = self._load_rate_limiter()
        self.scheduler = Scheduler(self.adapters, self.rate_limiter)
        self.rule_matcher = RuleMatcher(self.rules)
        self.excel_exporter = ExcelExporter(self.config['output']['result_dir'])
        self.screenshot_tool = ScreenshotTool(self.config['output']['screenshot_dir'])

    def _load_config(self) -> dict:
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        logger.info(f"配置文件加载成功: {self.config_path}")
        return config

    def _setup_logger(self):
        log_config = self.config.get('logging', {})
        logger.setup(
            log_dir=log_config.get('file', 'logs/evaluation.log').rsplit('/', 1)[0],
            log_file=log_config.get('file', 'logs/evaluation.log').rsplit('/', 1)[1],
            level=log_config.get('level', 'INFO'),
            format_str=log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )

    def _load_questions(self) -> list:
        questions = []
        for q in self.config.get('questions', []):
            questions.append(Question(
                id=q['id'],
                text=q['text'],
                category=q.get('category')
            ))
        logger.info(f"加载了 {len(questions)} 个问题")
        return questions

    def _load_rules(self) -> list:
        rules = []
        for r in self.config.get('rules', []):
            rules.append(Rule(
                id=r['id'],
                name=r['name'],
                type=r['type'],
                keywords=r.get('keywords'),
                pattern=r.get('pattern'),
                priority=r.get('priority', 1),
                label=r.get('label', ''),
                min_length=r.get('min_length'),
                max_length=r.get('max_length'),
                quality_keywords=r.get('quality_keywords'),
                quality_type=r.get('quality_type'),
                relevance_keywords=r.get('relevance_keywords')
            ))
        logger.info(f"加载了 {len(rules)} 个规则")
        return rules

    def _load_adapters(self) -> list:
        adapters = []
        platform_configs = self.config.get('platforms', {})

        adapter_classes = {
            'doubao': DoubaoAdapter,
            'yuanbao': YuanbaoAdapter,
            'qwen': QwenAdapter,
            'ernie': ErnieAdapter,
            'deepseek': DeepseekAdapter
        }

        for platform_id, platform_config in platform_configs.items():
            if platform_config.get('enabled', False):
                adapter_class = adapter_classes.get(platform_id)
                if adapter_class:
                    config_with_name = {
                        **platform_config,
                        'name': platform_id,
                        'captcha_handling': self.config.get('captcha_handling', {}),
                        'browser': self.config.get('browser', {})
                    }
                    adapter = adapter_class(config_with_name)
                    adapters.append(adapter)
                    logger.info(f"加载适配器: {adapter.name}")

        logger.info(f"共加载 {len(adapters)} 个适配器")
        return adapters

    def _load_rate_limiter(self) -> RateLimiter:
        rate_config = self.config.get('rate_limit', {})
        return RateLimiter(
            max_requests_per_minute=rate_config.get('max_requests_per_minute', 10),
            min_interval=rate_config.get('min_interval', 2.0),
            max_interval=rate_config.get('max_interval', 5.0),
            exponential_backoff=rate_config.get('exponential_backoff', True),
            max_retries=rate_config.get('max_retries', 3)
        )

    async def run(self):
        logger.info("=" * 50)
        logger.info("AI 问答评测工具启动（浏览器自动化模式）")
        logger.info("=" * 50)

        keep_browser_open = self.config.get('keep_browser_open', False)

        try:
            results = await self.scheduler.process_all_questions(self.questions)

            logger.info("开始应用规则匹配...")
            results = self.rule_matcher.apply_rules_to_results(results)

            stats = self.rule_matcher.get_statistics(results)
            logger.info(f"评测统计：{stats}")

            logger.info("开始导出 Excel 报告...")
            excel_file = self.excel_exporter.export(
                results,
                self.config['output']['excel_filename']
            )

            summary_file = self.excel_exporter.export_summary(
                results,
                "summary.xlsx"
            )

            logger.info("=" * 50)
            logger.info("评测完成!")
            logger.info(f"详细报告：{excel_file}")
            logger.info(f"汇总报告：{summary_file}")
            logger.info(f"成功率：{stats['success']}/{stats['total']} ({stats['success']/stats['total']*100:.2f}%)")
            logger.info("=" * 50)

            if keep_browser_open:
                logger.info("=" * 50)
                logger.info("🔵 浏览器保持打开状态...")
                logger.info("💡 按 Enter 键关闭浏览器并退出程序")
                logger.info("=" * 50)
                input()

        except Exception as e:
            logger.error(f"评测过程中发生错误：{str(e)}")
            raise
        finally:
            if not keep_browser_open:
                await self._cleanup_adapters()
                await self.screenshot_tool.close()

    async def run_sequential(self):
        logger.info("=" * 50)
        logger.info("AI 问答评测工具启动 (顺序模式)")
        logger.info("=" * 50)

        keep_browser_open = self.config.get('keep_browser_open', False)

        try:
            results = await self.scheduler.process_sequentially(self.questions)

            logger.info("开始应用规则匹配...")
            results = self.rule_matcher.apply_rules_to_results(results)

            stats = self.rule_matcher.get_statistics(results)
            logger.info(f"评测统计：{stats}")

            logger.info("开始导出 Excel 报告...")
            excel_file = self.excel_exporter.export(
                results,
                self.config['output']['excel_filename']
            )

            logger.info("=" * 50)
            logger.info("评测完成!")
            logger.info(f"详细报告：{excel_file}")
            logger.info(f"成功率：{stats['success']}/{stats['total']} ({stats['success']/stats['total']*100:.2f}%)")
            logger.info("=" * 50)

            if keep_browser_open:
                logger.info("=" * 50)
                logger.info("🔵 浏览器保持打开状态...")
                logger.info("💡 按 Enter 键关闭浏览器并退出程序")
                logger.info("=" * 50)
                input()

        except Exception as e:
            logger.error(f"评测过程中发生错误：{str(e)}")
            raise
        finally:
            if not keep_browser_open:
                await self._cleanup_adapters()
                await self.screenshot_tool.close()

    async def _cleanup_adapters(self):
        for adapter in self.adapters:
            try:
                await adapter.close()
            except Exception as e:
                logger.warning(f"关闭适配器 {adapter.name} 时出错：{str(e)}")
        logger.info("所有适配器已关闭")


async def main():
    import sys

    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    mode = sys.argv[2] if len(sys.argv) > 2 else "sequential"  # 默认使用顺序模式

    tool = AIEvaluationTool(config_path)

    if mode == "sequential":
        await tool.run_sequential()
    else:
        await tool.run()


if __name__ == "__main__":
    asyncio.run(main())
