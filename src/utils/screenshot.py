from pathlib import Path
from typing import Optional
from playwright.async_api import async_playwright, Browser, Page
from src.models.question import Question
from src.utils.logger import logger
import urllib.parse
import pyperclip


class ScreenshotTool:
    def __init__(self, screenshot_dir: str = "screenshots"):
        self.screenshot_dir = Path(screenshot_dir)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.browser: Optional[Browser] = None

    async def _get_browser(self) -> Browser:
        if self.browser is None:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(headless=True)
        return self.browser

    async def _wait_for_response_complete(self, page: Page, platform_id: str) -> bool:
        """等待AI回复完成（检测回复内容已渲染且不再加载）"""
        try:
            logger.info(f"{platform_id}开始等待AI回复完成...")
            logger.info(f"{platform_id}等待方法被调用，准备进入检测循环")

            content_selectors = [
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
                ".ds-message-content",
                ".deepseek-message",
                "div[class*='message']",
                "div[class*='assistant']",
            ]
            
            loading_indicators = [
                ".loading",
                ".typing",
                "span:has-text('正在')",
                "span:has-text('思考')",
                "span:has-text('typing')",
                "[aria-label*='loading']",
                "[aria-label*='typing']",
                ".ant-spin",
                ".spinner",
                "div[class*='loading']",
                "svg[class*='spin']",
            ]

            max_iterations = 60
            consecutive_ready_count = 0
            required_consecutive = 3

            for iteration in range(max_iterations):
                try:
                    logger.info(f"{platform_id}等待检测第 {iteration+1}/{max_iterations} 次")

                    # 优先检查输入框是否可用（回复完成后输入框会变为可用）
                    try:
                        textarea = await page.query_selector("textarea")
                        if textarea:
                            is_disabled = await textarea.get_attribute("disabled")
                            if is_disabled is None:
                                logger.info(f"{platform_id}输入框已可用，判定回复已完成")
                                await page.wait_for_timeout(1000)
                                return True
                    except Exception as e:
                        logger.debug(f"{platform_id}检查输入框失败: {str(e)}")
                        pass

                    is_loading = False
                    for loading_selector in loading_indicators:
                        try:
                            loading_elements = await page.query_selector_all(loading_selector)
                            if loading_elements:
                                for elem in loading_elements:
                                    if await elem.is_visible():
                                        is_loading = True
                                        break
                                if is_loading:
                                    break
                        except Exception as e:
                            logger.debug(f"{platform_id}检查loading选择器 {loading_selector} 失败: {str(e)}")
                            continue
                    
                    if is_loading:
                        consecutive_ready_count = 0
                        logger.info(f"{platform_id}检测到加载中...")
                        await page.wait_for_timeout(1000)
                        continue

                    content_found = False
                    for selector in content_selectors:
                        try:
                            elements = await page.query_selector_all(selector)
                            if elements and len(elements) > 0:
                                last_element = elements[-1]
                                is_visible = await last_element.is_visible()
                                if is_visible:
                                    text = await last_element.inner_text()
                                    if text and len(text.strip()) > 10:
                                        content_found = True
                                        logger.info(f"{platform_id}检测到回复内容已渲染")
                                        break
                        except Exception as e:
                            logger.debug(f"{platform_id}检查content选择器 {selector} 失败: {str(e)}")
                            continue

                    if content_found:
                        consecutive_ready_count += 1
                        logger.info(f"{platform_id}连续检测到准备好的次数: {consecutive_ready_count}/{required_consecutive}")
                        if consecutive_ready_count >= required_consecutive:
                            await page.wait_for_timeout(1000)
                            logger.info(f"{platform_id}回复已完成，准备返回")
                            return True
                    else:
                        consecutive_ready_count = 0

                except Exception as e:
                    logger.error(f"{platform_id}等待检测异常: {str(e)}")
                    pass

                if iteration % 5 == 0:
                    logger.info(f"{platform_id}仍在等待AI回复... ({iteration}/{max_iterations})")

                await page.wait_for_timeout(1000)

            logger.warning(f"{platform_id}等待AI回复完成超时（{max_iterations}秒），继续执行...")
            return True

        except Exception as e:
            logger.error(f"{platform_id}等待回复完成时发生错误: {str(e)}")
            return False

    async def download_shared_image(self, page: Page, platform_id: str, question: Question) -> Optional[str]:
        """尝试从AI平台下载分享图片"""
        if platform_id == "qwen":
            return await self._qwen_download_shared_image(page, question)
        elif platform_id == "deepseek":
            return await self._deepseek_download_shared_image(page, question)
        else:
            return await self._doubao_download_shared_image(page, platform_id, question)
    
    async def _doubao_download_shared_image(self, page: Page, platform_id: str, question: Question) -> Optional[str]:
        """豆包平台：三步流程下载分享图片（分享会话 → 分享图片 → 下载图片）"""
        try:
            download_path = self.screenshot_dir / f"{platform_id}_{question.id}_{question.timestamp.strftime('%Y%m%d_%H%M%S')}_shared.png"

            # ========== 第一步：点击分享会话按钮（带SVG图标的特定按钮） ==========
            logger.info(f"{platform_id}【第一步】查找分享会话按钮...")
            
            share_session_selectors = [
                "button[data-dbx-name='button'][data-state='closed'][data-trigger-type='hover'][class*='rounded-dbx-sm'][class*='p-\\[4px\\]'][class*='text-\\[16px\\]'][class*='leading-\\[24px\\]']",
                "button[data-dbx-name='button'][data-state='closed'][data-trigger-type='hover'][class*='rounded-dbx-sm'][class*='p-\\[4px\\]']",
                "button[data-dbx-name='button'][data-state='closed'][data-trigger-type='hover'][class*='rounded-dbx-sm'][class*='text-\\[16px\\]']",
                "button[data-dbx-name='button'][data-state='closed'][data-trigger-type='hover'][class*='rounded-dbx-sm']",
                "button[data-dbx-name='button'][data-state='closed'][data-trigger-type='hover'][class*='p-\\[4px\\]'][class*='text-\\[16px\\]']",
                "button[data-dbx-name='button'][data-state='closed'][data-trigger-type='hover'][class*='p-\\[4px\\]']"
            ]

            share_session_button = None
            
            # 优先在消息区域查找
            try:
                messages = await page.query_selector_all("[role='listitem'], .message-item, .chat-item, div[data-message-id]")
                if messages and len(messages) > 0:
                    last_message = messages[-1]
                    buttons_in_message = await last_message.query_selector_all("button")
                    
                    for btn in buttons_in_message:
                        try:
                            is_visible = await btn.is_visible()
                            has_svg = await btn.query_selector("svg") is not None
                            data_dbx = await btn.get_attribute("data-dbx-name") or ""
                            data_state = await btn.get_attribute("data-state") or ""
                            data_trigger = await btn.get_attribute("data-trigger-type") or ""
                            class_name = await btn.get_attribute("class") or ""
                            
                            if is_visible and has_svg and data_dbx == "button" and data_state == "closed" and data_trigger == "hover":
                                if "rounded-dbx-sm" in class_name and "p-" in class_name and "text-" in class_name:
                                    share_session_button = btn
                                    logger.info(f"{platform_id}【第一步】在消息区域找到分享会话按钮")
                                    break
                        except:
                            continue
            except Exception as e:
                logger.info(f"{platform_id}【第一步】在消息区域查找按钮失败: {str(e)}")

            # 如果消息区域未找到，使用选择器列表查找
            if not share_session_button:
                for selector in share_session_selectors:
                    try:
                        elements = await page.query_selector_all(selector)
                        if elements and len(elements) > 0:
                            logger.info(f"{platform_id}【第一步】找到 {len(elements)} 个候选按钮: {selector}")
                            
                            visible_buttons = []
                            for elem in elements:
                                try:
                                    is_visible = await elem.is_visible()
                                    if is_visible:
                                        has_svg = await elem.query_selector("svg") is not None
                                        if has_svg:
                                            visible_buttons.append(elem)
                                except:
                                    continue
                            
                            if len(visible_buttons) > 0:
                                if len(visible_buttons) >= 2:
                                    share_session_button = visible_buttons[-1]
                                    logger.info(f"{platform_id}【第一步】选择第 {len(visible_buttons)} 个按钮作为分享会话按钮")
                                else:
                                    share_session_button = visible_buttons[0]
                                    logger.info(f"{platform_id}【第一步】找到分享会话按钮: {selector}")
                                break
                    except Exception as e:
                        logger.info(f"{platform_id}【第一步】选择器 {selector} 查询失败: {str(e)}")
                        continue

            if not share_session_button:
                logger.info(f"{platform_id}【第一步】未找到分享会话按钮，将使用页面截图")
                return None

            logger.info(f"{platform_id}【第一步】点击分享会话按钮...")
            await share_session_button.click()
            await page.wait_for_timeout(2000)

            # ========== 第二步：点击"分享图片"按钮 ==========
            logger.info(f"{platform_id}【第二步】查找分享图片按钮...")
            
            share_image_selectors = [
                "button[data-dbx-name='button'][class*='rounded-dbx-lg'][class*='px-\\[12px\\]'][class*='py-\\[8px\\]'][class*='text-\\[14px\\]'][class*='bg-dbx-fill-trans-20']:has-text('分享图片')",
                "button[data-dbx-name='button'][class*='rounded-dbx-lg'][class*='px-\\[12px\\]'][class*='py-\\[8px\\]']:has-text('分享图片')",
                "button[data-dbx-name='button'][class*='rounded-dbx-lg'][class*='bg-dbx-fill-trans-20']:has-text('分享图片')",
                "button[data-dbx-name='button'][class*='rounded-dbx-lg']:has-text('分享图片')",
                "button[data-dbx-name='button'][class*='px-\\[12px\\]'][class*='py-\\[8px\\]']:has-text('分享图片')",
                "button.flex.shrink-0.items-center.justify-center[data-dbx-name='button']:has-text('分享图片')",
                "button:has-text('分享图片')"
            ]

            share_image_button = None
            for selector in share_image_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements and len(elements) > 0:
                        for elem in elements:
                            try:
                                is_visible = await elem.is_visible()
                                if is_visible:
                                    share_image_button = elem
                                    logger.info(f"{platform_id}【第二步】找到分享图片按钮: {selector}")
                                    break
                            except:
                                continue
                        if share_image_button:
                            break
                except:
                    continue

            # 通过子元素文本查找
            if not share_image_button:
                try:
                    all_buttons = await page.query_selector_all("button[data-dbx-name='button']")
                    for btn in all_buttons:
                        try:
                            text = await btn.inner_text()
                            if not text:
                                child_div = await btn.query_selector("div.min-w-0.truncate")
                                if child_div:
                                    text = await child_div.inner_text()
                            
                            is_visible = await btn.is_visible()
                            if "分享图片" in text and is_visible:
                                share_image_button = btn
                                logger.info(f"{platform_id}【第二步】通过子元素文本找到分享图片按钮")
                                break
                        except:
                            pass
                except Exception as e:
                    logger.info(f"{platform_id}【第二步】获取弹窗按钮信息失败: {str(e)}")

            if not share_image_button:
                await page.keyboard.press("Escape")
                logger.info(f"{platform_id}【第二步】未找到分享图片按钮，将使用页面截图")
                return None

            logger.info(f"{platform_id}【第二步】点击分享图片按钮...")
            await share_image_button.click()
            await page.wait_for_timeout(2000)

            # ========== 第三步：点击"下载图片"按钮 ==========
            logger.info(f"{platform_id}【第三步】查找下载图片按钮...")
            
            download_image_selectors = [
                "button[data-dbx-name='button'][class*='rounded-dbx-lg'][class*='px-\\[12px\\]'][class*='py-\\[8px\\]'][class*='text-\\[14px\\]'][class*='bg-dbx-text-highlight']:has-text('下载图片')",
                "button[data-dbx-name='button'][class*='rounded-dbx-lg'][class*='px-\\[12px\\]'][class*='py-\\[8px\\]'][class*='bg-dbx-text-highlight']:has-text('下载图片')",
                "button[data-dbx-name='button'][class*='rounded-dbx-lg'][class*='bg-dbx-text-highlight']:has-text('下载图片')",
                "button[data-dbx-name='button']:has-text('下载图片')",
                "button:has-text('下载图片')"
            ]

            download_button_element = None
            for selector in download_image_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements and len(elements) > 0:
                        for elem in elements:
                            try:
                                is_visible = await elem.is_visible()
                                if is_visible:
                                    download_button_element = elem
                                    logger.info(f"{platform_id}【第三步】找到下载图片按钮: {selector}")
                                    break
                            except:
                                continue
                        if download_button_element:
                            break
                except:
                    continue

            # 通过子元素文本查找
            if not download_button_element:
                try:
                    all_buttons = await page.query_selector_all("button[data-dbx-name='button']")
                    for btn in all_buttons:
                        try:
                            text = await btn.inner_text()
                            if not text:
                                child_div = await btn.query_selector("div.min-w-0.truncate")
                                if child_div:
                                    text = await child_div.inner_text()
                            
                            is_visible = await btn.is_visible()
                            if "下载图片" in text and is_visible:
                                download_button_element = btn
                                logger.info(f"{platform_id}【第三步】通过子元素文本找到下载图片按钮")
                                break
                        except:
                            pass
                except Exception as e:
                    logger.info(f"{platform_id}【第三步】获取按钮信息失败: {str(e)}")

            if not download_button_element:
                await page.keyboard.press("Escape")
                logger.info(f"{platform_id}【第三步】未找到下载图片按钮，将使用页面截图")
                return None

            # 执行下载
            async with page.expect_download() as download_info:
                await download_button_element.click()
                download = await download_info.value

                logger.info(f"{platform_id}【第三步】正在下载图片: {download.url}")
                await download.save_as(str(download_path))

            await page.keyboard.press("Escape")
            logger.info(f"{platform_id}三步分享流程完成，图片已保存：{download_path}")
            return str(download_path)

        except Exception as e:
            logger.error(f"{platform_id}下载分享图片失败：{str(e)}")
            try:
                await page.keyboard.press("Escape")
            except:
                pass
            return None
    
    async def _qwen_download_shared_image(self, page: Page, question: Question) -> Optional[str]:
        """千问平台：三步流程（全屏截图 → 点击更多按钮 → 点击分享 → 复制链接）"""
        try:
            platform_id = "qwen"
            download_path = self.screenshot_dir / f"{platform_id}_{question.id}_{question.timestamp.strftime('%Y%m%d_%H%M%S')}_shared.png"
            shared_link = None  # 初始化分享链接变量

            # ========== 第一步：页面全屏截图 ==========
            logger.info(f"{platform_id}【第一步】页面全屏截图...")
            try:
                await page.wait_for_timeout(2000)
                await page.screenshot(
                    path=str(download_path),
                    full_page=True,
                    timeout=60000
                )
                logger.info(f"{platform_id}【第一步】页面全屏截图已保存：{download_path}")
            except Exception as e:
                logger.error(f"{platform_id}【第一步】页面截图失败：{str(e)}")
                return None

            # ========== 第二步：点击"..."更多按钮 ==========
            logger.info(f"{platform_id}【第二步】查找更多按钮（...）...")
            
            more_button_selectors = [
                "svg[data-spm-anchor-id*='more']",
                "svg use[href*='icon-line-more']",
                ".ant-dropdown-trigger svg",
                "button:has(svg use[href*='more'])",
                "[role='button']:has(svg use[href*='more'])"
            ]
            
            more_button = None
            for selector in more_button_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements and len(elements) > 0:
                        for elem in elements:
                            try:
                                is_visible = await elem.is_visible()
                                if is_visible:
                                    more_button = elem
                                    logger.info(f"{platform_id}【第二步】找到更多按钮: {selector}")
                                    break
                            except:
                                continue
                        if more_button:
                            break
                except:
                    continue
            
            if not more_button:
                try:
                    all_svgs = await page.query_selector_all("svg")
                    for svg in all_svgs:
                        try:
                            use_elem = await svg.query_selector("use")
                            if use_elem:
                                href = await use_elem.get_attribute("xlink:href") or await use_elem.get_attribute("href")
                                if href and ("more" in href.lower() or "icon-line-more" in href):
                                    is_visible = await svg.is_visible()
                                    if is_visible:
                                        more_button = svg
                                        logger.info(f"{platform_id}【第二步】通过SVG找到更多按钮")
                                        break
                        except:
                            pass
                except Exception as e:
                    logger.info(f"{platform_id}【第二步】查找SVG按钮失败: {str(e)}")

            if not more_button:
                logger.info(f"{platform_id}【第二步】未找到更多按钮，跳过分享链接")
                return str(download_path)

            logger.info(f"{platform_id}【第二步】点击更多按钮...")
            await more_button.click()
            await page.wait_for_timeout(3000)  # 增加等待时间，确保下拉菜单完全显示

            # 等待下拉菜单出现
            try:
                await page.wait_for_selector(".ant-dropdown", timeout=3000)
                logger.info(f"{platform_id}【第二步】下拉菜单已出现")
            except:
                logger.info(f"{platform_id}【第二步】未检测到下拉菜单")

            # ========== 第三步：点击分享按钮 ==========
            logger.info(f"{platform_id}【第三步】查找分享按钮...")
            
            # 根据实际HTML结构优化选择器，按优先级排序
            share_button_selectors = [
                # 最精确的选择器 - 根据用户提供的HTML结构
                "li[data-menu-id='menu-content-share']",
                "li.ant-dropdown-menu-item.chat-menu-item[role='menuitem']",
                # 组合选择器
                "li.ant-dropdown-menu-item.chat-menu-item",
                ".ant-dropdown-menu-item.chat-menu-item",
                "[role='menuitem'].chat-menu-item",
                # 包含分享文本的元素
                ".chat-menu-item-icon-text:has-text('分享')",
                "span.chat-menu-item-icon-text",
                ".ant-dropdown-menu-title-content:has(.chat-menu-item-icon-text)",
                # 通用选择器
                "[role='menuitem']",
                "li.ant-dropdown-menu-item",
                ".ant-dropdown-menu-item",
                ".ant-dropdown-menu-title-content",
                # SVG图标选择器
                "svg use[xlink:href*='share']",
                "svg use[xlink:href='#icon-a-share20']",
                ".anticon svg",
                # 文本匹配选择器
                "span:has-text('分享')",
                ".ant-dropdown-menu-item:has(span:has-text('分享'))",
                "[aria-label*='分享']",
                ".share-action",
                "[data-key='share']",
                ".icon-share",
                "svg.icon-share"
            ]
            
            share_button = None
            for selector in share_button_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements and len(elements) > 0:
                        for elem in elements:
                            try:
                                is_visible = await elem.is_visible()
                                if is_visible:
                                    # 检查是否包含"分享"文本
                                    text = await elem.inner_text()
                                    has_share_text = False
                                    
                                    if text and "分享" in text:
                                        has_share_text = True
                                    else:
                                        # 检查子元素是否包含分享文本
                                        child_span = await elem.query_selector(".chat-menu-item-icon-text")
                                        if child_span:
                                            child_text = await child_span.inner_text()
                                            if child_text and "分享" in child_text:
                                                has_share_text = True
                                    
                                    if has_share_text:
                                        share_button = elem
                                        logger.info(f"{platform_id}【第三步】找到分享按钮: {selector}")
                                        break
                            except:
                                continue
                        if share_button:
                            break
                except:
                    continue

            # 通过子元素文本查找（增强版）
            if not share_button:
                try:
                    # 尝试查找所有可见的下拉菜单项
                    all_items = await page.query_selector_all("li.ant-dropdown-menu-item, [role='menuitem']")
                    for item in all_items:
                        try:
                            is_visible = await item.is_visible()
                            if is_visible:
                                # 查找子元素中的分享文本（尝试多种选择器）
                                text_selectors = [
                                    ".chat-menu-item-icon-text",
                                    ".ant-dropdown-menu-title-content",
                                    "span",
                                    "span.title",
                                    "span.text"
                                ]
                                found_share_text = False
                                for text_selector in text_selectors:
                                    text_elem = await item.query_selector(text_selector)
                                    if text_elem:
                                        text = await text_elem.inner_text()
                                        if text and "分享" in text:
                                            found_share_text = True
                                            break
                                
                                if found_share_text:
                                    share_button = item
                                    logger.info(f"{platform_id}【第三步】通过子元素文本找到分享按钮")
                                    break
                        except:
                            pass
                except Exception as e:
                    logger.info(f"{platform_id}【第三步】通过子元素查找分享按钮失败: {str(e)}")

            # 通过SVG图标查找分享按钮
            if not share_button:
                try:
                    share_icons = await page.query_selector_all("svg path[d*='M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z'], svg path[d*='M8 12a1 1 0 0 0-1-1H3a1 1 0 0 0-1 1v4a1 1 0 0 0 1 1h4a1 1 0 0 0 1-1v-4zm10-1a1 1 0 0 0-1 1v4a1 1 0 0 0 1 1h4a1 1 0 0 0 1-1v-4a1 1 0 0 0-1-1h-4zm-1 0H3a1 1 0 0 0-1 1v4a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-4a1 1 0 0 0-1-1z']")
                    for icon in share_icons:
                        try:
                            is_visible = await icon.is_visible()
                            if is_visible:
                                # 获取父级按钮元素
                                parent_button = await icon.query_selector("xpath=../..")
                                if parent_button:
                                    tag_name = await parent_button.evaluate("el => el.tagName.toLowerCase()")
                                    if tag_name == "button" or tag_name == "li":
                                        share_button = parent_button
                                        logger.info(f"{platform_id}【第三步】通过SVG图标找到分享按钮")
                                        break
                        except:
                            pass
                except Exception as e:
                    logger.info(f"{platform_id}【第三步】通过SVG图标查找分享按钮失败: {str(e)}")

            if not share_button:
                await page.keyboard.press("Escape")
                logger.info(f"{platform_id}【第三步】未找到分享按钮，跳过分享链接")
                return str(download_path)

            logger.info(f"{platform_id}【第三步】点击分享按钮...")
            await share_button.click()
            await page.wait_for_timeout(2000)

            # ========== 第四步：点击复制链接 ==========
            logger.info(f"{platform_id}【第四步】查找复制链接按钮...")
            
            copy_link_selectors = [
                "button:has-text('复制链接')",
                ".copy-link-btn",
                "[data-action='copy-link']",
                ".ant-btn:has-text('复制')"
            ]
            
            copy_button = None
            for selector in copy_link_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements and len(elements) > 0:
                        for elem in elements:
                            try:
                                is_visible = await elem.is_visible()
                                if is_visible:
                                    copy_button = elem
                                    logger.info(f"{platform_id}【第四步】找到复制链接按钮: {selector}")
                                    break
                            except:
                                continue
                        if copy_button:
                            break
                except:
                    continue

            if not copy_button:
                await page.keyboard.press("Escape")
                logger.info(f"{platform_id}【第四步】未找到复制链接按钮")
                return str(download_path)

            logger.info(f"{platform_id}【第四步】点击复制链接按钮...")
            await copy_button.click()
            await page.wait_for_timeout(1000)

            # 尝试获取剪贴板内容
            try:
                shared_link = await page.evaluate("navigator.clipboard.readText()")
                if shared_link:
                    # 保存分享链接到文件
                    link_path = self.screenshot_dir / f"{platform_id}_{question.id}_{question.timestamp.strftime('%Y%m%d_%H%M%S')}_link.txt"
                    with open(link_path, 'w', encoding='utf-8') as f:
                        f.write(shared_link)
                    logger.info(f"{platform_id}【第四步】分享链接已保存：{link_path}")
            except Exception as e:
                logger.info(f"{platform_id}【第四步】获取剪贴板失败: {str(e)}")

            await page.keyboard.press("Escape")
            logger.info(f"{platform_id}四步分享流程完成")
            return str(download_path)

        except Exception as e:
            logger.error(f"{platform_id}下载分享图片失败：{str(e)}")
            try:
                await page.keyboard.press("Escape")
            except:
                pass
            return None
    
    async def _deepseek_download_shared_image(self, page: Page, question: Question) -> Optional[str]:
        """Deepseek平台：四步流程（全屏截图 → 点击分享按钮 → 点击创建分享链接 → 点击创建并复制）"""
        try:
            platform_id = "deepseek"
            download_path = self.screenshot_dir / f"{platform_id}_{question.id}_{question.timestamp.strftime('%Y%m%d_%H%M%S')}_shared.png"
            shared_link = None  # 初始化分享链接变量

            # ========== 第一步：页面全屏截图 ==========
            logger.info(f"{platform_id}【第一步】页面全屏截图...")
            try:
                await page.wait_for_timeout(2000)
                await page.screenshot(
                    path=str(download_path),
                    full_page=True,
                    timeout=60000
                )
                logger.info(f"{platform_id}【第一步】页面全屏截图已保存：{download_path}")
            except Exception as e:
                logger.error(f"{platform_id}【第一步】页面截图失败：{str(e)}")
                return None

            # ========== 第二步：点击分享按钮（SVG图标） ==========
            logger.info(f"{platform_id}【第二步】查找分享按钮（SVG图标）...")
            
            share_button_selectors = [
                "svg[viewBox='0 0 16 16'] path[d*='M7.95889 1.52285']",
                "svg[width='16'][height='16']:has(path[d*='M7.95889'])",
                "button:has(svg[width='16'][height='16'])",
                "[role='button']:has(svg[width='16'][height='16'])",
                # 新增更多选择器
                "button:has(svg)",
                "[role='button']:has(svg)",
                "svg[class*='share']",
                "button[class*='share']",
                "[aria-label*='share']",
                "[aria-label*='分享']",
                "button:has-text('分享')",
                ".share-button"
            ]
            
            share_button = None
            for selector in share_button_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements and len(elements) > 0:
                        for elem in elements:
                            try:
                                is_visible = await elem.is_visible()
                                if is_visible:
                                    # 如果找到的是path元素，获取其父svg
                                    tag_name = await elem.evaluate("el => el.tagName.toLowerCase()")
                                    if tag_name == "path":
                                        elem = await elem.query_selector("xpath=..")
                                    # 如果找到的是svg，获取其父按钮
                                    tag_name = await elem.evaluate("el => el.tagName.toLowerCase()")
                                    if tag_name == "svg":
                                        parent_button = await elem.query_selector("xpath=..")
                                        if parent_button:
                                            elem = parent_button
                                    share_button = elem
                                    logger.info(f"{platform_id}【第二步】找到分享按钮: {selector}")
                                    break
                            except:
                                continue
                        if share_button:
                            break
                except:
                    continue

            if not share_button:
                logger.info(f"{platform_id}【第二步】未找到分享按钮，跳过分享链接")
                return str(download_path)

            logger.info(f"{platform_id}【第二步】点击分享按钮...")
            await share_button.click()
            await page.wait_for_timeout(2000)

            # ========== 第三步：点击创建并复制按钮 ==========
            logger.info(f"{platform_id}【第三步】查找创建并复制按钮...")
            
            create_link_button = None
            
            # 策略1：使用JavaScript直接查找包含特定文本的按钮（支持中文和Unicode编码）
            logger.info(f"{platform_id}【第三步】策略1：使用JavaScript查找按钮...")
            try:
                js_find_button = """
                (function() {
                    var buttons = document.querySelectorAll('[role=\"button\"], button, .ds-basic-button');
                    var targetTexts = ['创建并复制', '\u521b\u5efa\u5e76\u590d\u5236', 'create and copy', '复制分享链接', '鍒涘缓骞跺鍒?', '鍒涘缓鍒嗕韩閾炬帴'];
                    for(var i = 0; i < buttons.length; i++) {
                        var btn = buttons[i];
                        var text = btn.textContent || btn.innerText || '';
                        text = text.trim();
                        if(btn.offsetWidth > 0 && btn.offsetHeight > 0) {
                            for(var j = 0; j < targetTexts.length; j++) {
                                if(text.indexOf(targetTexts[j]) !== -1) {
                                    btn.setAttribute('data-found-btn', 'create-and-copy');
                                    return 'found_create_and_copy:' + text;
                                }
                            }
                        }
                    }
                    return 'not_found';
                })()
                """
                js_result = await page.evaluate(js_find_button)
                logger.info(f"{platform_id}【第三步】JavaScript查找结果: {js_result}")
                
                if js_result.startswith('found_create_and_copy'):
                    create_link_button = await page.query_selector("[data-found-btn='create-and-copy']")
                    if create_link_button:
                        text = await create_link_button.text_content()
                        logger.info(f"{platform_id}【第三步】通过JavaScript找到创建并复制按钮: {text.strip()}")
            except Exception as e:
                logger.info(f"{platform_id}【第三步】JavaScript查找失败: {str(e)}")
            
            # 策略2：如果没找到，使用选择器查找
            if not create_link_button:
                logger.info(f"{platform_id}【第三步】策略2：使用选择器查找按钮...")
                create_link_selectors = [
                    "[role='button']",
                    "button",
                    ".ds-basic-button",
                    ".ds-modal-footer [role='button']",
                    ".ds-modal-footer button",
                    "[class*='primary']"
                ]
                
                for selector in create_link_selectors:
                    try:
                        elements = await page.query_selector_all(selector)
                        if elements and len(elements) > 0:
                            for elem in elements:
                                try:
                                    is_visible = await elem.is_visible()
                                    if is_visible:
                                        text = await elem.text_content()
                                        text = text.strip() if text else ""
                                        # 优先找"创建并复制"按钮
                                        if "创建并复制" in text:
                                            create_link_button = elem
                                            logger.info(f"{platform_id}【第三步】找到创建并复制按钮: {selector}, 文本: {text}")
                                            break
                                except:
                                    continue
                            if create_link_button:
                                break
                    except:
                        continue
            
            # 策略3：如果还是没找到"创建并复制"，找"创建分享链接"按钮
            if not create_link_button:
                logger.info(f"{platform_id}【第三步】策略3：查找创建分享链接按钮...")
                for selector in create_link_selectors:
                    try:
                        elements = await page.query_selector_all(selector)
                        if elements and len(elements) > 0:
                            for elem in elements:
                                try:
                                    is_visible = await elem.is_visible()
                                    if is_visible:
                                        text = await elem.text_content()
                                        text = text.strip() if text else ""
                                        if "创建分享链接" in text:
                                            create_link_button = elem
                                            logger.info(f"{platform_id}【第三步】找到创建分享链接按钮: {selector}, 文本: {text}")
                                            break
                                except:
                                    continue
                            if create_link_button:
                                break
                    except:
                        continue

            if not create_link_button:
                await page.keyboard.press("Escape")
                logger.info(f"{platform_id}【第三步】未找到创建并复制按钮，跳过分享链接")
                return str(download_path)

            logger.info(f"{platform_id}【第三步】点击创建分享链接按钮...")
            # 在点击复制按钮前清空剪贴板，确保不会被之前的内容干扰
            pyperclip.copy("")
            await page.wait_for_timeout(500)
            
            # 记录点击前的页面URL
            before_url = await page.evaluate("window.location.href")
            logger.info(f"{platform_id}【第三步】点击前页面URL: {before_url}")
            
            # 使用 force=True 强制点击按钮，绕过可能的元素拦截
            await create_link_button.click(force=True)
            await page.wait_for_timeout(3000)  # 等待分享链接生成
            
            # 检查是否需要再次点击"复制"按钮（如果是"创建分享链接"按钮而不是"创建并复制"按钮）
            logger.info(f"{platform_id}【第三步】检查是否需要点击复制按钮...")
            copy_button = None
            copy_selectors = [
                "button:has-text('复制')",
                "[role='button']:has-text('复制')",
                ".copy-btn",
                ".ds-basic-button:has-text('复制')",
                "[class*='copy']"
            ]
            
            for selector in copy_selectors:
                try:
                    copy_button = await page.query_selector(selector)
                    if copy_button and await copy_button.is_visible():
                        text = await copy_button.text_content()
                        logger.info(f"{platform_id}【第三步】找到复制按钮: {selector}, 文本: {text.strip()}")
                        await copy_button.click(force=True)
                        await page.wait_for_timeout(2000)
                        break
                except:
                    continue
            
            # 记录点击后的页面URL
            after_url = await page.evaluate("window.location.href")
            logger.info(f"{platform_id}【第三步】点击后页面URL: {after_url}")
            
            # 检查URL是否包含分享链接
            if 'deepseek.com/share' in after_url:
                shared_link = after_url
                logger.info(f"{platform_id}【第三步】从页面URL获取分享链接: {shared_link}")

            # ========== 第四步：从剪贴板读取分享链接 ==========
            logger.info(f"{platform_id}【第四步】从剪贴板读取分享链接...")
            if not shared_link:
                shared_link = None
            
            # 增加等待后先检查页面变化
            await page.wait_for_timeout(2000)
            
            # 新增：尝试直接从页面中查找包含share的按钮或链接，可能需要再次点击
            if not shared_link:
                logger.info(f"{platform_id}【第四步】尝试查找分享链接按钮并点击...")
                try:
                    share_link_buttons = await page.query_selector_all("button:has-text('分享链接'), button:has-text('复制链接'), .copy-link-btn, [data-action*='copy'], button:has-text('复制')")
                    for btn in share_link_buttons:
                        if await btn.is_visible():
                            logger.info(f"{platform_id}【第四步】找到分享链接按钮，点击尝试复制...")
                            await btn.click()
                            await page.wait_for_timeout(2000)
                            break
                except Exception as e:
                    logger.info(f"{platform_id}【第四步】查找分享链接按钮失败: {str(e)}")
            
            # 新增：检查页面上所有可见的按钮，获取它们的文本内容用于调试
            if not shared_link:
                logger.info(f"{platform_id}【第四步】调试：获取页面上所有可见按钮的文本...")
                try:
                    all_buttons = await page.query_selector_all("button")
                    button_texts = []
                    for btn in all_buttons:
                        try:
                            if await btn.is_visible():
                                text = await btn.inner_text()
                                if text and len(text.strip()) > 0:
                                    button_texts.append(text.strip())
                        except:
                            continue
                    logger.info(f"{platform_id}【第四步】页面上可见按钮文本: {button_texts[:20]}")
                except Exception as e:
                    logger.info(f"{platform_id}【第四步】获取按钮文本失败: {str(e)}")
            
            # 首先尝试从弹窗或提示信息中提取分享链接
            logger.info(f"{platform_id}【第四步】尝试从弹窗内容提取分享链接...")
            
            # 增加更多选择器来查找分享链接元素
            try:
                # 尝试查找包含分享链接的输入框或文本元素
                link_input_selectors = [
                    "input[value*='deepseek.com']",
                    "textarea[value*='deepseek.com']",
                    "div[contenteditable='true']",
                    "[data-testid*='share']",
                    "[aria-label*='分享']",
                    "div[class*='share-link']",
                    "input[class*='share']",
                ]
                for selector in link_input_selectors:
                    try:
                        element = await page.query_selector(selector)
                        if element and await element.is_visible():
                            value = await element.get_attribute('value')
                            if value and 'deepseek.com/share' in value:
                                shared_link = value.strip()
                                logger.info(f"{platform_id}【第四步】从输入框找到分享链接: {shared_link}")
                                break
                            text = await element.text_content()
                            if text and 'deepseek.com/share' in text:
                                shared_link = text.strip()
                                logger.info(f"{platform_id}【第四步】从文本内容找到分享链接: {shared_link}")
                                break
                    except:
                        continue
            except Exception as e:
                logger.info(f"{platform_id}【第四步】额外选择器查找失败: {str(e)}")
            try:
                popup_selectors = [
                    "[class*='popup'] [class*='link']",
                    "[class*='modal'] [class*='link']",
                    "[class*='dialog'] [class*='link']",
                    "[class*='share'] [class*='link']",
                    "[class*='copy'] [class*='link']",
                    "div[class*='link']",
                    "span[class*='link']",
                    "p[class*='link']",
                    "[class*='result'] [class*='link']",
                    "[class*='success'] [class*='link']",
                    "div[class*='share']",
                ]
                
                for selector in popup_selectors:
                    try:
                        elements = await page.query_selector_all(selector)
                        for elem in elements:
                            try:
                                if await elem.is_visible():
                                    text = await elem.inner_text()
                                    if text and 'deepseek.com/share' in text:
                                        import re
                                        match = re.search(r'https://[^\s]*deepseek\.com/share[^\s]*', text)
                                        if match:
                                            shared_link = match.group(0).strip()
                                            logger.info(f"{platform_id}【第四步】从弹窗元素找到分享链接: {shared_link}")
                                            break
                                    if not shared_link:
                                        href = await elem.get_attribute('href')
                                        if href and 'deepseek.com/share' in href:
                                            shared_link = href.strip()
                                            logger.info(f"{platform_id}【第四步】从弹窗链接找到分享链接: {shared_link}")
                                            break
                            except:
                                continue
                        if shared_link:
                            break
                    except:
                        continue
            except Exception as popup_e:
                logger.info(f"{platform_id}【第四步】从弹窗提取链接失败: {str(popup_e)}")
            
            # 尝试使用JavaScript获取分享链接（直接从页面DOM中提取）
            if not shared_link or not shared_link.strip():
                logger.info(f"{platform_id}【第四步】尝试使用JavaScript提取分享链接...")
                try:
                    js_code = "var text = document.body.innerText; var match = text.match(/https:\\/\\/[^\\s]*deepseek\\.com\\/share[^\\s]*/); match ? match[0] : null;"
                    import asyncio
                    js_result = await asyncio.wait_for(page.evaluate(js_code), timeout=10.0)
                    if js_result and 'deepseek.com/share' in js_result:
                        shared_link = js_result.strip()
                        logger.info(f"{platform_id}【第四步】使用JavaScript从页面提取到分享链接: {shared_link}")
                    else:
                        logger.info(f"{platform_id}【第四步】JavaScript未提取到分享链接")
                except asyncio.TimeoutError:
                    logger.info(f"{platform_id}【第四步】JavaScript提取链接超时（10秒）")
                except Exception as js_e:
                    logger.info(f"{platform_id}【第四步】JavaScript提取链接失败: {str(js_e)}")
            
            # 新增备选方案：尝试从页面中所有包含deepseek.com的元素中提取链接
            if not shared_link or not shared_link.strip():
                logger.info(f"{platform_id}【第四步】尝试从页面所有包含deepseek.com的元素提取链接...")
                try:
                    all_elements = await page.query_selector_all("*")
                    for elem in all_elements:
                        try:
                            text = await elem.text_content()
                            if text and 'deepseek.com/share' in text:
                                import re
                                match = re.search(r'https://[^\s]*deepseek\.com/share[^\s]*', text)
                                if match:
                                    shared_link = match.group(0).strip()
                                    logger.info(f"{platform_id}【第四步】从页面元素文本提取分享链接: {shared_link}")
                                    break
                            if not shared_link:
                                href = await elem.get_attribute('href')
                                if href and 'deepseek.com/share' in href:
                                    shared_link = href.strip()
                                    logger.info(f"{platform_id}【第四步】从页面元素href提取分享链接: {shared_link}")
                                    break
                            if not shared_link:
                                value = await elem.get_attribute('value')
                                if value and 'deepseek.com/share' in value:
                                    shared_link = value.strip()
                                    logger.info(f"{platform_id}【第四步】从页面元素value提取分享链接: {shared_link}")
                                    break
                        except:
                            continue
                except Exception as e:
                    logger.info(f"{platform_id}【第四步】遍历页面元素提取链接失败: {str(e)}")
            
            # 尝试剪贴板读取（使用Playwright执行navigator.clipboard.readText()）
            if not shared_link or not shared_link.strip():
                try:
                    import re
                    link_pattern = r'https://[^\s]*deepseek\.com/share[^\s]*'
                    # 重试最多3次，每次间隔1秒
                    for retry in range(3):
                        await page.wait_for_timeout(1000)
                        # 先尝试使用Playwright的evaluate执行navigator.clipboard.readText()
                        try:
                            clipboard_content = await page.evaluate("navigator.clipboard.readText()")
                            if clipboard_content and clipboard_content.strip():
                                match = re.search(link_pattern, clipboard_content)
                                if match:
                                    shared_link = match.group(0).strip()
                                    logger.info(f"{platform_id}【第四步】第{retry+1}次尝试，使用navigator.clipboard读取成功: {shared_link}")
                                    break
                                else:
                                    logger.info(f"{platform_id}【第四步】第{retry+1}次尝试，剪贴板内容不是有效分享链接: {clipboard_content[:50]}...")
                            else:
                                logger.info(f"{platform_id}【第四步】第{retry+1}次尝试，navigator.clipboard返回为空")
                        except Exception as nav_e:
                            # 如果navigator.clipboard失败，尝试使用pyperclip
                            logger.info(f"{platform_id}【第四步】第{retry+1}次尝试，navigator.clipboard失败: {str(nav_e)}")
                            clipboard_content = pyperclip.paste()
                            if clipboard_content and clipboard_content.strip():
                                match = re.search(link_pattern, clipboard_content)
                                if match:
                                    shared_link = match.group(0).strip()
                                    logger.info(f"{platform_id}【第四步】第{retry+1}次尝试，使用pyperclip从系统剪贴板读取成功: {shared_link}")
                                    break
                                else:
                                    logger.info(f"{platform_id}【第四步】第{retry+1}次尝试，pyperclip内容不是有效分享链接: {clipboard_content[:50]}...")
                            else:
                                logger.info(f"{platform_id}【第四步】第{retry+1}次尝试，pyperclip剪贴板为空")
                except Exception as e:
                    logger.info(f"{platform_id}【第四步】使用剪贴板获取失败: {str(e)}")
            
            # 保存分享链接到文件
            if shared_link and shared_link.strip():
                link_path = self.screenshot_dir / f"{platform_id}_{question.id}_{question.timestamp.strftime('%Y%m%d_%H%M%S')}_link.txt"
                with open(link_path, 'w', encoding='utf-8') as f:
                    f.write(shared_link.strip())
                logger.info(f"{platform_id}【第四步】分享链接已保存：{link_path}")
                logger.info(f"{platform_id}【第四步】分享链接内容: {shared_link.strip()}")
            
            # 备选方案：如果剪贴板失败，尝试从页面中提取分享链接
            if not shared_link or not shared_link.strip():
                logger.info(f"{platform_id}【第四步】尝试从页面提取分享链接...")
                try:
                    page_content = await page.content()
                    import re
                    url_patterns = [
                        r'https://chat\.deepseek\.com/share/[\w-]+',
                        r'https://share\.deepseek\.com/[\w-]+',
                        r'https?://[^\s"\'<>]+/share/[\w-]+',
                        r'"(https://chat\.deepseek\.com[^"]+)"',
                        r"'(https://chat\.deepseek\.com[^']+)'",
                    ]
                    for pattern in url_patterns:
                        match = re.search(pattern, page_content)
                        if match:
                            shared_link = match.group(0).strip('\'"')
                            logger.info(f"{platform_id}【第四步】从页面内容提取分享链接: {shared_link}")
                            break
                except Exception as extract_e:
                    logger.info(f"{platform_id}【第四步】从页面内容提取链接失败: {str(extract_e)}")
            
            # 备选方案2：尝试从更多DOM元素获取（增强版）
            if not shared_link or not shared_link.strip():
                logger.info(f"{platform_id}【第四步】尝试从更多DOM元素提取分享链接...")
                try:
                    share_elements = await page.query_selector_all("[class*='share'], [id*='share'], [data-testid*='share'], [aria-label*='share']")
                    for elem in share_elements:
                        try:
                            if await elem.is_visible():
                                text = await elem.inner_text()
                                if text and 'deepseek.com/share' in text:
                                    import re
                                    match = re.search(r'https://[^\s]*deepseek\.com/share[^\s]*', text)
                                    if match:
                                        shared_link = match.group(0).strip()
                                        logger.info(f"{platform_id}【第四步】从share元素文本提取分享链接: {shared_link}")
                                        break
                                
                                if not shared_link:
                                    href = await elem.get_attribute('href')
                                    if href and 'deepseek.com/share' in href:
                                        shared_link = href.strip()
                                        logger.info(f"{platform_id}【第四步】从share元素href提取分享链接: {shared_link}")
                                        break
                                
                                if not shared_link:
                                    value = await elem.get_attribute('value')
                                    if value and 'deepseek.com/share' in value:
                                        shared_link = value.strip()
                                        logger.info(f"{platform_id}【第四步】从share元素value提取分享链接: {shared_link}")
                                        break
                                
                                if not shared_link:
                                    child_inputs = await elem.query_selector_all("input, textarea")
                                    for child in child_inputs:
                                        child_value = await child.get_attribute('value')
                                        if child_value and 'deepseek.com/share' in child_value:
                                            shared_link = child_value.strip()
                                            logger.info(f"{platform_id}【第四步】从share元素子输入框提取分享链接: {shared_link}")
                                            break
                        except:
                            continue
                    if shared_link:
                        logger.info(f"{platform_id}【第四步】已找到分享链接，跳过后续提取尝试")
                except Exception as e:
                    logger.info(f"{platform_id}【第四步】从share元素提取链接失败: {str(e)}")
            
            # 备选方案3：尝试从弹窗中的代码块或pre标签获取
            if not shared_link or not shared_link.strip():
                logger.info(f"{platform_id}【第四步】尝试从代码块提取分享链接...")
                try:
                    code_selectors = ["pre", "code", ".code-block", "[class*='code']", "[class*='pre']"]
                    for selector in code_selectors:
                        elements = await page.query_selector_all(selector)
                        for elem in elements:
                            try:
                                if await elem.is_visible():
                                    text = await elem.inner_text()
                                    if text and 'deepseek.com/share' in text:
                                        import re
                                        match = re.search(r'https://[^\s]*deepseek\.com/share[^\s]*', text)
                                        if match:
                                            shared_link = match.group(0).strip()
                                            logger.info(f"{platform_id}【第四步】从代码块提取分享链接: {shared_link}")
                                            break
                            except:
                                continue
                        if shared_link:
                            break
                except Exception as e:
                    logger.info(f"{platform_id}【第四步】从代码块提取链接失败: {str(e)}")
            
            # 备选方案4：尝试使用更强大的JavaScript提取
            if not shared_link or not shared_link.strip():
                logger.info(f"{platform_id}【第四步】尝试使用增强版JavaScript提取分享链接...")
                try:
                    enhanced_js_code = """
                    (function() {
                        var link = null;
                        var allElements = document.querySelectorAll('*');
                        for(var i = 0; i < allElements.length; i++) {
                            var elem = allElements[i];
                            var text = elem.textContent || elem.innerText || '';
                            if(text.indexOf('deepseek.com/share') !== -1) {
                                var match = text.match(/https:\\/\\/[^\\s]*deepseek\\.com\\/share[^\\s]*/);
                                if(match) {
                                    link = match[0];
                                    break;
                                }
                            }
                            if(!link && elem.href && elem.href.indexOf('deepseek.com/share') !== -1) {
                                link = elem.href;
                                break;
                            }
                            if(!link && elem.value && elem.value.indexOf('deepseek.com/share') !== -1) {
                                link = elem.value;
                                break;
                            }
                        }
                        return link;
                    })();
                    """
                    import asyncio
                    js_result = await asyncio.wait_for(page.evaluate(enhanced_js_code), timeout=15.0)
                    if js_result and 'deepseek.com/share' in js_result:
                        shared_link = js_result.strip()
                        logger.info(f"{platform_id}【第四步】使用增强版JavaScript提取到分享链接: {shared_link}")
                    else:
                        logger.info(f"{platform_id}【第四步】增强版JavaScript未提取到分享链接")
                except asyncio.TimeoutError:
                    logger.info(f"{platform_id}【第四步】增强版JavaScript提取链接超时（15秒）")
                except Exception as e:
                    logger.info(f"{platform_id}【第四步】增强版JavaScript提取链接失败: {str(e)}")
            
            # 备选方案2：尝试从输入框或文本区域获取
            if not shared_link or not shared_link.strip():
                try:
                    input_selectors = [
                        "input[value*='deepseek.com/share']",
                        "textarea[value*='deepseek.com/share']",
                        "input[placeholder*='分享']",
                        "textarea[placeholder*='分享']",
                        "input[type='text']",
                        "textarea",
                    ]
                    for selector in input_selectors:
                        try:
                            element = await page.query_selector(selector)
                            if element:
                                value = await element.get_attribute('value')
                                if value and 'deepseek.com/share' in value:
                                    shared_link = value.strip()
                                    logger.info(f"{platform_id}【第四步】从输入框value提取分享链接: {shared_link}")
                                    break
                                text = await element.text_content()
                                if text and 'deepseek.com/share' in text:
                                    shared_link = text.strip()
                                    logger.info(f"{platform_id}【第四步】从输入框text提取分享链接: {shared_link}")
                                    break
                        except:
                            continue
                except Exception as extract_e:
                    logger.info(f"{platform_id}【第四步】从输入框提取链接失败: {str(extract_e)}")
            
            # 备选方案3：尝试执行JavaScript获取可能存在的分享链接变量
            if not shared_link or not shared_link.strip():
                try:
                    shared_link = await page.evaluate("""
                        // 尝试从全局变量或DOM中获取分享链接
                        function findShareLink() {
                            // 检查常见的分享链接存储位置
                            const possibleVars = ['shareUrl', 'shareLink', 'sharedLink', 'link', 'url'];
                            for (const varName of possibleVars) {
                                if (window[varName] && typeof window[varName] === 'string' && window[varName].includes('deepseek')) {
                                    return window[varName];
                                }
                            }
                            // 检查meta标签
                            const metaTags = document.querySelectorAll('meta[property*="url"], meta[name*="url"], meta[content*="deepseek"]');
                            for (const tag of metaTags) {
                                const content = tag.getAttribute('content');
                                if (content && content.includes('deepseek.com/share')) {
                                    return content;
                                }
                            }
                            return null;
                        }
                        findShareLink();
                    """)
                    
                    if shared_link:
                        link_path = self.screenshot_dir / f"{platform_id}_{question.id}_{question.timestamp.strftime('%Y%m%d_%H%M%S')}_link.txt"
                        with open(link_path, 'w', encoding='utf-8') as f:
                            f.write(shared_link)
                        logger.info(f"{platform_id}【第四步】从JS变量提取分享链接: {shared_link}")
                except Exception as extract_e:
                    logger.info(f"{platform_id}【第四步】从JS变量提取链接失败: {str(extract_e)}")

            await page.keyboard.press("Escape")
            logger.info(f"{platform_id}四步分享流程完成")
            return str(download_path)

        except Exception as e:
            logger.error(f"{platform_id}下载分享图片失败：{str(e)}")
            try:
                await page.keyboard.press("Escape")
            except:
                pass
            return None

    async def capture_from_page(self, page: Page, platform_id: str, question: Question) -> tuple[Optional[str], bool, Optional[str]]:
        """
        优先尝试下载分享图片，如果失败则进行页面截图
        返回：(图片路径, 是否为分享图片, 分享链接)
        """
        logger.info(f"{platform_id}开始等待AI回复完成...")
        await self._wait_for_response_complete(page, platform_id)
        logger.info(f"{platform_id}等待完成，开始尝试三步分享流程...")

        shared_image_path = await self.download_shared_image(page, platform_id, question)
        
        # 尝试读取分享链接
        share_link_path = self.screenshot_dir / f"{platform_id}_{question.id}_{question.timestamp.strftime('%Y%m%d_%H%M%S')}_link.txt"
        share_link = None
        if share_link_path.exists():
            try:
                with open(share_link_path, 'r', encoding='utf-8') as f:
                    share_link = f.read().strip()
                    logger.info(f"{platform_id}读取到分享链接: {share_link}")
            except Exception as e:
                logger.info(f"{platform_id}读取分享链接失败: {str(e)}")
        
        if shared_image_path:
            return shared_image_path, True, share_link

        for attempt in range(3):
            try:
                filename = f"{platform_id}_{question.id}_{question.timestamp.strftime('%Y%m%d_%H%M%S')}.png"
                filepath = self.screenshot_dir / filename

                await page.wait_for_timeout(2000)
                await page.screenshot(
                    path=str(filepath),
                    full_page=True,
                    timeout=60000
                )

                logger.info(f"{platform_id}页面截图已保存：{filepath}")
                return str(filepath), False, share_link

            except Exception as e:
                error_msg = str(e)
                if "closed" in error_msg.lower() or "target page" in error_msg.lower():
                    logger.error(f"{platform_id}页面已被关闭（第{attempt+1}次）：{error_msg}")
                    raise Exception(f"{platform_id}浏览器页面已关闭，无法截图: {error_msg}")

                logger.error(f"{platform_id}页面截图失败（第{attempt+1}次）：{error_msg}")
                if attempt < 2:
                    logger.info(f"{platform_id}正在重试截图...")
                    await page.wait_for_timeout(2000)
                    continue

            try:
                filename = f"{platform_id}_{question.id}_{question.timestamp.strftime('%Y%m%d_%H%M%S')}.png"
                filepath = self.screenshot_dir / filename
                await page.screenshot(
                    path=str(filepath),
                    timeout=30000
                )
                logger.info(f"{platform_id}页面截图已保存（简化版）：{filepath}")
                return str(filepath), False, share_link
            except Exception as e2:
                error_msg = str(e2)
                if "closed" in error_msg.lower() or "target page" in error_msg.lower():
                    logger.error(f"{platform_id}页面已被关闭：{error_msg}")
                    raise Exception(f"{platform_id}浏览器页面已关闭，无法截图: {error_msg}")
                logger.error(f"{platform_id}简化截图也失败：{error_msg}")

        logger.error(f"{platform_id}截图全部失败")
        return None, False, None

    async def capture(self, platform_id: str, question: Question, answer: str) -> Optional[str]:
        try:
            browser = await self._get_browser()
            page = await browser.new_page()

            html_content = self._generate_html(platform_id, question, answer)
            await page.set_content(html_content)

            filename = f"{platform_id}_{question.id}_{question.timestamp.strftime('%Y%m%d_%H%M%S')}.png"
            filepath = self.screenshot_dir / filename

            await page.screenshot(path=str(filepath), full_page=True)
            await page.close()

            logger.info(f"截图已保存：{filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"截图失败：{str(e)}")
            return None

    def _generate_html(self, platform_id: str, question: Question, answer: str) -> str:
        platform_names = {
            "doubao": "豆包",
            "yuanbao": "元宝",
            "qwen": "千问",
            "ernie": "文心一言",
            "deepseek": "Deepseek"
        }

        platform_name = platform_names.get(platform_id, platform_id)

        html = f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>AI问答评测 - {platform_name}</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f5f5f5;
                }}
                .container {{
                    background-color: white;
                    border-radius: 8px;
                    padding: 30px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .header {{
                    border-bottom: 2px solid #4CAF50;
                    padding-bottom: 15px;
                    margin-bottom: 20px;
                }}
                .platform {{
                    font-size: 24px;
                    font-weight: bold;
                    color: #4CAF50;
                }}
                .question {{
                    background-color: #e3f2fd;
                    padding: 15px;
                    border-radius: 5px;
                    margin-bottom: 20px;
                }}
                .question-label {{
                    font-weight: bold;
                    color: #1976D2;
                    margin-bottom: 5px;
                }}
                .answer {{
                    background-color: #f1f8e9;
                    padding: 15px;
                    border-radius: 5px;
                    white-space: pre-wrap;
                }}
                .answer-label {{
                    font-weight: bold;
                    color: #388E3C;
                    margin-bottom: 5px;
                }}
                .timestamp {{
                    color: #666;
                    font-size: 12px;
                    margin-top: 20px;
                    text-align: right;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="platform">{platform_name}</div>
                </div>

                <div class="question">
                    <div class="question-label">问题：</div>
                    <div>{question.text}</div>
                </div>

                <div class="answer">
                    <div class="answer-label">回答：</div>
                    <div>{answer}</div>
                </div>

                <div class="timestamp">
                    问题ID: {question.id} | 时间: {question.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
                </div>
            </div>
        </body>
        </html>
        """

        return html

    async def close(self):
        if self.browser:
            await self.browser.close()
            self.browser = None
