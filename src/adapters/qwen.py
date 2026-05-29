from typing import Optional, Tuple
from src.adapters.base import BaseAdapter
from src.models.question import Question
from src.utils.logger import logger


class QwenAdapter(BaseAdapter):
    def __init__(self, config: dict):
        super().__init__(config)
        self.platform_id = "qwen"
        self.platform_url = config.get("web_url", "https://chat.qwen.ai/")
    
    async def _execute_login(self) -> bool:
        try:
            login_button_selectors = [
                "button:has-text('登录')",
                "button:has-text('Sign In')",
                "[data-testid='login']",
                ".login-btn"
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
                logger.warning("千问未找到登录按钮")
                return False
            
            await self.page.click(login_button)
            await self.page.wait_for_timeout(2000)
            
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
                logger.warning("千问未找到用户名输入框")
                return False
            
            password_selectors = [
                "input[name='password']",
                "input[type='password']",
                "input[placeholder*='密码']"
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
                logger.warning("千问未找到密码输入框")
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
                logger.info("千问登录表单已提交")
            else:
                logger.warning("千问未找到提交按钮")
            
            return True
        except Exception as e:
            logger.error(f"千问自动登录失败：{str(e)}")
            return False
    
    async def _navigate_to_chat(self) -> bool:
        try:
            await self.page.goto(self.platform_url, wait_until="domcontentloaded", timeout=60000)
            await self.page.wait_for_timeout(3000)
            return True
        except Exception as e:
            logger.error(f"千问导航失败：{str(e)}")
            return False
    
    async def _send_message(self, question: str) -> None:
        try:
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
                "[data-testid*='input']"
            ]
            
            input_selector = None
            for selector in input_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=10000)
                    input_selector = selector
                    break
                except:
                    continue
            
            if not input_selector:
                raise Exception("未找到输入框")
            
            await self.page.click(input_selector)
            await self.page.wait_for_timeout(500)
            await self.page.fill(input_selector, question)
            await self.page.wait_for_timeout(500)
            await self.page.press(input_selector, "Enter")
            
            logger.info(f"千问成功发送消息：{question[:30]}...")
            
        except Exception as e:
            logger.error(f"千问发送消息失败：{str(e)}")
            raise
    
    async def _get_answer(self) -> str:
        try:
            # 定义多种可能的回答选择器
            answer_selectors = [
                ".message-content",
                ".answer-content",
                ".response-content",
                ".chat-message",
                ".assistant-message",
                "[role='listitem']",
                ".message-body",
                ".markdown-body",
                ".prose",
                ".content",
                ".qwen-answer",
                ".ant-list-item",
                ".chat-history-item",
                ".msg-content",
                ".reply-content",
            ]
            
            # 等待最多60秒
            max_wait_time = 60
            wait_interval = 1
            
            for _ in range(max_wait_time // wait_interval):
                for selector in answer_selectors:
                    try:
                        answer_elements = await self.page.query_selector_all(selector)
                        if answer_elements and len(answer_elements) > 0:
                            last_answer = answer_elements[-1]
                            is_visible = await last_answer.is_visible()
                            if is_visible:
                                answer = await last_answer.inner_text()
                                if answer and len(answer.strip()) > 10:
                                    logger.info(f"千问成功获取回答: {answer[:30]}...")
                                    return answer.strip()
                    except:
                        continue
                
                # 检查是否正在加载
                try:
                    loading_elements = await self.page.query_selector_all(".loading, .typing, span:has-text('正在')")
                    is_loading = any(await elem.is_visible() for elem in loading_elements) if loading_elements else False
                    if not is_loading:
                        # 如果没有加载指示器，尝试检查输入框是否可用
                        textarea = await self.page.query_selector("textarea")
                        if textarea:
                            is_disabled = await textarea.get_attribute("disabled")
                            if is_disabled is None:
                                # 输入框可用，说明回复可能已完成
                                for selector in answer_selectors:
                                    try:
                                        answer_elements = await self.page.query_selector_all(selector)
                                        if answer_elements and len(answer_elements) > 0:
                                            last_answer = answer_elements[-1]
                                            answer = await last_answer.inner_text()
                                            if answer and len(answer.strip()) > 10:
                                                logger.info(f"千问成功获取回答: {answer[:30]}...")
                                                return answer.strip()
                                    except:
                                        continue
                except:
                    pass
                
                await self.page.wait_for_timeout(wait_interval * 1000)
            
            logger.warning("千问等待回答超时")
            return "未获取到回答"
            
        except Exception as e:
            logger.error(f"千问获取回答失败：{str(e)}")
            return f"获取回答失败：{str(e)}"
    
    async def screenshot(self, question: Question, answer: str) -> tuple[Optional[str], bool]:
        if self.page is None:
            return None, False
        
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
            logger.error(f"千问截图失败：{str(e)}")
            return None, False, None
    
    async def close(self):
        await super().close()