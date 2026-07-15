from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Browser, Page
from src.models.question import Question
from src.utils.logger import logger
from pathlib import Path
import json
import asyncio
import os

# 解决连接中断EPIPE问题（Node.js v24与Playwright兼容性问题）
os.environ.setdefault('PLAYWRIGHT_TRANSPORT', 'websocket')


class BaseAdapter(ABC):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = config.get("name", "Unknown")
        self.api_key = config.get("api_key", "")
        self.api_url = config.get("api_url", "")
        self.use_playwright = config.get("use_playwright", True)
        self.browser: Optional[Browser] = None
        self.playwright = None
        self.page: Optional[Page] = None
        self.platform_url = config.get("web_url", "")
        self.login_required = config.get("login_required", True)
        self.login_url = config.get("login_url", "")
        self.credentials = config.get("credentials", {})
        self.username = self.credentials.get("username", config.get("username", ""))
        self.password = self.credentials.get("password", config.get("password", ""))
        self.cookies_dir = Path("cookies")
        self.cookies_dir.mkdir(parents=True, exist_ok=True)
        self._browser_lock = asyncio.Lock()  # 浏览器锁
    
    async def _get_browser(self) -> Browser:
        async with self._browser_lock:
            should_recreate = False
            if self.browser is None:
                should_recreate = True
            else:
                try:
                    if not self.browser.is_connected:
                        logger.warning(f"{self.name}浏览器连接断开，需要重建")
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
                    if self.playwright is None:
                        self.playwright = await async_playwright().start()
                    
                    # 更完善的反检测参数
                    launch_args = [
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox',
                        '--disable-infobars',
                        '--disable-background-networking',
                        '--disable-breakpad',
                        '--disable-component-update',
                        '--disable-default-apps',
                        '--disable-extensions',
                        '--disable-sync',
                        '--metrics-recording-only',
                        '--no-first-run',
                        '--disable-features=IsolateOrigins,site-per-process',
                        '--enable-features=NetworkService,NetworkServiceInProcess',
                        '--window-size=1920,1080',
                        '--start-maximized',
                    ]
                    
                    logger.info(f"{self.name}正在启动浏览器...")
                    self.browser = await self.playwright.chromium.launch(
                        headless=False,
                        args=launch_args
                    )
                    logger.info(f"{self.name}浏览器进程已启动")
                    
                    context = await self.browser.new_context(
                        viewport={'width': 1920, 'height': 1080},
                        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        locale='zh-CN',
                        timezone_id='Asia/Shanghai',
                    )
                    logger.info(f"{self.name}浏览器上下文已创建")
                    
                    await self._load_cookies(context)
                    self.page = await context.new_page()
                    
                    # 监听页面关闭事件
                    self.page.on("close", lambda: logger.warning(f"{self.name}页面被关闭了！"))
                    
                    # 监听页面错误事件
                    self.page.on("pageerror", lambda err: logger.error(f"{self.name}页面错误: {err}"))
                    
                    # 监听页面崩溃事件
                    self.page.on("crash", lambda: logger.error(f"{self.name}页面崩溃了！"))
                    
                    logger.info(f"{self.name}浏览器启动完成，页面状态: is_closed={self.page.is_closed()}")
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
            logger.warning(f"{self.name}检查登录状态失败：{str(e)}")
            return False
    
    async def _check_login_status(self) -> bool:
        try:
            # 等待页面加载后再检查当前页面状态
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
                                logger.info(f"{self.name}已登录，找到元素: {selector}")
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
                                logger.info(f"{self.name}未登录，找到登录按钮: {selector}")
                                return False
                except Exception as e:
                    logger.debug(f"{self.name}检查选择器 {selector} 失败: {str(e)}")
                    continue
            
            # 如果没有找到明显的登录/退出按钮，可以尝试检查输入框是否可用（通常登录后才可用）
            input_selectors = ["textarea", "input[type='text']", "[role='textbox']", "[contenteditable='true']"]
            for selector in input_selectors:
                try:
                    elems = await self.page.query_selector_all(selector)
                    if elems:
                        for elem in elems:
                            if await elem.is_visible():
                                logger.info(f"{self.name}已登录，找到输入框")
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
    
    # ==================== 公共辅助方法 ====================
    
    async def _find_visible_element(self, selectors: list) -> Optional[Any]:
        """
        查找第一个可见的元素
        
        Args:
            selectors: CSS选择器列表
            
        Returns:
            找到的元素对象或未找到时返回None
        """
        for selector in selectors:
            try:
                elements = await self.page.query_selector_all(selector)
                if elements:
                    for elem in elements:
                        if await elem.is_visible():
                            return elem
            except Exception:
                continue
        return None
    
    async def _fill_form_field(self, field_selectors: list, value: str) -> bool:
        """
        填写表单字段
        
        Args:
            field_selectors: 字段选择器列表
            value: 要填写的值
            
        Returns:
            是否成功填写
        """
        try:
            elem = await self._find_visible_element(field_selectors)
            if elem:
                await elem.fill(value)
                await self.page.wait_for_timeout(500)
                return True
            return False
        except Exception as e:
            logger.debug(f"{self.name} 填写字段失败: {str(e)}")
            return False
    
    async def _click_button(self, button_selectors: list) -> bool:
        """
        点击按钮
        
        Args:
            button_selectors: 按钮选择器列表
            
        Returns:
            是否成功点击
        """
        try:
            elem = await self._find_visible_element(button_selectors)
            if elem:
                await elem.click()
                return True
            return False
        except Exception as e:
            logger.debug(f"{self.name} 点击按钮失败: {str(e)}")
            return False
    
    async def _robust_click(self, element, description: str = "element") -> bool:
        """
        多种方式尝试点击元素，确保成功率
        
        Args:
            element: 要点击的元素
            description: 元素描述，用于日志标识
            
        Returns:
            是否成功点击
        """
        if not element:
            return False
        
        # 1. 滚动到视图
        try:
            await element.scroll_into_view_if_needed()
            await self.page.wait_for_timeout(500)
        except:
            pass
        
        # 2. 尝试JS点击，如果可能
        try:
            await element.evaluate("el => el.click()")
            logger.debug(f"{self.name} JS点击 {description} 成功")
            return True
        except Exception:
            pass
        
        # 3. 尝试Playwright强制点击
        try:
            await element.click(force=True, timeout=3000)
            logger.debug(f"{self.name} 强制点击 {description} 成功")
            return True
        except Exception:
            pass
        
        # 4. 尝试坐标点击
        try:
            box = await element.bounding_box()
            if box:
                x = box['x'] + box['width'] / 2
                y = box['y'] + box['height'] / 2
                await self.page.mouse.click(x, y)
                logger.debug(f"{self.name} 坐标点击 {description} 成功")
                return True
        except Exception:
            pass
        
        logger.warning(f"{self.name} 所有点击方式失败: {description}")
        return False
    
    async def _wait_for_element_with_text(self, selectors: list, timeout: int = 5000) -> Optional[Any]:
        """
        等待包含特定文本的元素
        
        Args:
            selectors: 选择器列表
            timeout: 超时时间
            
        Returns:
            找到的元素或None
        """
        for selector in selectors:
            try:
                elem = await self.page.wait_for_selector(selector, timeout=timeout)
                if elem and await elem.is_visible():
                    return elem
            except Exception:
                continue
        return None
    
    # ==================== 抽象方法 ====================
    
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
            logger.info(f"{self.name}开始处理问题: {question.text[:30]}...")
            
            logger.info(f"{self.name}步骤1: 获取浏览器")
            await self._get_browser()
            
            # 导航到聊天页面
            logger.info(f"{self.name}步骤2: 导航到聊天页面")
            if not await self._navigate_to_chat():
                return "无法进入对话页面", "error"
            
            # 检查是否需要登录，如果需要则等待用户手动登录
            if self.login_required:
                logger.info(f"{self.name}步骤3: 检查登录状态")
                login_success = await self._ensure_logged_in()
                if not login_success:
                    return f"{self.name}登录失败或页面已关闭", "error"
            
            # 检查页面是否仍然有效
            page_is_closed = self.page.is_closed() if self.page else True
            if not self.page or page_is_closed:
                logger.error(f"{self.name}页面已关闭，无法继续操作")
                return f"{self.name}页面已关闭", "error"
            
            # 记录页面状态
            logger.info(f"{self.name}页面状态检查: URL={self.page.url}, 已关闭={page_is_closed}")
            
            # 发送问题并获取回答
            logger.info(f"{self.name}步骤4: 发送消息并获取回答")
            answer = await self._send_message_and_get_answer(question.text)
            logger.info(f"{self.name}步骤5: 获取回答成功，长度: {len(answer)}")
            
            # 验证回答有效性
            validation_result = self._validate_answer(answer)
            if validation_result["is_valid"]:
                return answer, "success"
            else:
                return answer, validation_result["status"]
            
        except Exception as e:
            logger.error(f"{self.name}提问失败: {str(e)}")
            return f"提问失败: {str(e)}", "error"
    
    def _validate_answer(self, answer: str) -> dict:
        """验证回答的有效性，检查是否为空、错误提示或内容过短"""
        if not answer:
            return {"is_valid": False, "status": "error", "reason": "回答为空"}
        
        answer_stripped = answer.strip()
        
        if not answer_stripped:
            return {"is_valid": False, "status": "error", "reason": "回答为空"}
        
        error_indicators = [
            "未找到回答",
            "获取回答失败",
            "提问失败",
            "页面已关闭",
            "登录失败",
            "无法进入",
            "网络错误",
            "error",
            "Error",
            "ERROR",
            "无法回答",
            "暂时无法",
            "系统繁忙",
            "服务器错误",
            "超时",
            "timeout",
            "Timeout"
        ]
        
        for indicator in error_indicators:
            if indicator in answer_stripped:
                return {"is_valid": False, "status": "error", "reason": f"检测到错误指示词: {indicator}"}
        
        if len(answer_stripped) < 5:
            return {"is_valid": False, "status": "error", "reason": f"回答过短（{len(answer_stripped)}字符）"}
        
        return {"is_valid": True, "status": "success", "reason": "回答有效"}
    
    async def _ensure_logged_in(self) -> bool:
        """确保用户已登录，如果未登录则尝试自动登录，失败则等待手动登录"""
        try:
            # 先检查页面是否有效
            if not self.page or self.page.is_closed():
                logger.error(f"{self.name}页面已关闭，无法检查登录状态")
                return False
            
            logger.info(f"{self.name}当前页面URL: {self.page.url}")
            
            # 先检查是否已登录（通过查找输入框）
            logger.info(f"{self.name}开始检查登录状态...")
            if await self._check_if_logged_in_with_input():
                logger.info(f"{self.name}已登录，找到输入框")
                return True
            
            # 再次检查页面是否有效
            if not self.page or self.page.is_closed():
                logger.error(f"{self.name}检查登录状态后页面已关闭")
                return False
            
            # 尝试自动登录
            if self.username and self.password:
                logger.info(f"{self.name}未登录，尝试自动登录...")
                if await self._login():
                    await self.page.wait_for_timeout(3000)
                    if await self._check_if_logged_in_with_input():
                        logger.info(f"{self.name}自动登录成功")
                        page_is_closed = self.page.is_closed() if self.page else True
                        logger.info(f"{self.name}登录后页面状态: URL={self.page.url}, 已关闭={page_is_closed}")
                        await self._save_cookies(self.page.context)
                        return True
                    else:
                        page_is_closed = self.page.is_closed() if self.page else True
                        logger.warning(f"{self.name}自动登录后未检测到登录状态，页面状态: URL={self.page.url}, 已关闭={page_is_closed}")
            
            # 自动登录失败或未配置账号密码，等待手动登录
            logger.info("=" * 50)
            logger.info(f"? {self.name}需要登录")
            logger.info("? 请在打开的浏览器中完成登录")
            logger.info("? 等待登录完成（最多等待60秒）")
            logger.info("? 登录完成后请保持浏览器窗口打开")
            logger.info("=" * 50)
            
            # 等待用户手动登录，每2秒检查一次（最多等待60秒）
            for i in range(30):
                try:
                    # 检查页面是否还存在
                    if not self.page:
                        logger.warning(f"{self.name}页面对象不存在")
                        return False
                    
                    if self.page.is_closed():
                        logger.warning(f"{self.name}页面已关闭（循环第{i}次检查）")
                        return False
                    
                    logger.info(f"{self.name}等待登录中... ({i+1}/60)")
                    await self.page.wait_for_timeout(2000)
                    
                    # 检查是否已登录
                    if await self._check_if_logged_in_with_input():
                        logger.info(f"{self.name}登录成功")
                        await self._save_cookies(self.page.context)
                        return True
                        
                except Exception as e:
                    logger.warning(f"{self.name}登录检查中错误: {str(e)}")
                    # 检查页面是否仍然有效
                    if not self.page or self.page.is_closed():
                        logger.warning(f"{self.name}异常后页面已关闭")
                        return False
                    continue
            
            logger.warning(f"{self.name}登录超时，继续执行...")
            return False
            
        except Exception as e:
            logger.warning(f"{self.name}登录处理失败: {str(e)}")
            return False
    
    async def _check_if_logged_in_with_input(self) -> bool:
        """通过检测页面是否有输入框来判断是否已登录（有输入框表示已进入聊天页）"""
        try:
            # 先检查页面是否有效
            if not self.page or self.page.is_closed():
                logger.warning(f"{self.name}页面已关闭，无法检查登录状态")
                return False
            
            await self.page.wait_for_timeout(1000)
            
            current_url = self.page.url
            logger.info(f"{self.name}检查登录状态，当前URL: {current_url}")
            
            # 优先通过 URL 模式判断登录状态（各平台可覆盖）
            url_check_result = await self._check_login_url_pattern(current_url)
            if url_check_result is not None:
                if url_check_result:
                    logger.info(f"{self.name}通过URL判定已登录")
                else:
                    logger.info(f"{self.name}通过URL判定未登录")
                return url_check_result
            
            # 检查是否在登录页面（有登录按钮、用户名输入框等）
            login_indicators = [
                "button:has-text('登录')",
                "button:has-text('Login')",
                "[placeholder*='用户名']",
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
                    if not self.page or self.page.is_closed():
                        logger.warning(f"{self.name}在检查选择器 {selector} 时页面已关闭")
                        return False
                    
                    elems = await self.page.query_selector_all(selector)
                    if elems:
                        for elem in elems:
                            if await elem.is_visible():
                                has_login_indicator = True
                                logger.info(f"{self.name}检测到登录页面元素: {selector}")
                                break
                        if has_login_indicator:
                            break
                except Exception as e:
                    logger.debug(f"{self.name}检测登录指示器失败: {str(e)}")
                    if not self.page or self.page.is_closed():
                        logger.warning(f"{self.name}检测登录指示器异常后页面已关闭")
                        return False
                    continue
            
            # 如果检测到登录页面元素，判定为未登录
            if has_login_indicator:
                logger.info(f"{self.name}检测到登录页面，判定为未登录")
                return False
            
            # 再检测聊天输入框来确认登录状态
            chat_input_selectors = [
                "textarea",
                "[role='textbox']",
                "[contenteditable='true']",
                ".chat-input",
                ".message-input",
                "textarea[placeholder*='提问']",
                "textarea[placeholder*='聊天']",
                "textarea[placeholder*='Message']",
            ]
            
            for selector in chat_input_selectors:
                try:
                    if not self.page or self.page.is_closed():
                        logger.warning(f"{self.name}在检查选择器 {selector} 时页面已关闭")
                        return False
                    
                    elems = await self.page.query_selector_all(selector)
                    if elems:
                        for elem in elems:
                            if await elem.is_visible():
                                logger.info(f"{self.name}找到聊天输入框: {selector}，判定已登录")
                                return True
                except Exception as e:
                    logger.debug(f"{self.name}检测聊天输入框失败: {str(e)}")
                    continue
            
            logger.info(f"{self.name}未找到聊天输入框，判定未登录")
            return False
            
        except Exception as e:
            logger.error(f"{self.name}检查登录状态失败: {str(e)}")
            return False
    
    async def _check_login_url_pattern(self, url: str) -> bool:
        """基于URL模式判断登录状态，各平台可覆盖此方法
        返回 True 表示已登录，False 表示未登录，None 表示无法通过URL判断"""
        login_keywords = ["login", "signin", "sign_in", "account", "auth", "register"]
        logged_in_keywords = ["chat", "conversation", "dashboard", "home"]
        
        url_lower = url.lower()
        
        has_login_keyword = any(kw in url_lower for kw in login_keywords)
        has_logged_in_keyword = any(kw in url_lower for kw in logged_in_keywords)
        
        if has_login_keyword and not has_logged_in_keyword:
            return False
        elif has_logged_in_keyword and not has_login_keyword:
            return True
        
        return None
    
    async def _send_message_and_get_answer(self, question: str) -> str:
        await self._send_message(question)
        await self.page.wait_for_timeout(5000)
        answer = await self._get_answer()
        return answer
    
    async def screenshot(self, question: Question) -> tuple[Optional[str], bool, Optional[str], Optional[str]]:
        """
        截图方法，尝试获取分享图片或截图
        返回：(图片路径, 是否为分享图片, 分享链接, 分享链接失败原因)
        """
        if self.page is None:
            return None, False, None, None
        
        try:
            from src.utils.screenshot import ScreenshotTool
            screenshot_tool = ScreenshotTool()
            
            await self.page.wait_for_timeout(1000)
            screenshot_path, is_shared_image, share_link, share_link_error = await screenshot_tool.capture_from_page(
                self.page, 
                self.platform_id, 
                question
            )
            return screenshot_path, is_shared_image, share_link, share_link_error
            
        except Exception as e:
            logger.error(f"截图失败：{str(e)}")
            return None, False, None, str(e)
    
    async def process(self, question: Question) -> Dict[str, Any]:
        try:
            answer, status = await self.ask(question)
            if status == "error":
                return {
                    "answer": answer,
                    "status": status,
                    "screenshot_path": None,
                    "is_shared_image": False,
                    "share_link": None,
                    "share_link_error": None,
                    "error_message": answer
                }
            screenshot_path, is_shared_image, share_link, share_link_error = await self.screenshot(question)
            
            return {
                "answer": answer,
                "status": status,
                "screenshot_path": screenshot_path,
                "is_shared_image": is_shared_image,
                "share_link": share_link,
                "share_link_error": share_link_error,
                "error_message": None
            }
        except Exception as e:
            return {
                "answer": "",
                "status": "error",
                "screenshot_path": None,
                "is_shared_image": False,
                "share_link": None,
                "share_link_error": None,
                "error_message": str(e)
            }
    
    async def close(self):
        if self.browser and self.page:
            await self._save_cookies(self.page.context)
        if self.browser:
            await self.browser.close()
            self.browser = None
            self.page = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None