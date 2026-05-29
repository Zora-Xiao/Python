from typing import Optional
from src.adapters.base import BaseAdapter
from src.models.question import Question
from src.utils.logger import logger


class ErnieAdapter(BaseAdapter):
    def __init__(self, config: dict):
        super().__init__(config)
        self.platform_id = "ernie"
        self.platform_url = config.get("web_url", "https://yiyan.baidu.com/")
    
    async def _execute_login(self) -> bool:
        try:
            logger.info(f"{self.platform_id}开始自动登录...")
            
            # 第一步：点击登录按钮
            login_button_selectors = [
                "button:has-text('登录')",
                "button:has-text('Sign In')",
                "[data-testid='login']",
                ".login-btn",
                "a:has-text('登录')",
                "[class*='login']"
            ]
            
            login_button = None
            for selector in login_button_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    if elements:
                        for elem in elements:
                            is_visible = await elem.is_visible()
                            if is_visible:
                                login_button = elem
                                logger.info(f"{self.platform_id}找到登录按钮: {selector}")
                                break
                        if login_button:
                            break
                except:
                    continue
            
            if not login_button:
                logger.warning(f"{self.platform_id}未找到登录按钮")
                return False
            
            await login_button.click()
            await self.page.wait_for_timeout(3000)
            logger.info(f"{self.platform_id}已点击登录按钮")
            
            # 第二步：选择账户登入（而不是短信登入）
            # 根据截图，登录弹窗有"账号登录"和"短信登录"两个选项卡，需要先切换到账号登录
            account_login_selectors = [
                "button:has-text('账号登录')",
                "a:has-text('账号登录')",
                "[data-tab='account']",
                "[data-type='account']",
                ".tab-item:has-text('账号登录')",
                ".login-tabs button:first-child",
                "div[role='tab']:has-text('账号登录')",
                "span:has-text('账号登录')"
            ]
            
            account_login_button = None
            for selector in account_login_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    if elements:
                        for elem in elements:
                            is_visible = await elem.is_visible()
                            if is_visible:
                                account_login_button = elem
                                logger.info(f"{self.platform_id}找到账号登录按钮: {selector}")
                                break
                        if account_login_button:
                            break
                except:
                    continue
            
            if account_login_button:
                await account_login_button.click()
                await self.page.wait_for_timeout(2000)
                logger.info(f"{self.platform_id}已选择账号登录")
            else:
                logger.info(f"{self.platform_id}未找到账号登录按钮，可能已经是账号登录界面")
            
            # 第三步：填写用户名
            username_selectors = [
                "input[name='username']",
                "input[name='email']",
                "input[name='account']",
                "input[type='text']",
                "input[placeholder*='账号']",
                "input[placeholder*='用户名']",
                "input[placeholder*='邮箱']",
                "input[id*='username']",
                "input[id*='account']"
            ]
            
            username_selector = None
            for selector in username_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    if elements:
                        for elem in elements:
                            is_visible = await elem.is_visible()
                            if is_visible:
                                username_selector = elem
                                logger.info(f"{self.platform_id}找到用户名输入框: {selector}")
                                break
                        if username_selector:
                            break
                except:
                    continue
            
            if username_selector:
                await username_selector.fill(self.username)
                await self.page.wait_for_timeout(500)
                logger.info(f"{self.platform_id}已填写用户名")
            else:
                logger.warning(f"{self.platform_id}未找到用户名输入框")
                return False
            
            # 第四步：填写密码
            password_selectors = [
                "input[name='password']",
                "input[type='password']",
                "input[placeholder*='密码']",
                "input[id*='password']"
            ]
            
            password_selector = None
            for selector in password_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    if elements:
                        for elem in elements:
                            is_visible = await elem.is_visible()
                            if is_visible:
                                password_selector = elem
                                logger.info(f"{self.platform_id}找到密码输入框: {selector}")
                                break
                        if password_selector:
                            break
                except:
                    continue
            
            if password_selector:
                await password_selector.fill(self.password)
                await self.page.wait_for_timeout(500)
                logger.info(f"{self.platform_id}已填写密码")
            else:
                logger.warning(f"{self.platform_id}未找到密码输入框")
                return False
            
            # 第五步：勾选"阅读并接受"协议复选框
            agree_checkbox_selectors = [
                "input[type='checkbox']",
                "[name='agree']",
                "[name='accept']",
                "[id*='agree']",
                "[id*='accept']",
                ".checkbox",
                "label:has-text('阅读')",
                "label:has-text('接受')",
                "input:has-text('阅读')"
            ]
            
            agree_checkbox = None
            for selector in agree_checkbox_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    if elements:
                        for elem in elements:
                            is_visible = await elem.is_visible()
                            if is_visible:
                                # 检查是否已经勾选
                                is_checked = await elem.is_checked()
                                if not is_checked:
                                    agree_checkbox = elem
                                    logger.info(f"{self.platform_id}找到协议复选框: {selector}")
                                    break
                        if agree_checkbox:
                            break
                except:
                    continue
            
            if agree_checkbox:
                await agree_checkbox.click()
                await self.page.wait_for_timeout(500)
                logger.info(f"{self.platform_id}已勾选协议复选框")
            else:
                logger.info(f"{self.platform_id}未找到协议复选框或已勾选")
            
            # 第六步：点击提交按钮
            submit_selectors = [
                "button[type='submit']",
                "button:has-text('登录')",
                "button:has-text('确定')",
                "button:has-text('提交')",
                ".submit-btn",
                "input[type='submit']"
            ]
            
            submit_selector = None
            for selector in submit_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    if elements:
                        for elem in elements:
                            is_visible = await elem.is_visible()
                            if is_visible:
                                submit_selector = elem
                                logger.info(f"{self.platform_id}找到提交按钮: {selector}")
                                break
                        if submit_selector:
                            break
                except:
                    continue
            
            if submit_selector:
                await submit_selector.click()
                await self.page.wait_for_timeout(5000)
                logger.info(f"{self.platform_id}登录表单已提交")
            else:
                logger.warning(f"{self.platform_id}未找到提交按钮")
            
            return True
        except Exception as e:
            logger.error(f"{self.platform_id}自动登录失败：{str(e)}")
            return False
    
    async def _navigate_to_chat(self) -> bool:
        try:
            logger.info(f"{self.platform_id}正在导航到: {self.platform_url}")
            # 简化等待策略，先导航过去，后续再等待
            await self.page.goto(self.platform_url, wait_until="commit", timeout=30000)
            logger.info(f"{self.platform_id}导航完成")
            
            # 额外等待页面加载
            await self.page.wait_for_timeout(5000)
            
            # 添加调试信息
            try:
                title = await self.page.title()
                url = self.page.url
                logger.info(f"{self.platform_id}页面标题: {title}")
                logger.info(f"{self.platform_id}当前URL: {url}")
            except:
                logger.warning(f"{self.platform_id}获取页面信息失败")
            
            return True
        except Exception as e:
            logger.error(f"文心一言导航失败：{str(e)}")
            return False
    
    async def _send_message(self, question: str) -> None:
        try:
            # 先多等待一会儿页面完全加载
            logger.info(f"文心一言等待页面加载...")
            await self.page.wait_for_timeout(5000)
            
            input_selectors = [
                # 文心一言常见的输入框选择器
                "textarea[placeholder*='输入']",
                "textarea[placeholder*='提问']",
                "textarea",
                "div[contenteditable='true']",
                "[role='textbox']",
                ".input-box",
                ".chat-input",
                "#prompt-textarea",
                "[class*='prompt']",
                "[class*='input']"
            ]
            
            logger.info(f"文心一言尝试查找输入框...")
            input_selector = None
            for selector in input_selectors:
                try:
                    elems = await self.page.query_selector_all(selector)
                    if elems:
                        for elem in elems:
                            if await elem.is_visible():
                                input_selector = selector
                                logger.info(f"文心一言找到输入框: {selector}")
                                break
                    if input_selector:
                        break
                except Exception as e:
                    logger.debug(f"选择器 {selector} 失败: {e}")
                    continue
            
            if not input_selector:
                # 如果找不到，尝试截屏看看页面是什么样子
                logger.warning(f"文心一言未找到输入框，尝试直接用JavaScript发送...")
                # 先试一下页面上所有的textarea
                try:
                    # 使用JavaScript查找所有textarea并尝试填充
                    await self.page.evaluate("""
                        (q) => {
                            const textareas = document.querySelectorAll('textarea');
                            for (let ta of textareas) {
                                if (ta.offsetParent !== null) {
                                    ta.value = q;
                                    ta.dispatchEvent(new Event('input', { bubbles: true }));
                                    ta.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
                                    return true;
                                }
                            }
                            return false;
                        }
                    """, question)
                    await self.page.wait_for_timeout(2000)
                    logger.info(f"文心一言尝试用JavaScript发送消息完成")
                    return
                except Exception as js_e:
                    logger.error(f"JavaScript发送失败: {js_e}")
                    raise Exception("未找到输入框，且JavaScript发送失败")
            
            # 找到输入框了，正常发送
            await self.page.click(input_selector)
            await self.page.wait_for_timeout(500)
            await self.page.fill(input_selector, question)
            await self.page.wait_for_timeout(500)
            
            # 尝试按回车键发送
            await self.page.press(input_selector, "Enter")
            
            # 或者尝试找发送按钮
            try:
                send_selectors = [
                    "button:has-text('发送')",
                    "button:has-text('Send')",
                    ".send-btn",
                    "[class*='send']"
                ]
                for send_sel in send_selectors:
                    send_elems = await self.page.query_selector_all(send_sel)
                    if send_elems:
                        for se in send_elems:
                            if await se.is_visible():
                                await se.click()
                                logger.info(f"文心一言点击发送按钮: {send_sel}")
                                break
                    break
            except:
                pass
            
            logger.info(f"文心一言成功发送消息：{question[:30]}...")
            
        except Exception as e:
            logger.error(f"文心一言发送消息失败：{str(e)}")
            raise
    
    async def _get_answer(self) -> str:
        try:
            # 等待回答生成，多等一会儿
            logger.info(f"文心一言等待回答生成...")
            await self.page.wait_for_timeout(10000)
            
            answer_selectors = [
                ".message-content",
                "[class*='message']",
                "[class*='answer']",
                "[class*='response']",
                "div[class*='content']"
            ]
            
            for selector in answer_selectors:
                try:
                    answer_elements = await self.page.query_selector_all(selector)
                    if answer_elements:
                        # 取最后一个
                        last_answer = answer_elements[-1]
                        answer = await last_answer.inner_text()
                        if answer and len(answer.strip()) > 0:
                            logger.info(f"文心一言获取回答成功（选择器: {selector}）")
                            return answer.strip()
                except Exception as e:
                    logger.debug(f"选择器 {selector} 获取回答失败: {e}")
                    continue
            
            logger.warning(f"文心一言未找到回答，尝试返回页面可见文本")
            # 尝试返回页面的主要文本
            page_text = await self.page.evaluate("() => document.body.innerText")
            return page_text[:500] if page_text else "未找到回答"
        except Exception as e:
            logger.error(f"文心一言获取回答失败：{str(e)}")
            return f"获取回答失败: {str(e)}"
    
    async def ask(self, question) -> tuple[str, str]:
        """重写ask方法，简化流程"""
        try:
            logger.info(f"{self.platform_id}开始处理问题: {question.text[:30]}...")
            
            logger.info(f"{self.platform_id}步骤1: 获取浏览器")
            await self._get_browser()
            
            # 导航到聊天页面
            logger.info(f"{self.platform_id}步骤2: 导航到聊天页面")
            if not await self._navigate_to_chat():
                return "无法导航到对话页面", "error"
            
            # 跳过复杂的登录检查，直接发送消息
            logger.info(f"{self.platform_id}步骤3: 发送消息并获取回答")
            answer = await self._send_message_and_get_answer(question.text)
            logger.info(f"{self.platform_id}步骤4: 获取回答成功，长度: {len(answer)}")
            
            return answer, "success"
        except Exception as e:
            logger.error(f"{self.platform_id}适配器错误: {str(e)}")
            return f"请求异常：{str(e)}", "error"
    
    async def screenshot(self, question: Question, answer: str) -> tuple[Optional[str], bool, Optional[str]]:
        if self.page is None:
            return None, False, None
        
        try:
            logger.info(f"{self.platform_id}开始自定义截图流程...")
            
            # 等待回答完全加载
            await self.page.wait_for_timeout(3000)
            
            # 第一步：找到分享按钮并点击
            # 根据用户提供的HTML，分享按钮是一个SVG元素，class包含"share"
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
                                logger.info(f"{self.platform_id}找到分享按钮: {selector}")
                                break
                        if share_button:
                            break
                except Exception as e:
                    logger.debug(f"{self.platform_id}检查分享按钮选择器 {selector} 失败: {str(e)}")
                    continue
            
            if not share_button:
                logger.warning(f"{self.platform_id}未找到分享按钮，使用默认截图方法")
                return await self._default_screenshot(question, answer)
            
            await share_button.click()
            await self.page.wait_for_timeout(2000)
            logger.info(f"{self.platform_id}已点击分享按钮")
            
            # 第二步：点击生成图片
            generate_button_selectors = [
                "button:has-text('生成图片')",
                "button:has-text('生成')",
                "[class*='generate']",
                "[class*='image']",
                "[data-testid*='generate']"
            ]
            
            generate_button = None
            for selector in generate_button_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    if elements:
                        for elem in elements:
                            if await elem.is_visible():
                                generate_button = elem
                                logger.info(f"{self.platform_id}找到生成图片按钮: {selector}")
                                break
                        if generate_button:
                            break
                except Exception as e:
                    logger.debug(f"{self.platform_id}检查生成按钮选择器 {selector} 失败: {str(e)}")
                    continue
            
            if not generate_button:
                logger.warning(f"{self.platform_id}未找到生成图片按钮，使用默认截图方法")
                return await self._default_screenshot(question, answer)
            
            await generate_button.click()
            await self.page.wait_for_timeout(3000)  # 等待图片生成
            logger.info(f"{self.platform_id}已点击生成图片按钮")
            
            # 第三步：点击保存图片
            save_button_selectors = [
                "button:has-text('保存图片')",
                "button:has-text('保存')",
                "[class*='save']",
                "[download]",
                "[data-testid*='save']"
            ]
            
            save_button = None
            for selector in save_button_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    if elements:
                        for elem in elements:
                            if await elem.is_visible():
                                save_button = elem
                                logger.info(f"{self.platform_id}找到保存图片按钮: {selector}")
                                break
                        if save_button:
                            break
                except Exception as e:
                    logger.debug(f"{self.platform_id}检查保存按钮选择器 {selector} 失败: {str(e)}")
                    continue
            
            if not save_button:
                logger.warning(f"{self.platform_id}未找到保存图片按钮，使用默认截图方法")
                return await self._default_screenshot(question, answer)
            
            await save_button.click()
            await self.page.wait_for_timeout(2000)
            logger.info(f"{self.platform_id}已点击保存图片按钮")
            
            # 返回截图路径（实际保存路径需要根据下载目录确定）
            from src.utils.screenshot import ScreenshotTool
            screenshot_tool = ScreenshotTool()
            screenshot_path, is_shared_image, share_link = await screenshot_tool.capture_from_page(
                self.page, 
                self.platform_id, 
                question
            )
            
            return screenshot_path, True, share_link
            
        except Exception as e:
            logger.error(f"{self.platform_id}自定义截图失败：{str(e)}")
            return await self._default_screenshot(question, answer)
    
    async def _default_screenshot(self, question: Question, answer: str) -> tuple[Optional[str], bool, Optional[str]]:
        """默认截图方法"""
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
            logger.error(f"{self.platform_id}默认截图失败：{str(e)}")
            return None, False, None
    
    async def close(self):
        await super().close()