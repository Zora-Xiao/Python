# -*- coding: utf-8 -*-
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
                "button:has-text('login')",
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
                logger.warning("千问登录按钮未找到")
                return False

            await self.page.click(login_button)
            await self.page.wait_for_timeout(2000)

            username_selectors = [
                "input[name='username']",
                "input[name='email']",
                "input[name='phone']",
                "input[type='text']"
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
                logger.warning("千问用户名输入框未找到")
                return False

            password_selectors = [
                "input[name='password']",
                "input[type='password']"
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
                logger.warning("千问密码输入框未找到")
                return False

            submit_selectors = [
                "button[type='submit']",
                "button:has-text('login')",
                "button:has-text('confirm')",
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
                logger.warning("千问提交按钮未找到")

            return True
        except Exception as e:
            logger.error(f"千问登录失败：{str(e)}")
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

            input_selector = None
            for selector in input_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=10000)
                    input_selector = selector
                    break
                except:
                    continue

            if not input_selector:
                raise Exception("输入框未找到")

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
                ".ant-list-item",
                ".chat-history-item",
                ".msg-content",
                ".reply-content"
            ]

            max_wait = 60
            for _ in range(max_wait):
                for selector in answer_selectors:
                    try:
                        elems = await self.page.query_selector_all(selector)
                        if elems and len(elems) > 0:
                            last = elems[-1]
                            is_visible = await last.is_visible()
                            if is_visible:
                                text = await last.inner_text()
                                if text and len(text.strip()) > 10:
                                    logger.info(f"千问成功获取回答：{text[:30]}...")
                                    return text.strip()
                    except Exception as e:
                        logger.debug(f"获取回答 {selector} 失败：{str(e)}")
                        continue
                try:
                    loading_elements = await self.page.query_selector_all(".loading,.typing")
                    is_loading = any(await e.is_visible() for e in loading_elements) if loading_elements else False
                    if not is_loading:
                        textarea = await self.page.query_selector("textarea")
                        if textarea:
                            is_disabled = await textarea.get_attribute("disabled")
                            if is_disabled is None:
                                for selector in answer_selectors:
                                    try:
                                        answer_elements = await self.page.query_selector_all(selector)
                                        if answer_elements and len(answer_elements) > 0:
                                            last_answer = answer_elements[-1]
                                            answer = await last_answer.inner_text()
                                            if answer and len(answer.strip()) > 10:
                                                logger.info(f"千问成功获取回答：{answer[:30]}...")
                                                return answer.strip()
                                    except Exception as e:
                                        continue
                except Exception as e:
                    pass

                await self.page.wait_for_timeout(1000)

            logger.warning("千问等待回答超时")
            return "未找到回答"

        except Exception as e:
            logger.error(f"千问获取回答失败：{str(e)}")
            return f"获取回答失败：{str(e)}"

    async def screenshot(self, question: Question, answer: str) -> tuple[Optional[str], bool, Optional[str]]:
        if self.page is None:
            return None, False, None

        try:
            from src.utils.screenshot import ScreenshotTool
            screenshot_tool = ScreenshotTool()

            logger.info("千问等待AI响应...")
            await self.page.wait_for_timeout(3000)

            logger.info("千问步骤1：全屏截图...")
            screenshot_path, is_shared_image, share_link = await screenshot_tool.capture_from_page(
                self.page,
                self.platform_id,
                question
            )

            logger.info("千问步骤2：查找分享按钮...")
            share_button_selectors = [
                ".qwen-chat-package-comp-new-action-control-container-share",
                "[class*='share']",
                "button[class*='share']",
                "[data-testid*='share']"
            ]

            share_button = None
            for selector in share_button_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    if elements:
                        for elem in elements:
                            if await elem.is_visible():
                                share_button = elem
                                logger.info(f"千问找到分享按钮：{selector}")
                                break
                        if share_button:
                            break
                except Exception as e:
                    logger.debug(f"千问检查分享按钮选择器 {selector} 失败：{str(e)}")
                    continue

            if share_button:
                await share_button.click()
                await self.page.wait_for_timeout(2000)
                logger.info("千问点击分享按钮")

                logger.info("千问步骤3：查找复制链接按钮...")
                copy_link_selectors = [
                    "button:has-text('复制链接')",
                    "button:has-text('copy link')",
                    "button:has-text('copy')",
                    "[class*='copy-link']",
                    "[data-testid*='copy-link']"
                ]

                copy_link_button = None
                for selector in copy_link_selectors:
                    try:
                        elements = await self.page.query_selector_all(selector)
                        if elements:
                            for elem in elements:
                                if await elem.is_visible():
                                    copy_link_button = elem
                                    logger.info(f"千问找到复制链接按钮：{selector}")
                                    break
                            if copy_link_button:
                                break
                    except Exception as e:
                        logger.debug(f"千问检查复制链接按钮选择器 {selector} 失败：{str(e)}")
                        continue

                if copy_link_button:
                    await copy_link_button.click()
                    await self.page.wait_for_timeout(1000)
                    logger.info("千问点击复制链接按钮")
                    share_link = None
                    logger.info("千问链接已复制到剪贴板")
            else:
                logger.warning("千问分享按钮未找到，仅使用全屏截图")

            return screenshot_path, is_shared_image, share_link

        except Exception as e:
            logger.error(f"千问截图失败：{str(e)}")
            return await self._default_screenshot(question, answer)

    async def _default_screenshot(self, question: Question, answer: str) -> tuple[Optional[str], bool, Optional[str]]:
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
            logger.error(f"千问默认截图失败：{str(e)}")
            return None, False, None

    async def close(self):
        await super().close()
