# -*- coding: utf-8 -*-
from typing import Optional
from src.adapters.base import BaseAdapter
from src.models.question import Question
from src.utils.logger import logger
from playwright.async_api import Page


class DoubaoAdapter(BaseAdapter):
    def __init__(self, config: dict):
        super().__init__(config)
        self.platform_id = "doubao"
        self.platform_url = config.get("web_url", "https://www.doubao.com/chat/")

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
                logger.warning("豆包登录按钮未找到")
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
                logger.warning("豆包用户名输入框未找到")
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
                logger.warning("豆包密码输入框未找到")
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
                logger.info("豆包登录表单已提交")
            else:
                logger.warning("豆包提交按钮未找到")

            return True
        except Exception as e:
            logger.error(f"豆包登录失败：{str(e)}")
            return False

    async def _navigate_to_chat(self) -> bool:
        try:
            await self.page.goto(self.platform_url, wait_until="domcontentloaded", timeout=60000)
            await self.page.wait_for_timeout(3000)
            return True
        except Exception as e:
            logger.error(f"豆包导航失败：{str(e)}")
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

            logger.info(f"豆包发送消息：{question[:30]}...")

        except Exception as e:
            logger.error(f"豆包发送消息失败：{str(e)}")
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
                ".content"
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
                                    logger.info(f"豆包成功获取回答：{text[:30]}...")
                                    return text.strip()
                    except Exception as e:
                        continue
                await self.page.wait_for_timeout(1000)

            logger.warning("豆包等待回答超时")
            return "未找到回答"

        except Exception as e:
            logger.error(f"豆包获取回答失败：{str(e)}")
            return "获取回答失败"

    async def screenshot(self, question: Question, answer: str) -> tuple[Optional[str], bool, Optional[str]]:
        if self.page is None:
            return None, False, None

        try:
            from src.utils.screenshot import ScreenshotTool
            screenshot_tool = ScreenshotTool()

            logger.info("豆包等待AI响应...")
            await self.page.wait_for_timeout(3000)

            logger.info("豆包步骤1：查找分享按钮...")
            share_button_selectors = [
                "[data-dbx-name='button']",
                "[data-state='closed']",
                "div[class*='share']",
                "button[class*='share']",
                "svg[class*='share']",
                "[class*='share-btn']",
                "[class*='share-button']",
                "[data-testid*='share']",
                ".share-icon",
                "button:has(svg[class*='share'])"
            ]

            share_button = None
            for selector in share_button_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    if elements:
                        for elem in elements:
                            if await elem.is_visible():
                                share_button = elem
                                logger.info(f"豆包找到分享按钮：{selector}")
                                break
                        if share_button:
                            break
                except Exception as e:
                    logger.debug(f"豆包检查分享按钮选择器 {selector} 失败：{str(e)}")
                    continue

            if not share_button:
                logger.warning("豆包分享按钮未找到，使用默认截图")
                return await self._default_screenshot(question, answer)

            await share_button.click()
            await self.page.wait_for_timeout(2000)
            logger.info("豆包点击分享按钮")

            logger.info("豆包步骤2：查找分享图片按钮（透明背景按钮）...")
            share_image_selectors = [
                "button:has-text('share image')",
                "button:has-text('分享图片')",
                "button:has-text('image')",
                "button[class*='transparent']",
                "button[class*='ghost']",
                "[class*='image']"
            ]

            share_image_button = None
            for selector in share_image_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    if elements:
                        for elem in elements:
                            if await elem.is_visible():
                                share_image_button = elem
                                logger.info(f"豆包找到分享图片按钮：{selector}")
                                break
                        if share_image_button:
                            break
                except Exception as e:
                    logger.debug(f"豆包检查分享图片按钮选择器 {selector} 失败：{str(e)}")
                    continue

            if not share_image_button:
                logger.warning("豆包分享图片按钮未找到，使用默认截图")
                return await self._default_screenshot(question, answer)

            await share_image_button.click()
            await self.page.wait_for_timeout(2000)
            logger.info("豆包点击分享图片按钮")

            logger.info("豆包步骤3：查找下载按钮（高亮背景按钮）...")
            download_selectors = [
                "button:has-text('download')",
                "button:has-text('下载')",
                "button[class*='highlight']",
                "button[class*='primary']",
                "button[class*='download']",
                "button[class*='save']",
                "[class*='download']",
                "[class*='save']",
                "[download]"
            ]

            download_button = None
            for selector in download_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    if elements:
                        for elem in elements:
                            if await elem.is_visible():
                                download_button = elem
                                logger.info(f"豆包找到下载按钮：{selector}")
                                break
                        if download_button:
                            break
                except Exception as e:
                    logger.debug(f"豆包检查下载按钮选择器 {selector} 失败：{str(e)}")
                    continue

            if download_button:
                await download_button.click()
                await self.page.wait_for_timeout(2000)
                logger.info("豆包点击下载按钮")
            else:
                logger.warning("豆包下载按钮未找到，继续使用默认截图")

            screenshot_path, is_shared_image, share_link = await screenshot_tool.capture_from_page(
                self.page,
                self.platform_id,
                question
            )

            return screenshot_path, is_shared_image, share_link

        except Exception as e:
            logger.error(f"豆包截图失败：{str(e)}")
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
            logger.error(f"豆包默认截图失败：{str(e)}")
            return None, False, None

    async def close(self):
        await super().close()
