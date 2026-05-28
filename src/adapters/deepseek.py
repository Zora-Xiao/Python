from typing import Optional
from src.adapters.base import BaseAdapter
from src.models.question import Question
from src.utils.logger import logger


class DeepseekAdapter(BaseAdapter):
    def __init__(self, config: dict):
        super().__init__(config)
        self.platform_id = "deepseek"
        self.platform_url = config.get("web_url", "https://chat.deepseek.com/")
    
    async def _execute_login(self) -> bool:
        try:
            # 先等待页面加载完成
            await self.page.wait_for_timeout(5000)
            
            login_button_selectors = [
                "button:has-text('登录')",
                "button:has-text('Sign In')",
                "[data-testid='login']",
                ".login-btn",
                "button[data-testid*='login']",
                ".ds-basic-button:has-text('登录')",
                "[role='button']:has-text('登录')"
            ]
            
            login_button = None
            for selector in login_button_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=5000)
                    login_button = selector
                    break
                except:
                    continue
            
            if not login_button:
                logger.warning("Deepseek未找到登录按钮")
                return False
            
            await self.page.click(login_button)
            await self.page.wait_for_timeout(3000)  # 增加等待时间
            
            # 尝试切换到密码登录模式
            logger.info("Deepseek尝试切换到密码登录模式...")
            password_login_selectors = [
                "button:has-text('密码登录')",
                "button:has-text('使用密码登录')",
                "button:has-text('Password Login')",
                "a:has-text('密码登录')",
                "div:has-text('密码登录')",
                ".password-login-btn",
                "[data-testid*='password-login']"
            ]
            
            for selector in password_login_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    if elements and len(elements) > 0:
                        for elem in elements:
                            try:
                                is_visible = await elem.is_visible()
                                if is_visible:
                                    await elem.click()
                                    logger.info(f"Deepseek已切换到密码登录模式: {selector}")
                                    await self.page.wait_for_timeout(2000)
                                    break
                            except:
                                continue
                        break
                except:
                    continue
            
            username_selectors = [
                "input[name='username']",
                "input[name='email']",
                "input[name='phone']",
                "input[type='text']",
                "input[placeholder*='账号']",
                "input[placeholder*='手机号']",
                "input[placeholder*='邮箱']"
            ]
            
            username_selector = None
            for selector in username_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=3000)
                    username_selector = selector
                    break
                except:
                    continue
            
            if username_selector:
                await self.page.fill(username_selector, self.username)
                await self.page.wait_for_timeout(500)
            else:
                logger.warning("Deepseek未找到用户名输入框")
                return False
            
            password_selectors = [
                "input[name='password']",
                "input[type='password']",
                "input[placeholder*='密码']",
                "input[placeholder*='Password']",
                ".ds-input[type='password']",
                "[data-testid*='password']",
                "input[class*='password']"
            ]
            
            password_selector = None
            for selector in password_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=3000)
                    password_selector = selector
                    break
                except:
                    continue
            
            if password_selector:
                await self.page.fill(password_selector, self.password)
                await self.page.wait_for_timeout(500)
            else:
                logger.warning("Deepseek未找到密码输入框")
                return False
            
            submit_selectors = [
                "button[type='submit']",
                "button:has-text('登录')",
                "button:has-text('确定')",
                ".submit-btn"
            ]
            
            submit_selector = None
            for selector in submit_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=3000)
                    submit_selector = selector
                    break
                except:
                    continue
            
            if submit_selector:
                await self.page.click(submit_selector)
                await self.page.wait_for_timeout(5000)
                logger.info("Deepseek登录表单已提交")
            else:
                logger.warning("Deepseek未找到提交按钮")
            
            return True
        except Exception as e:
            logger.error(f"Deepseek自动登录失败：{str(e)}")
            return False
    
    async def _navigate_to_chat(self) -> bool:
        try:
            await self.page.goto(self.platform_url, wait_until="domcontentloaded", timeout=60000)
            await self.page.wait_for_timeout(3000)
            return True
        except Exception as e:
            logger.error(f"Deepseek 导航失败：{str(e)}")
            return False
    
    async def _send_message(self, question: str) -> None:
        try:
            # 增加等待时间，确保页面完全加载
            await self.page.wait_for_timeout(2000)
            
            input_selectors = [
                "textarea[placeholder*='输入']",
                "textarea[placeholder*='提问']",
                "textarea[placeholder*='Message']",
                "textarea[placeholder*='ask']",
                "textarea[placeholder*='Send']",
                "textarea[placeholder*='AI']",
                "textarea",
                "input[type='text']",
                "input[placeholder*='输入']",
                "input[placeholder*='提问']",
                "div[contenteditable='true']",
                "[contenteditable='true']",
                "[role='textbox']",
                ".chat-input",
                ".composer-input",
                "#prompt-input",
                "[data-testid*='input']",
                ".ds-input",
                "[class*='input']",
                # 新增更多选择器
                "[class*='textarea']",
                ".message-input",
                ".prompt-input",
                ".ask-input",
                "[placeholder*='输入']",
                "[placeholder*='提问']"
            ]
            
            input_selector = None
            for selector in input_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=5000)
                    # 检查元素是否可见
                    element = await self.page.query_selector(selector)
                    if element:
                        is_visible = await element.is_visible()
                        if is_visible:
                            input_selector = selector
                            break
                except:
                    continue
            
            if not input_selector:
                # 尝试打印页面上所有可能的输入元素进行调试
                try:
                    elements = await self.page.query_selector_all("textarea, input[type='text'], [contenteditable]")
                    logger.info(f"Deepseek 页面上找到 {len(elements)} 个潜在输入元素")
                except:
                    pass
                raise Exception("未找到输入框")
            
            await self.page.click(input_selector)
            await self.page.wait_for_timeout(500)
            await self.page.fill(input_selector, question)
            await self.page.wait_for_timeout(500)
            await self.page.press(input_selector, "Enter")
            
            logger.info(f"Deepseek 成功发送消息：{question[:30]}...")
            
        except Exception as e:
            logger.error(f"Deepseek 发送消息失败：{str(e)}")
            raise
    
    async def _get_answer(self) -> str:
        try:
            answer_selector = ".message-content"
            await self.page.wait_for_selector(answer_selector, timeout=15000)
            answer_elements = await self.page.query_selector_all(answer_selector)
            
            if answer_elements:
                last_answer = answer_elements[-1]
                answer = await last_answer.inner_text()
                return answer.strip()
            
            return "未找到回答"
        except Exception as e:
            logger.error(f"Deepseek 获取回答失败：{str(e)}")
            return "获取回答失败"
    
    async def screenshot(self, question: Question, answer: str) -> tuple[Optional[str], bool, Optional[str]]:
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
            logger.error(f"Deepseek 截图失败：{str(e)}")
            return None, False, None
    
    async def close(self):
        await super().close()