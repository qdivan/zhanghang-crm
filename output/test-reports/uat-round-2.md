# UAT Round 2

## 基线
- 提交：`6a0efc9`
- 计划：`/Users/shangyifan/Documents/New project/.sdd/specs/2026-02-26-daizhang-mvp/execution-plan-uat-round-2.md`
- 当前状态：`DONE`

## 总结
- 场景总数：`20`
- 通过：`20`
- 失败：`0`
- 缺陷：`P0 0 / P1 0 / P2 0`
- 说明：本轮主测边界场景、权限边界、到账口径一致性与数据清理。为避免污染演示环境，已在最后执行清理。

## 结果表
| 编号 | 角色 | 模块 | 场景 | 期望 | 实际 | 严重级别 | 证据 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| UAT2-001 | boss | 客户开发 | 新增线索时输入已存在客户名 | 自动建议并关联已有客户，不重复建客户 | 在新增线索弹窗输入“海恩诺”后出现建议项“海恩诺 海恩诺负责人 / 13800000012”，可直接选择已有客户。 | PASS | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T17-41-36-503Z.yml` |
| UAT2-002 | boss | 客户开发 | 已关联老客户的线索再转化 | 复用已有客户，不重复生成客户档案 | 线索 19 转化后进入 /customers/2?from=leads；当时数据库中“海恩诺”客户数保持 1，lead#19 关联 existing customer#2。 | PASS | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T17-42-57-567Z.yml` |
| UAT2-003 | boss | 客户开发 | 放弃线索后列表排序与提醒 | 进入已丢失且不再要求继续提醒 | status=LOST, reminder=不跟进, next=None | PASS | `API GET /leads -> lead#20` |
| UAT2-004 | boss | 客户档案 | 新增待跟进事项并办结 | 状态、提醒、办结结果完整回写 | status=DONE, reminder=2026-03-27, completed=2026-03-25, result=UAT2-004 已办结 | PASS | `API /customers/13/timeline-events source_id=6` |
| UAT2-005 | boss | 客户档案 | 同一客户重复套用香港模板 | 同周期重复套用应被拦截 | status=400, detail=香港公司模板已应用到当前周期 | PASS | `API POST /customers/13/timeline-templates/hk-company` |
| UAT2-006 | accountant | 客户列表 | 直接访问他人客户详情 URL | 被拦截或看不到越权数据 | status=403, detail=No access to this customer | PASS | `API GET /customers/14 as accountant` |
| UAT2-007 | accountant | 收费明细 | 直接访问到账核对 URL | 被拦截 | status=403, detail=No access to receipt account ledger | PASS | `API GET /billing-records/receipt-account-ledger as accountant` |
| UAT2-008 | accountant | 收费明细 | 催收记录输入金额 | 不影响实收，金额仍按 0 处理 | received_amount=0.0 | PASS | `API GET /billing-records/19/activities + record list` |
| UAT2-009 | accountant | 收费明细 | 收款选择入账账户后到账核对同步 | 收费页与到账核对口径一致 | latest_receipt_account=支付宝, ledger_matches=2, received=154.0 | PASS | `API POST PAYMENTs + GET receipt-account-ledger?receipt_account=支付宝` |
| UAT2-010 | boss | 收费明细 | 提前终止日期键盘直输 | YYYYMMDD 可规范化并成功提交 | 终止日期输入 20261015 后自动规范为 2026-10-15；提交后收费单更新为 26.3-26.10，到期日 2026-10-15，备注追加“冲减费用:200.00”。 | PASS | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T17-57-18-760Z.yml ; /Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T17-57-33-186Z.yml` |
| UAT2-011 | manager | 客户列表 | 查看非下属客户详情 | 不可见 | status=403, detail=No access to this customer | PASS | `API GET /customers/13 as manager` |
| UAT2-012 | manager | 收费明细 | 查看非下属收费单 | 不可见 | record_count=1, contains_customer_13=False | PASS | `API GET /billing-records as manager` |
| UAT2-013 | manager | 到账核对 | 切换账户与时间范围 | 只统计下属范围且汇总/流水一致 | total_received=600.0, entry_sum=600.0, entries=1, all_subordinate=True | PASS | `API GET /billing-records/receipt-account-ledger?receipt_account=一帆光大 as manager` |
| UAT2-014 | admin | 管理员面板 | 把会计直属经理改派 | 保存后立即生效 | old_manager_has_customer14=False, new_manager_has_customer14=True | PASS | `API PATCH /users/4 manager_user_id + GET /customers as old/new manager` |
| UAT2-015 | admin | 管理员面板 | 停用有直属下属的部门经理 | 被正确拦截 | status=400, detail=该部门经理仍有关联下属，不能直接停用 | PASS | `API PATCH /users/7 {is_active:false}` |
| UAT2-016 | admin | 常用资料 | 内部资料改成公开资料 | 公开页可见且系统页仍可编辑 | public_hits=1, visibility=PUBLIC | PASS | `API PATCH /common-library-items/11 visibility=PUBLIC` |
| UAT2-017 | boss | 公开资料 | 公开资料搜索/筛选 | 能定位新增公开资料 | keyword_hits=1, module_keyword_hits=1 | PASS | `API GET /common-library-items/public?keyword=UAT2-016&module_type=TEMPLATE` |
| UAT2-018 | boss | 到账核对 | 筛选单一账户后累计入账连续正确 | 累计数不倒退 | entries=2, monotonic=True, temp_entries=2, total_received=154.0 | PASS | `API GET /billing-records/receipt-account-ledger?receipt_account=支付宝` |
| UAT2-019 | boss | 移动端 | 抽屉菜单切页后自动收起 | 不遮挡内容 | 390x844 视口下打开抽屉后点击“收费明细”，页面进入 /billing，抽屉已自动关闭（目标快照 dialog count = 0）。 | PASS | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T17-58-34-750Z.yml ; /Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T17-58-51-044Z.yml` |
| UAT2-020 | boss | 数据清理 | 删除本轮临时 UAT 数据 | 演示环境恢复整洁 | 已删除 temp lead#19/#20、客户事项、收费单、公开资料、临时经理账号，并将 accountant2 直属经理恢复为 7。 | PASS | `/Users/shangyifan/Documents/New project/output/test-reports/uat-round-2-cleanup.txt` |

## 清理说明
- 已回收本轮新增的重复线索、临时收费单、客户事项、公开资料、临时经理账号。
- `accountant2` 的直属经理已恢复为 `manager(id=7)`。
- 清理校验文件：`/Users/shangyifan/Documents/New project/output/test-reports/uat-round-2-cleanup.txt`
