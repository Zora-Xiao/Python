# -*- coding: utf-8 -*-
from typing import Optional
from datetime import datetime
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
            logger.info(f"{self.platform_id} 开始登录...")

            login_button_selectors = [
                "button:has-text('login')",
                "button:has-text('Sign In')",
                "[data-testid='login']",
                ".login-btn"
            ]

            login_button = await self._find_visible_element(login_button_selectors)
            if not login_button:
                logger.warning(f"{self.platform_id} 登录按钮未找到")
                return False

            await login_button.click()
            await self.page.wait_for_timeout(2000)

            username_selectors = [
                "input[name='username']",
                "input[name='email']",
                "input[name='phone']",
                "input[type='text']"
            ]

            if not await self._fill_form_field(username_selectors, self.username):
                logger.warning(f"{self.platform_id} 用户名输入框未找到")
                return False

            password_selectors = [
                "input[name='password']",
                "input[type='password']"
            ]

            if not await self._fill_form_field(password_selectors, self.password):
                logger.warning(f"{self.platform_id} 密码输入框未找到")
                return False

            submit_selectors = [
                "button[type='submit']",
                "button:has-text('login')",
                "button:has-text('submit')",
                ".submit-btn"
            ]

            if await self._click_button(submit_selectors):
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
    
    async def screenshot(self, question: Question) -> tuple[Optional[str], bool, Optional[str], Optional[str]]:
        if self.page is None:
            return None, False, None, None
        
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
                return await self._default_screenshot(question)
            
            logger.info(f"元宝成功定位分享按钮，准备点击...")
            
            # --- 执行点击和后续流程 ---
            # 先获取分享按钮的详细信息
            try:
                share_btn_html = await share_btn.evaluate("el => el.outerHTML")
                share_btn_box = await share_btn.bounding_box()
                logger.info(f"元宝分享按钮HTML: {share_btn_html[:200]}")
                logger.info(f"元宝分享按钮位置: {share_btn_box}")
            except:
                pass
            
            clicked = await self._robust_click(share_btn, "分享按钮")
            if not clicked:
                logger.warning("元宝点击分享按钮失败，执行默认截图")
                return await self._default_screenshot(question)
            
            await self.page.wait_for_timeout(1500) 

            # --- 等待分享弹窗出现并查找生成图片按钮 ---
            logger.info("元宝等待分享弹窗出现...")
            share_bar_container = None
            
            # 尝试多种方式等待分享弹窗
            share_popup_selectors = [
                "div.agent-chat__share-bar-container",
                "div[class*='share-bar']",
                "[role='dialog'][class*='share']",
                "div[class*='share']"
            ]
            
            for popup_sel in share_popup_selectors:
                try:
                    share_bar_container = await self.page.wait_for_selector(popup_sel, timeout=3000, state="visible")
                    if share_bar_container:
                        logger.info(f"元宝分享弹窗已出现: {popup_sel}")
                        break
                except:
                    continue
            
            if not share_bar_container:
                logger.warning("元宝未找到分享弹窗")
                # 保存调试截图
                try:
                    debug_path = Path("screenshots") / f"yuanbao_no_popup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    await self.page.screenshot(path=str(debug_path), full_page=True)
                    logger.info(f"元宝无弹窗调试截图已保存: {debug_path}")
                except:
                    pass
                return await self._default_screenshot(question)
            
            # 获取弹窗的HTML用于调试
            try:
                popup_html = await share_bar_container.evaluate("el => el.outerHTML")
                logger.debug(f"元宝分享弹窗HTML: {popup_html[:500]}")
            except:
                pass
            
            # --- 查找生成图片按钮 ---
            logger.info("元宝步骤3: 查找生成图片按钮...")
            gen_btn = None
            
            # 根据提供的HTML结构，生成图片按钮的精准选择器
            gen_btn_selectors = [
                # 1. 最精准：基于完整结构路径
                "div.agent-chat__share-bar__content__center .agent-chat__share-bar__item:nth-child(2)",
                "div.agent-chat__share-bar__content__center > div.agent-chat__share-bar__item",
                
                # 2. 基于按钮名称文本查找（包含文本的div）
                "div.agent-chat__share-bar__item__name:has-text('生成图片')",
                
                # 3. 查找包含生成图片文本的item项
                "div.agent-chat__share-bar__item:has(div.agent-chat__share-bar__item__name:has-text('生成图片'))",
                
                # 4. 基于SVG特征（第二个SVG的path特征 - 生成图片的图标）
                "div.agent-chat__share-bar__item:has(svg path[d*='M2.5 5C2.5 4.44771'])",
                
                # 5. 通用选择器
                "div[class*='share-bar__item']:has(div:has-text('生成图片'))"
            ]
            
            found_items = []
            for selector in gen_btn_selectors:
                try:
                    elems = await self.page.query_selector_all(selector)
                    if elems:
                        logger.debug(f"元宝选择器 '{selector}' 匹配到 {len(elems)} 个元素")
                        for i, elem in enumerate(elems):
                            if await elem.is_visible():
                                try:
                                    text = await elem.text_content()
                                    html = await elem.evaluate("el => el.outerHTML")
                                    box = await elem.bounding_box()
                                    found_items.append({
                                        'selector': selector,
                                        'index': i,
                                        'text': text.strip() if text else None,
                                        'html': html[:150],
                                        'box': box
                                    })
                                except:
                                    found_items.append({
                                        'selector': selector,
                                        'index': i,
                                        'text': None,
                                        'html': None,
                                        'box': None
                                    })
                except Exception as e:
                    logger.debug(f"查找生成图片按钮失败: {e}")
                    continue
            
            # 打印所有找到的元素信息
            if found_items:
                logger.info(f"元宝找到 {len(found_items)} 个潜在按钮元素:")
                for item in found_items:
                    logger.info(f"  - 选择器: {item['selector']}")
                    logger.info(f"    索引: {item['index']}, 文本: {item['text']}")
                    logger.info(f"    位置: {item['box']}")
                    logger.debug(f"    HTML: {item['html']}")
            
            # 选择最可能的按钮
            for item in found_items:
                if item['text'] and '生成图片' in item['text']:
                    # 通过querySelectorAll重新获取元素
                    elems = await self.page.query_selector_all(item['selector'])
                    if elems and item['index'] < len(elems):
                        gen_btn = elems[item['index']]
                        logger.info(f"元宝选择包含'生成图片'文本的按钮")
                        break
                elif item['selector'] == "div.agent-chat__share-bar__content__center .agent-chat__share-bar__item:nth-child(2)":
                    # 第二个item通常是生成图片
                    elems = await self.page.query_selector_all(item['selector'])
                    if elems:
                        gen_btn = elems[0]
                        logger.info(f"元宝选择第二个分享按钮（通常是生成图片）")
                        break
            
            if not gen_btn and found_items:
                # 如果没有找到明确的生成图片按钮，使用第一个可见的item
                elems = await self.page.query_selector_all("div.agent-chat__share-bar__item")
                if elems:
                    for elem in elems:
                        if await elem.is_visible():
                            gen_btn = elem
                            text = await elem.text_content()
                            logger.info(f"元宝使用第一个可见的分享按钮，文本: {text.strip() if text else '未知'}")
                            break
            
            if gen_btn:
                logger.info("元宝准备点击生成图片按钮...")
                
                # 获取按钮信息
                try:
                    btn_text = await gen_btn.text_content()
                    btn_html = await gen_btn.evaluate("el => el.outerHTML")
                    btn_box = await gen_btn.bounding_box()
                    logger.info(f"元宝生成按钮文本: '{btn_text.strip() if btn_text else 'None'}'")
                    logger.info(f"元宝生成按钮位置: {btn_box}")
                    logger.debug(f"元宝生成按钮HTML: {btn_html[:300]}")
                except:
                    pass
                
                # 确保按钮在可视区域
                try:
                    await gen_btn.scroll_into_view_if_needed()
                    await self.page.wait_for_timeout(500)
                except:
                    pass
                
                # 尝试多种点击方式
                clicked_gen = False
                
                # 方式1: 直接点击生成按钮元素
                try:
                    await gen_btn.click(timeout=3000)
                    logger.info("元宝直接点击生成图片按钮")
                    clicked_gen = True
                except Exception as e:
                    logger.debug(f"直接点击失败: {e}")
                
                # 方式2: 如果直接点击失败，尝试点击内部的logo或name元素
                if not clicked_gen:
                    try:
                        # 查找按钮内部的可点击元素
                        inner_selectors = [
                            "div.agent-chat__share-bar__item__logo",
                            "div.agent-chat__share-bar__item__name",
                            "svg"
                        ]
                        for inner_sel in inner_selectors:
                            inner_elem = await gen_btn.query_selector(inner_sel)
                            if inner_elem:
                                await inner_elem.click(timeout=2000)
                                logger.info(f"元宝点击按钮内部元素: {inner_sel}")
                                clicked_gen = True
                                break
                    except Exception as e:
                        logger.debug(f"点击内部元素失败: {e}")
                
                # 方式3: JavaScript点击
                if not clicked_gen:
                    try:
                        await gen_btn.evaluate("el => el.click()")
                        logger.info("元宝使用JavaScript点击生成图片按钮")
                        clicked_gen = True
                    except Exception as e:
                        logger.debug(f"JS点击失败: {e}")
                
                # 方式4: 坐标点击
                if not clicked_gen:
                    try:
                        box = await gen_btn.bounding_box()
                        if box:
                            x = box['x'] + box['width'] / 2
                            y = box['y'] + box['height'] / 2
                            await self.page.mouse.click(x, y)
                            logger.info(f"元宝使用坐标点击生成图片按钮: ({x}, {y})")
                            clicked_gen = True
                    except Exception as e:
                        logger.debug(f"坐标点击失败: {e}")
                
                if not clicked_gen:
                    logger.error("元宝所有点击方式均失败")
                    return await self._default_screenshot(question)
                
                logger.info("元宝已点击生成图片按钮，等待图片生成及预览窗口出现...")
                
                # 增加图片生成等待时间，生成图片可能需要较长时间
                for wait_time in [3000, 3000, 4000]:
                    await self.page.wait_for_timeout(wait_time)
                    
                    # 检查是否出现图片预览弹窗
                    try:
                        preview_modal = await self.page.query_selector("div[class*='preview'], div[class*='modal'], [role='dialog']")
                        if preview_modal:
                            logger.info("元宝检测到图片预览弹窗出现")
                            break
                    except:
                        pass
                
                # --- 查找并点击下载按钮 ---
                logger.info("元宝步骤4: 查找并点击下载按钮...")
                download_btn = None
                
                download_selectors = [
                    # 精准选择器
                    "div.agent-chat__share-bar__item:has(div:has-text('下载'))",
                    "div[class*='share-bar'] button:has-text('下载')",
                    # 通用选择器
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
                            
                            # 获取下载按钮信息
                            try:
                                btn_text = await download_btn.text_content()
                                btn_box = await download_btn.bounding_box()
                                logger.info(f"元宝下载按钮文本: '{btn_text.strip() if btn_text else 'None'}'")
                                logger.info(f"元宝下载按钮位置: {btn_box}")
                            except:
                                pass
                            
                            break
                    except Exception as e:
                        logger.debug(f"查找下载按钮失败: {e}")
                        continue
                
                if download_btn:
                    logger.info("元宝准备点击下载按钮...")
                    
                    # 尝试多种点击方式
                    clicked_download = False
                    
                    # 方式1: 直接点击
                    try:
                        await download_btn.click(timeout=3000)
                        logger.info("元宝直接点击下载按钮")
                        clicked_download = True
                    except Exception as e:
                        logger.debug(f"直接点击下载按钮失败: {e}")
                    
                    # 方式2: JS点击
                    if not clicked_download:
                        try:
                            await download_btn.evaluate("el => el.click()")
                            logger.info("元宝JS点击下载按钮")
                            clicked_download = True
                        except Exception as e:
                            logger.debug(f"JS点击下载按钮失败: {e}")
                    
                    if clicked_download:
                        logger.info("元宝已点击下载按钮，等待图片下载...")
                        # 等待下载完成
                        await self.page.wait_for_timeout(5000)
                    else:
                        logger.warning("元宝点击下载按钮失败")
                else:
                    logger.warning("元宝未找到下载按钮")
                
                # --- 尝试截取生成的图片或预览区域 ---
                logger.info("元宝步骤5: 查找并截取生成的图片...")
                
                # 等待图片生成完成
                await self.page.wait_for_timeout(2000)
                
                # 保存调试截图和HTML
                try:
                    debug_path = Path("screenshots") / f"yuanbao_gen_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    await self.page.screenshot(path=str(debug_path), full_page=True)
                    logger.info(f"元宝生成调试截图已保存: {debug_path}")
                except:
                    pass
                
                img_container_selectors = [
                    # 图片预览窗口中的图片
                    "div[class*='preview'] img",
                    "div[class*='photo-view'] img",
                    "[role='dialog'] img",
                    ".modal img",
                    
                    # canvas截图
                    "canvas[class*='share']",
                    "canvas[class*='preview']",
                    
                    # 分享弹窗中的图片
                    "div.agent-chat__share-bar-container img",
                    "div.agent-chat__share-bar img",
                    
                    # 通用选择器
                    "img[src*='blob:']",
                    "img[src*='data:image']",
                    "img[class*='share']",
                    "img[class*='preview']"
                ]
                
                final_img_elem = None
                found_images = []
                
                # 先收集所有可能的图片元素
                for sel in img_container_selectors:
                    try:
                        elems = await self.page.query_selector_all(sel)
                        if elems:
                            for elem in elems:
                                if await elem.is_visible():
                                    try:
                                        src = await elem.get_attribute("src")
                                        box = await elem.bounding_box()
                                        found_images.append({
                                            'selector': sel,
                                            'element': elem,
                                            'src': src[:100] if src else None,
                                            'box': box
                                        })
                                    except:
                                        found_images.append({
                                            'selector': sel,
                                            'element': elem,
                                            'src': None,
                                            'box': None
                                        })
                    except Exception as e:
                        logger.debug(f"查找图片元素失败: {e}")
                        continue
                
                # 打印找到的图片信息
                if found_images:
                    logger.info(f"元宝找到 {len(found_images)} 个潜在图片元素:")
                    for i, img in enumerate(found_images):
                        logger.info(f"  - [{i}] 选择器: {img['selector']}")
                        logger.info(f"    src: {img['src']}")
                        logger.info(f"    位置: {img['box']}")
                
                # 选择最可能的图片（优先选择blob或canvas）
                for img_info in found_images:
                    if img_info['src'] and ('blob:' in img_info['src'] or 'data:image' in img_info['src']):
                        final_img_elem = img_info['element']
                        logger.info(f"元宝选择blob/data图片")
                        break
                    elif 'canvas' in img_info['selector']:
                        final_img_elem = img_info['element']
                        logger.info(f"元宝选择canvas元素")
                        break
                
                # 如果没有特殊的图片，选择第一个可见的图片
                if not final_img_elem and found_images:
                    final_img_elem = found_images[0]['element']
                    logger.info("元宝选择第一个可见图片")
                
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
                            return str(file_path), True, None, None
                        else:
                            logger.warning(f"元宝分享图片文件无效，回退到默认截图")
                            return await self._default_screenshot(question)
                    except Exception as screenshot_err:
                        logger.error(f"元宝截取图片元素失败: {str(screenshot_err)}")
                        return await self._default_screenshot(question)
                else:
                    logger.warning("元宝点击了生成/下载按钮但未检测到结果图片")
                    # 保存无图片时的调试信息
                    try:
                        debug_path = Path("screenshots") / f"yuanbao_no_image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                        await self.page.screenshot(path=str(debug_path), full_page=True)
                        logger.info(f"元宝无图片调试截图已保存: {debug_path}")
                    except:
                        pass
                    return await self._default_screenshot(question)
            else:
                logger.warning("元宝未找到生成图片按钮，直接使用默认截图")
                return await self._default_screenshot(question)

        except Exception as e:
            logger.error(f"元宝截图流程异常: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return await self._default_screenshot(question)

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
            logger.error(f"元宝默认截图失败：{str(e)}")
            return None, False, None, str(e)
    
    async def close(self):
        await super().close()