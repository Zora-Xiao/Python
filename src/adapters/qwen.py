# -*- coding: utf-8 -*-
from typing import Optional
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
            logger.info(f"{self.platform_id} 开始登录...")

            login_button_selectors = [
                "button:has-text('登录')",
                "button:has-text('login')",
                "button:has-text('Sign In')",
                "a:has-text('登录')",
                "[data-testid='login']",
                ".login-btn",
                "[class*='login']",
                "[class*='signin']",
                "[class*='sign-in']"
            ]

            login_button = await self._find_visible_element(login_button_selectors)
            if not login_button:
                logger.warning(f"{self.platform_id} 登录按钮未找到")
                return False

            await login_button.click()
            await self.page.wait_for_timeout(2000)

            username_selectors = [
                "input[name='username']",
                "input[name='email']",
                "input[name='phone']",
                "input[type='text']"
            ]

            if not await self._fill_form_field(username_selectors, self.username):
                logger.warning(f"{self.platform_id} 用户名输入框未找到")
                return False

            password_selectors = [
                "input[name='password']",
                "input[type='password']"
            ]

            if not await self._fill_form_field(password_selectors, self.password):
                logger.warning(f"{self.platform_id} 密码输入框未找到")
                return False

            submit_selectors = [
                "button[type='submit']",
                "button:has-text('登录')",
                "button:has-text('login')",
                "button:has-text('confirm')",
                ".submit-btn",
                "[class*='btn-primary']",
                "[class*='btn-login']"
            ]

            if await self._click_button(submit_selectors):
                await self.page.wait_for_timeout(5000)
                
                current_url = self.page.url
                if "login" not in current_url.lower() and "signin" not in current_url.lower():
                    await self._save_cookies(self.page.context)
                    logger.info(f"{self.platform_id} 登录成功，当前URL: {current_url}")
                    return True
                else:
                    logger.warning(f"{self.platform_id} 登录后仍在登录页面，可能登录失败")
                    return False
            else:
                logger.warning(f"{self.platform_id} 提交按钮未找到")
                return False
        except Exception as e:
            logger.error(f"{self.platform_id} 登录失败：{str(e)}")
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
                "textarea",
                "textarea[placeholder*='ask']",
                "textarea[placeholder*='Message']",
                "textarea[placeholder*='Send']",
                "textarea[placeholder*='AI']",
                "input[type='text']",
                "div[contenteditable='true']",
                "[contenteditable='true']",
                "[role='textbox']",
                ".chat-input",
                ".composer-input",
                "[data-testid*='input']"
            ]

            input_elem = await self._find_visible_element(input_selectors)
            if not input_elem:
                raise Exception("输入框未找到")

            await input_elem.click()
            await self.page.wait_for_timeout(500)
            await input_elem.fill(question)
            await self.page.wait_for_timeout(500)
            await input_elem.press("Enter")

            logger.info(f"{self.platform_id} 成功发送消息：{question[:30]}...")

        except Exception as e:
            logger.error(f"{self.platform_id} 发送消息失败：{str(e)}")
            raise

    async def _get_answer(self, question: str = "") -> str:
        try:
            answer_selectors = [
                ".qwen-chat-package-comp-new-message-content",
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
                ".ant-list-item",
                ".chat-history-item",
                ".msg-content",
                ".reply-content",
                "[class*='message-content']",
                "[class*='answer']",
                "[class*='response']",
                "[class*='markdown']",
                "[class*='content']",
                ".qwen-message-content",
                "[class*='qwen-chat']",
                "[class*='conv-message']",
                "[class*='bot-message']"
            ]

            max_wait = 60
            last_answer = ""
            stable_count = 0
            stable_threshold = 3
            
            for _ in range(max_wait):
                current_text = ""
                for selector in answer_selectors:
                    try:
                        elems = await self.page.query_selector_all(selector)
                        if elems and len(elems) > 0:
                            last = elems[-1]
                            is_visible = await last.is_visible()
                            if is_visible:
                                text = await last.inner_text()
                                if text and len(text.strip()) > 5:
                                    if question and text.strip() == question:
                                        continue
                                    if question and text.strip().startswith(question[:20]):
                                        continue
                                    current_text = text.strip()
                                    break
                    except Exception as e:
                        logger.debug(f"获取回答 {selector} 失败：{str(e)}")
                        continue
                
                if current_text:
                    if current_text == last_answer:
                        stable_count += 1
                        if stable_count >= stable_threshold:
                            logger.info(f"千问成功获取回答：{current_text[:30]}...")
                            return current_text
                    else:
                        stable_count = 0
                        last_answer = current_text
                
                try:
                    loading_elements = await self.page.query_selector_all(".loading,.typing,[class*='loading'],[class*='typing']")
                    is_loading = any(await e.is_visible() for e in loading_elements) if loading_elements else False
                    if not is_loading and last_answer:
                        return last_answer
                except Exception as e:
                    pass

                await self.page.wait_for_timeout(1000)

            if last_answer:
                return last_answer
            
            logger.warning("千问等待回答超时")
            return "未找到回答"

        except Exception as e:
            logger.error(f"千问获取回答失败：{str(e)}")
            return f"获取回答失败：{str(e)}"
    
    async def _send_message_and_get_answer(self, question: str) -> str:
        """发送消息并等待回答完成（处理流式输出）"""
        try:
            await self._send_message(question)
            
            logger.info("千问等待AI回答中...")
            
            max_wait_time = 180
            check_interval = 1500
            waited_time = 0
            
            last_valid_answer = ""
            stable_count = 0
            stable_threshold = 5
            
            answer_selectors = [
                ".qwen-chat-package-comp-new-message-content",
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
                ".ant-list-item",
                ".chat-history-item",
                ".msg-content",
                ".reply-content",
                "[class*='message-content']",
                "[class*='answer']",
                "[class*='response']",
                "[class*='markdown']",
                "[class*='content']",
                ".qwen-message-content",
                "[class*='qwen-chat']",
                "[class*='conv-message']",
                "[class*='bot-message']"
            ]
            
            typing_indicators = [
                ".typing",
                "[class*='typing']",
                "[aria-label*='typing']",
                ".loading",
                "[class*='loading']",
                "span:has-text('typing')",
                "span:has-text('正在输入')",
                "span:has-text('正在思考')",
                "span:has-text('正在生成')",
                "span:has-text('AI正在思考')",
                "span:has-text('AI正在回答')",
                "span:has-text('正在撰写')",
                "div[class*='thinking']",
                "div[class*='spin']",
                "div[class*='dot']",
                "div[class*='pulse']",
                ".ant-spin",
                "[class*='animate']",
                "[class*='cursor']"
            ]
            
            while waited_time < max_wait_time:
                try:
                    is_typing = False
                    for selector in typing_indicators:
                        try:
                            elems = await self.page.query_selector_all(selector)
                            if elems:
                                for elem in elems:
                                    if await elem.is_visible():
                                        is_typing = True
                                        break
                                if is_typing:
                                    break
                        except:
                            continue
                    
                    current_text = ""
                    for selector in answer_selectors:
                        try:
                            elems = await self.page.query_selector_all(selector)
                            if elems and len(elems) > 0:
                                last = elems[-1]
                                is_visible = await last.is_visible()
                                if is_visible:
                                    text = await last.inner_text()
                                    if text and len(text.strip()) > 5:
                                        if text.strip() == question:
                                            continue
                                        if text.strip().startswith(question[:20]):
                                            continue
                                        current_text = text.strip()
                                        break
                        except Exception as e:
                            logger.debug(f"获取回答 {selector} 失败：{str(e)}")
                            continue
                    
                    if current_text:
                        if current_text == last_valid_answer:
                            stable_count += 1
                            if stable_count >= stable_threshold:
                                logger.info(f"千问回答已完成，内容长度: {len(current_text)}")
                                return current_text
                        else:
                            stable_count = 0
                            last_valid_answer = current_text
                    
                    if is_typing:
                        logger.debug(f"千问AI正在回答中，已等待 {waited_time:.1f} 秒")
                    elif last_valid_answer:
                        if stable_count >= stable_threshold:
                            logger.info(f"千问回答已完成，内容长度: {len(last_valid_answer)}")
                            return last_valid_answer
                    
                    await self.page.wait_for_timeout(check_interval)
                    waited_time += check_interval / 1000
                    
                except Exception as e:
                    logger.debug(f"千问等待回答时出错: {str(e)}")
                    await self.page.wait_for_timeout(check_interval)
                    waited_time += check_interval / 1000
            
            if last_valid_answer:
                logger.info(f"千问等待超时，但获取到部分回答，长度: {len(last_valid_answer)}")
                return last_valid_answer
            
            logger.warning(f"千问等待回答超时（{max_wait_time}秒），尝试获取当前内容")
            return await self._get_answer(question)
            
        except Exception as e:
            logger.error(f"千问发送消息并获取回答失败: {str(e)}")
            raise

    async def _check_login_url_pattern(self, url: str) -> bool:
        url_lower = url.lower()
        if "login" in url_lower or "signin" in url_lower or "auth" in url_lower:
            return False
        return None
    
    async def _check_login_status(self) -> bool:
        try:
            await self.page.wait_for_timeout(2000)
            
            logged_in_indicators = [
                ".user-avatar",
                ".avatar",
                "[class*='avatar']",
                "[data-testid*='avatar']",
                "button:has-text('退出')",
                "button:has-text('Logout')",
                "a:has-text('退出')",
                "a:has-text('Logout')",
                "[class*='user-info']",
                "[class*='user-profile']",
                "[class*='logout']",
                "[class*='header-user']",
                "[class*='nickname']",
                "[class*='user-name']"
            ]
            
            for selector in logged_in_indicators:
                try:
                    elems = await self.page.query_selector_all(selector)
                    if elems:
                        for elem in elems:
                            if await elem.is_visible():
                                logger.info(f"{self.platform_id}已登录，找到元素: {selector}")
                                return True
                except Exception as e:
                    logger.debug(f"{self.platform_id}检查选择器 {selector} 失败: {str(e)}")
                    continue
            
            login_indicators = [
                "button:has-text('登录')",
                "a:has-text('登录')",
                "[class*='login']",
                "[placeholder*='用户名']",
                "[placeholder*='密码']",
                "input[type='password']",
                "[class*='sign-in']",
                "[class*='signin']"
            ]
            
            for selector in login_indicators:
                try:
                    elems = await self.page.query_selector_all(selector)
                    if elems:
                        for elem in elems:
                            if await elem.is_visible():
                                logger.info(f"{self.platform_id}未登录，检测到登录元素: {selector}")
                                return False
                except Exception as e:
                    logger.debug(f"{self.platform_id}检查登录选择器 {selector} 失败: {str(e)}")
                    continue
            
            logger.info(f"{self.platform_id}未找到明确的登录/登出指示元素")
            return False
            
        except Exception as e:
            logger.error(f"{self.platform_id}检查登录状态失败: {str(e)}")
            return False

    async def screenshot(self, question: Question) -> tuple[Optional[str], bool, Optional[str], Optional[str]]:
        if self.page is None:
            return None, False, None, None

        try:
            from src.utils.screenshot import ScreenshotTool
            screenshot_tool = ScreenshotTool()

            logger.info(f"{self.platform_id} 等待AI响应...")
            await self.page.wait_for_timeout(3000)

            share_link = None
            share_link_error = None

            logger.info(f"{self.platform_id} 步骤1：查找分享按钮...")
            share_button_selectors = [
                ".qwen-chat-package-comp-new-action-control-container-share",
                "[class*='share']",
                "button[class*='share']",
                "[data-testid*='share']"
            ]

            share_button = await self._find_visible_element(share_button_selectors)

            if share_button:
                await share_button.click()
                await self.page.wait_for_timeout(2000)
                logger.info(f"{self.platform_id} 点击分享按钮")

                logger.info(f"{self.platform_id} 步骤2：查找复制链接按钮...")
                copy_link_selectors = [
                    "button:has-text('复制链接')",
                    "button:has-text('copy link')",
                    "button:has-text('copy')",
                    "[class*='copy-link']",
                    "[data-testid*='copy-link']"
                ]

                copy_link_button = await self._find_visible_element(copy_link_selectors)

                if copy_link_button:
                    await copy_link_button.click()
                    await self.page.wait_for_timeout(1000)
                    logger.info(f"{self.platform_id} 点击复制链接按钮")
                    logger.info(f"{self.platform_id} 链接已复制到剪贴板")
                else:
                    share_link_error = "未找到复制链接按钮"
            else:
                share_link_error = "分享按钮未找到"
                logger.warning(f"{self.platform_id} 分享按钮未找到")

            logger.info(f"{self.platform_id} 步骤3：执行截图...")
            screenshot_path, is_shared_image, share_link, share_err = await screenshot_tool.capture_from_page(
                self.page,
                self.platform_id,
                question
            )
            if share_err and not share_link_error:
                share_link_error = share_err

            return screenshot_path, is_shared_image, share_link, share_link_error

        except Exception as e:
            logger.error(f"{self.platform_id} 截图失败：{str(e)}")
            return await self._default_screenshot(question)

    async def _default_screenshot(self, question: Question) -> tuple[Optional[str], bool, Optional[str], Optional[str]]:
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
            logger.error(f"{self.platform_id} 默认截图失败：{str(e)}")
            return None, False, None, str(e)

    async def close(self):
        await super().close()
