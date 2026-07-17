# AI 问答评测工具 - Spec

## 1. 项目目标
批量向多个AI平台发送固定问题，按规则自动判断回答质量，输出Excel报告并自动截图，用于对比各平台在特定场景下的表现。

## 2. 范围
### 包含
- 问题列表与规则配置
- 5大AI平台对接（豆包、元宝、千问、文心一言、Deepseek）
- 异步并发调度 + 限速防封号
- 规则引擎（关键词/正则匹配）
- 自动截图（分享页）
- Excel结果导出（含截图嵌入）

### 不包含
- GUI界面（纯命令行）
- 付费API密钥管理（用户自行配置）
- 人工审核环节

## 3. 核心流程
1. 读取 config.yaml → 问题列表、规则、平台配置
2. 初始化各平台适配器（API/Playwright）

### 登录方式
- **DeepSeek**：自动登录（需配置 username/password），保存 Cookie，Cookie 验证失败时自动等待手动重新登录
- **Qwen**：自动登录（需配置 username/password），保存 Cookie，Cookie 验证失败时自动等待手动重新登录
- **其他平台（豆包、元宝、千问、文心）**：手动登录生成 Cookie，Cookie 验证失败时自动等待手动重新登录

1. 并发调度：对每个问题，依次/错开发送到选中平台（支持顺序处理模式）
2. 每个平台：发送问题 → 等待回复完成 → 获取回答 → 截图 → 返回结果
   - **验证码处理**（豆包平台）：
     - 在发送消息和获取回答过程中，检测页面是否出现验证码
     - 检测方式：关键词检测（验证、人机、captcha、滑块、图片验证）和 CSS 选择器检测（.captcha、[class*='verify']、[class*='slider']、.geetest）
     - 处理方式：根据配置模式处理
       - manual 模式：暂停自动化流程，等待用户手动完成验证码（超时时间可配置，默认 120 秒）
       - fail 模式：直接标记任务失败，继续下一个平台
   - **截图流程**（豆包平台）：
     - 等待AI回复完成（检测输入框可用或回复内容已渲染）
     - 第一步：点击分享会话按钮（带SVG图标的特定按钮，data-dbx-name='button'，data-state='closed'）
     - 第二步：点击"分享图片"按钮（透明背景按钮）
     - 第三步：点击"下载图片"按钮（高亮背景按钮）
     - 失败回退：若任意步骤失败，使用页面全屏截图
   - **截图流程**（千问平台）：
     - 等待AI回复完成（检测输入框可用或回复内容已渲染）
     - 第一步：页面全屏截图
     - 第二步：点击分享按钮（精确选择器 .qwen-chat-package-comp-new-action-control-container-share）
     - 第三步：点击"复制链接"按钮（button:has-text('复制链接')），并保存链接到文本文件
     - 失败回退：若分享链接失败，仅保留页面截图
   - **截图流程**（Deepseek平台）：
     - 等待AI回复完成（等待3秒确保回答完全加载）
     - 第一步：页面全屏截图同时点击分享按钮
       - 先保存页面全屏截图
       - 点击分享按钮，HTML内容为：div class="db183363 ds-icon-button ds-icon-button--m ds-icon-button--sizing-container" tabindex="0" role="button" aria-disabled="false"
       - 选择器列表：div.db183363.ds-icon-button.ds-icon-button--m.ds-icon-button--sizing-container, .ds-icon-button[role='button'], div[role='button'][tabindex='0']
     - 第二步：点击"创建分享链接"按钮
       - HTML内容为：button role="button" aria-disabled="false" class="ds-atom-button ds-basic-button ds-basic-button--primary"
       - 选择器列表：button.ds-atom-button.ds-basic-button.ds-basic-button--primary:has-text('创建分享链接'), button:has-text('创建分享链接'), .ds-basic-button--primary:has-text('创建')
     - 第三步：点击"创建并复制"按钮
       - 复制链接地址并保存到Excel中
       - 选择器列表：button:has-text('创建并复制'), button:has-text('复制'), .ds-basic-button--primary:has-text('复制')
     - 失败回退：若任意步骤失败，使用默认截图方法（页面全屏截图）
   - **截图流程**（文心一言平台）：
     - 等待AI回复完成（等待3秒确保回答完全加载）
     - 第一步：查找并点击分享按钮（SVG元素，class包含"share"）
       - 选择器列表：div[class*='share'], button[class*='share'], svg[class*='share'], [class*='share-btn'], [class*='share-button'], [data-testid*='share'], .share-icon, button:has(svg[class*='share'])
     - 第二步：点击"生成图片"按钮
       - 选择器列表：button:has-text('生成图片'), button:has-text('生成'), [class*='generate'], [class*='image'], [data-testid*='generate']
       - 等待3秒让图片生成
     - 第三步：点击"保存图片"按钮
       - 选择器列表：button:has-text('保存图片'), button:has-text('保存'), [class*='save'], [download], [data-testid*='save']
     - 失败回退：若任意步骤失败，使用默认截图方法（页面全屏截图）
   - **截图流程**（元宝平台）：
     - 等待AI回复完成（等待5秒确保回答完全加载）
     - 第一步：查找并点击分享按钮
       - HTML结构：div class="Toolbar_icon__xGP8b Toolbar_shareIcon__pXI31 Toolbar_isWeb__zF51c"
       - 内部SVG：span class="yb-icon iconfont-yb icon-yb-ic_share_2504"
       - 选择器列表：div.Toolbar_shareIcon__pXI31, div[class*='Toolbar_shareIcon'], span.icon-yb-ic_share_2504, div[class*='shareIcon']
       - 点击方式：直接点击、JS点击、坐标点击（多种方式确保成功）
       - 点击前确保按钮在可视区域（scroll_into_view_if_needed）
     - 第二步：等待分享弹窗出现并点击"生成图片"按钮
       - 弹窗HTML结构：div class="agent-chat__share-bar-container"
       - 生成图片按钮位于弹窗中央第二个位置
       - HTML结构：div class="agent-chat__share-bar__item" 包含 div.agent-chat__share-bar__item__name:has-text('生成图片')
       - 选择器列表：div.agent-chat__share-bar__content__center .agent-chat__share-bar__item:nth-child(2), div.agent-chat__share-bar__item:has(div.agent-chat__share-bar__item__name:has-text('生成图片'))
       - 点击方式：直接点击、点击内部元素（logo/name/svg）、JS点击、坐标点击
       - 等待图片生成（最多10秒，分阶段检查预览弹窗）
     - 第三步：查找并点击下载按钮
       - 选择器列表：div.agent-chat__share-bar__item:has(div:has-text('下载')), div[class*='share-bar'] button:has-text('下载'), div:has-text('下载')
       - 点击方式：直接点击、JS点击
       - 等待下载完成（5秒）
     - 第四步：截取生成的图片
       - 图片元素选择器：div[class*='preview'] img, img[src*='blob:'], img[src*='data:image'], canvas[class*='share']
       - 优先选择blob或data:image类型的图片，其次选择canvas元素
       - 保存截图到 screenshots/yuanbao_share_{timestamp}.png
     - 失败回退：若任意步骤失败，使用默认截图方法（页面全屏截图）
     - 调试功能：每个关键步骤保存调试截图和HTML，便于问题排查
3. 规则引擎：匹配回答 → 输出标签（支持多种规则类型）
   - **keyword**：关键词匹配，检测回答中是否包含指定关键词
   - **regex**：正则表达式匹配，使用正则模式检测回答内容
   - **quality**：质量检测，分为 positive（正面评价）和 negative（负面评价）
   - **length**：长度校验，根据回答字数判断是否正常/过短/过长
   - **relevance**：相关性分析，检测回答是否与问题相关
4. 结果汇总 → 写入Excel → 嵌入截图
5. 将获取的链接地址单独保存至文本文件（share_links.txt）
6. 输出日志与报告文件

## 4. 技术约束
- 语言：Python 3.11+
- 并发：asyncio + aiohttp
- 浏览器：Playwright（无头模式）
- 表格：pandas + openpyxl
- 剪贴板：pyperclip（系统剪贴板访问）
- 限速：令牌桶 + 指数退避 + 随机间隔
- 编码：UTF-8，日志级别INFO