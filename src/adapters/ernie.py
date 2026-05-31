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

            login_button = None
            for selector in login_button_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    if elements:
                        for elem in elements:
                            is_visible = await elem.is_visible()
                            if is_visible:
                                login_button = elem
                                logger.info(f"{self.platform_id} 找到登录按钮：{selector}")
                                break
                        if login_button:
                            break
                except:
                    continue

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
                logger.warning(f"{self.platform_id} 用户名输入框未找到")
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
                logger.warning(f"{self.platform_id} 密码输入框未找到")
                return False

            submit_selectors = [
                "button[type='submit']",
                "button:has-text('login')",
                "button:has-text('submit')",
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

            share_button = None
            for selector in share_button_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    if elements:
                        for elem in elements:
                            if await elem.is_visible():
                                share_button = elem
                                logger.info(f"{self.platform_id} 找到分享按钮：{selector}")
                                break
                        if share_button:
                            break
                except Exception as e:
                    logger.debug(f"{self.platform_id} 检查分享按钮选择器 {selector} 失败：{str(e)}")
                    continue

            if not share_button:
                logger.warning(f"{self.platform_id} 分享按钮未找到，使用默认截图")
                return await self._default_screenshot(question, answer)

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

            generate_button = None
            for selector in generate_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    if elements:
                        for elem in elements:
                            if await elem.is_visible():
                                generate_button = elem
                                logger.info(f"{self.platform_id} 找到生成图片按钮：{selector}")
                                break
                        if generate_button:
                            break
                except Exception as e:
                    logger.debug(f"{self.platform_id} 检查生成按钮选择器 {selector} 失败：{str(e)}")
                    continue

            if not generate_button:
                logger.warning(f"{self.platform_id} 生成图片按钮未找到，使用默认截图")
                return await self._default_screenshot(question, answer)

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

            save_button = None
            for selector in save_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    if elements:
                        for elem in elements:
                            if await elem.is_visible():
                                save_button = elem
                                logger.info(f"{self.platform_id} 找到保存按钮：{selector}")
                                break
                        if save_button:
                            break
                except Exception as e:
                    logger.debug(f"{self.platform_id} 检查保存按钮选择器 {selector} 失败：{str(e)}")
                    continue

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
            logger.error(f"{self.platform_id} 默认截图失败：{str(e)}")
            return None, False, None

    async def close(self):
        await super().close()
