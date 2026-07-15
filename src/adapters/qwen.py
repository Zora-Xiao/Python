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
                "button:has-text('login')",
                "button:has-text('Sign In')",
                "[data-testid='login']",
                ".login-btn"
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
                "button:has-text('login')",
                "button:has-text('confirm')",
                ".submit-btn"
            ]

            if await self._click_button(submit_selectors):
                await self.page.wait_for_timeout(5000)
                logger.info(f"{self.platform_id} 登录表单已提交")
            else:
                logger.warning(f"{self.platform_id} 提交按钮未找到")

            return True
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

    async def _get_answer(self) -> str:
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
                "[class*='response']"
            ]

            max_wait = 60
            last_answer = ""
            stable_count = 0
            stable_threshold = 3
            question_text = "你好，请介绍一下你自己"
            
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
                                if text and len(text.strip()) > 10:
                                    if text.strip() == question_text:
                                        continue
                                    if text.strip().startswith(question_text):
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

            logger.warning("千问等待回答超时")
            return "未找到回答"

        except Exception as e:
            logger.error(f"千问获取回答失败：{str(e)}")
            return f"获取回答失败：{str(e)}"

    async def _check_login_url_pattern(self, url: str) -> bool:
        url_lower = url.lower()
        if "login" in url_lower or "signin" in url_lower:
            return False
        elif "chat" in url_lower or "qwen" in url_lower:
            return True
        return None

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
