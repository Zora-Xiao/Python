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
                logger.warning("豆包未找到登录按钮")
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
                logger.warning("豆包未找到用户名输入框")
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
                logger.warning("豆包未找到密码输入框")
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
                logger.info("豆包登录表单已提交")
            else:
                logger.warning("豆包未找到提交按钮")

            return True
        except Exception as e:
            logger.error(f"豆包自动登录失败：{str(e)}")
            return False

    async def _navigate_to_chat(self) -> bool:
        try:
            logger.info(f"豆包正在导航到: {self.platform_url}")

            current_url = self.page.url
            if current_url == self.platform_url:
                logger.info("豆包已在聊天页面，强制刷新...")
                await self.page.goto("https://www.doubao.com/", wait_until="domcontentloaded", timeout=60000)
                await self.page.wait_for_timeout(1000)

            await self.page.goto(self.platform_url, wait_until="domcontentloaded", timeout=60000)
            await self.page.wait_for_timeout(5000)
            logger.info("豆包导航成功")
            return True
        except Exception as e:
            logger.error(f"豆包导航失败：{str(e)}")
            return False

    async def _send_message(self, question: str) -> None:
        try:
            input_selectors = [
                "textarea",
                "textarea[placeholder]",
                "textarea[placeholder*='输入']",
                "textarea[placeholder*='提问']",
                "textarea[placeholder*='Message']",
                "textarea[placeholder*='ask']",
                "textarea[placeholder*='Send']",
                "textarea[placeholder*='AI']",
                "input[type='text']",
                "input[placeholder*='输入']",
                "input[placeholder*='提问']",
                "input[placeholder*='Message']",
                "div[contenteditable='true']",
                "[contenteditable='true']",
                "[role='textbox']",
                ".chat-input",
                ".input-box",
                ".composer-input",
                "#chat-input",
                "#composer-input"
            ]

            input_selector = None
            for selector in input_selectors:
                try:
                    logger.info(f"豆包尝试选择器: {selector}")
                    await self.page.wait_for_selector(selector, timeout=5000)
                    input_selector = selector
                    logger.info(f"豆包找到输入框: {selector}")
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

            logger.info(f"豆包成功发送消息：{question[:30]}...")

        except Exception as e:
            logger.error(f"豆包发送消息失败：{str(e)}")
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
            logger.error(f"豆包获取回答失败：{str(e)}")
            return "获取回答失败"

    async def screenshot(self, question: Question, answer: str) -> Optional[str]:
        if self.page is None:
            return None

        try:
            from src.utils.screenshot import ScreenshotTool
            screenshot_tool = ScreenshotTool()

            await self.page.wait_for_timeout(1000)
            screenshot_path = await screenshot_tool.capture_from_page(
                self.page,
                self.platform_id,
                question
            )
            return screenshot_path

        except Exception as e:
            logger.error(f"豆包截图失败：{str(e)}")
            return None

    async def close(self):
        await super().close()
