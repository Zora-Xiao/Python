# -*- coding: utf-8 -*-
from typing import Optional
from src.adapters.base import BaseAdapter
from src.models.question import Question
from src.utils.logger import logger


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
                # 豆包实际HTML结构选择器（基于分析）
                ".auto-hide-last-sibling-br.paragraph-element",
                ".auto-hide-last-sibling-br.paragraph-pP9ZLC",
                ".flow-markdown-body",
                ".md-box-root",
                "[data-render-engine='node']",
                "[data-container-type='block-v2']",
                # 通用选择器
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

            max_wait = 120
            last_text = ""
            stable_count = 0
            
            for _ in range(max_wait):
                for selector in answer_selectors:
                    try:
                        elems = await self.page.query_selector_all(selector)
                        if elems and len(elems) > 0:
                            last = elems[-1]
                            is_visible = await last.is_visible()
                            if is_visible:
                                text = await last.inner_text()
                                text = text.strip()
                                
                                if text and len(text) > 10:
                                    # 检测流式输出是否稳定（内容不再变化）
                                    if text == last_text:
                                        stable_count += 1
                                    else:
                                        last_text = text
                                        stable_count = 0
                                    
                                    # 内容稳定3秒且长度超过30字符认为回答完成
                                    if stable_count >= 3 and len(text) > 30:
                                        logger.info(f"豆包成功获取回答：{text[:30]}...")
                                        return text
                    except Exception as e:
                        continue
                
                # 尝试通过data-message-id定位最新消息
                try:
                    messages = await self.page.query_selector_all("[data-message-id]")
                    if messages and len(messages) > 0:
                        last_msg = messages[-1]
                        content = await last_msg.inner_text()
                        content = content.strip()
                        if content and len(content) > 10:
                            if content == last_text:
                                stable_count += 1
                            else:
                                last_text = content
                                stable_count = 0
                            
                            if stable_count >= 3 and len(content) > 30:
                                logger.info(f"豆包通过data-message-id获取回答：{content[:30]}...")
                                return content
                except Exception:
                    pass
                    
                await self.page.wait_for_timeout(1000)

            # 如果超时但有部分内容，返回已获取的内容
            if last_text and len(last_text) > 10:
                logger.warning(f"豆包回答获取超时，返回已获取内容：{last_text[:30]}...")
                return last_text
                
            logger.warning("豆包等待回答超时")
            return "未找到回答"

        except Exception as e:
            logger.error(f"豆包获取回答失败：{str(e)}")
            return "获取回答失败"

    async def screenshot(self, question: Question) -> tuple[Optional[str], bool, Optional[str]]:
        """
        优化后的截图逻辑：
        1. 尝试通过UI交互生成分享图片/链接。
        2. 如果分享流程成功，返回分享结果（通常 is_shared_image=True）。
        3. 如果分享流程任何环节失败，降级为默认页面截图。
        """
        if self.page is None:
            return None, False, None

        try:
            logger.info("豆包开始尝试生成分享图片...")
            
            # 标记分享流程是否成功
            share_success = False
            share_link = None

            # --- 步骤 1: 查找并点击分享按钮 ---
            share_button_selectors = [
                "[data-dbx-name='button']", # 注意：这个选择器可能过于宽泛，建议结合具体业务调整
                "div[class*='share']",
                "button[class*='share']",
                "svg[class*='share']",
                "[class*='share-btn']",
                "[class*='share-button']",
                "[data-testid*='share']",
                ".share-icon",
                "button:has(svg[class*='share'])"
            ]

            share_button_elem = await self._find_visible_element(share_button_selectors)
            
            if share_button_elem:
                await share_button_elem.click()
                await self.page.wait_for_timeout(2000) # 等待弹窗出现
                logger.info("豆包已点击分享按钮")

                # --- 步骤 2: 查找并点击“分享图片”或“生成图片”按钮 ---
                # 注意：豆包的UI可能会变化，这里需要适配具体的“生成图片/分享图片”按钮
                share_image_selectors = [
                    "button:has-text('分享图片')",
                    "button:has-text('生成图片')",
                    "button:has-text('Image')",
                    "div[class*='share-image']",
                    "button[class*='image']",
                    "[role='menuitem']:has-text('图片')"
                ]

                share_image_elem = await self._find_visible_element(share_image_selectors, timeout=5000)

                if share_image_elem:
                    await share_image_elem.click()
                    await self.page.wait_for_timeout(3000) # 等待图片生成或弹窗变化
                    logger.info("豆包已点击分享图片按钮")
                    
                    # --- 步骤 3: 尝试点击下载/保存（如果存在）---
                    # 有些流程是点击分享后直接生成预览，可能需要手动下载
                    download_selectors = [
                        "button:has-text('下载')",
                        "button:has-text('Download')",
                        "button[class*='download']",
                        "a[download]"
                    ]
                    
                    download_elem = await self._find_visible_element(download_selectors, timeout=3000)
                    if download_elem:
                        await download_elem.click()
                        await self.page.wait_for_timeout(2000)
                        logger.info("豆包已点击下载按钮")

                    # --- 步骤 4: 验证分享是否成功 ---
                    # 这里假设如果走到了这一步，且没有抛出异常，我们认为分享UI交互已完成。
                    # 具体的“成功”定义取决于 ScreenshotTool 如何捕获。
                    # 如果豆包生成了一个独立的图片预览层，我们可以尝试捕获该层。
                    
                    # 尝试获取分享后的特定容器截图，或者让 ScreenshotTool 处理
                    # 由于 Playwright 难以直接判断“分享成功”的业务逻辑，我们通常依赖 UI 状态。
                    # 如果上述按钮都找到了并点击了，我们暂定为“尝试了分享流程”。
                    
                    # 关键判断：如果分享流程产生了新的DOM结构（如图片预览），我们可以尝试截取那个特定区域。
                    # 但为了简化，如果按钮点击成功，我们调用 capture_from_page，并标记为 shared 尝试。
                    
                    share_success = True
                else:
                    logger.warning("豆包未找到‘分享图片’按钮，分享流程中断")
            else:
                logger.warning("豆包未找到主‘分享’按钮，分享流程中断")

            # --- 决策点：如果分享流程成功，尝试捕获分享结果；否则回退到默认截图 ---
            if share_success:
                logger.info("豆包分享流程执行完毕，尝试捕获分享结果...")
                # 注意：这里可能需要特殊的逻辑来截取“分享生成的图片”而不是整个页面。
                # 如果 ScreenshotTool.capture_from_page 能够智能识别当前高亮的分享区域，则直接使用。
                # 否则，可能需要传入特定的 selector 给 screenshot_tool。
                
                # 假设 capture_from_page 会尝试截取当前视口或特定元素。
                # 如果分享成功，通常会有一个浮层。我们可以尝试截取这个浮层。
                share_overlay_selectors = [
                    ".share-modal",
                    ".image-preview-container",
                    "[class*='preview']",
                    "div[class*='share-content']"
                ]
                
                overlay_elem = await self._find_visible_element(share_overlay_selectors)
                
                if overlay_elem:
                    import time
                    import os
                    timestamp = int(time.time() * 1000)
                    save_dir = "screenshots"
                    os.makedirs(save_dir, exist_ok=True)
                    file_path = os.path.join(save_dir, f"doubao_share_{timestamp}.png")
                    
                    await overlay_elem.screenshot(path=file_path)
                    logger.info(f"豆包成功截取分享图片: {file_path}")
                    return file_path, True, share_link

                else:
                    # 分享了但没找到预览层，可能只是打开了分享菜单，没生成图片
                    logger.warning("豆包分享后未找到预览层，回退到默认截图")
                    return await self._default_screenshot(question)

            else:
                # 分享流程失败，执行默认截图
                logger.info("豆包分享流程失败，执行默认页面截图")
                return await self._default_screenshot(question)

        except Exception as e:
            logger.error(f"豆包截图逻辑异常：{str(e)}")
            # 发生任何异常，确保至少有一张默认截图
            return await self._default_screenshot(question)

    async def _find_visible_element(self, selectors: list, timeout: int = 5000) -> Optional[object]:
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
            logger.error(f"豆包默认截图失败：{str(e)}")
            return None, False, None

    async def close(self):
        await super().close()