# AI 问答评测工具 - Tasks

## 阶段1：项目初始化和基础配置 ✅
1. 创建项目目录结构 ✅
2. 初始化 git + .gitignore ✅
3. 创建虚拟环境 + 安装 requirements.txt 依赖 ✅
   - 依赖包括：aiohttp, playwright, pandas, openpyxl, pyyaml, regex, pyperclip
4. 创建 config.yaml 配置文件模板 ✅
5. 创建日志工具模块 utils/logger.py ✅

## 阶段2：平台适配器开发 ✅
1. 创建 src/adapters/base.py 基类，包含 ask(), screenshot() 方法 ✅
2. 实现豆包适配器 doubao.py，包含 Cookie 管理 ✅
3. 实现元宝适配器 yuanbao.py，包含 Cookie 管理 ✅
4. 实现千问适配器 qwen.py，包含 Cookie 管理 ✅
5. 实现文心一言适配器 ernie.py，包含 Cookie 管理 ✅
6. Deepseek 适配器 deepseek.py，包含自动登录（username/password）✅
7. 实现各平台的回答获取逻辑 ✅
8. Cookie 保存和加载功能 ✅

## 阶段3：核心引擎 ✅
1. 实现 src/engine/rate_limiter.py 限速器 + 指数退避 ✅
2. 实现 src/engine/scheduler.py 调度器，支持并发/顺序模式 ✅
3. 实现 src/engine/rule_matcher.py 关键词/正则匹配规则引擎 ✅
4. 实现 src/models/question.py, rule.py, result.py 数据模型 ✅

## 阶段4：导出功能 ✅
1. 实现 src/utils/screenshot.py Playwright 截图工具 + 分享图片逻辑 ✅
2. Excel 导出器 src/exporter/excel_exporter.py 实现报告导出 ✅

## 阶段5：主程序集成 ✅
1. 创建 main.py 入口程序，集成所有模块 ✅
2. 支持顺序执行模式/并发模式配置 ✅
3. 配置文件支持多平台（已启用5个）+ 多规则 ✅
4. 实现完整的日志记录功能 ✅

## 阶段6：文档和优化 🔄
1. 更新 README.md 文档，添加阶段完成说明 ✅
2. 根据 spec.md 更新所有平台的截图流程 ✅
3. 更新 tasks.md 标记已完成任务 ✅
4. 添加单元测试（可选）
5. 代码优化和性能提升
