# -*- coding: utf-8 -*-
import random
import time
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
            await self.page.wait_for_timeout(3000)
            
            login_button_selectors = [
                "button:has-text('登录')",
                "button:has-text('login')",
                "button:has-text('Sign In')",
                "a:has-text('登录')",
                "[data-testid='login']",
                ".login-btn",
                "[class*='login']",
                "[class*='signin']"
            ]

            login_button_elem = None
            for selector in login_button_selectors:
                try:
                    elems = await self.page.query_selector_all(selector)
                    if elems:
                        for elem in elems:
                            if await elem.is_visible():
                                login_button_elem = elem
                                logger.info(f"豆包找到登录按钮: {selector}")
                                break
                        if login_button_elem:
                            break
                except Exception as e:
                    logger.debug(f"豆包尝试查找登录按钮 {selector} 失败: {str(e)}")
                    continue

            if not login_button_elem:
                logger.warning("豆包登录按钮未找到")
                return False

            await login_button_elem.click()
            await self.page.wait_for_timeout(3000)

            username_selectors = [
                "input[name='username']",
                "input[name='email']",
                "input[name='phone']",
                "input[type='text']",
                "[placeholder*='用户名']",
                "[placeholder*='邮箱']",
                "[placeholder*='手机号']",
                "[placeholder*='email']",
                "[placeholder*='phone']",
                "[data-testid*='username']",
                "[data-testid*='email']",
                ".ant-input",
                "input[class*='input']"
            ]

            username_elem = None
            for selector in username_selectors:
                try:
                    elems = await self.page.query_selector_all(selector)
                    if elems:
                        for elem in elems:
                            if await elem.is_visible():
                                username_elem = elem
                                await elem.fill(self.username)
                                await self.page.wait_for_timeout(500)
                                logger.info(f"豆包找到用户名输入框: {selector}")
                                break
                        if username_elem:
                            break
                except Exception as e:
                    logger.debug(f"豆包尝试填写用户名 {selector} 失败: {str(e)}")
                    continue

            if not username_elem:
                logger.warning("豆包用户名输入框未找到")
                return False

            password_selectors = [
                "input[name='password']",
                "input[type='password']",
                "[placeholder*='密码']",
                "[placeholder*='password']",
                "[data-testid*='password']",
                ".ant-input-password",
                "input[class*='password']"
            ]

            password_elem = None
            for selector in password_selectors:
                try:
                    elems = await self.page.query_selector_all(selector)
                    if elems:
                        for elem in elems:
                            if await elem.is_visible():
                                password_elem = elem
                                await elem.fill(self.password)
                                await self.page.wait_for_timeout(500)
                                logger.info(f"豆包找到密码输入框: {selector}")
                                break
                        if password_elem:
                            break
                except Exception as e:
                    logger.debug(f"豆包尝试填写密码 {selector} 失败: {str(e)}")
                    continue

            if not password_elem:
                logger.warning("豆包密码输入框未找到")
                return False

            submit_selectors = [
                "button[type='submit']",
                "button:has-text('登录')",
                "button:has-text('login')",
                "button:has-text('confirm')",
                ".submit-btn",
                "[class*='btn-primary']",
                "[class*='btn-login']",
                "[data-testid*='submit']"
            ]

            submit_elem = None
            for selector in submit_selectors:
                try:
                    elems = await self.page.query_selector_all(selector)
                    if elems:
                        for elem in elems:
                            if await elem.is_visible():
                                submit_elem = elem
                                await elem.click()
                                await self.page.wait_for_timeout(5000)
                                logger.info(f"豆包点击提交按钮: {selector}")
                                break
                        if submit_elem:
                            break
                except Exception as e:
                    logger.debug(f"豆包尝试点击提交按钮 {selector} 失败: {str(e)}")
                    continue

            if not submit_elem:
                logger.warning("豆包提交按钮未找到")
                return False

            await self.page.wait_for_timeout(3000)
            
            current_url = self.page.url
            if "login" not in current_url.lower() and "signin" not in current_url.lower():
                logger.info(f"豆包登录成功，当前URL: {current_url}")
                return True
            else:
                logger.warning(f"豆包登录后仍在登录页面，可能登录失败")
                return False
                
        except Exception as e:
            logger.error(f"豆包登录失败：{str(e)}")
            return False

    async def _check_captcha(self) -> bool:
        """检测页面是否出现人机验证（CAPTCHA）
        返回 True 表示检测到验证码，False 表示未检测到"""
        try:
            captcha_indicators = [
                # 关键词检测
                "验证",
                "人机",
                "captcha",
                "滑块",
                "图片验证",
                "选择图片",
                "安全验证",
                "请选择",
                # CSS选择器检测
                ".captcha",
                "[class*='captcha']",
                "[class*='verify']",
                "[class*='slider']",
                "[class*='challenge']",
                "[data-captcha]",
                ".geetest",
                ".gt_captcha",
                "#captcha",
                ".security-check",
                "[class*='security']"
            ]

            page_content = await self.page.content()
            page_text = await self.page.inner_text()
            
            page_lower = page_text.lower()
            content_lower = page_content.lower()

            for indicator in captcha_indicators:
                if indicator.lower() in page_lower or indicator.lower() in content_lower:
                    logger.warning(f"豆包检测到验证码关键词: {indicator}")
                    return True

            for selector in [
                ".captcha", "[class*='captcha']", "[class*='verify']",
                "[class*='slider']", "[class*='challenge']", "[data-captcha]",
                ".geetest", ".gt_captcha", "#captcha", ".security-check"
            ]:
                try:
                    elements = await self.page.query_selector_all(selector)
                    if elements:
                        for elem in elements:
                            if await elem.is_visible():
                                logger.warning(f"豆包检测到验证码元素: {selector}")
                                return True
                except Exception:
                    continue

            return False
        except Exception as e:
            logger.debug(f"豆包验证码检测异常: {str(e)}")
            return False

    async def _handle_captcha(self) -> bool:
        """处理验证码：根据配置决定等待用户手动处理或直接失败
        返回 True 表示处理成功（用户手动完成验证），False 表示处理失败或超时"""
        captcha_config = self.config.get("captcha_handling", {})
        mode = captcha_config.get("mode", "fail")
        timeout = captcha_config.get("timeout", 120)
        platforms = captcha_config.get("platforms", [])

        if self.platform_id not in platforms:
            return False

        if mode == "fail":
            logger.error("豆包检测到验证码，配置为fail模式，标记失败")
            return False

        logger.warning(f"豆包检测到验证码，等待用户手动处理... (超时时间: {timeout}秒)")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            await self.page.wait_for_timeout(3000)
            
            if not await self._check_captcha():
                logger.info("豆包验证码已被用户手动完成")
                return True
            
            elapsed = int(time.time() - start_time)
            logger.info(f"豆包等待验证码处理中... ({elapsed}/{timeout}秒)")

        logger.error(f"豆包验证码等待超时 ({timeout}秒)")
        return False

    async def _simulate_human_behavior(self):
        """模拟人类行为：添加随机延迟、鼠标移动等"""
        try:
            await self.page.wait_for_timeout(random.randint(500, 1500))
            
            viewport = await self.page.viewport_size
            if viewport:
                target_x = random.randint(100, viewport.get("width", 1920) - 100)
                target_y = random.randint(100, viewport.get("height", 1080) - 100)
                
                await self.page.mouse.move(target_x, target_y)
                await self.page.wait_for_timeout(random.randint(200, 500))
                
                await self.page.mouse.move(
                    target_x + random.randint(-50, 50),
                    target_y + random.randint(-50, 50)
                )
        except Exception as e:
            logger.debug(f"模拟人类行为异常: {str(e)}")

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
            await self._simulate_human_behavior()

            if await self._check_captcha():
                if not await self._handle_captcha():
                    raise Exception("验证码处理失败")

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
            await self.page.wait_for_timeout(random.randint(300, 800))
            await self.page.fill(input_selector, question)
            await self.page.wait_for_timeout(random.randint(300, 800))
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
            question_text = "你好，请介绍一下你自己"
            
            for _ in range(max_wait):
                if await self._check_captcha():
                    logger.warning("豆包获取回答过程中检测到验证码")
                    if not await self._handle_captcha():
                        return "验证码处理失败"

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
                                    if text == question_text:
                                        continue
                                    if text.strip().startswith(question_text):
                                        continue
                                        
                                    if text == last_text:
                                        stable_count += 1
                                    else:
                                        last_text = text
                                        stable_count = 0
                                    
                                    if stable_count >= 3 and len(text) > 30:
                                        logger.info(f"豆包成功获取回答：{text[:30]}...")
                                        return text
                    except Exception as e:
                        continue
                
                try:
                    messages = await self.page.query_selector_all("[data-message-id]")
                    if messages and len(messages) > 0:
                        last_msg = messages[-1]
                        content = await last_msg.inner_text()
                        content = content.strip()
                        if content and len(content) > 10:
                            if content == question_text:
                                continue
                            if content.strip().startswith(question_text):
                                continue
                                
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

            if last_text and len(last_text) > 10:
                logger.warning(f"豆包回答获取超时，返回已获取内容：{last_text[:30]}...")
                return last_text
                
            logger.warning("豆包等待回答超时")
            return "未找到回答"

        except Exception as e:
            logger.error(f"豆包获取回答失败：{str(e)}")
            return "获取回答失败"

    async def screenshot(self, question: Question) -> tuple[Optional[str], bool, Optional[str], Optional[str]]:
        """
        优化后的截图逻辑：
        1. 尝试通过UI交互生成分享图片/链接。
        2. 如果分享流程成功，返回分享结果（通常 is_shared_image=True）。
        3. 如果分享流程任何环节失败，降级为默认页面截图。
        """
        if self.page is None:
            return None, False, None, None

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
                    return file_path, True, share_link, None

                else:
                    logger.warning("豆包分享后未找到预览层，回退到默认截图")
                    return await self._default_screenshot(question)

            else:
                logger.info("豆包分享流程失败，执行默认页面截图")
                return await self._default_screenshot(question)

        except Exception as e:
            logger.error(f"豆包截图逻辑异常：{str(e)}")
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
            logger.error(f"豆包默认截图失败：{str(e)}")
            return None, False, None, str(e)

    async def _check_login_url_pattern(self, url: str) -> bool:
        url_lower = url.lower()
        if "login" in url_lower or "auth" in url_lower or "signin" in url_lower:
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
    
    async def close(self):
        await super().close()