# -*- coding: utf-8 -*-
from typing import Optional
from src.adapters.base import BaseAdapter
from src.models.question import Question
from src.utils.logger import logger


class ErnieAdapter(BaseAdapter):
    def __init__(self, config: dict):
        super().__init__(config)
        self.platform_id = "ernie"
        self.platform_url = config.get("web_url", "https://yiyan.baidu.com/")

    async def _find_visible_element(self, selectors: list) -> Optional[object]:
        """
        辅助方法：查找第一个可见的元素
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

    async def _execute_login(self) -> bool:
        logger.info(f"{self.name} 不支持自动登录，请手动登录")
        return False

    async def _navigate_to_chat(self) -> bool:
        try:
            await self.page.goto(self.platform_url, wait_until="domcontentloaded", timeout=60000)
            await self.page.wait_for_timeout(3000)
            return True
        except Exception as e:
            logger.error(f"{self.platform_id} 导航失败：{str(e)}")
            return False

    async def _send_message(self, question: str) -> None:
        try:
            input_selectors = [
                "textarea",
                "textarea[placeholder*='ask']",
                "textarea[placeholder*='Message']",
                "textarea[placeholder*='Send']",
                "input[type='text']",
                "div[contenteditable='true']",
                "[role='textbox']"
            ]

            input_elem = await self._find_visible_element(input_selectors)
            if not input_elem:
                raise Exception("输入框未找到")

            await input_elem.click()
            await self.page.wait_for_timeout(500)
            
            await input_elem.fill(question)
            await self.page.wait_for_timeout(500)
            
            await self.page.keyboard.press("Enter")
            await self.page.wait_for_timeout(1000)
            
            try:
                send_selectors = [
                    "button:has-text('发送')",
                    "button:has-text('Send')",
                    ".send-btn",
                    "[class*='send']",
                    "button[type='submit']"
                ]
                for sel in send_selectors:
                    try:
                        send_btn = await self.page.query_selector(sel)
                        if send_btn and await send_btn.is_visible():
                            await send_btn.click()
                            logger.info(f"{self.platform_id} 点击发送按钮: {sel}")
                            break
                    except:
                        continue
            except Exception as e:
                logger.debug(f"{self.platform_id} 查找发送按钮失败: {str(e)}")

            logger.info(f"{self.platform_id} 发送消息：{question[:30]}...")

        except Exception as e:
            logger.error(f"{self.platform_id} 发送消息失败：{str(e)}")
            raise

    async def _get_answer(self) -> str:
        try:
            answer_selectors = [
                ".response-content",
                ".msg-content",
                ".markdown-body",
                ".content-body",
                "[class*='response']",
                "[class*='message-content']",
                "[class*='answer']",
                ".ant-list-item",
                ".chat-item",
                ".assistant-message",
                ".message-content",
                ".answer-content",
                ".chat-message",
                "[role='listitem']",
                ".message-body",
                ".prose",
                ".content",
                "div[class*='markdown']",
                "div[class*='rich-text']",
                "div[class*='reply']",
                ".yiyan-answer",
                ".baidu-chat-answer",
                "[data-testid*='answer']",
                "[data-testid*='message']"
            ]

            max_wait = 60
            last_answer = ""
            stable_count = 0
            stable_threshold = 3
            
            for i in range(max_wait):
                current_text = ""
                for selector in answer_selectors:
                    try:
                        elems = await self.page.query_selector_all(selector)
                        if elems and len(elems) > 0:
                            last = elems[-1]
                            is_visible = await last.is_visible()
                            if is_visible:
                                text = await last.inner_text()
                                if text and len(text.strip()) > 10:
                                    current_text = text.strip()
                                    break
                    except Exception as e:
                        logger.debug(f"{self.platform_id} 获取回答 {selector} 失败：{str(e)}")
                        continue
                
                if current_text:
                    if current_text == last_answer:
                        stable_count += 1
                        if stable_count >= stable_threshold:
                            logger.info(f"{self.platform_id} 成功获取回答：{current_text[:30]}...")
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

            logger.warning(f"{self.platform_id} 等待回答超时")
            return "未找到回答"

        except Exception as e:
            logger.error(f"{self.platform_id} 获取回答失败：{str(e)}")
            return f"获取回答失败：{str(e)}"

    async def _check_login_status(self) -> Optional[bool]:
        try:
            await self.page.wait_for_timeout(3000)
            
            page_content = await self.page.content()
            
            import re
            json_match = re.search(r'<script type="application/json" name="aiTabFrameBaseData">(.*?)</script>', page_content, re.DOTALL)
            if json_match:
                try:
                    import json
                    data = json.loads(json_match.group(1))
                    user_info = data.get("userInfo", {})
                    is_user_login = user_info.get("isUserLogin", 0)
                    
                    if is_user_login == 1:
                        logger.info(f"{self.platform_id}已登录，isUserLogin={is_user_login}")
                        return True
                    else:
                        logger.info(f"{self.platform_id}未登录，isUserLogin={is_user_login}")
                        return False
                except json.JSONDecodeError as e:
                    logger.debug(f"{self.platform_id}解析aiTabFrameBaseData失败: {str(e)}")
            
            login_indicators = [
                "button:has-text('登录')",
                "a:has-text('登录')",
                "[class*='login']",
                "[placeholder*='用户名']",
                "[placeholder*='密码']",
                "input[type='password']",
                "[class*='sign-in']",
                "[class*='signin']",
                ".passport-login-btn",
                "[class*='passport']",
                "div[class*='login-modal']",
                "div[class*='login-overlay']"
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
            
            logged_in_indicators = [
                "button:has-text('退出')",
                "a:has-text('退出')",
                "[class*='logout']",
                ".user-avatar",
                "[class*='user-info']",
                "[class*='user-profile']",
                "[class*='header-user']",
                "[class*='nickname']",
                "[class*='user-name']",
                ".baidu-avatar",
                "[class*='head-img']",
                "[data-testid*='avatar']",
                ".avatar"
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
            
            logger.info(f"{self.platform_id}未找到明确的登录/登出指示元素，尝试检查聊天页面特征")
            
            chat_page_indicators = [
                "textarea[placeholder*='提问']",
                "textarea[placeholder*='聊天']",
                ".chat-container",
                ".message-list",
                ".conversation-list",
                "[class*='chat-history']",
                "[class*='message-container']"
            ]
            
            for selector in chat_page_indicators:
                try:
                    elems = await self.page.query_selector_all(selector)
                    if elems:
                        for elem in elems:
                            if await elem.is_visible():
                                logger.info(f"{self.platform_id}找到聊天页面特征元素: {selector}，判定已登录")
                                return True
                except Exception as e:
                    logger.debug(f"{self.platform_id}检查聊天页面选择器 {selector} 失败: {str(e)}")
                    continue
            
            logger.info(f"{self.platform_id}未找到明确的登录状态指示，判定为未登录")
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

            screenshot_path, is_shared_image, share_link, share_link_error = await screenshot_tool.capture_from_page(
                self.page, 
                self.platform_id, 
                question
            )

            return screenshot_path, is_shared_image, share_link, share_link_error

        except Exception as e:
            logger.error(f"{self.platform_id} 截图失败：{str(e)}")
            return None, False, None, str(e)

    async def close(self):
        await super().close()
