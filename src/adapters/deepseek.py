# -*- coding: utf-8 -*-
from typing import Optional
from src.adapters.base import BaseAdapter
from src.models.question import Question
from src.utils.logger import logger


class DeepseekAdapter(BaseAdapter):
    def __init__(self, config: dict):
        super().__init__(config)
        self.platform_id = "deepseek"
        self.platform_url = config.get("web_url", "https://chat.deepseek.com/")

    async def _load_cookies(self, context):
        # DeepSeek 不加载已保存的 cookies，每次都重新登录
        logger.info(f"{self.name} DeepSeek 不加载 Cookie，准备自动登录")

    async def _save_cookies(self, context):
        # DeepSeek 不保存 cookies，每次都重新登录
        logger.info(f"{self.name} DeepSeek 不保存 Cookie")

    async def _prepare_cookies_if_needed(self):
        """DeepSeek平台每次都自动登录，不依赖cookies"""
        logger.info(f"{self.name} DeepSeek平台每次都自动登录，不检查cookies")

        try:
            navigate_url = self.login_url if self.login_url else self.platform_url
            if navigate_url:
                logger.info(f"{self.name} 导航到: {navigate_url}")
                await self.page.goto(navigate_url, wait_until="domcontentloaded", timeout=60000)
            else:
                logger.warning(f"{self.name} 未配置login_url或platform_url，无法导航")
                return

            if self.username and self.password:
                logger.info(f"{self.name} 开始自动登录...")
                if await self._execute_login():
                    await self.page.wait_for_timeout(3000)
                    if await self._check_login_status():
                        logger.info(f"{self.name} 自动登录成功")
                        await self._save_cookies(self.page.context)
                        logger.info(f"{self.name} cookies已保存（即使可能无法使用）")
                        return
                    else:
                        logger.warning(f"{self.name} 自动登录后未检测到登录状态")
                else:
                    logger.warning(f"{self.name} 自动登录失败")
            else:
                logger.warning(f"{self.name} 未配置用户名和密码，无法自动登录")

        except Exception as e:
            logger.error(f"{self.name} 自动登录过程错误: {str(e)}")

        try:
            navigate_url = self.login_url if self.login_url else self.platform_url
            if navigate_url:
                logger.info(f"{self.name} 导航到: {navigate_url}")
                await self.page.goto(navigate_url, wait_until="domcontentloaded", timeout=60000)
            else:
                logger.warning(f"{self.name} 未配置login_url或platform_url，无法导航")
                return

            if self.username and self.password:
                logger.info(f"{self.name} 开始自动登录...")
                if await self._execute_login():
                    await self.page.wait_for_timeout(3000)
                    if await self._check_login_status():
                        logger.info(f"{self.name} 自动登录成功")
                        await self._save_cookies(self.page.context)
                        logger.info(f"{self.name} cookies已保存（即使可能无法使用）")
                        return
                    else:
                        logger.warning(f"{self.name} 自动登录后未检测到登录状态")
                else:
                    logger.warning(f"{self.name} 自动登录失败")
            else:
                logger.warning(f"{self.name} 未配置用户名和密码，无法自动登录")

        except Exception as e:
            logger.error(f"{self.name} 自动登录过程错误: {str(e)}")

    async def _execute_login(self) -> bool:
        try:
            logger.info("Deepseek 开始登录过程...")

            # 1. 等待初始页面加载
            await self.page.wait_for_timeout(5000)

            logger.info("Deepseek 步骤1: 查找登录按钮")
            login_selectors = [
                "text=登录",
                "text=Sign In",
                "button:has-text('登录')",
                "button:has-text('Sign In')",
                "[class*='login']",
                "a:has-text('登录')"
            ]

            login_btn = None
            for sel in login_selectors:
                try:
                    elements = await self.page.query_selector_all(sel)
                    if elements:
                        for elem in elements:
                            if await elem.is_visible():
                                login_btn = elem
                                logger.info(f"Deepseek 找到登录按钮: {sel}")
                                break
                        if login_btn:
                            break
                except Exception as e:
                    logger.debug(f"Deepseek 检查 {sel} 失败: {e}")

            if login_btn:
                await login_btn.click()
                await self.page.wait_for_timeout(5000)
                logger.info("Deepseek: 已点击登录，等待弹出窗口")
            else:
                logger.warning("Deepseek 未找到登录按钮，可能已登录？")

            logger.info("Deepseek 步骤2: 点击密码登录按钮（使用精确选择器）")
            try:
                # 使用精确的类名选择器
                password_login_button = await self.page.wait_for_selector("button.ds-link-button.ds-sign-in-form__social-link", timeout=10000)
                if password_login_button:
                    await password_login_button.click()
                    logger.info("Deepseek: 通过精确选择器成功点击密码登录")
                else:
                    raise Exception("未找到密码登录按钮")
            except Exception as e:
                logger.warning(f"Deepseek: 精确选择器密码登录点击失败: {e}")
                # 回退：尝试其他方式
                try:
                    password_login_selectors = [
                        "button:has-text('密码登录')",
                        "text=密码登录",
                        ".ds-link-button"
                    ]
                    pwd_btn = None
                    for sel in password_login_selectors:
                        try:
                            elements = await self.page.query_selector_all(sel)
                            if elements:
                                for elem in elements:
                                    if await elem.is_visible():
                                        pwd_btn = elem
                                        break
                                if pwd_btn:
                                    break
                        except:
                            continue
                    if pwd_btn:
                        await pwd_btn.click()
                        logger.info("Deepseek: 通过回退选择器成功点击密码登录")
                except Exception as e2:
                    logger.warning(f"Deepseek: 回退选择器密码登录点击失败: {e2}")

            await self.page.wait_for_timeout(3000)
            logger.info("Deepseek: 已切换到密码登录")

            logger.info("Deepseek 步骤3: 输入用户名（使用Playwright）")
            try:
                await self.page.wait_for_timeout(2000)
                # 使用Playwright选择器查找用户名输入框
                username_input = await self.page.wait_for_selector("input[type='text'], input[type='email'], input[placeholder*='手机号'], input[placeholder*='邮箱'], input[placeholder*='账号']", timeout=5000)
                if username_input:
                    await username_input.fill(self.username.strip())
                    await self.page.wait_for_timeout(500)
                    # 验证输入
                    value = await username_input.input_value()
                    if value == self.username.strip():
                        logger.info(f"Deepseek: 用户名输入成功，值: {value[:3]}***")
                    else:
                        logger.warning(f"Deepseek: 用户名输入失败，期望: {self.username[:3]}***，实际: {value[:3]}***")
                else:
                    logger.warning("Deepseek: 未找到用户名输入框")
            except Exception as e:
                logger.warning(f"Deepseek 用户名输入失败: {e}")

            logger.info("Deepseek 步骤4: 输入密码（使用Playwright locator）")
            password_filled = False
            try:
                await self.page.wait_for_timeout(2000)  # 等待密码输入框加载
                # 使用Playwright locator直接填充，不等待
                password_selectors = [
                    "input[type='password']",
                    "input[placeholder*='密码']",
                    "input[placeholder*='Password']",
                    "[class*='password']",
                    "[name*='password']",
                    "[data-testid*='password']"
                ]

                for selector in password_selectors:
                    try:
                        # 使用locator和first，不等待
                        password_input = self.page.locator(selector).first
                        if await password_input.count() > 0:
                            is_visible = await password_input.is_visible()
                            if is_visible:
                                await password_input.fill(self.password.strip())
                                await self.page.wait_for_timeout(500)
                                # 验证输入
                                value = await password_input.input_value()
                                if len(value) > 0:
                                    logger.info(f"Deepseek: 密码输入成功，长度: {len(value)}")
                                    password_filled = True
                                    break
                                else:
                                    logger.warning(f"Deepseek: 密码输入验证失败，选择器: {selector}")
                    except Exception as e:
                        logger.debug(f"Deepseek: 尝试选择器 {selector} 失败: {e}")
                        continue

                if not password_filled:
                    logger.warning("Deepseek: 所有Playwright选择器都失败，尝试JavaScript")
                    await self.page.evaluate(f"""
                        (password) => {{
                            const selectors = [
                                'input[type="password"]',
                                'input[placeholder*="密码"]',
                                'input[placeholder*="Password"]',
                                '[class*="password"]',
                                '[name*="password"]',
                                '[data-testid*="password"]'
                            ];
                            let passwordInput = null;
                            for (const selector of selectors) {{
                                const elements = document.querySelectorAll(selector);
                                for (const elem of elements) {{
                                    if (elem.offsetWidth > 0 && elem.offsetHeight > 0) {{
                                        passwordInput = elem;
                                        break;
                                    }}
                                }}
                                if (passwordInput) break;
                            }}
                            if (passwordInput) {{
                                passwordInput.focus();
                                passwordInput.value = password;
                                const event = new Event('input', {{ bubbles: true }});
                                passwordInput.dispatchEvent(event);
                                const changeEvent = new Event('change', {{ bubbles: true }});
                                passwordInput.dispatchEvent(changeEvent);
                                return true;
                            }}
                            return false;
                        }}
                    """, self.password.strip())
                    await self.page.wait_for_timeout(500)
                    logger.info("Deepseek: JavaScript密码填充完成")
            except Exception as e:
                logger.warning(f"Deepseek 密码输入异常: {e}")

            logger.info("Deepseek 步骤5: 提交登录（使用精确选择器）")
            try:
                await self.page.wait_for_timeout(2000)
                
                # 列出所有可见的按钮供调试
                buttons_info = await self.page.evaluate("""
                    () => {
                        const buttons = Array.from(document.querySelectorAll('button'));
                        const visibleButtons = [];
                        buttons.forEach(btn => {
                            if (btn.offsetWidth > 0 && btn.offsetHeight > 0) {
                                visibleButtons.push({
                                    text: btn.textContent.trim().substring(0, 50),
                                    class: btn.className,
                                    type: btn.type,
                                    width: btn.offsetWidth,
                                    height: btn.offsetHeight
                                });
                            }
                        });
                        return visibleButtons;
                    }
                """)
                logger.info(f"Deepseek: 找到 {len(buttons_info)} 个可见按钮: {buttons_info}")
                
                # 尝试使用button[type="submit"]的登录按钮
                submit_btn = await self.page.query_selector("button[type='submit']")
                if submit_btn and await submit_btn.is_visible():
                    await submit_btn.click()
                    logger.info("Deepseek: 通过type=submit点击登录按钮")
                else:
                    # 尝试查找包含"登录"的按钮
                    login_btn_found = False
                    for btn_info in buttons_info:
                        if '登录' in btn_info['text'] or 'Sign' in btn_info['text']:
                            logger.info(f"Deepseek: 准备点击登录按钮: {btn_info}")
                            try:
                                await self.page.evaluate("""
                                    (btnInfo) => {
                                        const buttons = Array.from(document.querySelectorAll('button'));
                                        for (const btn of buttons) {
                                            if (btn.textContent.trim().substring(0, 50) === btnInfo.text &&
                                                btn.offsetWidth === btnInfo.width &&
                                                btn.offsetHeight === btnInfo.height) {
                                                btn.click();
                                                return true;
                                            }
                                        }
                                        return false;
                                    }
                                """, btn_info)
                                login_btn_found = True
                                logger.info("Deepseek: JavaScript点击登录按钮成功")
                                break
                            except Exception as e:
                                logger.warning(f"Deepseek: JavaScript点击登录按钮失败: {e}")
                    
                    if not login_btn_found:
                        raise Exception("未找到登录按钮")
                        
            except Exception as e:
                logger.warning(f"Deepseek: 登录按钮点击失败: {e}")
                # 回退：尝试Playwright查找
                try:
                    submit_selectors = [
                        "button[type='submit']",
                        "button:has-text('登录')",
                        "button:has-text('Sign in')"
                    ]
                    for sel in submit_selectors:
                        try:
                            elements = await self.page.query_selector_all(sel)
                            if elements:
                                for elem in elements:
                                    if await elem.is_visible():
                                        await elem.click()
                                        logger.info(f"Deepseek: Playwright点击登录按钮成功: {sel}")
                                        break
                        except:
                            continue
                except Exception as e2:
                    logger.warning(f"Deepseek: Playwright登录按钮点击失败: {e2}")

            logger.info("Deepseek: 等待登录请求完成...")
            await self.page.wait_for_timeout(10000)  # 等待10秒
            # 检查当前URL，判断是否需要导航
            current_url = self.page.url
            logger.info(f"Deepseek: 当前URL: {current_url}")
            # 如果还在登录页面，再等待10秒
            if "sign_in" in current_url or "login" in current_url:
                logger.info("Deepseek: 还在登录页面，继续等待...")
                await self.page.wait_for_timeout(10000)

            # 尝试导航到聊天页面
            logger.info("Deepseek: 尝试导航到聊天页面...")
            try:
                await self.page.goto("https://chat.deepseek.com/", wait_until="domcontentloaded", timeout=30000)
                await self.page.wait_for_timeout(3000)
                logger.info(f"Deepseek: 导航后URL: {self.page.url}")
            except Exception as e:
                logger.warning(f"Deepseek: 导航失败: {e}")

            logger.info("Deepseek: 登录请求等待完成")
            await self._save_cookies(self.page.context)
            return True
        except Exception as e:
            logger.error(f"Deepseek 登录失败: {str(e)}")
            return False

    async def _navigate_to_chat(self) -> bool:
        try:
            await self.page.goto(self.platform_url, wait_until="domcontentloaded", timeout=60000)
            await self.page.wait_for_timeout(3000)
            return True
        except Exception as e:
            logger.error(f"Deepseek 导航失败: {str(e)}")
            return False

    async def _send_message(self, question: str) -> None:
        try:
            await self.page.wait_for_timeout(3000)
            # 最新的输入选择器
            input_selectors = [
                "textarea.ds-textarea",
                "textarea[placeholder*='输入问题']",
                "textarea[placeholder*='输入消息']",
                "textarea",
                "div[contenteditable='true']",
                "[role='textbox']"
            ]
            found_element = None
            for sel in input_selectors:
                try:
                    elements = await self.page.query_selector_all(sel)
                    for elem in elements:
                        if await elem.is_visible():
                            found_element = elem
                            logger.info(f"Deepseek 找到输入框: {sel}")
                            break
                    if found_element:
                        break
                except Exception as e:
                    logger.debug(f"Deepseek 检查 {sel} 失败: {e}")
            if not found_element:
                raise Exception("Deepseek 未找到输入框")
            await found_element.click()
            await self.page.wait_for_timeout(500)
            # 先尝试填充，回退为键入
            try:
                await found_element.fill(question)
            except:
                await found_element.type(question)
            await self.page.wait_for_timeout(500)

            # 尝试在输入框上按Enter键，回退为查找和点击发送按钮
            try:
                await found_element.press("Enter")
            except:
                send_selectors = [
                    "button:has(svg)",
                    "button:has-text('发送')",
                    "button:has-text('Send')",
                    "[class*='send']"
                ]
                send_btn = None
                for sel in send_selectors:
                    try:
                        elements = await self.page.query_selector_all(sel)
                        for elem in elements:
                            if await elem.is_visible():
                                send_btn = elem
                                break
                        if send_btn:
                            break
                    except:
                        continue
                if send_btn:
                    await send_btn.click()

            logger.info(f"Deepseek 发送问题: {question[:30]}...")
        except Exception as e:
            logger.error(f"Deepseek 发送消息失败: {str(e)}")
            raise

    async def _get_answer(self) -> str:
        try:
            answer_selectors = [
                ".message-content",
                ".ds-message-content",
                ".answer",
                "[class*='message']"
            ]
            max_wait = 60
            answer = ""
            last_answer = ""
            stable_count = 0
            stable_threshold = 3  # 需要连续3秒文本不变才算完成
            
            for _ in range(max_wait):
                current_text = ""
                for sel in answer_selectors:
                    try:
                        elems = await self.page.query_selector_all(sel)
                        if elems and len(elems) > 0:
                            last = elems[-1]
                            text = await last.inner_text()
                            if text and len(text.strip()) > 10:
                                current_text = text.strip()
                                break
                    except Exception as e:
                        logger.debug(f"Deepseek 获取回答 {sel} 失败: {e}")
                        continue
                
                if current_text:
                    answer = current_text
                    if current_text == last_answer:
                        stable_count += 1
                        logger.debug(f"Deepseek 回答稳定中: {stable_count}/{stable_threshold}")
                        if stable_count >= stable_threshold:
                            logger.info(f"Deepseek 回答已完全完成: {answer[:30]}...")
                            return answer
                    else:
                        stable_count = 0
                        last_answer = current_text
                elif answer:
                    # 如果已经有过回答，现在又空了，可能是刷新，继续等
                    stable_count = 0
                await self.page.wait_for_timeout(1000)
            
            if answer:
                logger.warning(f"Deepseek 未检测到完全稳定，但返回现有回答: {answer[:30]}...")
                return answer
            logger.warning("Deepseek 等待回答超时")
            return ""
        except Exception as e:
            logger.error(f"Deepseek 获取回答失败: {str(e)}")
            return ""

    async def screenshot(self, question: Question) -> tuple[Optional[str], bool, Optional[str]]:
        try:
            logger.info("deepseek 等待AI回复完全完成...")
            await self.page.wait_for_timeout(5000)  # 等待5秒确保回复彻底完成

            # 第一步：悬停到消息上，等待分享按钮出现
            logger.info("deepseek 步骤1: 悬停到消息上等待分享按钮...")
            
            message_selectors = [".message-content", ".ds-message-content", "[class*='message']"]
            last_message = None
            for sel in message_selectors:
                try:
                    elems = await self.page.query_selector_all(sel)
                    if elems and len(elems) > 0:
                        last_message = elems[-1]
                        break
                except:
                    continue
            
            if last_message:
                logger.info("deepseek 悬停到最后一条消息...")
                await last_message.hover()
                await self.page.wait_for_timeout(3000)  # 等待3秒让分享按钮完全出现
            
            # 第二步：找到分享按钮
            logger.info("deepseek 步骤2: 查找分享按钮...")
            share_button = None
            max_wait = 10
            
            # 先获取消息区域的边界框
            message_area_box = None
            try:
                # 尝试查找消息容器
                message_container = await self.page.query_selector("[class*='message'], .ds-message, [class*='chat']")
                if message_container:
                    message_area_box = await message_container.bounding_box()
                    logger.info(f"deepseek 消息区域: {message_area_box}")
            except Exception as e:
                logger.debug(f"deepseek 查找消息区域失败: {str(e)}")
            
            for _ in range(max_wait):
                # 查找所有可能的按钮元素
                all_elements = await self.page.query_selector_all("div[role='button'], .ds-icon-button, button")
                for elem in all_elements:
                    try:
                        if await elem.is_visible():
                            class_name = await elem.get_attribute("class") or ""
                            bounding_box = await elem.bounding_box()
                            
                            # 检查是否是分享按钮（新的class: _57370c5 _5dedc1e）
                            if "_57370c5" in class_name or "_5dedc1e" in class_name:
                                share_button = elem
                                logger.info(f"deepseek 找到分享按钮 (新class): {class_name[:50]}")
                                logger.info(f"deepseek 按钮位置: {bounding_box}")
                                break
                    except:
                        continue
                if share_button:
                    break
                
                if not share_button and i < max_wait - 1:
                    logger.debug(f"deepseek 等待分享按钮出现第{i+1}次...")
                    await self.page.wait_for_timeout(1000)
            
            if not share_button:
                share_button_selectors = [
                    "div.ds-icon-button__hover-bg",
                    "div.db183363.ds-icon-button.ds-icon-button--m.ds-icon-button--sizing-container",
                    ".ds-icon-button[role='button']",
                    "div[role='button'][tabindex='0']"
                ]
                for selector in share_button_selectors:
                    try:
                        elements = await self.page.query_selector_all(selector)
                        if elements:
                            for elem in elements:
                                if await elem.is_visible():
                                    # 验证是否在消息区域内
                                    bounding_box = await elem.bounding_box()
                                    if bounding_box and message_area_box:
                                        # 检查是否在消息区域右侧
                                        if bounding_box['x'] >= message_area_box['x']:
                                            share_button = elem
                                            logger.info(f"deepseek 找到分享按钮 (备用选择器): {selector}, 位置: {bounding_box}")
                                            break
                                    else:
                                        share_button = elem
                                        logger.info(f"deepseek 找到分享按钮 (备用选择器): {selector}")
                                        break
                        if share_button:
                            break
                    except Exception as e:
                        logger.debug(f"deepseek 检查分享按钮 {selector} 失败: {str(e)}")
                        continue

            if not share_button:
                logger.warning("deepseek 分享按钮未找到，使用默认截图")
                return await self._default_screenshot(question, answer)
            
            # 第三步：点击分享按钮
            logger.info("deepseek 步骤3: 点击分享按钮...")
            try:
                # 先检查元素信息
                is_visible = await share_button.is_visible()
                bounding_box = await share_button.bounding_box()
                logger.info(f"deepseek 分享按钮状态: 可见={is_visible}, 位置={bounding_box}")
                
                # 方法1：JavaScript点击
                await self.page.evaluate("(element) => { element.click(); }", share_button)
                logger.info("deepseek JavaScript点击成功")
                
                # 验证点击是否生效 - 检查按钮状态变化
                await self.page.wait_for_timeout(500)
                try:
                    # 检查是否有新的弹窗或遮罩层出现
                    overlay = await self.page.query_selector("[class*='overlay'], [class*='modal'], [class*='dialog']")
                    if overlay and await overlay.is_visible():
                        logger.info("deepseek 检测到弹窗/遮罩层出现")
                except:
                    pass
                    
            except Exception as e:
                logger.warning(f"deepseek JavaScript点击失败: {str(e)}，尝试普通点击")
                try:
                    await share_button.click()
                    logger.info("deepseek 普通点击成功")
                except Exception as e2:
                    logger.error(f"deepseek 普通点击也失败: {str(e2)}")
                    # 尝试通过坐标点击
                    if bounding_box:
                        x = bounding_box['x'] + bounding_box['width'] / 2
                        y = bounding_box['y'] + bounding_box['height'] / 2
                        await self.page.mouse.click(x, y)
                        logger.info(f"deepseek 坐标点击: ({x}, {y})")
            
            await self.page.wait_for_timeout(3000)  # 等待弹窗出现
            logger.info("deepseek 分享按钮已点击")
            
            # 调试：点击后立即截图看页面状态
            try:
                from datetime import datetime
                from pathlib import Path
                debug_path = Path("screenshots") / f"debug_after_click_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                await self.page.screenshot(path=str(debug_path), full_page=False)
                logger.info(f"deepseek 点击后截图保存: {debug_path}")
            except Exception as e:
                logger.debug(f"deepseek 点击后截图失败: {str(e)}")
            
            # 第四步：保存全屏截图
            logger.info("deepseek 步骤4: 保存全屏截图...")
            default_screenshot_path, _, _ = await self._default_screenshot(question, answer)
            
            # 第五步：等待弹窗出现并点击相关按钮
            logger.info("deepseek 步骤5: 等待弹窗...")
            share_link = None
            button_found = False
            
            for wait_round in range(10):
                await self.page.wait_for_timeout(500)
                
                # 调试：查看点击分享按钮后的页面状态
                if wait_round == 1 or wait_round == 3 or wait_round == 5:
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
                            logger.info(f"deepseek 弹窗调试(wait_round={wait_round}): {visible_with_text[:10]}")
                    except Exception as e:
                        logger.debug(f"deepseek 弹窗调试失败: {str(e)}")
                
                # 查找弹窗中的按钮
                button_selectors = [
                    "button:has-text('创建并复制')",
                    "[role='button']:has-text('创建并复制')",
                    "button:has-text('创建分享链接')",
                    "[role='button']:has-text('创建分享链接')",
                    "button:has-text('复制')",
                    "[role='button']:has-text('复制')",
                    ".ds-basic-button--primary"
                ]
                
                for selector in button_selectors:
                    try:
                        elements = await self.page.query_selector_all(selector)
                        if elements:
                            for elem in elements:
                                if await elem.is_visible():
                                    text = await elem.inner_text()
                                    text = text.strip() if text else ""
                                    if "创建并复制" in text or "创建分享链接" in text or "复制" in text:
                                        # 找到按钮了
                                        try:
                                            await self.page.evaluate("(element) => { element.click(); }", elem)
                                        except:
                                            await elem.click()
                                        logger.info(f"deepseek 找到并点击按钮: {text}")
                                        button_found = True
                                        
                                        # 如果点击的是创建分享链接，可能还需要再等一下找创建并复制
                                        if "创建分享链接" in text:
                                            await self.page.wait_for_timeout(2000)
                                            # 再次查找创建并复制
                                            for sel2 in ["button:has-text('创建并复制')", "[role='button']:has-text('创建并复制')"]:
                                                try:
                                                    elems2 = await self.page.query_selector_all(sel2)
                                                    if elems2:
                                                        for e2 in elems2:
                                                            if await e2.is_visible():
                                                                await e2.click()
                                                                logger.info("deepseek 点击创建并复制")
                                                                break
                                                except:
                                                    continue
                                        break
                        if button_found:
                            break
                    except Exception as e:
                        logger.debug(f"deepseek 查找按钮 {selector} 失败: {str(e)}")
                        continue
                if button_found:
                    break
            
            if button_found:
                await self.page.wait_for_timeout(2000)
                # 尝试获取链接
                try:
                    import pyperclip
                    share_link = pyperclip.paste()
                    if share_link and share_link.startswith("http"):
                        logger.info(f"deepseek 从剪贴板获取链接: {share_link}")
                    else:
                        # 查找链接输入框
                        try:
                            link_input = await self.page.query_selector("input[value*='http']")
                            if link_input:
                                share_link = await link_input.input_value()
                                logger.info(f"deepseek 从输入框获取链接: {share_link}")
                        except:
                            share_link = None
                except Exception as e:
                    logger.debug(f"deepseek 获取链接失败: {str(e)}")
            else:
                logger.warning("deepseek 未找到分享相关按钮，仅保存截图")

            return default_screenshot_path, False, share_link

        except Exception as e:
            logger.error(f"deepseek 截图失败: {str(e)}")
            return await self._default_screenshot(question)

    async def _default_screenshot(self, question: Question) -> tuple[Optional[str], bool, Optional[str]]:
        try:
            from datetime import datetime
            from pathlib import Path

            await self.page.wait_for_timeout(1000)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshots_dir = Path("screenshots")
            screenshots_dir.mkdir(exist_ok=True)
            
            screenshot_path = screenshots_dir / f"{self.platform_id}_{question.id}_{timestamp}_full.png"
            
            await self.page.screenshot(path=str(screenshot_path), full_page=True)
            logger.info(f"deepseek全屏截图已保存：{screenshot_path}")
            
            return str(screenshot_path), False, None

        except Exception as e:
            logger.error(f"deepseek 默认截图失败: {str(e)}")
            return None, False, None

    async def close(self):
        await super().close()
