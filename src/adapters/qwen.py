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
            logger.info("千问等待AI响应...")
            await self.page.wait_for_timeout(5000)

            share_link = None
            default_screenshot_path = None

            logger.info("千问步骤1：悬停到消息上等待分享按钮...")

            message_selectors = [
                ".message-content",
                ".qwen-message-content",
                "[class*='message']",
                ".chat-message",
                ".assistant-message"
            ]
            last_message = None
            for sel in message_selectors:
                try:
                    elems = await self.page.query_selector_all(sel)
                    if elems and len(elems) > 0:
                        last_message = elems[-1]
                        logger.info(f"千问找到消息元素：{sel}")
                        break
                except:
                    continue

            if last_message:
                logger.info("千问悬停到最后一条消息...")
                await last_message.hover()
                await self.page.wait_for_timeout(3000)

            logger.info("千问步骤2：查找分享按钮...")
            share_button = None
            max_wait = 10

            message_area_box = None
            try:
                message_container = await self.page.query_selector("[class*='message'], .qwen-message, [class*='chat']")
                if message_container:
                    message_area_box = await message_container.bounding_box()
                    logger.info(f"千问消息区域: {message_area_box}")
            except Exception as e:
                logger.debug(f"千问查找消息区域失败: {str(e)}")

            share_button_selectors = [
                ".qwen-chat-package-comp-new-action-control-container-share",
                "[class*='share']",
                "button[class*='share']",
                "[data-testid*='share']",
                "div[role='button'][tabindex='0']",
                "button:has-text('share')"
            ]

            for i in range(max_wait):
                for selector in share_button_selectors:
                    try:
                        elements = await self.page.query_selector_all(selector)
                        if elements:
                            for elem in elements:
                                if await elem.is_visible():
                                    class_name = await elem.get_attribute("class") or ""
                                    text = await elem.inner_text() or ""
                                    bounding_box = await elem.bounding_box()

                                    if bounding_box and message_area_box:
                                        if bounding_box['x'] >= message_area_box['x']:
                                            share_button = elem
                                            logger.info(f"千问找到分享按钮: {selector}, 位置: {bounding_box}")
                                            break
                                    elif "share" in class_name.lower() or "share" in text.lower():
                                        share_button = elem
                                        logger.info(f"千问找到分享按钮: {selector}, 文本: {text}")
                                        break
                            if share_button:
                                break
                    except Exception as e:
                        logger.debug(f"千问检查分享按钮 {selector} 失败: {str(e)}")
                        continue
                if share_button:
                    break

                if not share_button and i < max_wait - 1:
                    logger.debug(f"千问等待分享按钮出现第{i+1}次...")
                    await self.page.wait_for_timeout(1000)

            if not share_button:
                logger.warning("千问分享按钮未找到，使用默认截图")
                return await self._default_screenshot(question, answer)

            logger.info("千问步骤3：点击分享按钮...")
            try:
                is_visible = await share_button.is_visible()
                bounding_box = await share_button.bounding_box()
                logger.info(f"千问分享按钮状态: 可见={is_visible}, 位置={bounding_box}")

                await self.page.evaluate("(element) => { element.click(); }", share_button)
                logger.info("千问JavaScript点击成功")

                await self.page.wait_for_timeout(500)
                try:
                    overlay = await self.page.query_selector("[class*='overlay'], [class*='modal'], [class*='dialog']")
                    if overlay and await overlay.is_visible():
                        logger.info("千问检测到弹窗/遮罩层出现")
                except:
                    pass

            except Exception as e:
                logger.warning(f"千问JavaScript点击失败: {str(e)}，尝试普通点击")
                try:
                    await share_button.click()
                    logger.info("千问普通点击成功")
                except Exception as e2:
                    logger.error(f"千问普通点击也失败: {str(e2)}")
                    if bounding_box:
                        x = bounding_box['x'] + bounding_box['width'] / 2
                        y = bounding_box['y'] + bounding_box['height'] / 2
                        await self.page.mouse.click(x, y)
                        logger.info(f"千问坐标点击: ({x}, {y})")

            await self.page.wait_for_timeout(3000)
            logger.info("千问分享按钮已点击")

            try:
                from datetime import datetime
                from pathlib import Path
                debug_path = Path("screenshots") / f"qwen_debug_after_click_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                await self.page.screenshot(path=str(debug_path), full_page=False)
                logger.info(f"千问点击后截图保存: {debug_path}")
            except Exception as e:
                logger.debug(f"千问点击后截图失败: {str(e)}")

            logger.info("千问步骤4：等待并处理弹窗...")
            button_found = False

            for wait_round in range(10):
                await self.page.wait_for_timeout(500)

                if wait_round in [1, 3, 5]:
                    try:
                        all_elements = await self.page.query_selector_all("*")
                        visible_with_text = []
                        for elem in all_elements:
                            try:
                                if await elem.is_visible():
                                    text = await elem.inner_text()
                                    text = text.strip() if text else ""
                                    if text and len(text) < 50:
                                        class_name = await elem.get_attribute("class") or ""
                                        tag_name = await elem.evaluate("(e) => e.tagName")
                                        visible_with_text.append(f"{tag_name}.{class_name[:30]}:'{text[:20]}'")
                            except:
                                continue
                        if visible_with_text:
                            logger.info(f"千问弹窗调试(wait_round={wait_round}): {visible_with_text[:10]}")
                    except Exception as e:
                        logger.debug(f"千问弹窗调试失败: {str(e)}")

                button_selectors = [
                    "button:has-text('创建并复制')",
                    "[role='button']:has-text('创建并复制')",
                    "button:has-text('创建分享链接')",
                    "[role='button']:has-text('创建分享链接')",
                    "button:has-text('复制链接')",
                    "[role='button']:has-text('复制链接')",
                    "button:has-text('复制')",
                    "[role='button']:has-text('复制')",
                    "[class*='copy']"
                ]

                for selector in button_selectors:
                    try:
                        elements = await self.page.query_selector_all(selector)
                        if elements:
                            for elem in elements:
                                if await elem.is_visible():
                                    text = await elem.inner_text()
                                    text = text.strip() if text else ""
                                    if any(keyword in text for keyword in ["创建并复制", "创建分享链接", "复制链接", "复制"]):
                                        try:
                                            await self.page.evaluate("(element) => { element.click(); }", elem)
                                        except:
                                            await elem.click()
                                        logger.info(f"千问找到并点击按钮: {text}")
                                        button_found = True

                                        if "创建分享链接" in text:
                                            await self.page.wait_for_timeout(2000)
                                            for sel2 in ["button:has-text('创建并复制')", "[role='button']:has-text('创建并复制')"]:
                                                try:
                                                    elems2 = await self.page.query_selector_all(sel2)
                                                    if elems2:
                                                        for e2 in elems2:
                                                            if await e2.is_visible():
                                                                await e2.click()
                                                                logger.info("千问点击创建并复制")
                                                                break
                                                except:
                                                    continue
                                        break
                        if button_found:
                            break
                    except Exception as e:
                        logger.debug(f"千问查找按钮 {selector} 失败: {str(e)}")
                        continue
                if button_found:
                    break

            if button_found:
                await self.page.wait_for_timeout(2000)
                try:
                    import pyperclip
                    share_link = pyperclip.paste()
                    if share_link and share_link.startswith("http"):
                        logger.info(f"千问从剪贴板获取链接: {share_link}")
                    else:
                        try:
                            link_input = await self.page.query_selector("input[value*='http']")
                            if link_input:
                                share_link = await link_input.input_value()
                                logger.info(f"千问从输入框获取链接: {share_link}")
                        except:
                            share_link = None
                except Exception as e:
                    logger.debug(f"千问获取链接失败: {str(e)}")
            else:
                logger.warning("千问未找到分享相关按钮")

            logger.info("千问步骤5：保存截图...")
            default_screenshot_path, _, _ = await self._default_screenshot(question, answer)

            return default_screenshot_path, False, share_link

        except Exception as e:
            logger.error(f"千问截图失败: {str(e)}")
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
