from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Browser, Page
from src.models.question import Question
from src.utils.logger import logger
from pathlib import Path
import json
import asyncio


class BaseAdapter(ABC):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = config.get("name", "Unknown")
        self.api_key = config.get("api_key", "")
        self.api_url = config.get("api_url", "")
        self.use_playwright = config.get("use_playwright", True)
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.platform_url = config.get("web_url", "")
        self.login_required = config.get("login_required", True)
        self.login_url = config.get("login_url", "")
        self.credentials = config.get("credentials", {})
        self.username = self.credentials.get("username", "")
        self.password = self.credentials.get("password", "")
        self.cookies_dir = Path("cookies")
        self.cookies_dir.mkdir(parents=True, exist_ok=True)
        self._browser_lock = asyncio.Lock()  # 添加锁机制
    
    async def _get_browser(self) -> Browser:
        async with self._browser_lock:  # 使用锁确保线程安全
            if self.browser is None:
                playwright = await async_playwright().start()
                self.browser = await playwright.chromium.launch(
                    headless=False,
                    args=['--disable-blink-features=AutomationControlled',
                          '--disable-dev-shm-usage',
                          '--no-sandbox']
                )
                context = await self.browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                
                await self._load_cookies(context)
                self.page = await context.new_page()
        return self.browser
    
    def _get_cookies_file(self) -> Path:
        return self.cookies_dir / f"{self.platform_id}_cookies.json"
    
    async def _load_cookies(self, context):
        cookies_file = self._get_cookies_file()
        if cookies_file.exists():
            try:
                with open(cookies_file, 'r', encoding='utf-8') as f:
                    cookies = json.load(f)
                    await context.add_cookies(cookies)
                logger.info(f"{self.name}已加载保存的Cookie")
            except Exception as e:
                logger.warning(f"{self.name}加载Cookie失败：{str(e)}")
    
    async def _save_cookies(self, context):
        cookies_file = self._get_cookies_file()
        try:
            cookies = await context.cookies()
            with open(cookies_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, indent=2)
            logger.info(f"{self.name}Cookie已保存")
        except Exception as e:
            logger.warning(f"{self.name}保存Cookie失败：{str(e)}")
    
    async def _is_logged_in(self) -> bool:
        try:
            await self.page.wait_for_timeout(2000)
            logged_in = await self._check_login_status()
            return logged_in
        except Exception as e:
            logger.warning(f"{self.name}检测登录状态失败：{str(e)}")
            return False
    
    async def _check_login_status(self) -> bool:
        try:
            await self.page.goto(self.platform_url, wait_until="domcontentloaded", timeout=60000)
            await self.page.wait_for_timeout(2000)
            
            logout_selectors = [
                "button:has-text('退出')",
                "button:has-text('Logout')",
                "a:has-text('退出')",
                "a:has-text('Logout')",
                ".user-avatar",
                ".avatar"
            ]
            
            for selector in logout_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=3000)
                    logger.info(f"{self.name}已登录")
                    return True
                except:
                    continue
            
            login_selectors = [
                "button:has-text('登录')",
                "button:has-text('Login')",
                "a:has-text('登录')",
                "a:has-text('Login')",
                "[href*='login']"
            ]
            
            for selector in login_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=3000)
                    logger.info(f"{self.name}未登录")
                    return False
                except:
                    continue
            
            return False
        except Exception as e:
            logger.error(f"{self.name}检查登录状态时出错：{str(e)}")
            return False
    
    async def _login(self) -> bool:
        if not self.username or not self.password:
            logger.warning(f"{self.name}未配置账号密码，跳过自动登录")
            return False
        
        try:
            logger.info(f"{self.name}开始自动登录...")
            
            if self.login_url:
                await self.page.goto(self.login_url, wait_until="domcontentloaded", timeout=60000)
            else:
                await self.page.goto(self.platform_url, wait_until="domcontentloaded", timeout=60000)
            
            await self.page.wait_for_timeout(2000)
            result = await self._execute_login()
            
            if result:
                await self._save_cookies(self.page.context)
                logger.info(f"{self.name}自动登录成功")
            else:
                logger.warning(f"{self.name}自动登录失败，可能需要手动登录")
            
            return result
        except Exception as e:
            logger.error(f"{self.name}自动登录异常：{str(e)}")
            return False
    
    @abstractmethod
    async def _execute_login(self) -> bool:
        pass
    
    @abstractmethod
    async def _navigate_to_chat(self) -> bool:
        pass
    
    @abstractmethod
    async def _send_message(self, question: str) -> None:
        pass
    
    @abstractmethod
    async def _get_answer(self) -> str:
        pass
    
    async def ask(self, question: Question) -> tuple[str, str]:
        try:
            await self._get_browser()
            
            # 直接导航到聊天页面，不进行登录检测（避免检测失败导致流程中断）
            if not await self._navigate_to_chat():
                return "无法导航到对话页面", "error"
            
            # 尝试发送消息
            answer = await self._send_message_and_get_answer(question.text)
            return answer, "success"
            
        except Exception as e:
            logger.error(f"{self.name}适配器错误: {str(e)}")
            return f"请求异常：{str(e)}", "error"
    
    async def _send_message_and_get_answer(self, question: str) -> str:
        await self._send_message(question)
        await self.page.wait_for_timeout(3000)
        answer = await self._get_answer()
        return answer
    
    async def screenshot(self, question: Question, answer: str) -> Optional[str]:
        if self.page is None:
            return None
        
        try:
            from src.utils.screenshot import ScreenshotTool
            screenshot_tool = ScreenshotTool()
            
            await self.page.wait_for_timeout(1000)
            screenshot_path = await screenshot_tool.capture_from_page(
                self.page, 
                self.platform_id, 
                question
            )
            return screenshot_path
            
        except Exception as e:
            logger.error(f"截图失败：{str(e)}")
            return None
    
    async def process(self, question: Question) -> Dict[str, Any]:
        try:
            answer, status = await self.ask(question)
            screenshot_path = await self.screenshot(question, answer)
            
            return {
                "answer": answer,
                "status": status,
                "screenshot_path": screenshot_path,
                "error_message": None
            }
        except Exception as e:
            return {
                "answer": "",
                "status": "error",
                "screenshot_path": None,
                "error_message": str(e)
            }
    
    async def close(self):
        if self.browser and self.page:
            await self._save_cookies(self.page.context)
        if self.browser:
            await self.browser.close()
            self.browser = None
            self.page = None