# Dev 真实试运行反馈日志

## 环境
- 基线提交：`fbef315`
- Web：`http://127.0.0.1:32080`
- API：`http://127.0.0.1:32000`
- 计划：`/Users/shangyifan/Documents/New project/.sdd/specs/2026-02-26-daizhang-mvp/execution-plan-dev-trial.md`

## 使用说明
- 每发现一个问题，新增一行。
- 不要只写“有问题”“不顺手”这类模糊描述。
- 必须写明具体页面、操作路径、期望、实际结果。
- 有截图时，把绝对路径写在“证据”列。

## 问题表
| 编号 | 日期 | 角色 | 页面 | 操作路径 | 期望 | 实际 | 严重级别 | 阻塞试用 | 证据 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 暂无 | - | - | - | - | - | - | - | - | - | - |

## 每日汇总
| 日期 | 新增问题数 | P0 | P1 | P2 | P3 | 是否继续试运行 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-03-25 | 0 | 0 | 0 | 0 | 0 | 是 | Day 0 基线 smoke + Day 1 桌面/移动端托管巡检完成：boss/accountant/manager/admin 核心页面可用，未发现问题；真实人工试运行待持续记录。 |
| 2026-03-25 | 0 | 0 | 0 | 0 | 0 | 是 | 安全性与性能专项完成：安全 `PASS 14/14`，API 性能通过，前端两项性能问题已优化并在浏览器内复测收口。 |
| 2026-03-25 | 0 | 0 | 0 | 0 | 0 | 是 | Day 2 托管巡检：`/api/v1/health` 正常、数据基线快照已刷新、boss/accountant/manager/admin 登录 smoke 正常；当前仍未收到真实人工试运行问题。 |

## Day 0 基线记录
- 角色 `boss`：已验证登录、客户列表、客户档案、收费明细、到账核对。
- 角色 `accountant`：已验证登录、客户列表、客户档案、收费明细、常用资料。
- 结果：未发现 `P0/P1/P2/P3`。
- 证据：
  - `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T18-14-40-148Z.yml`
  - `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T18-15-08-589Z.yml`
  - `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T18-15-21-866Z.yml`
  - `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T18-15-36-118Z.yml`
  - `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T18-17-41-667Z.yml`
  - `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T18-18-05-870Z.yml`
  - `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T18-18-29-636Z.yml`
  - `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T18-18-58-085Z.yml`

## Day 1 托管巡检补充
- 角色 `manager`：已验证登录、客户列表、收费明细、到账核对。
- 角色 `admin`：已验证登录、管理员面板。
- 结果：未发现 `P0/P1/P2/P3`。
- 说明：以上为托管巡检，不替代后续真实人工试运行。
- 证据：
  - `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T18-21-16-434Z.yml`
  - `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T18-21-16-888Z.yml`
  - `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T18-21-17-505Z.yml`
  - `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T18-21-18-368Z.yml`
  - `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T18-21-38-050Z.yml`
  - `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T18-21-38-762Z.yml`

## Day 1 移动端托管巡检补充
- 设备：`390x844`。
- 角色 `boss`：已验证移动端登录、客户开发、收费明细、到账核对。
- 角色 `accountant`：已验证移动端登录、客户开发、客户列表、收费明细、常用资料。
- 结果：未发现 `P0/P1/P2/P3`。
- 说明：移动端关键页面可进入，未出现明显阻塞。
- 证据：
  - `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T18-23-43-263Z.yml`
  - `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T18-23-47-960Z.yml`
  - `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T18-23-49-376Z.yml`
  - `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T18-23-50-741Z.yml`
  - `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T18-24-11-502Z.yml`
  - `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T18-24-16-662Z.yml`
  - `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T18-24-17-728Z.yml`
  - `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T18-24-19-107Z.yml`
  - `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T18-24-20-284Z.yml`

## 人工试运行基线快照
- 快照文件：`/Users/shangyifan/Documents/New project/output/test-reports/dev-trial-baseline-2026-03-25.md`
- 作用：作为真实人工试运行的事实对照基线，用于判断后续数据变化是否异常。
- 记录口径：线索/客户/收费单/待办/常用资料/账户收款分布。

## 执行辅助
- 每日清单：`/Users/shangyifan/Documents/New project/output/test-reports/dev-trial-daily-checklist.md`
- 快照脚本：`python3 /Users/shangyifan/Documents/New project/scripts/capture_dev_trial_snapshot.py`
- 试运行交接说明：`/Users/shangyifan/Documents/New project/output/test-reports/dev-trial-handoff-2026-03-25.md`

## 安全性与性能专项补充
- 专项计划：`/Users/shangyifan/Documents/New project/.sdd/specs/2026-02-26-daizhang-mvp/execution-plan-security-performance.md`
- 安全日志：`/Users/shangyifan/Documents/New project/output/test-reports/security-test-log.md`
- 性能日志：`/Users/shangyifan/Documents/New project/output/test-reports/performance-test-log.md`
- 汇总结论：`/Users/shangyifan/Documents/New project/output/test-reports/security-performance-summary.md`
- 当前结论：
  - 安全性：`PASS`
  - 性能：`PASS`
  - 当前无新增 `P0/P1/P2` 阻塞项

## Day 2 托管巡检补充
- 健康检查：`http://127.0.0.1:32000/api/v1/health -> {"status":"ok"}`
- 快照刷新：`/Users/shangyifan/Documents/New project/output/test-reports/dev-trial-baseline-2026-03-25.md`
- 浏览器 smoke：
  - `boss` 登录后进入 `/leads` 正常
  - `accountant` 登录后进入 `/leads` 正常
  - `manager` 登录后进入 `/leads` 正常
  - `admin` 登录后进入 `/leads` 正常
- 结果：未发现新增 `P0/P1/P2/P3`
- 可视化证据：
  - `boss -> 收费明细`：`/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-25T02-43-48-561Z.png`
  - `accountant -> 客户列表`：`/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-25T02-44-15-502Z.png`
  - `admin -> 管理员面板`：`/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-25T02-44-26-632Z.png`

## 修复出队规则
1. `P0`：立即修
2. `P1`：按影响面排序后集中修
3. `P2`：等一轮试运行结束后统一收口
4. `P3`：只归档，不抢占当前试运行节奏
