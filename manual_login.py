import asyncio
import json
import os
from playwright.async_api import async_playwright

async def manual_login(platform_name, platform_url, cookie_file):
    """手动登录并保存Cookie"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--start-maximized'
            ]
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        page = await context.new_page()
        
        try:
            print(f"正在打开 {platform_name}...")
            await page.goto(platform_url, wait_until="domcontentloaded", timeout=60000)
            
            print(f"\n{'='*60}")
            print(f"请手动完成以下操作:")
            print(f"1. 在浏览器窗口中登录您的 {platform_name} 账号")
            print(f"2. 确保登录成功后进入聊天界面")
            print(f"3. 按 Enter 键保存Cookie")
            print(f"{'='*60}")
            
            # 等待用户手动登录
            await asyncio.get_event_loop().run_in_executor(None, input)
            
            # 获取Cookie
            cookies = await context.cookies()
            print(f"\n已获取 {len(cookies)} 个Cookie")
            
            # 保存Cookie到文件
            os.makedirs(os.path.dirname(cookie_file), exist_ok=True)
            with open(cookie_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, indent=2, ensure_ascii=False)
            
            print(f"Cookie已保存到: {cookie_file}")
            
            # 测试登录状态
            print("\n测试登录状态...")
            await page.wait_for_timeout(2000)
            
            # 检查是否有输入框（表示已登录到聊天界面）
            input_selectors = [
                "textarea",
                "[contenteditable='true']",
                "[role='textbox']"
            ]
            
            found_input = False
            for selector in input_selectors:
                elements = await page.query_selector_all(selector)
                if elements:
                    found_input = True
                    print(f"✅ 找到输入框，登录成功!")
                    break
            
            if not found_input:
                print("⚠️ 未找到输入框，请检查是否已正确登录")
            
        except Exception as e:
            print(f"\n❌ 错误: {str(e)}")
        finally:
            await browser.close()
            print("\n浏览器已关闭")

if __name__ == "__main__":
    # 配置
    PLATFORM_NAME = "豆包"
    PLATFORM_URL = "https://www.doubao.com/chat/"
    COOKIE_FILE = "cookies/doubao_cookies.json"
    
    print(f"{'='*60}")
    print(f"手动登录工具 - {PLATFORM_NAME}")
    print(f"{'='*60}")
    
    asyncio.run(manual_login(PLATFORM_NAME, PLATFORM_URL, COOKIE_FILE))
    print("\n操作完成!")
