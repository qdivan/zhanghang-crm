# UAT Round 1

## 基线
- 提交：`60be401`
- 计划：`/Users/shangyifan/Documents/New project/.sdd/specs/2026-02-26-daizhang-mvp/execution-plan-uat-closure.md`
- 当前状态：`DONE`

## 结果表
| 编号 | 角色 | 模块 | 场景 | 期望 | 实际 | 严重级别 | 证据 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PRE-001 | boss | 登录/客户开发 | 正常登录并进入客户开发 | `/login -> /leads` | 通过，已进入客户开发首页 | PASS | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T15-11-49-150Z.yml` |
| UAT-001 | boss | 客户开发 | 新增线索 | 可录入并出现在未成单列表 | 通过，已创建 `UAT-BOSS-20260324-A`，线索出现在客户开发列表 | PASS | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T15-13-55-829Z.yml` |
| UAT-002 | boss | 客户开发 | 线索跟进并自动提醒 | 跟进后提醒值/下次提醒正确回写 | 通过，等级改为 `待下单` 后提醒值联动为 `3天`，客户档案显示下次提醒 `2026-03-27` | PASS | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T15-16-13-303Z.yml` |
| UAT-003 | boss | 客户开发 | 线索转客户并指定会计 | 成功进入客户列表且归属正确 | 通过，已转为客户 `ID 13`，分配会计 `accountant` | PASS | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T15-16-13-303Z.yml` |
| UAT-004 | boss | 客户列表/档案 | 查看客户档案 | 可见成单后完整时间线 | 通过，时间线包含开始开发、开发跟进、转化记录 | PASS | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T15-16-13-303Z.yml` |
| UAT-005 | boss | 客户档案 | 新增客户事项 | 事项进入时间线并带记录人 | 通过，新增 `UAT-005 客户已确认年审资料本周提交`，记录人显示 `boss` | PASS | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T16-29-12-962Z.yml` |
| UAT-006 | boss | 客户档案 | 香港公司模板 | 可生成年度事项与提醒 | 通过，已生成 3 条香港公司事项，时间线总数变为 `7 条` | PASS | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T16-30-19-325Z.yml` |
| UAT-007 | accountant | 客户列表 | 只看自己负责客户 | 无越权数据 | 通过，客户列表仅显示会计 `accountant` 负责客户，且侧栏无 `到账核对/管理员面板` | PASS | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T16-31-56-784Z.yml` |
| UAT-008 | accountant | 客户档案 | 查看客户时间线 | 可看到收费/事项/执行记录 | 通过，会计可查看客户完整时间线，包括 `boss` 记录的客户事项与香港模板事项 | PASS | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T16-32-19-115Z.yml` |
| UAT-009 | accountant | 收费明细 | 查看自己的收费单 | 列表只含自己范围 | 通过，会计可进入收费明细并查看本范围收费单，无到账核对入口 | PASS | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T16-32-40-021Z.yml` |
| UAT-010 | accountant | 收费明细 | 新增催收记录 | 催收记录可保存且不影响实收 | 通过，已新增 `UAT-010 催收日志`，金额保持 `0`，下次跟进为 `2026-03-28` | PASS | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T16-34-19-851Z.yml` |
| UAT-011 | accountant | 收费明细 | 新增收款记录 | 贷方/余额/到账账户正确更新 | 通过，海恩诺新增 `100` 元微信收款，贷方 `5600 -> 5700`，余额 `2800 -> 2700` | PASS | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T16-36-49-357Z.yml` |
| UAT-012 | accountant | 收费明细 | 点公司名看往来账 | 当前页可展开往来账 | 通过，点击 `海恩诺` 后当前页展开 `往来账 - 海恩诺` | PASS | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T16-33-22-538Z.yml` |
| UAT-013 | boss | 收费明细 | 查看逾期/到期提醒 | 逾期与 7 天内到期数据可信 | 通过，收费明细汇总显示 `收费单数 18 / 应收合计 81200 / 未收合计 52100 / 7天内到期 2 / 已逾期 11`，列表包含 `海恩诺` 与 `UAT-MANAGER-20260325-A` 的逾期记录 | PASS | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T17-24-10-433Z.yml` |
| UAT-014 | manager | 收费明细 | 查看下属会计收费范围 | 仅可见下属数据 | 通过，经理仅看到直属下属 `accountant2/3/4` 范围内收费；本轮用 `UAT-MANAGER-20260325-A` 作为下属样本，列表 `1 条`，无管理员入口 | PASS | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T17-23-09-817Z.yml` |
| UAT-015 | manager | 到账核对 | 按账户查收款 | 只看自己管理范围 | 通过，到账核对仅显示 `一帆光大 1 笔 / 600`，流水仅 1 条，记录人为 `accountant2` | PASS | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T17-23-33-827Z.yml` |
| UAT-016 | boss | 到账核对 | 核对微信/银行收款 | 左侧账户汇总与右侧流水一致 | 通过，左侧显示 `未指定 8 笔 / 37300`、`一帆光大 1 笔 / 600`、`微信 2 笔 / 400`；右侧流水同时包含 `海恩诺` 微信收款和 `UAT-MANAGER-20260325-A` 光大收款 | PASS | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T17-24-30-044Z.yml` |
| UAT-017 | admin | 管理员面板 | 用户角色与直属经理配置 | 可配置且立即生效 | 通过，管理员面板可见 `部门经理` 与 `直属经理` 配置；实测创建临时账号后编辑直属经理为 `manager`，列表即时回写，然后已删除恢复到 `7 人` | PASS | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T17-34-55-197Z.yml`；`/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T17-35-27-498Z.yml` |
| UAT-018 | admin | 常用资料 | 新增内部资料 | 内部资料仅系统内可见 | 通过，已新增 `UAT-018 内部资料 20260325`；系统内列表可见，公开资料页不可见 | PASS | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T17-27-26-749Z.yml`；`/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T17-29-48-402Z.yml` |
| UAT-019 | boss | 常用资料/公开资料 | 新增公开资料并查看公开页 | 公开资料页可见对应内容 | 通过，已新增 `UAT-019 公开资料 20260325`，公开资料页可直接看到对应标题与内容 | PASS | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T17-29-25-160Z.yml`；`/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T17-29-48-402Z.yml` |
| UAT-020 | boss | 全局 | 移动端主流程抽查 | 登录/客户档案/收费明细/到账核对无阻塞 | 通过，`390x844` 视口下，菜单抽屉、客户列表、客户档案、收费明细、到账核对均可通过移动端路径正常进入 | PASS | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T17-31-16-932Z.yml`；`/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T17-32-11-364Z.yml`；`/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T17-32-17-072Z.yml`；`/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T17-32-22-623Z.yml` |

## 结论
- 已完成：`PRE-001 + UAT-001 ~ UAT-020`
- 本轮结果：`PASS 21 / FAIL 0`
- 缺陷：`P0 0 / P1 0 / P2 0`

## 说明
- 为验证 `manager` 的收费/到账范围，本轮补充了一条下属样本客户与收费单：`UAT-MANAGER-20260325-A`（归属 `accountant2`）。
- 为验证管理员配置即时生效，本轮临时创建了账号 `uat_admin_role_0325`，验证后已删除。
