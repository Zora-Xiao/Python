# AI 问答评测工具

一个强大的 AI 平台问答评测工具，支持批量向多个 AI 平台发送问题，自动评测回答质量，生成详细的 Excel 报告和截图。

## 功能特性

### 浏览器自动化模式（推荐）
- ✅ **无需 API 密钥**：直接通过网页版对话交互
- ✅ **自动登录**：支持保存登录状态（Cookie）
- ✅ **真实截图**：截取实际对话页面，包含完整 UI
- ✅ **多平台支持**：豆包、元宝、千问、文心一言、Deepseek
- ✅ **异步并发处理**：提高评测效率
- ✅ **智能限速机制**：防止账号被封
- ✅ **灵活的规则引擎**：支持关键词和正则匹配
- ✅ **验证码处理**：支持手动处理和自动失败两种模式
- ✅ **Excel 报告导出**：包含截图嵌入和详细统计
- ✅ **详细的日志记录**：方便调试和追踪
- ✅ **统一的适配器架构**：代码复用率高，易于扩展

### API 模式（可选）
- 支持各平台的官方 API
- 适合批量自动化测试

## 项目结构

```
.
├── main.py                      # 主入口文件
├── config.yaml                  # 配置文件
├── requirements.txt             # 依赖包列表
├── .gitignore                   # Git 忽略文件
├── src/
│   ├── adapters/               # 平台适配器
│   │   ├── base.py            # 适配器基类（包含公共辅助方法）
│   │   ├── doubao.py          # 豆包适配器
│   │   ├── yuanbao.py         # 元宝适配器
│   │   ├── qwen.py            # 千问适配器
│   │   ├── ernie.py           # 文心一言适配器
│   │   └── deepseek.py        # Deepseek 适配器
│   ├── engine/                 # 核心引擎
│   │   ├── rate_limiter.py    # 限速器
│   │   ├── scheduler.py       # 调度器
│   │   └── rule_matcher.py    # 规则引擎
│   ├── models/                 # 数据模型
│   │   ├── question.py        # 问题模型
│   │   ├── rule.py            # 规则模型
│   │   └── result.py          # 结果模型
│   ├── utils/                  # 工具类
│   │   ├── logger.py          # 日志工具
│   │   └── screenshot.py      # 截图工具
│   └── exporter/               # 导出器
│       └── excel_exporter.py  # Excel 导出器
├── tests/                      # 测试目录
├── screenshots/                # 截图保存目录
├── results/                    # 结果保存目录
└── logs/                       # 日志保存目录
```

## 安装说明

### 环境要求

- Python 3.11+
- Windows/Linux/macOS

### 安装步骤

1. 克隆项目仓库

```bash
git clone <repository-url>
cd <project-directory>
```

2. 创建虚拟环境

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

3. 安装依赖

```bash
pip install -r requirements.txt
```

4. 安装 Playwright 浏览器

```bash
python -m playwright install chromium
```

## 配置说明

编辑 `config.yaml` 文件来配置评测工具：

### 问题配置

```yaml
questions:
  - id: q001
    text: "请介绍一下 Python 的主要特点"
    category: "编程语言"
```

### 规则配置

```yaml
rules:
  - id: r001
    name: "提及关键词"
    type: "keyword"
    keywords:
      - "Python"
      - "python"
    priority: 1
    label: "提及"
```

### 平台配置（浏览器自动化模式）

```yaml
platforms:
  doubao:
    enabled: true
    name: "豆包"
    web_url: "https://www.doubao.com/chat/"
    login_required: true
    login_url: "https://www.doubao.com/"
    credentials:
      username: ""
      password: ""
```

### 限速配置

```yaml
rate_limit:
  enabled: true
  max_requests_per_minute: 10
  min_interval: 2.0
  max_interval: 5.0
  exponential_backoff: true
  max_retries: 3
```

### 验证码处理配置

```yaml
captcha_handling:
  mode: "manual"    # manual: 等待用户手动处理验证码 | fail: 检测到验证码时直接标记失败
  timeout: 120      # 用户手动处理验证码的超时时间（秒）
  platforms:        # 需要启用验证码处理的平台列表
    - doubao
```

### 浏览器配置

```yaml
browser:
  headless: true    # 是否使用无头模式运行
  slow_mo: 100      # 操作间隔（毫秒），模拟人类操作速度
  timeout: 30000    # 页面超时时间（毫秒）
```

## 使用方法

### 基本使用（浏览器自动化模式）

```bash
python main.py config.yaml sequential
```

