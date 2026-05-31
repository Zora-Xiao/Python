from pathlib import Path
from typing import Optional
from playwright.async_api import async_playwright, Browser, Page
from src.models.question import Question
from src.utils.logger import logger
import urllib.parse
import pyperclip
import asyncio


class ScreenshotTool:
    def __init__(self, screenshot_dir: str = "screenshots"):
        self.screenshot_dir = Path(screenshot_dir)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.browser: Optional[Browser] = None
        self.playwright = None

    async def close(self):
        """关闭浏览器资源"""
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None

    async def _get_browser(self) -> Browser:
        if self.browser is None:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=True)
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

    async def capture_from_page(self, page: Page, platform_id: str, question: Question) -> tuple[Optional[str], bool, Optional[str]]:
        """截取页面全屏截图并尝试获取分享图片

        Returns:
            tuple[screenshot_path, is_shared_image, share_link]
        """
        try:
            screenshot_path = self.screenshot_dir / f"{platform_id}_{question.id}_{question.timestamp.strftime('%Y%m%d_%H%M%S')}_full.png"

            await page.wait_for_timeout(2000)
            await page.screenshot(
                path=str(screenshot_path),
                full_page=True,
                timeout=60000
            )
            logger.info(f"{platform_id}全屏截图已保存：{screenshot_path}")

            shared_image_path = await self.download_shared_image(page, platform_id, question)
            is_shared = shared_image_path is not None

            if is_shared:
                return shared_image_path, True, None
            else:
                return str(screenshot_path), False, None

        except Exception as e:
            logger.error(f"{platform_id}截图失败：{str(e)}")
            return None, False, None

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
        """千问平台：三步流程（全屏截图 → 点击分享按钮 → 点击复制链接）"""
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

            # ========== 第二步：点击分享按钮（根据用户提供的HTML结构） ==========
            logger.info(f"{platform_id}【第二步】查找分享按钮...")
            
            # 根据用户提供的HTML结构优化选择器
            # 分享按钮通常出现在回复消息的右上角，包含分享图标
            share_button_selectors = [
                # 用户提供的精确选择器 - 分享按钮容器类名
                ".qwen-chat-package-comp-new-action-control-container-share",
                "[class*='qwen-chat-package-comp-new-action-control-container-share']",
                ".qwen-chat-package-comp-new-action-control-container.qwen-chat-package-comp-new-action-control-container-share",
                # 分享按钮图标容器
                ".qwen-chat-package-comp-new-action-control-icon:has(.anticon)",
                "[class*='action-control-icon']",
                # 包含分享图标的SVG选择器
                "svg use[xlink:href='#icon-line-share-01']",
                "svg use[href='#icon-line-share-01']",
                "svg use[xlink:href*='share']",
                "svg use[href*='share']",
                ".anticon:has(svg use[xlink:href*='share'])",
                ".anticon:has(svg use[href*='share'])",
                # 父级按钮选择器
                "button:has(.anticon)",
                "button:has(svg use[xlink:href*='share'])",
                "[role='button']:has(.anticon)",
                "[role='button']:has(svg use[xlink:href*='share'])",
                # 下拉触发器
                ".ant-dropdown-trigger",
                "[class*='ant-dropdown-trigger']",
                # 动作控制相关
                "[class*='action-control']",
                "[class*='qwen-chat-package-comp-new-action']",
                # ARIA属性选择器
                "[aria-describedby*='_r_']",
                "[aria-label*='分享']",
                "[aria-label*='share']",
                # 通用按钮选择器
                ".share-btn",
                ".share-button",
                "[data-action='share']"
            ]
            
            share_button = None
            
            # 策略1：使用选择器列表查找
            for selector in share_button_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements and len(elements) > 0:
                        logger.info(f"{platform_id}【第二步】选择器 {selector} 找到 {len(elements)} 个元素")
                        for elem in elements:
                            try:
                                is_visible = await elem.is_visible()
                                if is_visible:
                                    tag_name = await elem.evaluate("el => el.tagName.toLowerCase()")
                                    class_name = await elem.get_attribute("class") or ""
                                    logger.info(f"{platform_id}【第二步】可见元素: tag={tag_name}, class={class_name[:50]}")
                                    share_button = elem
                                    logger.info(f"{platform_id}【第二步】找到分享按钮: {selector}")
                                    break
                            except Exception as elem_e:
                                logger.debug(f"{platform_id}【第二步】检查元素失败: {str(elem_e)}")
                                continue
                        if share_button:
                            break
                except Exception as sel_e:
                    logger.debug(f"{platform_id}【第二步】选择器 {selector} 查询失败: {str(sel_e)}")
                    continue

            # 策略2：使用JavaScript查找分享按钮
            if not share_button:
                logger.info(f"{platform_id}【第二步】策略2：尝试使用JavaScript查找分享按钮...")
                try:
                    js_find_button = """
                    (function() {
                        var buttons = document.querySelectorAll('button, [role="button"], div');
                        var targetTexts = ['分享', 'share', 'Share'];
                        var targetIcons = ['icon-line-share', 'share-icon', 'anticon-share'];
                        for(var i = 0; i < buttons.length; i++) {
                            var btn = buttons[i];
                            var text = btn.textContent || btn.innerText || '';
                            text = text.trim();
                            if(btn.offsetWidth > 0 && btn.offsetHeight > 0) {
                                // 检查文本
                                for(var j = 0; j < targetTexts.length; j++) {
                                    if(text.indexOf(targetTexts[j]) !== -1) {
                                        btn.setAttribute('data-found-btn', 'share');
                                        return 'found_share:' + text + ':class=' + (btn.className || '');
                                    }
                                }
                                // 检查是否包含分享图标
                                var svg = btn.querySelector('svg use');
                                if(svg) {
                                    var href = svg.getAttribute('xlink:href') || svg.getAttribute('href') || '';
                                    for(var k = 0; k < targetIcons.length; k++) {
                                        if(href.indexOf(targetIcons[k]) !== -1) {
                                            btn.setAttribute('data-found-btn', 'share');
                                            return 'found_share_by_icon:' + href + ':class=' + (btn.className || '');
                                        }
                                    }
                                }
                            }
                        }
                        return 'not_found';
                    })()
                    """
                    js_result = await page.evaluate(js_find_button)
                    logger.info(f"{platform_id}【第二步】JavaScript查找结果: {js_result}")
                    
                    if js_result.startswith('found_share'):
                        share_button = await page.query_selector("[data-found-btn='share']")
                        if share_button:
                            logger.info(f"{platform_id}【第二步】通过JavaScript找到分享按钮")
                except Exception as e:
                    logger.info(f"{platform_id}【第二步】JavaScript查找失败: {str(e)}")

            # 策略3：查找所有可见按钮并记录（调试模式）
            if not share_button:
                logger.info(f"{platform_id}【第二步】策略3：调试模式 - 获取所有可见按钮信息...")
                try:
                    all_buttons = await page.query_selector_all("button, [role='button']")
                    button_info = []
                    for btn in all_buttons:
                        try:
                            if await btn.is_visible():
                                text = await btn.inner_text()
                                tag_name = await btn.evaluate("el => el.tagName.toLowerCase()")
                                class_name = await btn.get_attribute("class") or ""
                                button_info.append(f"{tag_name}: '{text.strip()[:30]}' class={class_name[:50]}")
                        except:
                            continue
                    logger.info(f"{platform_id}【第二步】页面上可见按钮列表: {button_info[:20]}")
                except Exception as e:
                    logger.info(f"{platform_id}【第二步】获取按钮列表失败: {str(e)}")

            # 如果找到的是svg或use元素，获取其父按钮
            if share_button:
                tag_name = await share_button.evaluate("el => el.tagName.toLowerCase()")
                if tag_name == "svg" or tag_name == "use":
                    # 获取父级容器（可能需要多层级）
                    parent_div = await share_button.query_selector("xpath=../..")
                    if parent_div:
                        parent_tag = await parent_div.evaluate("el => el.tagName.toLowerCase()")
                        if parent_tag == "button" or parent_tag == "div":
                            share_button = parent_div
                            logger.info(f"{platform_id}【第二步】调整为父级容器作为分享按钮")
                        else:
                            # 再往上找一层
                            grand_parent = await parent_div.query_selector("xpath=..")
                            if grand_parent:
                                grand_tag = await grand_parent.evaluate("el => el.tagName.toLowerCase()")
                                if grand_tag == "button" or grand_tag == "div":
                                    share_button = grand_parent
                                    logger.info(f"{platform_id}【第二步】调整为祖父容器作为分享按钮")

            if not share_button:
                logger.info(f"{platform_id}【第二步】所有策略都未找到分享按钮，跳过分享链接")
                return str(download_path)

            logger.info(f"{platform_id}【第二步】点击分享按钮...")
            await share_button.click()
            await page.wait_for_timeout(3000)  # 增加等待时间，确保弹窗完全显示

            # 等待弹窗出现
            try:
                await page.wait_for_selector("[class*='modal'], [class*='popup'], [class*='dialog']", timeout=3000)
                logger.info(f"{platform_id}【第二步】分享弹窗已出现")
            except:
                logger.info(f"{platform_id}【第二步】未检测到分享弹窗")

            # ========== 第三步：点击复制链接按钮 ==========
            logger.info(f"{platform_id}【第三步】查找复制链接按钮...")
            
            # 千问平台的复制链接按钮选择器（根据用户描述的弹窗结构优化）
            # 分享弹窗中通常会有"复制链接"选项，需要在弹窗出现后查找
            copy_link_selectors = [
                # ========== 精确匹配复制链接按钮 ==========
                "button:has-text('复制链接')",
                "div:has-text('复制链接')",
                "[role='menuitem']:has-text('复制链接')",
                ".ant-dropdown-menu-item:has-text('复制链接')",
                ".ant-dropdown-menu-item-link:has-text('复制链接')",
                # 包含"复制"的按钮（可能不带"链接"）
                "button:has-text('复制')",
                "div:has-text('复制')",
                "[role='menuitem']:has-text('复制')",
                ".ant-dropdown-menu-item:has-text('复制')",
                ".ant-dropdown-menu-item-link:has-text('复制')",
                # 英文版本
                "button:has-text('Copy Link')",
                "button:has-text('Copy')",
                "[role='menuitem']:has-text('Copy')",
                # ========== 千问平台特定选择器 ==========
                # 根据千问平台弹窗结构
                ".qwen-chat-package-comp-new-action-control-popup",
                "[class*='qwen-chat-package-comp-new-action-control-popup']",
                "[class*='action-control-popup']",
                # 弹窗内的菜单项
                ".ant-dropdown-wrap .ant-dropdown-menu-item",
                ".ant-dropdown-content .ant-dropdown-menu-item",
                ".ant-dropdown-content [role='menuitem']",
                # ========== 使用属性选择器 ==========
                "[class*='copy']",
                "[class*='link']",
                "[class*='Copy']",
                "[class*='Link']",
                ".copy-btn",
                ".copy-link-btn",
                "[data-action='copy']",
                "[data-action='copy-link']",
                "[data-testid*='copy']",
                "[data-testid*='link']",
                # ========== Ant Design标准选择器 ==========
                ".ant-btn-primary",
                ".ant-btn",
                "button.ant-btn",
                "[role='button']",
                # ========== 下拉菜单项 ==========
                ".ant-dropdown-menu li",
                ".ant-dropdown-menu-item",
                ".ant-dropdown-menu-item-link",
                "[role='menuitem']",
                # ========== 包含SVG图标的按钮 ==========
                "button:has(svg)",
                "[role='button']:has(svg)",
                # 复制图标SVG
                "svg use[xlink:href*='copy']",
                "svg use[href*='copy']",
                ".anticon-copy",
                # ========== 弹窗容器内的按钮 ==========
                "[class*='modal'] button",
                "[class*='popup'] button",
                "[class*='dialog'] button",
                "[class*='dropdown'] button",
            ]
            
            copy_button = None
            
            # 策略1：使用选择器列表查找
            for selector in copy_link_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements and len(elements) > 0:
                        logger.info(f"{platform_id}【第三步】选择器 {selector} 找到 {len(elements)} 个元素")
                        for elem in elements:
                            try:
                                is_visible = await elem.is_visible()
                                if is_visible:
                                    text = await elem.inner_text()
                                    tag_name = await elem.evaluate("el => el.tagName.toLowerCase()")
                                    class_name = await elem.get_attribute("class") or ""
                                    logger.info(f"{platform_id}【第三步】可见元素: tag={tag_name}, class={class_name[:50]}, text='{text.strip()[:30]}'")
                                    if text and ("复制" in text or "链接" in text):
                                        copy_button = elem
                                        logger.info(f"{platform_id}【第三步】找到复制链接按钮: {selector}, 文本: {text.strip()}")
                                        break
                            except Exception as elem_e:
                                logger.debug(f"{platform_id}【第三步】检查元素失败: {str(elem_e)}")
                                continue
                        if copy_button:
                            break
                except Exception as sel_e:
                    logger.debug(f"{platform_id}【第三步】选择器 {selector} 查询失败: {str(sel_e)}")
                    continue

            # 策略2：使用JavaScript查找按钮（更强大的查找能力）
            if not copy_button:
                logger.info(f"{platform_id}【第三步】策略2：尝试使用JavaScript查找复制按钮...")
                try:
                    js_find_button = """
                    (function() {
                        var buttons = document.querySelectorAll('button, [role="button"], div, span');
                        var targetTexts = ['复制链接', '复制', 'copy link', 'copy', '分享链接', 'share'];
                        for(var i = 0; i < buttons.length; i++) {
                            var btn = buttons[i];
                            var text = btn.textContent || btn.innerText || '';
                            text = text.trim();
                            if(btn.offsetWidth > 0 && btn.offsetHeight > 0) {
                                for(var j = 0; j < targetTexts.length; j++) {
                                    if(text.indexOf(targetTexts[j]) !== -1) {
                                        btn.setAttribute('data-found-btn', 'copy-link');
                                        return 'found_copy_link:' + text + ':class=' + (btn.className || '');
                                    }
                                }
                            }
                        }
                        return 'not_found';
                    })()
                    """
                    js_result = await page.evaluate(js_find_button)
                    logger.info(f"{platform_id}【第三步】JavaScript查找结果: {js_result}")
                    
                    if js_result.startswith('found_copy_link'):
                        copy_button = await page.query_selector("[data-found-btn='copy-link']")
                        if copy_button:
                            text = await copy_button.text_content()
                            logger.info(f"{platform_id}【第三步】通过JavaScript找到复制按钮: {text.strip()}")
                except Exception as e:
                    logger.info(f"{platform_id}【第三步】JavaScript查找失败: {str(e)}")

            # 策略3：查找所有可见按钮并记录，用于调试
            if not copy_button:
                logger.info(f"{platform_id}【第三步】策略3：调试模式 - 获取所有可见按钮信息...")
                try:
                    all_buttons = await page.query_selector_all("button, [role='button'], .ant-dropdown-menu-item")
                    button_info = []
                    for btn in all_buttons:
                        try:
                            if await btn.is_visible():
                                text = await btn.inner_text()
                                tag_name = await btn.evaluate("el => el.tagName.toLowerCase()")
                                class_name = await btn.get_attribute("class") or ""
                                button_info.append(f"{tag_name}: '{text.strip()[:30]}' class={class_name[:50]}")
                        except:
                            continue
                    logger.info(f"{platform_id}【第三步】页面上可见按钮列表: {button_info[:20]}")
                except Exception as e:
                    logger.info(f"{platform_id}【第三步】获取按钮列表失败: {str(e)}")

            # 策略4：查找下拉菜单中的链接项
            if not copy_button:
                logger.info(f"{platform_id}【第三步】策略4：查找下拉菜单中的链接项...")
                try:
                    dropdown_items = await page.query_selector_all(".ant-dropdown-menu-item, .ant-dropdown-menu-item-link, [role='menuitem']")
                    for item in dropdown_items:
                        try:
                            if await item.is_visible():
                                text = await item.inner_text()
                                if text and ("复制" in text or "链接" in text):
                                    copy_button = item
                                    logger.info(f"{platform_id}【第三步】在下拉菜单找到按钮: {text.strip()}")
                                    break
                        except:
                            continue
                except Exception as e:
                    logger.info(f"{platform_id}【第三步】查找下拉菜单失败: {str(e)}")

            # 策略5：查找包含特定图标的元素
            if not copy_button:
                logger.info(f"{platform_id}【第三步】策略5：查找包含复制图标的元素...")
                try:
                    svg_selectors = [
                        "svg use[xlink:href*='copy']",
                        "svg use[href*='copy']",
                        "svg:has(use[xlink:href*='copy'])",
                        ".anticon-copy",
                    ]
                    for selector in svg_selectors:
                        svg_elem = await page.query_selector(selector)
                        if svg_elem and await svg_elem.is_visible():
                            # 获取父级按钮
                            parent_button = await svg_elem.query_selector("xpath=../..")
                            if parent_button:
                                tag_name = await parent_button.evaluate("el => el.tagName.toLowerCase()")
                                if tag_name == "button" or tag_name == "div":
                                    copy_button = parent_button
                                    logger.info(f"{platform_id}【第三步】通过复制图标找到按钮")
                                    break
                except Exception as e:
                    logger.info(f"{platform_id}【第三步】查找复制图标失败: {str(e)}")

            if not copy_button:
                await page.keyboard.press("Escape")
                logger.info(f"{platform_id}【第三步】所有策略都未找到复制链接按钮，跳过分享链接")
                return str(download_path)

            # 清空剪贴板，确保不会被之前的内容干扰
            try:
                pyperclip.copy("")
            except:
                pass
            await page.wait_for_timeout(500)

            logger.info(f"{platform_id}【第三步】点击复制链接按钮...")
            try:
                await copy_button.click(force=True)
            except Exception as click_e:
                logger.info(f"{platform_id}【第三步】点击复制链接按钮失败: {str(click_e)}")
                await page.keyboard.press("Escape")
                return str(download_path)
            
            # 增加等待时间，确保复制操作完成
            await page.wait_for_timeout(3000)

            # ========== 第四步：从剪贴板读取分享链接 ==========
            logger.info(f"{platform_id}【第四步】从剪贴板读取分享链接...")

            # 重试最多3次，每次间隔1秒，整个步骤最多15秒
            max_total_wait = 15
            start_time = await page.locator("body").evaluate("() => Date.now()")

            for retry in range(3):
                current_time = await page.locator("body").evaluate("() => Date.now()")
                elapsed = (current_time - start_time) / 1000
                if elapsed >= max_total_wait:
                    logger.info(f"{platform_id}【第四步】已达到最大等待时间（{elapsed:.1f}秒），跳过分享链接")
                    break
                    
                logger.info(f"{platform_id}【第四步】第{retry+1}/3次尝试读取剪贴板...")
                
                # 方法1：优先使用pyperclip读取系统剪贴板（更可靠）
                try:
                    clipboard_content = pyperclip.paste()
                    if clipboard_content and clipboard_content.strip():
                        content_length = len(clipboard_content.strip())
                        logger.info(f"{platform_id}【第四步】第{retry+1}次尝试，pyperclip读取到内容，长度: {content_length}")
                        if 'qwen.ai' in clipboard_content or 'share' in clipboard_content.lower():
                            shared_link = clipboard_content.strip()
                            logger.info(f"{platform_id}【第四步】第{retry+1}次尝试，使用pyperclip读取成功: {shared_link[:50]}...")
                            break
                        else:
                            logger.info(f"{platform_id}【第四步】第{retry+1}次尝试，pyperclip内容不包含qwen.ai: '{clipboard_content[:50]}...'")
                    else:
                        logger.info(f"{platform_id}【第四步】第{retry+1}次尝试，pyperclip内容为空")
                except Exception as pyperclip_e:
                    logger.info(f"{platform_id}【第四步】第{retry+1}次尝试，pyperclip失败: {str(pyperclip_e)}")
                
                # 方法2：使用navigator.clipboard（备用）
                if not shared_link:
                    try:
                        clipboard_content = await page.evaluate("navigator.clipboard.readText()")
                        if clipboard_content and clipboard_content.strip():
                            content_length = len(clipboard_content.strip())
                            logger.info(f"{platform_id}【第四步】第{retry+1}次尝试，navigator.clipboard读取到内容，长度: {content_length}")
                            if 'qwen.ai' in clipboard_content or 'share' in clipboard_content.lower():
                                shared_link = clipboard_content.strip()
                                logger.info(f"{platform_id}【第四步】第{retry+1}次尝试，使用navigator.clipboard读取成功: {shared_link[:50]}...")
                                break
                            else:
                                logger.info(f"{platform_id}【第四步】第{retry+1}次尝试，navigator.clipboard内容不包含qwen.ai: '{clipboard_content[:50]}...'")
                    except Exception as nav_e:
                        logger.info(f"{platform_id}【第四步】第{retry+1}次尝试，navigator.clipboard失败: {str(nav_e)}")
                
                if retry < 2:
                    await page.wait_for_timeout(1000)
            
            logger.info(f"{platform_id}【第四步】剪贴板读取完成，结果: {'成功' if shared_link else '失败'}")

            # 尝试从页面元素中提取链接（备用策略）
            if not shared_link:
                logger.info(f"{platform_id}【第四步】尝试从页面元素提取分享链接...")
                try:
                    all_elements = await page.query_selector_all("input, textarea, div[class*='link'], span[class*='link']")
                    for elem in all_elements:
                        try:
                            if await elem.is_visible():
                                value = await elem.get_attribute('value')
                                text = await elem.text_content()
                                if value and ('qwen.ai' in value or 'share' in value.lower()):
                                    shared_link = value.strip()
                                    logger.info(f"{platform_id}【第四步】从元素value提取分享链接: {shared_link[:50]}...")
                                    break
                                if text and ('qwen.ai' in text or 'share' in text.lower()):
                                    import re
                                    match = re.search(r'https://[^\s]*qwen\.ai[^\s]*', text)
                                    if match:
                                        shared_link = match.group(0).strip()
                                        logger.info(f"{platform_id}【第四步】从元素文本提取分享链接: {shared_link[:50]}...")
                                        break
                        except:
                            continue
                except Exception as e:
                    logger.info(f"{platform_id}【第四步】从页面元素提取链接失败: {str(e)}")

            # 保存分享链接到文件
            if shared_link:
                link_path = self.screenshot_dir / f"{platform_id}_{question.id}_{question.timestamp.strftime('%Y%m%d_%H%M%S')}_link.txt"
                with open(link_path, 'w', encoding='utf-8') as f:
                    f.write(shared_link)
                logger.info(f"{platform_id}【第四步】分享链接已保存：{link_path}")

            await page.keyboard.press("Escape")
            logger.info(f"{platform_id}三步分享流程完成")
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
            
            # 等待分享链接生成，最多等待10秒，每2秒检查一次
            logger.info(f"{platform_id}【第三步】等待分享链接生成...")
            shared_link = None
            for i in range(5):
                await page.wait_for_timeout(2000)
                current_url = await page.evaluate("window.location.href")
                if 'deepseek.com/share' in current_url:
                    shared_link = current_url
                    logger.info(f"{platform_id}【第三步】从URL获取分享链接: {shared_link}")
                    break
                
                # 尝试从剪贴板获取链接
                try:
                    clipboard_content = pyperclip.paste()
                    if clipboard_content and 'deepseek.com/share' in clipboard_content:
                        shared_link = clipboard_content.strip()
                        logger.info(f"{platform_id}【第三步】从剪贴板获取分享链接: {shared_link}")
                        break
                except:
                    pass
            
            if shared_link:
                # 保存分享链接到文件
                share_link_file = self.screenshot_dir / f"{platform_id}_{question.id}_{question.timestamp.strftime('%Y%m%d_%H%M%S')}_link.txt"
                try:
                    with open(share_link_file, 'w', encoding='utf-8') as f:
                        f.write(shared_link)
                    logger.info(f"{platform_id}【第三步】分享链接已保存到: {share_link_file}")
                except Exception as e:
                    logger.info(f"{platform_id}【第三步】保存分享链接失败: {str(e)}")
                
                # 关闭弹窗
                await page.keyboard.press("Escape")
                await page.wait_for_timeout(1000)
                return str(download_path)
            
            # 如果还没获取到链接，返回截图路径
            logger.info(f"{platform_id}【第三步】未能获取分享链接，返回截图路径")
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(1000)
            return str(download_path)
        
        except Exception as e:
            logger.error(f"{platform_id}【第三步】分享链接获取失败: {str(e)}")
            return str(download_path) if 'download_path' in locals() else None
