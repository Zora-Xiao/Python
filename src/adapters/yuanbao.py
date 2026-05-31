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
            logger.info("元宝等待AI响应...")
            await self.page.wait_for_timeout(5000)
            
            default_screenshot_path = None
            share_link = None
            
            logger.info("元宝步骤1：悬停到消息上等待分享按钮...")
            
            message_selectors = [
                ".message-content",
                ".yuanbao-message-content",
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
                        logger.info(f"元宝找到消息元素：{sel}")
                        break
                except:
                    continue
            
            if last_message:
                logger.info("元宝悬停到最后一条消息...")
                await last_message.hover()
                await self.page.wait_for_timeout(3000)
            
            logger.info("元宝步骤2：查找分享按钮...")
            share_button_elem = None
            
            share_button_selectors = [
                "button[data-testid='share-button']",
                "div.chat-footer button[class*='share']",
                "div.message-actions button[class*='share']",
                "button[aria-label*='share']",
                "button[title*='分享']",
                ".share-icon-wrapper",
                "div[class*='share']:not(.sidebar-share)",
                "button[class*='share']",
                "svg[class*='share']",
                "[class*='share-btn']",
                "[class*='share-button']",
                "[data-testid*='share']",
                ".share-icon",
                "button:has(svg[class*='share'])"
            ]
            
            for selector in share_button_selectors:
                try:
                    elem = await self.page.wait_for_selector(selector, timeout=5000, state="visible")
                    if elem:
                        share_button_elem = elem
                        logger.info(f"元宝潜在分享按钮匹配成功: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"元宝检查分享按钮选择器 {selector} 失败: {str(e)}")
                    continue
            
            if not share_button_elem:
                logger.warning("元宝分享按钮未找到，使用默认截图")
                return await self._default_screenshot(question, answer)
            
            logger.info("元宝步骤3：尝试点击分享按钮...")
            
            try:
                bounding_box = await share_button_elem.bounding_box()
                if bounding_box:
                    logger.info(f"元宝分享按钮位置: x={bounding_box['x']}, y={bounding_box['y']}, width={bounding_box['width']}, height={bounding_box['height']}")
                    
                    center_x = bounding_box['x'] + bounding_box['width'] / 2
                    center_y = bounding_box['y'] + bounding_box['height'] / 2
                    logger.info(f"元宝分享按钮中心坐标: ({center_x}, {center_y})")
                
                await share_button_elem.scroll_into_view_if_needed()
                await self.page.wait_for_timeout(500)
                
                await share_button_elem.hover()
                logger.info("元宝hover分享按钮成功")
                await self.page.wait_for_timeout(1000)
                
                max_click_attempts = 3
                for click_attempt in range(max_click_attempts):
                    try:
                        logger.info(f"元宝第{click_attempt + 1}次尝试点击分享按钮...")
                        
                        await share_button_elem.click(timeout=5000)
                        logger.info(f"元宝第{click_attempt + 1}次标准点击分享按钮成功")
                        
                        await self.page.wait_for_timeout(1000)
                        
                        if click_attempt < max_click_attempts - 1:
                            try:
                                popup = await self.page.query_selector("div[class*='share-modal'], div[class*='popup'], [role='dialog'], [class*='share-menu']")
                                if popup and await popup.is_visible():
                                    logger.info("元宝检测到弹窗已出现，停止点击尝试")
                                    break
                            except:
                                pass
                            
                            logger.warning(f"元宝第{click_attempt + 1}次点击后未检测到弹窗，继续点击...")
                            await self.page.wait_for_timeout(1000)
                        else:
                            logger.warning("元宝已达到最大点击次数")
                            
                    except Exception as e:
                        logger.warning(f"元宝第{click_attempt + 1}次标准点击分享按钮失败: {str(e)}")
                        if click_attempt < max_click_attempts - 1:
                            await self.page.wait_for_timeout(500)
                            continue
                        raise
                        
            except Exception as e:
                logger.warning(f"元宝标准点击分享按钮失败: {str(e)}，尝试强制点击...")
                try:
                    await share_button_elem.click(force=True, timeout=5000)
                    logger.info("元宝强制点击分享按钮成功")
                    await self.page.wait_for_timeout(1000)
                except Exception as e2:
                    logger.error(f"元宝强制点击分享按钮也失败: {str(e2)}，尝试JS点击...")
                    try:
                        await share_button_elem.evaluate("el => el.click()")
                        logger.info("元宝JS点击分享按钮成功")
                        await self.page.wait_for_timeout(1000)
                    except Exception as e3:
                        logger.error(f"元宝JS点击分享按钮也失败: {str(e3)}，尝试坐标点击...")
                        try:
                            if bounding_box:
                                x = bounding_box['x'] + bounding_box['width'] / 2
                                y = bounding_box['y'] + bounding_box['height'] / 2
                                await self.page.mouse.click(x, y)
                                logger.info(f"元宝坐标点击分享按钮成功: ({x}, {y})")
                                await self.page.wait_for_timeout(1000)
                            else:
                                raise Exception("无法获取按钮位置信息")
                        except Exception as e4:
                            logger.error(f"元宝所有点击方式均失败: {str(e4)}")
                            return await self._default_screenshot(question, answer)
            
            try:
                await self.page.wait_for_selector("div[class*='share-modal'], div[class*='popup'], [role='dialog'], [class*='share-menu']", timeout=5000)
                logger.info("元宝分享弹窗已出现")
                
                debug_path = Path("screenshots") / f"yuanbao_debug_popup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                await self.page.screenshot(path=str(debug_path), full_page=False)
                logger.info(f"元宝弹窗截图保存: {debug_path}")
            except:
                logger.warning("元宝分享弹窗未及时出现，可能点击无效")
            
            await self.page.wait_for_timeout(1000)
            
            try:
                from datetime import datetime
                from pathlib import Path
                debug_path = Path("screenshots") / f"yuanbao_debug_after_click_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                await self.page.screenshot(path=str(debug_path), full_page=False)
                logger.info(f"元宝点击后截图保存: {debug_path}")
            except Exception as e:
                logger.debug(f"元宝点击后截图失败: {str(e)}")
            
            logger.info("元宝步骤4：查找生成图片按钮...")
            gen_btn = None
            max_wait_rounds = 10
            
            gen_selectors = [
                "button:has-text('生成图片')",
                "button:has-text('保存图片')",
                "button:has-text('分享图片')",
                "button:has-text('Share Image')",
                "button:has-text('Create Image')",
                "button:has-text('generate image')",
                "button:has-text('Generate Image')",
                "button:has-text('generate')",
                "div[class*='share-option']:visible",
                "div[class*='share-menu'] button",
                "div[class*='popup'] button",
                "[class*='share-option']:visible",
                "[class*='generate-image']",
                "[class*='create-image']",
                "[data-testid*='generate']",
                "[aria-label*='image']"
            ]
            
            for round_num in range(max_wait_rounds):
                logger.info(f"元宝查找生成图片按钮第{round_num + 1}轮...")
                
                for selector in gen_selectors:
                    try:
                        elements = await self.page.query_selector_all(selector)
                        if elements:
                            for elem in elements:
                                if await elem.is_visible():
                                    text = await elem.inner_text() or ""
                                    class_name = await elem.get_attribute("class") or ""
                                    
                                    if any(keyword in text.lower() or keyword in class_name.lower() 
                                           for keyword in ['生成', '图片', 'image', 'generate', 'save']):
                                        gen_btn = elem
                                        logger.info(f"元宝找到生成/分享图片按钮: {selector}, 文本: '{text}', class: {class_name[:50]}")
                                        break
                            if gen_btn:
                                break
                    except Exception as e:
                        logger.debug(f"元宝检查生成图片按钮 {selector} 失败: {str(e)}")
                        continue
                
                if gen_btn:
                    break
                
                if round_num < max_wait_rounds - 1:
                    logger.debug(f"元宝等待生成图片按钮出现第{round_num + 1}次...")
                    await self.page.wait_for_timeout(1000)
            
            if not gen_btn:
                logger.warning("元宝生成图片按钮未找到，使用默认截图")
                return await self._default_screenshot(question, answer)
            
            try:
                await gen_btn.hover()
                await self.page.wait_for_timeout(500)
                
                await gen_btn.click(timeout=5000)
                logger.info("元宝标准点击生成图片按钮成功")
            except Exception as e:
                logger.warning(f"元宝标准点击生成图片按钮失败: {str(e)}，尝试强制点击...")
                try:
                    await gen_btn.click(force=True, timeout=5000)
                    logger.info("元宝强制点击生成图片按钮成功")
                except Exception as e2:
                    logger.error(f"元宝强制点击生成图片按钮也失败: {str(e2)}，尝试JS点击...")
                    try:
                        await gen_btn.evaluate("el => el.click()")
                        logger.info("元宝JS点击生成图片按钮成功")
                    except Exception as e3:
                        logger.error(f"元宝所有点击方式均失败: {str(e3)}")
                        return await self._default_screenshot(question, answer)
            
            await self.page.wait_for_timeout(3000)
            logger.info("元宝生成图片按钮已点击")
            
            logger.info("元宝步骤5：查找保存图片按钮...")
            save_selectors = [
                "button:has-text('save image')",
                "button:has-text('save')",
                "button:has-text('保存')",
                "[class*='save']",
                "[download]",
                "[data-testid*='save']"
            ]
            
            save_btn = None
            for selector in save_selectors:
                try:
                    elem = await self.page.wait_for_selector(selector, timeout=3000, state="visible")
                    if elem:
                        save_btn = elem
                        logger.info(f"元宝找到保存图片按钮: {selector}")
                        break
                except:
                    continue
            
            if save_btn:
                try:
                    await save_btn.hover()
                    await self.page.wait_for_timeout(500)
                    
                    await save_btn.click(timeout=5000)
                    logger.info("元宝标准点击保存图片按钮成功")
                except Exception as e:
                    logger.warning(f"元宝标准点击保存图片按钮失败: {str(e)}，尝试强制点击...")
                    try:
                        await save_btn.click(force=True, timeout=5000)
                        logger.info("元宝强制点击保存图片按钮成功")
                    except Exception as e2:
                        logger.error(f"元宝强制点击保存图片按钮也失败: {str(e2)}，尝试JS点击...")
                        try:
                            await save_btn.evaluate("el => el.click()")
                            logger.info("元宝JS点击保存图片按钮成功")
                        except Exception as e3:
                            logger.error(f"元宝所有点击方式均失败: {str(e3)}")
                await self.page.wait_for_timeout(2000)
            else:
                logger.warning("元宝保存图片按钮未找到")
            
            logger.info("元宝步骤6：保存截图...")
            default_screenshot_path, _, _ = await self._default_screenshot(question, answer)
            
            return default_screenshot_path, False, share_link
            
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