**运行说明**：
- **DeepSeek**：程序会自动登录（需配置 username 和 password），登录成功后保存 Cookie，后续运行自动验证 Cookie 有效性，Cookie 验证失败时等待手动重新登录
- **Qwen**：程序会自动登录（需配置 username 和 password），登录成功后保存 Cookie，后续运行自动验证 Cookie 有效性，Cookie 验证失败时等待手动重新登录
- **豆包、元宝、文心一言**：需要手动登录生成 Cookie，后续运行自动验证 Cookie 有效性，Cookie 验证失败时等待手动重新登录
- **验证码处理**：当检测到验证码时，根据配置模式处理（manual：等待用户手动完成；fail：直接标记失败）

### 指定配置文件

```bash
python main.py custom_config.yaml
```

### 顺序执行模式

```bash
python main.py config.yaml sequential
```

## 输出结果

### Excel 报告

工具会生成两个 Excel 文件：

1. `evaluation_results.xlsx` - 详细评测结果
   - 问题 ID、平台名称、问题内容、回答内容
   - 状态、匹配规则、错误信息、时间戳
   - 截图嵌入

2. `summary.xlsx` - 汇总统计
   - 总览统计
   - 各平台详细统计

### 截图

所有问答截图会保存在 `screenshots/` 目录下，包含完整的对话页面。

### 日志

运行日志会保存在 `logs/evaluation.log` 文件中。

## 规则引擎

规则引擎支持多种匹配方式：

### 关键词匹配

```yaml
type: "keyword"
keywords:
  - "Python"
  - "编程"
```

### 正则表达式匹配

```yaml
type: "regex"
pattern: "(推荐 | 建议).*(使用 | 采用 | 选择)"
```

### 质量检测

```yaml
type: "quality"
quality_keywords: ["好的", "没问题", "可以", "good", "great"]
quality_type: "positive"  # positive | negative
```

### 长度校验

```yaml
type: "length"
min_length: 10
max_length: 2000
```

### 相关性分析

```yaml
type: "relevance"
relevance_keywords: ["介绍", "说明", "解释", "是什么"]
```

规则按优先级从高到低匹配，可以设置多个规则。

## 平台登录说明

### 浏览器自动化模式

#### DeepSeek 平台（自动登录）
- 程序启动时自动完成登录
- 需要在 `config.yaml` 中配置 `username` 和 `password`
- 无需手动登录，自动化程度高
- 不保存 Cookie，每次运行都重新登录

#### 其他平台（手动登录生成 Cookie）
- 首次运行时需要手动登录
- 登录成功后 Cookie 会自动保存
- 后续运行会验证 Cookie 有效性
- 如果 Cookie 验证失败，会等待手动重新登录

**首次运行流程**：
1. 程序会自动打开浏览器
2. 手动登录到各个 AI 平台
3. 浏览器会保存 Cookie 和登录状态
4. 后续运行会验证 Cookie 有效性

**支持的平台**：
- 豆包：https://www.doubao.com/chat/
- 元宝：https://yuanbao.tencent.com/chat/
- 千问：https://chat.qwen.ai/
- 文心一言：https://yiyan.baidu.com/
- Deepseek：https://chat.deepseek.com/

**平台登录配置示例**：

```yaml
platforms:
  # 手动登录平台
  doubao:
    enabled: true
    cookies_path: "cookies/doubao_cookies.json"
  
  yuanbao:
    enabled: true
    cookies_path: "cookies/yuanbao_cookies.json"
  
  # 自动登录平台（需要配置账号密码）
  deepseek:
    enabled: true
    cookies_path: "cookies/deepseek_cookies.json"
    username: "your_email@example.com"
    password: "your_password"
```

### API 模式（可选）

各平台需要配置相应的 API 密钥：
- 豆包：在字节跳动开放平台申请
- 元宝：在腾讯云申请
- 千问：在阿里云申请
- 文心一言：在百度智能云申请
- Deepseek：在 Deepseek 官网申请

## 注意事项

1. **浏览器自动化模式**
   - 首次运行需要手动登录
   - 确保网络连接正常
   - 不要关闭自动打开的浏览器窗口
   - 登录状态会保存在浏览器配置中

2. **限速配置**
   - 注意调整限速参数，避免账号被封
   - 建议根据各平台的实际限制进行配置

3. **截图功能**
   - 需要足够的磁盘空间
   - 截图会保存在 screenshots 目录

4. **环境要求**
   - 首次运行需要安装 Playwright 浏览器
   - 建议在虚拟环境中运行

5. **安全警告**
   - `config.yaml` 文件包含敏感信息（用户名、密码等），**切勿提交到版本控制系统**
   - 项目已配置 `.gitignore`，会自动忽略 `config.yaml` 和 `cookies/` 目录
   - 建议使用环境变量管理敏感凭据，避免明文存储
   - 示例：
     ```bash
     export DOUBAO_USERNAME="your_username"
     export DOUBAO_PASSWORD="your_password"
     ```

## 故障排除

### 常见问题

1. **浏览器无法打开**
   - 确保已安装 Playwright：`python -m playwright install chromium`
   - 检查系统权限

