# AI 问答评测工具 - Tasks

## 阶段1：项目初始化（必须先做） ✅ 已完成
1. 创建项目目录结构（按上文结构） ✅
2. 初始化 git + .gitignore ✅
3. 创建虚拟环境 + 依赖安装（requirements.txt） ✅
   - 依赖：aiohttp, playwright, pandas, openpyxl, pyyaml, regex, pyperclip
4. 编写 config.yaml 模板（含示例问题、规则、平台开关） ✅
5. 编写日志工具（utils/logger.py） ✅

## 阶段2：平台适配器（逐个实现） ✅ 已完成
1. 基类：src/adapters/base.py（统一接口：ask(), screenshot()） ✅
2. 豆包适配器：doubao.py（API优先，无则Playwright） ✅
3. 元宝适配器：yuanbao.py ✅
4. 千问适配器：qwen.py ✅
5. 文心一言适配器：ernie.py ✅
6. Deepseek适配器：deepseek.py ✅
7. 所有适配器统一返回：answer, status, screenshot_path ✅

## 阶段3：核心引擎 ✅ 已完成
1. 限速器：src/engine/rate_limiter.py（令牌桶+随机间隔） ✅
2. 调度器：src/engine/scheduler.py（异步并发、任务队列、错误处理） ✅
3. 规则引擎：src/engine/rule_matcher.py（关键词/正则匹配、优先级） ✅
4. 数据模型：src/models/question.py, rule.py, result.py ✅

## 阶段4：结果导出 ✅ 已完成
1. 截图工具：src/utils/screenshot.py（Playwright分享页截图、保存到本地、支持分享链接提取） ✅
2. Excel导出：src/exporter/excel_exporter.py（生成表格、嵌入截图） ✅

## 阶段5：入口与测试 ⚠️ 部分完成
1. 编写 main.py（读取配置→调度→导出） ✅
2. 单元测试：每个适配器/引擎写1–2个测试用例 ❌ 未完成
3. 端到端测试：跑3个问题+2个平台，验证结果与截图 ✅
4. 优化限速：调整间隔，确保不封号 ✅

## 阶段6：文档与交付 ⚠️ 进行中
1. 完善 README.md（安装、配置、运行） ⚠️ 待完善
2. 生成示例配置与示例结果（包含截图） ✅
3. 提交代码到 GitHub 仓库 ✅
4. 发布 PyPI 包（可选） ❌ 暂不发布
5. 文档：用户手册、开发指南、贡献指南 ❌ 未开始