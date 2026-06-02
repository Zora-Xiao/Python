# -*- coding: utf-8 -*-
from typing import Optional
from src.adapters.base import BaseAdapter
from src.models.question import Question
from src.utils.logger import logger
import requests
import json
from pathlib import Path
from datetime import datetime

#region debug-point instrumentation
def report_debug_log(event: str, message: str, data: dict = None):
    """Report debug log to Debug Server"""
    try:
        log_entry = {
            'event': event,
            'message': message,
            'data': data or {}
        }
        requests.post('http://localhost:9527/log', json=log_entry, timeout=1)
    except:
        pass  # Silently fail if Debug Server is not available
#endregion


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
        """根据提供的HTML结构提取AI回答内容"""
        try:
            # 根据用户提供的HTML结构，AI回答内容在以下路径中：
            # .agent-chat__bubble__content > .agent-chat__conv--ai__speech_show > .agent-chat__speech-text--box > .agent-chat__speech-text > .hyc-component-text > .hyc-content-md > .hyc-common-markdown
            
            answer_selectors = [
                # 最精准的选择器 - 根据提供的HTML结构
                "div.agent-chat__conv--ai__speech_show .agent-chat__speech-text",
                "div.agent-chat__bubble__content .hyc-common-markdown",
                "div.agent-chat__bubble--ai .hyc-component-text",
                
                # 备用选择器
                "div.agent-chat__speech-text--box",
                "div.hyc-content-md",
                ".message-content"
            ]
            
            for selector in answer_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=8000)
                    answer_elements = await self.page.query_selector_all(selector)
                    
                    if answer_elements:
                        last_answer = answer_elements[-1]
                        answer = await last_answer.inner_text()
                        if answer and answer.strip():
                            logger.info(f"元宝成功获取回答，内容长度: {len(answer)}")
                            return answer.strip()
                except Exception as e:
                    logger.debug(f"尝试选择器 '{selector}' 获取回答失败: {e}")
                    continue
            
            return "未找到回答"
        except Exception as e:
            logger.error(f"元宝获取回答失败：{str(e)}")
            return "获取回答失败"
    
    async def _send_message_and_get_answer(self, question: str) -> str:
        """发送消息并等待回答完成（处理流式输出）"""
        try:
            await self._send_message(question)
            
            logger.info("元宝等待AI回答中...")
            
            max_wait_time = 120
            check_interval = 2000
            waited_time = 0
            
            # 根据提供的HTML结构，AI回答的容器选择器
            answer_container_selectors = [
                "div.agent-chat__conv--ai__speech_show",
                "div.agent-chat__bubble--ai"
            ]
            
            while waited_time < max_wait_time:
                try:
                    # 检查是否有打字指示器（表明回答正在生成）
                    typing_indicators = [
                        ".typing",
                        "[class*='typing']",
                        "[aria-label*='typing']",
                        ".loading",
                        "[class*='loading']",
                        "span:has-text('typing')",
                        "span:has-text('正在输入')",
                        "span:has-text('正在思考')",
                        "span:has-text('正在生成')",
                        "div[class*='thinking']",
                        "div[class*='spin']"
                    ]
                    
                    is_typing = False
                    for selector in typing_indicators:
                        try:
                            elems = await self.page.query_selector_all(selector)
                            if elems:
                                for elem in elems:
                                    if await elem.is_visible():
                                        is_typing = True
                                        break
                                if is_typing:
                                    break
                        except:
                            continue
                    
                    if is_typing:
                        logger.debug(f"元宝AI正在回答中，已等待 {waited_time} 秒")
                        await self.page.wait_for_timeout(check_interval)
                        waited_time += check_interval / 1000
                        continue
                    
                    # 使用提供的HTML结构选择器检查回答
                    for container_selector in answer_container_selectors:
                        try:
                            answer_elements = await self.page.query_selector_all(container_selector)
                            if answer_elements and len(answer_elements) > 0:
                                last_answer = answer_elements[-1]
                                answer_text = await last_answer.inner_text()
                                if answer_text and answer_text.strip():
                                    # 检查是否还有继续追加的迹象（末尾是否有"..."或其他标记）
                                    trimmed_text = answer_text.strip()
                                    if not trimmed_text.endswith('...') and not trimmed_text.endswith('。'):
                                        logger.info(f"元宝回答已完成，内容长度: {len(answer_text)}")
                                        return answer_text.strip()
                        except Exception as e:
                            logger.debug(f"检查回答容器 '{container_selector}' 失败: {e}")
                    
                    # 如果没有找到回答，继续等待
                    await self.page.wait_for_timeout(check_interval)
                    waited_time += check_interval / 1000
                    
                except Exception as e:
                    logger.debug(f"元宝等待回答时出错: {str(e)}")
                    await self.page.wait_for_timeout(check_interval)
                    waited_time += check_interval / 1000
            
            logger.warning(f"元宝等待回答超时（{max_wait_time}秒），尝试获取当前内容")
            return await self._get_answer()
            
        except Exception as e:
            logger.error(f"元宝发送消息并获取回答失败: {str(e)}")
            raise

    async def _robust_click(self, element, description: str = "element") -> bool:
        """
        尝试多种方式点击元素，提高成功率
        返回: True if click likely succeeded (no exception), False otherwise
        """
        if not element:
            return False
        
        # 1. Scroll into view
        try:
            await element.scroll_into_view_if_needed()
            await self.page.wait_for_timeout(500)
        except:
            pass

        # 2. Try JS Click (Most reliable for obscured elements)
        try:
            await element.evaluate("el => el.click()")
            logger.info(f"元宝 JS点击 {description} 成功")
            return True
        except Exception as e:
            logger.debug(f"元宝 JS点击 {description} 失败: {e}")

        # 3. Try Playwright Click with force
        try:
            await element.click(force=True, timeout=3000)
            logger.info(f"元宝 强制点击 {description} 成功")
            return True
        except Exception as e:
            logger.debug(f"元宝 强制点击 {description} 失败: {e}")

        # 4. Try Coordinate Click
        try:
            box = await element.bounding_box()
            if box:
                x = box['x'] + box['width'] / 2
                y = box['y'] + box['height'] / 2
                await self.page.mouse.click(x, y)
                logger.info(f"元宝 坐标点击 {description} 成功 ({x}, {y})")
                return True
        except Exception as e:
            logger.debug(f"元宝 坐标点击 {description} 失败: {e}")

        logger.warning(f"元宝 所有点击方式均失败 for {description}")
        return False

    async def _find_element_with_hover(self, selectors: list, hover_target_selector: str = None) -> Optional[object]:
            """
            尝试查找元素，如果提供了 hover_target_selector，先悬停在该目标上再查找。
            """
            # 如果需要悬停触发
            if hover_target_selector:
                try:
                    hover_elem = await self.page.wait_for_selector(hover_target_selector, timeout=3000, state="visible")
                    if hover_elem:
                        await hover_elem.hover()
                        await self.page.wait_for_timeout(800) # 等待动画或DOM更新
                        logger.info(f"元宝已悬停在 {hover_target_selector} 以触发菜单")
                except Exception as e:
                    logger.debug(f"悬停目标 {hover_target_selector} 未找到或失败: {e}")

            # 查找目标元素
            for selector in selectors:
                try:
                    # 使用较短超时快速遍历
                    elem = await self.page.query_selector(selector)
                    if elem and await elem.is_visible():
                        return elem
                except:
                    continue
            return None
    
    async def screenshot(self, question: Question, answer: str) -> tuple[Optional[str], bool, Optional[str]]:
        if self.page is None:
            return None, False, None
        
        try:
            logger.info("元宝开始截图流程...")
            await self.page.wait_for_timeout(3000) 
            
            share_btn = None
            
            # --- 策略 1: 根据用户提供的HTML结构查找分享按钮 ---
            # 分享按钮位于: .agent-chat__conv--ai__toolbar > .agent-chat__toolbar > .agent-chat__toolbar__right
            # 按钮结构: <div class="Toolbar_icon__xGP8b Toolbar_shareIcon__pXI31 Toolbar_isWeb__zF51c">
            #             <span class="yb-icon iconfont-yb icon-yb-ic_share_2504"></span>
            #          </div>
            direct_share_selectors = [
                # 基于提供的HTML结构 - 最精准的选择器
                "div.Toolbar_shareIcon__pXI31",
                "div[class*='Toolbar_shareIcon']",
                "span.icon-yb-ic_share_2504",
                "span[class*='icon-yb-ic_share']",
                "div.agent-chat__toolbar__right div[class*='shareIcon']",
                "div.agent-chat__conv--ai__toolbar div[class*='share']",
                
                # 备用选择器
                "div[class*='shareIcon']",
                "button[class*='share']",
                "svg[path*='share']",
                "[title*='分享']",
                "button[aria-label*='分享']"
            ]
            
            # 最后一条消息的选择器（用于悬停触发菜单）
            last_message_selector = "div.agent-chat__list__item--ai:last-child, div.agent-chat__bubble--ai:last-child"
            
            logger.info("元宝策略1: 尝试悬停在最后一条消息并查找分享按钮...")
            share_btn = await self._find_element_with_hover(direct_share_selectors, hover_target_selector=last_message_selector)
            
            if not share_btn:
                logger.info("元宝策略1失败。策略2: 尝试全局查找分享按钮...")
                share_btn = await self._find_element_with_hover(direct_share_selectors, hover_target_selector=None)

            if not share_btn:
                # --- 策略 3: 尝试查找工具栏区域 ---
                logger.info("元宝策略2失败。策略3: 尝试查找工具栏区域...")
                toolbar_selectors = [
                    "div.agent-chat__toolbar",
                    "div.agent-chat__conv--ai__toolbar"
                ]
                
                for toolbar_sel in toolbar_selectors:
                    try:
                        toolbar_elem = await self.page.wait_for_selector(toolbar_sel, timeout=3000)
                        if toolbar_elem:
                            await toolbar_elem.hover()
                            await self.page.wait_for_timeout(800)
                            share_btn = await self._find_element_with_hover(direct_share_selectors, hover_target_selector=None)
                            if share_btn:
                                break
                    except Exception as e:
                        logger.debug(f"尝试工具栏选择器 '{toolbar_sel}' 失败: {e}")
                        continue

            if not share_btn:
                # --- 如果仍然没找到，进行调试截图并回退 ---
                logger.error("元宝所有策略均未找到分享按钮！")
                debug_path = Path("screenshots") / f"yuanbao_debug_no_btn_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                await self.page.screenshot(path=str(debug_path), full_page=True)
                logger.info(f"元宝调试截图已保存: {debug_path}")
                return await self._default_screenshot(question, answer)
            
            logger.info(f"元宝成功定位分享按钮，准备点击...")
            
            # --- 执行点击和后续流程 ---
            clicked = await self._robust_click(share_btn, "分享按钮")
            if not clicked:
                logger.warning("元宝点击分享按钮失败，执行默认截图")
                return await self._default_screenshot(question, answer)
            
            await self.page.wait_for_timeout(1500) 

            # --- 等待分享弹窗出现并查找生成图片按钮 ---
            # 根据提供的HTML结构：
            # <div class="agent-chat__share-bar-container">
            #   <div class="agent-chat__share-bar">
            #     <div class="agent-chat__share-bar__content">
            #       <div class="agent-chat__share-bar__content__center">
            #         <div class="agent-chat__share-bar__item">...</div>
            #         <div class="agent-chat__share-bar__item">
            #           <div class="agent-chat__share-bar__item__logo"><svg>...</svg></div>
            #           <div class="agent-chat__share-bar__item__name">生成图片</div>
            #         </div>
            #       </div>
            #     </div>
            #   </div>
            # </div>
            
            logger.info("元宝等待分享弹窗出现...")
            share_bar_container = None
            try:
                share_bar_container = await self.page.wait_for_selector(
                    "div.agent-chat__share-bar-container", 
                    timeout=5000, 
                    state="visible"
                )
                logger.info("元宝分享弹窗已出现")
            except Exception as e:
                logger.warning(f"元宝分享弹窗未出现: {e}")
                # 尝试查找是否有其他形式的分享弹窗
                alternative_containers = [
                    "div[class*='share-bar']",
                    "[role='dialog'][class*='share']"
                ]
                for alt_sel in alternative_containers:
                    try:
                        share_bar_container = await self.page.wait_for_selector(alt_sel, timeout=2000, state="visible")
                        if share_bar_container:
                            logger.info(f"元宝找到备选分享弹窗: {alt_sel}")
                            break
                    except:
                        continue
            
            if not share_bar_container:
                logger.warning("元宝未找到分享弹窗，执行默认截图")
                return await self._default_screenshot(question, answer)
            
            # --- 查找生成图片按钮 ---
            logger.info("元宝步骤3: 查找生成图片按钮...")
            gen_btn = None
            
            # 根据提供的HTML结构，生成图片按钮的精准选择器
            gen_btn_selectors = [
                # 1. 最精准：基于完整结构路径
                "div.agent-chat__share-bar__content__center .agent-chat__share-bar__item:has(div.agent-chat__share-bar__item__name:has-text('生成图片'))",
                
                # 2. 基于按钮名称文本查找
                "div.agent-chat__share-bar__item__name:has-text('生成图片')",
                
                # 3. 查找包含生成图片文本的item项（备用）
                "div.agent-chat__share-bar__item:has-text('生成图片')",
                
                # 4. 基于SVG特征（第二个SVG的path特征）
                "div.agent-chat__share-bar__item:has(svg path[d*='M2.5 5C2.5 4.44771'])",
                
                # 5. 更通用的选择器（备用）
                "div[class*='share-bar__item']:has(div:has-text('生成图片'))"
            ]
            
            for selector in gen_btn_selectors:
                try:
                    logger.debug(f"元宝尝试生成图片按钮选择器: {selector}")
                    elems = await self.page.query_selector_all(selector)
                    if elems:
                        for elem in elems:
                            if await elem.is_visible():
                                # 验证按钮内容
                                try:
                                    button_text = await elem.text_content()
                                    if button_text and '生成图片' in button_text:
                                        logger.info(f"元宝找到生成图片按钮: {selector}")
                                        gen_btn = elem
                                        break
                                    elif selector == "div.agent-chat__share-bar__item__name:has-text('生成图片')":
                                        # 如果找到的是name元素，获取其父级item
                                        parent_item = await elem.evaluate("el => el.parentElement")
                                        if parent_item:
                                            gen_btn = parent_item
                                            logger.info(f"元宝找到生成图片按钮（通过name元素）")
                                            break
                                except:
                                    # 验证失败时直接使用找到的元素
                                    gen_btn = elem
                                    logger.info(f"元宝找到生成图片按钮: {selector}")
                                    break
                        if gen_btn:
                            break
                except Exception as e:
                    logger.debug(f"查找生成图片按钮失败: {e}")
                    continue
            
            if gen_btn:
                logger.info("元宝准备点击生成图片按钮...")
                
                # 点击生成图片按钮
                clicked_gen = await self._robust_click(gen_btn, "生成图片按钮")
                if not clicked_gen:
                    logger.error("元宝点击生成图片按钮失败")
                    return await self._default_screenshot(question, answer)
                
                logger.info("元宝已点击生成图片按钮，等待图片生成及预览窗口出现...")
                await self.page.wait_for_timeout(6000)
                
                # --- 查找并点击下载按钮 ---
                logger.info("元宝步骤4: 查找并点击下载按钮...")
                download_btn = None
                
                download_selectors = [
                    "div:has-text('下载')",
                    "button:has-text('下载')",
                    "[aria-label*='下载']",
                    "[aria-label*='Download']",
                    "[class*='download']"
                ]
                
                for selector in download_selectors:
                    try:
                        elem = await self.page.wait_for_selector(selector, timeout=3000, state="visible")
                        if elem:
                            download_btn = elem
                            logger.info(f"元宝找到下载按钮: {selector}")
                            break
                    except Exception as e:
                        logger.debug(f"查找下载按钮失败: {e}")
                        continue
                
                if download_btn:
                    logger.info("元宝准备点击下载按钮...")
                    clicked_download = await self._robust_click(download_btn, "下载按钮")
                    if clicked_download:
                        logger.info("元宝已点击下载按钮，等待保存...")
                        await self.page.wait_for_timeout(3000)
                    else:
                        logger.warning("元宝点击下载按钮失败")
                else:
                    logger.warning("元宝未找到下载按钮，将尝试直接截取预览图")
                
                # --- 尝试截取生成的图片或预览区域 ---
                logger.info("元宝步骤5: 查找并截取生成的图片...")
                img_container_selectors = [
                    "div[class*='photo-view'] img",
                    "div[class*='preview'] img",
                    "[role='dialog'] img",
                    ".modal img",
                    "canvas[class*='share']"
                ]
                
                final_img_elem = None
                for sel in img_container_selectors:
                    try:
                        final_img_elem = await self.page.wait_for_selector(sel, timeout=3000, state="visible")
                        if final_img_elem:
                            logger.info(f"元宝找到最终图片元素: {sel}")
                            break
                    except Exception as e:
                        logger.debug(f"查找图片元素失败: {e}")
                        continue
                
                if final_img_elem:
                    await self.page.wait_for_timeout(1000)
                    
                    timestamp = int(datetime.now().timestamp() * 1000)
                    save_dir = Path("screenshots")
                    save_dir.mkdir(exist_ok=True)
                    file_path = save_dir / f"yuanbao_share_{timestamp}.png"
                    
                    try:
                        await final_img_elem.screenshot(path=str(file_path))
                        logger.info(f"元宝成功截取分享图片: {file_path}")
                        
                        if file_path.exists() and file_path.stat().st_size > 0:
                            logger.info(f"元宝分享图片文件大小: {file_path.stat().st_size} bytes")
                            return str(file_path), True, None
                        else:
                            logger.warning(f"元宝分享图片文件无效，回退到默认截图")
                            return await self._default_screenshot(question, answer)
                    except Exception as screenshot_err:
                        logger.error(f"元宝截取图片元素失败: {str(screenshot_err)}")
                        return await self._default_screenshot(question, answer)
                else:
                    logger.warning("元宝点击了生成/下载按钮但未检测到结果图片")
                    return await self._default_screenshot(question, answer)
            else:
                logger.warning("元宝未找到生成图片按钮，直接使用默认截图")
                return await self._default_screenshot(question, answer)

            return await self._default_screenshot(question, answer)

        except Exception as e:
            logger.error(f"元宝截图流程异常: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
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