2. **登录状态丢失**
   - 每次运行前确保已登录
   - 检查浏览器配置目录权限

3. **截图失败**
   - 确保浏览器窗口正常打开
   - 检查 screenshots 目录权限

4. **限速问题**
   - 调整 rate_limit 配置
   - 增加请求间隔时间

5. **Excel 导出失败**
   - 确保 results 目录存在且有写入权限
   - 检查是否安装了 openpyxl

6. **验证码问题**
   - 如果配置为 manual 模式，检测到验证码时程序会暂停等待用户手动处理
   - 如果配置为 fail 模式，检测到验证码时会直接标记失败并继续下一个平台
   - 建议将 slow_mo 设置为 100-200ms，降低触发验证码的概率

## 开发指南

### 添加新的平台适配器

1. 在 `src/adapters/` 目录下创建新的适配器文件
2. 继承 `BaseAdapter` 类
3. 实现 `_navigate_to_chat()`、`_send_message()` 和 `_get_answer()` 方法
4. 可使用基类提供的公共方法：
   - `_find_visible_element(selectors)` - 查找第一个可见元素
   - `_fill_form_field(selectors, value)` - 填写表单字段
   - `_click_button(selectors)` - 点击按钮
   - `_robust_click(element, description)` - 健壮的点击方法

示例：

```python
from src.adapters.base import BaseAdapter

class NewPlatformAdapter(BaseAdapter):
    async def _navigate_to_chat(self) -> bool:
        # 实现导航逻辑
        await self.page.goto("https://example.com/chat")
        return True
    
    async def _send_message(self, question: str) -> None:
        # 实现发送消息逻辑
        await self.page.fill("textarea", question)
        await self.page.press("textarea", "Enter")
    
    async def _get_answer(self) -> str:
        # 实现获取回答逻辑
        answer = await self.page.inner_text(".message-content")
        return answer
```

### 运行测试

```bash
pytest tests/
```

## 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 许可证

本项目采用 MIT 许可证。

## 联系方式

如有问题或建议，请提交 Issue。

## 更新日志

### v2.3.0 (2026-07-16)
- ✨ 文心一言平台登录状态检测优化：基于页面 JSON 数据中的 `isUserLogin` 字段精确判断登录状态
- ✨ 文心一言平台分享图片功能修复：实现分享按钮 → 生成图片 → 保存图片的完整流程
- ✨ 文心一言平台分享链接功能：添加 URL 过滤逻辑，只保存有效的 HTTP 链接
- ✨ 优化各平台适配器的截图流程，统一委托给 ScreenshotTool 处理
- 🐛 修复文心一言平台已登录但日志提示未登录的问题
- 🐛 修复文心一言平台分享按钮、生成图片按钮、保存图片按钮未找到的问题
- 🧹 清理 ernie.py 中的调试代码和重复方法
- 📦 更新 requirements.txt：移除未使用依赖（aiohttp, regex, python-dotenv），添加缺失依赖（pyperclip）

### v2.2.0 (2026-07-15)
- ✨ 豆包平台新增验证码（CAPTCHA）检测和处理机制
- ✨ 支持 manual 和 fail 两种验证码处理模式
- ✨ 优化浏览器行为：设置 slow_mo=100ms，添加随机延迟和鼠标移动模拟
- ✨ 重构 DeepSeek 自动登录流程，添加完整的登录验证机制
- ✨ 修复 Qwen 和 Doubao 平台回答内容误判问题（排除用户问题文本）
- ✨ 优化登录状态检测逻辑，基于 URL 模式判断登录状态
- 🐛 修复所有平台的登录状态误判问题
- 🐛 修复 DeepSeek 登录按钮点击失败但返回 True 的问题
- 🐛 修复 Ernie 截图方法参数错误问题
- 📦 平台成功率提升至 5/5（100%）

### v2.1.0 (2026-06-09)
- ✨ 重构适配器架构，提取公共方法到 BaseAdapter 基类
- ✨ 统一代码风格和异常处理机制
- ✨ 优化豆包适配器的回答获取逻辑（支持流式输出检测）
- ✨ 优化各平台适配器的登录、消息发送和截图功能
- 🐛 修复所有代码诊断警告（未使用变量、不可达代码等）
- 📦 代码重复率降低约 60%，代码行数减少约 200 行

### v2.0.0 (2026-05-25)
- ✨ 新增浏览器自动化模式
- ✨ 支持网页版对话交互
- ✨ 无需 API 密钥即可使用
- ✨ 自动保存登录状态
- 🐛 修复截图功能
- 🐛 优化适配器架构

### v1.0.0 (2024-01-01)
- 初始版本发布
- 支持 5 个 AI 平台
- 实现核心评测功能
- Excel 报告导出
- 自动截图功能
