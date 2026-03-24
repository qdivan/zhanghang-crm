# 页面优化 + 实机回归并行计划

## 基线
- 基线提交：`0216859`
- 当前分工：`Session A = 页面优化`，`Session B = 实机回归`
- 当前事实来源：本文件

## Shared execution contract
- `Session A` 只负责前端页面与样式，不改业务规则口径；允许修改视图、组件、布局、样式、提示文案。
- `Session B` 默认不改业务代码，只做实机回归、截图、缺陷登记；只在出现明确的前端文案/布局级小问题且不影响 `Session A` 文件 ownership 时，才可单独修复。
- 共享输出固定：
  - 计划：`/Users/shangyifan/Documents/New project/.sdd/specs/2026-02-26-daizhang-mvp/execution-plan-ui-regression.md`
  - 回归报告：`/Users/shangyifan/Documents/New project/output/test-reports/real-device-regression.md`
  - 截图：`/Users/shangyifan/Documents/New project/output/playwright/real-device/`

## Ownership
- `Session A` ownership：
  - `/Users/shangyifan/Documents/New project/apps/web/src/views/LoginView.vue`
  - `/Users/shangyifan/Documents/New project/apps/web/src/views/CustomerDetailView.vue`
  - `/Users/shangyifan/Documents/New project/apps/web/src/views/BillingView.vue`
  - `/Users/shangyifan/Documents/New project/apps/web/src/components/billing/BillingRecordsCard.vue`
  - `/Users/shangyifan/Documents/New project/apps/web/src/components/billing/BillingFilterCard.vue`
  - `/Users/shangyifan/Documents/New project/apps/web/src/components/billing/BillingSummaryPanel.vue`
  - `/Users/shangyifan/Documents/New project/apps/web/src/views/ReceiptReconciliationView.vue`
  - `/Users/shangyifan/Documents/New project/apps/web/src/views/DashboardView.vue`
  - `/Users/shangyifan/Documents/New project/apps/web/src/style.css`
- `Session B` ownership：
  - `/Users/shangyifan/Documents/New project/output/test-reports/real-device-regression.md`
  - `/Users/shangyifan/Documents/New project/output/playwright/real-device/`

## Current status
- `Session A`：`DONE`
- `Session B`：`DONE`
- 最新阻塞项：`无`
- 追加移动端 smoke：`DONE`（工作台 / 客户档案 / 收费明细 / 到账核对，390x844）

## Session A 范围
1. 登录页：继续减字，只保留品牌、系统范围、登录入口、公开资料次级入口；压缩左右留白，避免海报感过强。
2. 客户档案：继续压缩上半区信息块与按钮区，提升信息密度；把低频字段保持在折叠区，不回到大表格。
3. 收费明细：列表行高、列宽、筛选区、汇总区再收紧，强调“会计账页”感；公司名点击往来账的主路径保持不变。
4. 到账核对：优化左侧账户汇总与右侧流水表密度，减少空白；桌面端优先呈现“查账/核对”感，而不是普通后台表格。
5. 工作台：系统待办与手动待办布局收紧，保证高频任务一屏可读。
- 移动端优化只覆盖以上 5 页，不扩散到全站；目标是无横向空白、按钮不挤压、核心信息首屏可见。
- 不改数据结构、不改接口语义、不新增新模块；本轮只做页面与交互收敛。

## Session B 范围
- 设备：桌面 Chrome `1440x900`，移动 `390x844`
- 角色：`boss` / `admin` / `manager` / `accountant`
- 场景 24 条，格式固定为：`编号 / 角色 / 设备 / 页面 / 操作 / 期望 / 实际 / 严重级别 / 截图路径 / 是否阻塞 Session A`
- 严重级别：`P0` 核心流程走不通，`P1` 功能可走但有明显错误，`P2` 视觉/交互问题
- `Session B` 每发现一个 `P0/P1`，立即写入共享报告，不在聊天里堆积；`Session A` 只处理自己 ownership 内的 `P2` 和前端级 `P1`。

## Test Plan
- 每轮页面优化后固定执行：
  - `npm run build:web`
  - `cd /Users/shangyifan/Documents/New project/apps/api && ./.venv/bin/pytest -q`
- `Session B` 在桌面和移动端各做一轮 smoke：
  - 登录页
  - 客户档案
  - 收费明细
  - 到账核对
- 若 `Session A` 修改了高频页面布局，`Session B` 只重测受影响页面，不全量重跑 24 条，直到阶段收口后再做全量复测。

## Assumptions
- 当前业务功能主线已具备，接下来以“前端收敛 + 回归验收”为主，而不是继续扩新模块。
- 共享计划必须落到仓库文档；否则两个独立 session 无法稳定共享同一份执行上下文。
- 本轮不做 Excel 导入、多租户、软删除、备份等 Phase 6 工作。
- 如果回归暴露后端权限或数据错误，先记为缺陷，不在页面优化轮次里混合大范围后端重构。
