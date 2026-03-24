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
| 2026-03-25 | 0 | 0 | 0 | 0 | 0 | 是 | Day 0 基线 smoke：boss 登录/客户列表/客户档案/收费明细/到账核对通过；accountant 登录/客户列表/客户档案/收费明细/常用资料通过。 |

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

## 修复出队规则
1. `P0`：立即修
2. `P1`：按影响面排序后集中修
3. `P2`：等一轮试运行结束后统一收口
4. `P3`：只归档，不抢占当前试运行节奏
