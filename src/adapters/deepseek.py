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
            await self.page.wait_for_timeout(3000)
            
            input_selectors = [
                # Deepseek特定选择器
                "textarea.ds-textarea",
                "textarea[class*='textarea']",
                "textarea[placeholder*='输入问题']",
                "textarea[placeholder*='输入消息']",
                "textarea[placeholder*='Message']",
                "textarea[placeholder*='Ask']",
                # 通用选择器
                "textarea",
                "input[type='text']",
                "div[contenteditable='true']",
                "[contenteditable='true']",
                "[role='textbox']",
                ".chat-input",
                ".composer-input",
                "#prompt-input",
                "[data-testid*='input']",
                ".ds-input",
                "[class*='input']",
                ".message-input",
                ".prompt-input",
                ".ask-input",
            ]
            
            input_selector = None
            found_element = None
            
            for selector in input_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    if elements and len(elements) > 0:
                        for elem in elements:
                            is_visible = await elem.is_visible()
                            if is_visible:
                                input_selector = selector
                                found_element = elem
                                logger.info(f"Deepseek 找到可见输入框: {selector}")
                                break
                        if found_element:
                            break
                except Exception as e:
                    logger.debug(f"Deepseek 检查选择器 {selector} 失败: {str(e)}")
                    continue
            
            if not found_element:
                # 尝试打印页面上所有可能的输入元素进行调试
                try:
                    elements = await self.page.query_selector_all("textarea, input[type='text'], [contenteditable]")
                    logger.info(f"Deepseek 页面上找到 {len(elements)} 个潜在输入元素")
                    for i, elem in enumerate(elements):
                        try:
                            tag_name = await elem.evaluate("el => el.tagName")
                            placeholder = await elem.get_attribute("placeholder") or ""
                            class_name = await elem.get_attribute("class") or ""
                            is_vis = await elem.is_visible()
                            logger.info(f"  元素{i}: {tag_name}, visible={is_vis}, placeholder={placeholder[:30]}, class={class_name[:50]}")
                        except:
                            pass
                except Exception as e:
                    logger.info(f"Deepseek 调试信息获取失败: {str(e)}")
                raise Exception("未找到输入框")
            
            logger.info(f"Deepseek 准备输入消息")
            await found_element.click()
            await self.page.wait_for_timeout(500)
            
            # 使用fill方法填充文本
            try:
                await self.page.fill(input_selector, question)
            except:
                # 如果fill失败，尝试使用type方法
                logger.info("Deepseek fill方法失败，尝试使用type方法")
                await found_element.type(question)
            
            await self.page.wait_for_timeout(500)
            
            # 尝试按Enter发送
            await self.page.press(input_selector, "Enter")
            
            logger.info(f"Deepseek 成功发送消息：{question[:30]}...")
            
        except Exception as e:
            logger.error(f"Deepseek 发送消息失败：{str(e)}")
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
                ".ds-message-content",
                ".deepseek-answer",
                ".msg-content",
                ".reply-content",
                "div[class*='message']",
                "div[class*='answer']",
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
                                    logger.info(f"Deepseek成功获取回答: {answer[:30]}...")
                                    return answer.strip()
                    except Exception as e:
                        logger.debug(f"Deepseek 检查选择器 {selector} 失败: {str(e)}")
                        continue
                
                # 检查是否正在加载
                try:
                    loading_elements = await self.page.query_selector_all(".loading, .typing, span:has-text('正在'), span:has-text('思考')")
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
                                                logger.info(f"Deepseek成功获取回答: {answer[:30]}...")
                                                return answer.strip()
                                    except:
                                        continue
                except:
                    pass
                
                await self.page.wait_for_timeout(wait_interval * 1000)
            
            logger.warning("Deepseek等待回答超时")
            return "未获取到回答"
            
        except Exception as e:
            logger.error(f"Deepseek获取回答失败：{str(e)}")
            return f"获取回答失败：{str(e)}"
    
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