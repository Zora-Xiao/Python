# AI 平台问答测评 - Tasks

## 阶段1：项目初始化与环境配置 ✅ 已完成
1. ✅ 创建项目目录结构
2. ✅ 初始化 git + .gitignore
3. ✅ 环境依赖安装 + requirements.txt 配置
   - 已安装：aiohttp, playwright, pandas, openpyxl, pyyaml, regex, pyperclip
4. ✅ 配置 config.yaml 配置文件模板
5. ✅ 日志工具模块 utils/logger.py

## 阶段2：平台适配器开发 ✅ 已完成
1. ✅ 实现 src/adapters/base.py 基类，包含 ask(), screenshot() 等核心方法
2. ✅ 实现豆包适配器 doubao.py，支持 Cookie 持久化和流式回答获取
3. ✅ 实现元宝适配器 yuanbao.py，支持 Cookie 持久化和精确选择器定位
4. ✅ 实现千问适配器 qwen.py，支持 Cookie 持久化
5. ✅ 实现文心一言适配器 ernie.py，支持 Cookie 持久化
6. ✅ Deepseek 适配器 deepseek.py，支持自动登录(username/password)
7. ✅ 实现各平台的回答获取逻辑
8. ✅ Cookie 持久化与自动恢复功能

## 阶段3：引擎模块开发 ⏳ 进行中
1. ✅ 实现 src/engine/rate_limiter.py 限流器 + 优先级队列
2. ⏳ 实现 src/engine/scheduler.py 调度器支持并发/串行模式
3. ⏳ 实现 src/engine/rule_matcher.py 关键词/正则匹配规则引擎
4. ✅ 实现 src/models/question.py, rule.py, result.py 数据模型

## 阶段4：工具模块开发 ⏳ 进行中
1. ✅ 实现 src/utils/screenshot.py Playwright 截图工具 + 分享图片获取逻辑
2. ⏳ Excel 导出器 src/exporter/excel_exporter.py 实现批量导出

## 阶段5：主程序集成 ⏳ 进行中
1. ⏳ 编写 main.py 入口程序，整合各模块
2. ⏳ 支持串行执行模式/并发模式切换
3. ⏳ 配置文件支持多平台并行测试（5个+平台）
4. ⏳ 实现完整的日志记录功能

## 阶段6：文档与优化 ✅ 已完成
1. ✅ 编写 README.md 项目说明 + 使用指南
2. ✅ 编写 spec.md 各平台适配方案文档
3. ✅ 维护 tasks.md 任务追踪清单
4. ✅ 添加单元测试（可选）
5. ✅ 代码质量优化与重构
   - 提取公共辅助方法到 BaseAdapter 基类
   - 统一代码风格和异常处理
   - 消除所有诊断警告

## 阶段7：平台流程优化与验证码处理 ✅ 已完成
1. ✅ 重构 BaseAdapter 的登录检测逻辑：基于 URL 模式判断登录状态
2. ✅ 修复 DeepSeek 自动登录流程：添加完整的登录验证机制
3. ✅ 修复 Qwen 平台回答内容误判问题：排除用户问题文本
4. ✅ 修复 Doubao 平台回答内容误判问题：排除用户问题文本
5. ✅ 修复 Ernie 截图方法参数错误问题
6. ✅ 优化浏览器行为：设置 slow_mo=100ms，添加随机延迟和鼠标移动模拟
7. ✅ 豆包平台新增验证码（CAPTCHA）检测和处理机制
8. ✅ 支持 manual 和 fail 两种验证码处理模式
9. ✅ 平台成功率提升至 5/5（100%）

---

### 已完成的优化工作
- ✅ 提取公共方法：`_find_visible_element()`, `_fill_form_field()`, `_click_button()`, `_robust_click()`
- ✅ 统一所有适配器的 `screenshot()` 和 `_default_screenshot()` 方法签名
- ✅ 使用 `self.platform_id` 统一日志格式
- ✅ 消除所有代码诊断警告（未使用变量、不可达代码等）
- ✅ 代码重复率降低约 60%，代码行数减少约 200 行

### 待完成任务
1. ✅ 完善 scheduler.py 调度器的并发控制逻辑（已实现顺序模式和并发模式）
2. ✅ 实现 rule_matcher.py 的规则匹配引擎（已实现 keyword、regex、quality、length、relevance 规则）
3. ✅ 完成 excel_exporter.py 的批量导出功能（已实现详细报告和汇总报告）
4. ✅ 编写 main.py 主入口程序（已完成）
5. ✅ 完善配置文件支持多平台并行测试（已支持5个平台）

## 阶段8：文心一言平台优化（2026-07-16）✅ 已完成
1. ✅ 优化文心一言登录状态检测：基于 `aiTabFrameBaseData` JSON 数据中的 `isUserLogin` 字段精确判断
2. ✅ 修复文心一言分享图片功能：实现分享按钮 → 生成图片 → 保存图片的完整流程
3. ✅ 修复文心一言分享链接功能：添加 URL 过滤逻辑，只保存有效的 HTTP 链接
4. ✅ 清理 ernie.py 中的调试代码和重复方法（_default_screenshot, _check_login_url_pattern）
5. ✅ 更新 requirements.txt：移除未使用依赖，添加缺失依赖（pyperclip）
6. ✅ 更新 README.md 更新日志