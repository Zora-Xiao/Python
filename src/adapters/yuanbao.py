# -*- coding: utf-8 -*-
from typing import Optional
from src.adapters.base import BaseAdapter
from src.models.question import Question
from src.utils.logger import logger


class YuanbaoAdapter(BaseAdapter):
    def __init__(self, config: dict):
        super().__init__(config)
        self.platform_id = "yuanbao"
        self.platform_url = config.get("web_url", "https://yuanbao.tencent.com/chat/")
    
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
                logger.warning("元宝登录按钮未找到")
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
                logger.warning("元宝用户名输入框未找到")
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
                logger.warning("元宝密码输入框未找到")
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
                logger.info("元宝登录成功")
            else:
                logger.warning("元宝提交按钮未找到")
            
            return True
        except Exception as e:
            logger.error(f"元宝登录失败：{str(e)}")
            return False
    
    async def _navigate_to_chat(self) -> bool:
        try:
            await self.page.goto(self.platform_url, wait_until="domcontentloaded", timeout=60000)
            await self.page.wait_for_timeout(3000)
            return True
        except Exception as e:
            logger.error(f"元宝导航失败：{str(e)}")
            return False
    
    async def _send_message(self, question: str) -> None:
        try:
            input_selectors = [
                "textarea",
                "textarea[placeholder*='Message']",
                "textarea[placeholder*='ask']",
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
            
            logger.info(f"元宝发送消息：{question[:30]}...")
            
        except Exception as e:
            logger.error(f"元宝发送消息失败：{str(e)}")
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
            logger.error(f"元宝获取回答失败：{str(e)}")
            return "获取回答失败"
    
    async def screenshot(self, question: Question, answer: str) -> tuple[Optional[str], bool, Optional[str]]:
        if self.page is None:
            return None, False, None
        
        try:
            from src.utils.screenshot import ScreenshotTool
            screenshot_tool = ScreenshotTool()
            
            logger.info("元宝等待AI响应...")
            await self.page.wait_for_timeout(3000)
            
            logger.info("元宝步骤1：查找分享按钮...")
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
                                logger.info(f"元宝找到分享按钮：{selector}")
                                break
                        if share_button:
                            break
                except Exception as e:
                    logger.debug(f"元宝检查分享按钮选择器 {selector} 失败：{str(e)}")
                    continue
            
            if not share_button:
                logger.warning("元宝分享按钮未找到，使用默认截图")
                return await self._default_screenshot(question, answer)
            
            await share_button.click()
            await self.page.wait_for_timeout(2000)
            logger.info("元宝点击分享按钮")
            
            logger.info("元宝步骤2：查找生成图片按钮...")
            gen_selectors = [
                "button:has-text('generate image')",
                "button:has-text('generate')",
                "[class*='generate']",
                "[class*='image']",
                "[data-testid*='generate']"
            ]
            
            gen_btn = None
            for selector in gen_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    if elements:
                        for elem in elements:
                            if await elem.is_visible():
                                gen_btn = elem
                                logger.info(f"元宝找到生成图片按钮：{selector}")
                                break
                        if gen_btn:
                            break
                except Exception as e:
                    logger.debug(f"元宝检查生成按钮选择器 {selector} 失败：{str(e)}")
                    continue
            
            if not gen_btn:
                logger.warning("元宝生成图片按钮未找到，使用默认截图")
                return await self._default_screenshot(question, answer)
            
            await gen_btn.click()
            await self.page.wait_for_timeout(3000)
            logger.info("元宝点击生成图片按钮")
            
            logger.info("元宝步骤3：查找保存图片按钮...")
            save_selectors = [
                "button:has-text('save image')",
                "button:has-text('save')",
                "[class*='save']",
                "[download]",
                "[data-testid*='save']"
            ]
            
            save_btn = None
            for selector in save_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    if elements:
                        for elem in elements:
                            if await elem.is_visible():
                                save_btn = elem
                                logger.info(f"元宝找到保存图片按钮：{selector}")
                                break
                        if save_btn:
                            break
                except Exception as e:
                    logger.debug(f"元宝检查保存按钮选择器 {selector} 失败：{str(e)}")
                    continue
            
            if save_btn:
                await save_btn.click()
                await self.page.wait_for_timeout(2000)
                logger.info("元宝点击保存图片按钮")
            else:
                logger.warning("元宝保存图片按钮未找到，继续使用默认截图")
            
            screenshot_path, is_shared_image, share_link = await screenshot_tool.capture_from_page(
                self.page, 
                self.platform_id, 
                question
            )
            
            return screenshot_path, is_shared_image, share_link
            
        except Exception as e:
            logger.error(f"元宝截图失败：{str(e)}")
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
            logger.error(f"元宝默认截图失败：{str(e)}")
            return None, False, None
    
    async def close(self):
        await super().close()
