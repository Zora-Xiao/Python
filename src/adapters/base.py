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
        async with self._browser_lock:
            should_recreate = False
            if self.browser is None:
                should_recreate = True
            else:
                try:
                    if not self.browser.is_connected:
                        logger.warning(f"{self.name}浏览器已断开，需要重建")
                        should_recreate = True
                except Exception:
                    should_recreate = True

            page_is_valid = False
            if self.page and self.browser and not should_recreate:
                try:
                    if self.page.is_closed:
                        logger.warning(f"{self.name}页面已关闭，需要新建页面")
                        page_is_valid = False
                    else:
                        page_is_valid = True
                except Exception:
                    page_is_valid = False

            if should_recreate or not page_is_valid:
                if self.browser and should_recreate:
                    try:
                        await self.browser.close()
                    except:
                        pass
                    self.browser = None
                    self.page = None

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
                    logger.info(f"{self.name}浏览器已重建")
                elif self.page is None or page_is_valid is False:
                    try:
                        context = await self.browser.new_context(
                            viewport={'width': 1920, 'height': 1080},
                            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                        )
                        await self._load_cookies(context)
                        self.page = await context.new_page()
                        logger.info(f"{self.name}新页面已创建")
                    except Exception as e:
                        logger.error(f"{self.name}创建新页面失败：{str(e)}")
                        should_recreate = True
                        if self.browser:
                            try:
                                await self.browser.close()
                            except:
                                pass
                            self.browser = None
                            self.page = None
                        raise Exception(f"{self.name}无法创建有效页面：{str(e)}")

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
            # 不重新导航，直接检查当前页面状态
            await self.page.wait_for_timeout(1000)
            
            logout_selectors = [
                "button:has-text('退出')",
                "button:has-text('Logout')",
                "a:has-text('退出')",
                "a:has-text('Logout')",
                ".user-avatar",
                ".avatar",
                "[class*='avatar']",
                "[data-testid*='avatar']"
            ]
            
            for selector in logout_selectors:
                try:
                    elems = await self.page.query_selector_all(selector)
                    if elems:
                        for elem in elems:
                            if await elem.is_visible():
                                logger.info(f"{self.name}已登录（找到元素: {selector}）")
                                return True
                except Exception as e:
                    logger.debug(f"{self.name}检查选择器 {selector} 失败: {str(e)}")
                    continue
            
            login_selectors = [
                "button:has-text('登录')",
                "button:has-text('Login')",
                "a:has-text('登录')",
                "a:has-text('Login')",
                "[href*='login']",
                "[href*='signin']",
                ".login-btn",
                "[data-testid*='login']"
            ]
            
            for selector in login_selectors:
                try:
                    elems = await self.page.query_selector_all(selector)
                    if elems:
                        for elem in elems:
                            if await elem.is_visible():
                                logger.info(f"{self.name}未登录（找到登录按钮: {selector}）")
                                return False
                except Exception as e:
                    logger.debug(f"{self.name}检查选择器 {selector} 失败: {str(e)}")
                    continue
            
            # 如果都没找到，检查是否有输入框（通常登录后才有输入框）
            input_selectors = ["textarea", "input[type='text']", "[role='textbox']", "[contenteditable='true']"]
            for selector in input_selectors:
                try:
                    elems = await self.page.query_selector_all(selector)
                    if elems:
                        for elem in elems:
                            if await elem.is_visible():
                                logger.info(f"{self.name}已登录（找到输入框）")
                                return True
                except:
                    continue
            
            logger.info(f"{self.name}无法确定登录状态")
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
            
            # 导航到聊天页面
            if not await self._navigate_to_chat():
                return "无法导航到对话页面", "error"
            
            # 检查是否需要登录，如果需要则等待用户手动登录
            if self.login_required:
                await self._ensure_logged_in()
            
            # 尝试发送消息
            answer = await self._send_message_and_get_answer(question.text)
            return answer, "success"
            
        except Exception as e:
            logger.error(f"{self.name}适配器错误: {str(e)}")
            return f"请求异常：{str(e)}", "error"
    
    async def _ensure_logged_in(self):
        """确保用户已登录，如果未登录则尝试自动登录，失败后等待手动登录"""
        try:
            # 先检查是否已登录（通过检测输入框）
            if await self._check_if_logged_in_with_input():
                logger.info(f"{self.name}已登录（检测到输入框）")
                return
            
            # 尝试自动登录
            if self.username and self.password:
                logger.info(f"{self.name}未登录，尝试自动登录...")
                if await self._login():
                    await self.page.wait_for_timeout(3000)
                    if await self._check_if_logged_in_with_input():
                        logger.info(f"{self.name}自动登录成功")
                        await self._save_cookies(self.page.context)
                        return
                    else:
                        logger.warning(f"{self.name}自动登录后仍未检测到登录状态")
            
            # 自动登录失败或未配置账号密码，等待手动登录
            logger.info(f"=" * 50)
            logger.info(f"🔴 {self.name}需要登录")
            logger.info(f"💡 请在弹出的浏览器窗口中完成登录")
            logger.info(f"⏳ 等待登录完成（最多等待120秒）")
            logger.info(f"💡 登录完成后请保持浏览器窗口打开")
            logger.info(f"=" * 50)
            
            # 等待用户手动登录，每2秒检查一次
            for i in range(60):
                try:
                    # 检查页面是否还存在
                    if not self.page or self.page.is_closed:
                        logger.warning(f"{self.name}页面已关闭")
                        return
                    
                    await self.page.wait_for_timeout(2000)
                    
                    # 检查是否已登录
                    if await self._check_if_logged_in_with_input():
                        logger.info(f"{self.name}登录成功")
                        await self._save_cookies(self.page.context)
                        return
                        
                except Exception as e:
                    logger.debug(f"{self.name}登录检查中出错: {str(e)}")
                    continue
            
            logger.warning(f"{self.name}登录超时，继续尝试...")
            
        except Exception as e:
            logger.warning(f"{self.name}登录检查失败: {str(e)}")
    
    async def _check_if_logged_in_with_input(self) -> bool:
        """通过检测聊天输入框是否可用来判断是否已登录（排除登录页面的输入框）"""
        try:
            await self.page.wait_for_timeout(1000)
            
            # 先检查是否在登录页面（有登录按钮或密码输入框）
            login_indicators = [
                "button:has-text('登录')",
                "button:has-text('Login')",
                "[placeholder*='邮箱']",
                "[placeholder*='密码']",
                "[placeholder*='username']",
                "[placeholder*='password']",
                "input[type='password']",
                "button[type='submit']",
                "form"
            ]
            
            has_login_indicator = False
            for selector in login_indicators:
                try:
                    elems = await self.page.query_selector_all(selector)
                    if elems:
                        for elem in elems:
                            if await elem.is_visible():
                                has_login_indicator = True
                                logger.debug(f"{self.name}检测到登录页面元素: {selector}")
                                break
                        if has_login_indicator:
                            break
                except Exception as e:
                    logger.debug(f"{self.name}检查登录指示器失败: {str(e)}")
                    continue
            
            # 如果检测到登录页面元素，判定为未登录
            if has_login_indicator:
                logger.debug(f"{self.name}检测到登录页面，判定为未登录")
                return False
            
            # 再检查聊天输入框（已登录状态）
            chat_input_selectors = [
                "textarea",
                "[role='textbox']",
                "[contenteditable='true']",
                ".chat-input",
                ".message-input",
                "textarea[placeholder*='输入']",
                "textarea[placeholder*='提问']",
                "textarea[placeholder*='Message']",
            ]
            
            for selector in chat_input_selectors:
                try:
                    elems = await self.page.query_selector_all(selector)
                    if elems:
                        for elem in elems:
                            if await elem.is_visible():
                                # 检查这个输入框是否是聊天输入框（不是登录输入框）
                                placeholder = await self.page.evaluate('(el) => el.placeholder || ""', elem)
                                # 如果没有登录页面的特征，且有输入框，则判定为已登录
                                if not has_login_indicator:
                                    logger.info(f"{self.name}检测到聊天输入框，判定为已登录")
                                    return True
                except Exception as e:
                    logger.debug(f"{self.name}检查输入框 {selector} 失败: {str(e)}")
                    continue
            
            logger.debug(f"{self.name}未找到明确的登录状态标识")
            return False
        except Exception as e:
            logger.debug(f"{self.name}检查登录状态失败: {str(e)}")
            return False
    
    async def _send_message_and_get_answer(self, question: str) -> str:
        await self._send_message(question)
        await self.page.wait_for_timeout(5000)
        answer = await self._get_answer()
        return answer
    
    async def screenshot(self, question: Question, answer: str) -> tuple[Optional[str], bool, Optional[str]]:
        """
        截图方法，优先尝试下载分享图片
        返回：(图片路径, 是否为分享图片, 分享链接)
        """
        if self.page is None:
            return None, False, None
        
        try:
            from src.utils.screenshot import ScreenshotTool
            screenshot_tool = ScreenshotTool()
            
            await self.page.wait_for_timeout(1000)
            screenshot_path, is_shared_image, share_link = await screenshot_tool.capture_from_page(
                self.page, 
                self.platform_id, 
                question
            )
            return screenshot_path, is_shared_image, share_link
            
        except Exception as e:
            logger.error(f"截图失败：{str(e)}")
            return None, False, None
    
    async def process(self, question: Question) -> Dict[str, Any]:
        try:
            answer, status = await self.ask(question)
            screenshot_path, is_shared_image, share_link = await self.screenshot(question, answer)
            
            return {
                "answer": answer,
                "status": status,
                "screenshot_path": screenshot_path,
                "is_shared_image": is_shared_image,
                "share_link": share_link,
                "error_message": None
            }
        except Exception as e:
            return {
                "answer": "",
                "status": "error",
                "screenshot_path": None,
                "is_shared_image": False,
                "error_message": str(e)
            }
    
    async def close(self):
        if self.browser and self.page:
            await self._save_cookies(self.page.context)
        if self.browser:
            await self.browser.close()
            self.browser = None
            self.page = None
