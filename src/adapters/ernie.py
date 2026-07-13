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
        try:
            logger.info(f"{self.platform_id} 开始登录...")

            login_button_selectors = [
                "button:has-text('login')",
                "button:has-text('Sign In')",
                "[data-testid='login']",
                ".login-btn",
                "a:has-text('login')",
                "[class*='login']"
            ]

            login_button = await self._find_visible_element(login_button_selectors)
            if not login_button:
                logger.warning(f"{self.platform_id} 登录按钮未找到")
                return False

            await login_button.click()
            await self.page.wait_for_timeout(3000)
            logger.info(f"{self.platform_id} 点击登录按钮")

            username_selectors = [
                "input[name='username']",
                "input[name='email']",
                "input[name='phone']",
                "input[type='text']"
            ]

            username_elem = await self._find_visible_element(username_selectors)
            if not username_elem:
                logger.warning(f"{self.platform_id} 用户名输入框未找到")
                return False

            await username_elem.fill(self.username)
            await self.page.wait_for_timeout(500)

            password_selectors = [
                "input[name='password']",
                "input[type='password']"
            ]

            password_elem = await self._find_visible_element(password_selectors)
            if not password_elem:
                logger.warning(f"{self.platform_id} 密码输入框未找到")
                return False

            await password_elem.fill(self.password)
            await self.page.wait_for_timeout(500)

            submit_selectors = [
                "button[type='submit']",
                "button:has-text('login')",
                "button:has-text('submit')",
                ".submit-btn"
            ]

            submit_elem = await self._find_visible_element(submit_selectors)
            if submit_elem:
                await submit_elem.click()
                await self.page.wait_for_timeout(5000)
                logger.info(f"{self.platform_id} 登录成功")
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
            await input_elem.press("Enter")

            logger.info(f"{self.platform_id} 发送消息：{question[:30]}...")

        except Exception as e:
            logger.error(f"{self.platform_id} 发送消息失败：{str(e)}")
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
                                    logger.info(f"{self.platform_id} 成功获取回答：{text[:30]}...")
                                    return text.strip()
                    except Exception as e:
                        continue
                await self.page.wait_for_timeout(1000)

            logger.warning(f"{self.platform_id} 等待回答超时")
            return "未找到回答"

        except Exception as e:
            logger.error(f"{self.platform_id} 获取回答失败：{str(e)}")
            return f"获取回答失败：{str(e)}"

    async def screenshot(self, question: Question, answer: str) -> tuple[Optional[str], bool, Optional[str]]:
        if self.page is None:
            return None, False, None

        try:
            from src.utils.screenshot import ScreenshotTool
            screenshot_tool = ScreenshotTool()

            logger.info(f"{self.platform_id} 等待AI响应...")
            await self.page.wait_for_timeout(3000)

            logger.info(f"{self.platform_id} 步骤1：查找分享按钮...")
            share_button_selectors = [
                "div[class*='share']",
                "button[class*='share']",
                "svg[class*='share']",
                "[class*='share-btn']",
                "[class*='share-button']",
                "[data-testid*='share']",
                ".share-icon",
                "button:has(svg[class*='share'])"
            ]

            share_button = await self._find_visible_element(share_button_selectors)
            if not share_button:
                logger.warning(f"{self.platform_id} 分享按钮未找到，使用默认截图")
                return await self._default_screenshot(question)

            await share_button.click()
            await self.page.wait_for_timeout(2000)
            logger.info(f"{self.platform_id} 点击分享按钮")

            logger.info(f"{self.platform_id} 步骤2：查找生成图片按钮...")
            generate_selectors = [
                "button:has-text('generate image')",
                "button:has-text('generate')",
                "[class*='generate']",
                "[class*='image']",
                "[data-testid*='generate']"
            ]

            generate_button = await self._find_visible_element(generate_selectors)
            if not generate_button:
                logger.warning(f"{self.platform_id} 未找到生成图片按钮，使用默认截图")
                return await self._default_screenshot(question)

            await generate_button.click()
            await self.page.wait_for_timeout(3000)
            logger.info(f"{self.platform_id} 点击生成图片按钮")

            logger.info(f"{self.platform_id} 步骤3：查找保存图片按钮...")
            save_selectors = [
                "button:has-text('save image')",
                "button:has-text('save')",
                "[class*='save']",
                "[download]",
                "[data-testid*='save']"
            ]

            save_button = await self._find_visible_element(save_selectors)
            if save_button:
                await save_button.click()
                await self.page.wait_for_timeout(2000)
                logger.info(f"{self.platform_id} 点击保存图片按钮")
            else:
                logger.warning(f"{self.platform_id} 保存按钮未找到，继续使用默认截图")

            screenshot_path, is_shared_image, share_link = await screenshot_tool.capture_from_page(
                self.page, 
                self.platform_id, 
                question
            )

            return screenshot_path, is_shared_image, share_link

        except Exception as e:
            logger.error(f"{self.platform_id} 截图失败：{str(e)}")
            return await self._default_screenshot(question)

    async def _default_screenshot(self, question: Question) -> tuple[Optional[str], bool, Optional[str]]:
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
            logger.error(f"{self.platform_id} 默认截图失败：{str(e)}")
            return None, False, None

    async def close(self):
        await super().close()
