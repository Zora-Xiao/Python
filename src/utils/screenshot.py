from pathlib import Path
from typing import Optional
from playwright.async_api import async_playwright, Browser, Page
from src.models.question import Question
from src.utils.logger import logger


class ScreenshotTool:
    def __init__(self, screenshot_dir: str = "screenshots"):
        self.screenshot_dir = Path(screenshot_dir)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.browser: Optional[Browser] = None
    
    async def _get_browser(self) -> Browser:
        if self.browser is None:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(headless=True)
        return self.browser
    
    async def capture_from_page(self, page: Page, platform_id: str, question: Question) -> Optional[str]:
        try:
            filename = f"{platform_id}_{question.id}_{question.timestamp.strftime('%Y%m%d_%H%M%S')}.png"
            filepath = self.screenshot_dir / filename
            
            await page.wait_for_timeout(2000)
            await page.screenshot(
                path=str(filepath), 
                full_page=True,
                timeout=60000
            )
            
            logger.info(f"页面截图已保存：{filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"页面截图失败：{str(e)}")
            try:
                filename = f"{platform_id}_{question.id}_{question.timestamp.strftime('%Y%m%d_%H%M%S')}.png"
                filepath = self.screenshot_dir / filename
                await page.screenshot(
                    path=str(filepath),
                    timeout=30000
                )
                logger.info(f"页面截图已保存（简化版）：{filepath}")
                return str(filepath)
            except Exception as e2:
                logger.error(f"简化截图也失败：{str(e2)}")
                return None
    
    async def capture(self, platform_id: str, question: Question, answer: str) -> Optional[str]:
        try:
            browser = await self._get_browser()
            page = await browser.new_page()
            
            html_content = self._generate_html(platform_id, question, answer)
            await page.set_content(html_content)
            
            filename = f"{platform_id}_{question.id}_{question.timestamp.strftime('%Y%m%d_%H%M%S')}.png"
            filepath = self.screenshot_dir / filename
            
            await page.screenshot(path=str(filepath), full_page=True)
            await page.close()
            
            logger.info(f"截图已保存：{filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"截图失败：{str(e)}")
            return None
    
    def _generate_html(self, platform_id: str, question: Question, answer: str) -> str:
        platform_names = {
            "doubao": "豆包",
            "yuanbao": "元宝",
            "qwen": "千问",
            "ernie": "文心一言",
            "deepseek": "Deepseek"
        }
        
        platform_name = platform_names.get(platform_id, platform_id)
        
        html = f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>AI问答评测 - {platform_name}</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f5f5f5;
                }}
                .container {{
                    background-color: white;
                    border-radius: 8px;
                    padding: 30px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .header {{
                    border-bottom: 2px solid #4CAF50;
                    padding-bottom: 15px;
                    margin-bottom: 20px;
                }}
                .platform {{
                    font-size: 24px;
                    font-weight: bold;
                    color: #4CAF50;
                }}
                .question {{
                    background-color: #e3f2fd;
                    padding: 15px;
                    border-radius: 5px;
                    margin-bottom: 20px;
                }}
                .question-label {{
                    font-weight: bold;
                    color: #1976D2;
                    margin-bottom: 5px;
                }}
                .answer {{
                    background-color: #f1f8e9;
                    padding: 15px;
                    border-radius: 5px;
                    white-space: pre-wrap;
                }}
                .answer-label {{
                    font-weight: bold;
                    color: #388E3C;
                    margin-bottom: 5px;
                }}
                .timestamp {{
                    color: #666;
                    font-size: 12px;
                    margin-top: 20px;
                    text-align: right;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="platform">{platform_name}</div>
                </div>
                
                <div class="question">
                    <div class="question-label">问题：</div>
                    <div>{question.text}</div>
                </div>
                
                <div class="answer">
                    <div class="answer-label">回答：</div>
                    <div>{answer}</div>
                </div>
                
                <div class="timestamp">
                    问题ID: {question.id} | 时间: {question.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    async def close(self):
        if self.browser:
            await self.browser.close()
            self.browser = None