# Tasks - 2026-02-26-daizhang-mvp（Excel 覆盖路线）

## Phase 0 - Excel 基线（已完成）
1. `T0-1` 全量盘点三个 Excel 的字段、表结构、隐含逻辑。
   - Status: `DONE`
   - Output: `excel-analysis.md`
2. `T0-2` 将字段覆盖要求回写 SDD 文档。
   - Status: `DONE`
   - Output: `requirements.md`, `design.md`, `description.md`

## Phase 1 - 工程与认证（已完成）
1. `T1-1` 前后端脚手架与 Docker 启动链路。
   - Status: `DONE`
2. `T1-2` 本地账号登录 + JWT + RBAC。
   - Status: `DONE`
3. `T1-3` 路由守卫与基础布局。
   - Status: `DONE`

## Phase 2 - 客户开发字段覆盖（进行中）
1. `T2-1` 后端 `leads` 模型扩展，支持两套模板字段。
   - Status: `DONE`
2. `T2-2` 前端客户开发页支持模板切换与扩展字段录入。
   - Status: `DONE`
3. `T2-3` 明细跟进、最后跟进日期、提醒值联动。
   - Status: `DONE`
4. `T2-4` 补齐联系人字段缺口（传真、其他联系方式）并支持编辑。
   - Status: `DONE`
5. `T2-5` 地址资源（`地址资源` sheet）结构化页面。
   - Status: `DONE`
6. `T2-6` 线索独立详情页（总览 -> 明细页）。
   - Status: `DONE`
7. `T2-7` 线索转化后自动进入客户档案页。
   - Status: `DONE`

## Phase 2.5 - 客户管理闭环（进行中）
1. `T2.5-1` 新增客户列表 API 与页面（已转化客户可检索）。
   - Status: `DONE`
2. `T2.5-2` 新增客户档案 API 与页面（基础信息 + 来源线索 + 跟进历史）。
   - Status: `DONE`
3. `T2.5-3` 客户档案页支持继续跟进，回写来源线索最后跟进。
   - Status: `DONE`
4. `T2.5-4` 客户档案页支持编辑并持久化。
   - Status: `DONE`
5. `T2.5-5` 线索详情返回路径保持上下文（从客户列表进入则返回客户列表）。
   - Status: `DONE`

## Phase 3 - 收费台账覆盖（进行中）
1. `T3-1` 后端 `billing_records` 建模对齐 `周 (2)`。
   - Status: `DONE`
2. `T3-2` 收费台账页面（总费用/月费用/周期/到期日/付款方式/备注）。
   - Status: `DONE`
3. `T3-3` 收费状态显式字段（清账/全欠/部分收费）替代色块判断。
   - Status: `DONE`
4. `T3-4` 收款登记与催收日志（与台账联动）。
   - Status: `DONE`
5. `T3-5` 收费记录绑定客户档案（customer_id）并可跳转客户页。
   - Status: `DONE`
6. `T3-6` 转化撤销保护：有关联收费记录时禁止撤销。
   - Status: `DONE`
7. `T3-7` 收费序号改为数字，去除 `周xx` 语义并显示会计字段。
   - Status: `DONE`
8. `T3-8` 移除收费台账 6/7/8 月快照列，统一为通用月费用模型。
   - Status: `DONE`

## Phase 4 - Excel 导入（未开始）
1. `T4-1` 导入预览：识别三文件与字段映射。
   - Status: `TODO`
2. `T4-2` 导入提交：事务写入 + 错误回滚。
   - Status: `TODO`
3. `T4-3` 导入核对报表：客户数/跟进数/收费数核对。
   - Status: `TODO`

## Phase 5 - 验收与优化（未开始）
1. `T5-1` 角色验收脚本（老板/管理员/会计）。
   - Status: `TODO`
2. `T5-2` 手机端布局优化（客户开发页、收费台账页、地址资源页）。
   - Status: `TODO`
3. `T5-3` LDAP 单点登录接入（二期，当前仅完成账号同步）。
   - Status: `TODO`
4. `T5-4` 日期输入统一为“日历选择 + 键盘录入（YYYYMMDD/YYMMDD）”双模式。
   - Status: `DONE`
5. `T5-5` 第三方回归测试问题修复（会计跟进权限、转化分配会计、催收金额约束、演示账号扩容）。
   - Status: `DONE`
6. `T5-6` 管理员面板（用户管理）与权限边界实现（管理员全量、老板不含管理员）。
   - Status: `DONE`
7. `T5-7` 管理员面板增强（最近登录时间、操作日志、LDAP 设置与账号同步）。
   - Status: `DONE`
8. `T5-8` 客户开发总览精简（核心字段）与转化弹窗差异信息录入（客户名/联系人/电话）。
   - Status: `DONE`
9. `T5-9` 客户开发总览交互优化（已转化置底排序 + 流程说明弹窗 + 模板用途说明）。
   - Status: `DONE`
10. `T5-10` 管理员面板补齐账号删除闭环（前后端 DELETE + 关联数据阻断 + 审计日志）。
   - Status: `DONE`
11. `T5-11` 移动端主导航重构为抽屉菜单（修复侧栏挤压）。
   - Status: `DONE`
12. `T5-12` 用户管理与认证错误文案中文化 + 用户更新日志记录字段 diff。
   - Status: `DONE`
13. `T5-13` Docker 开发栈默认切换 PostgreSQL 连接（API 不再默认连 sqlite）。
   - Status: `DONE`
14. `T5-14` 收费收款抽屉“收款金额不可输入”阻塞修复（类型兼容识别 + 提交流程兜底）。
   - Status: `DONE`
15. `T5-15` 前端本地直跑 API 代理补齐（未配置 `VITE_API_BASE_URL` 时可通过 Vite proxy 访问后端）。
   - Status: `DONE`
16. `T5-16` 收费录入升级为多明细增行表单（线索转化 / 客户列表 / 收费台账统一支持同客户多条收费项批量录入）。
   - Status: `DONE`
17. `T5-17` 提前终止合同补充日期合法性校验（不得早于服务开始、不得晚于当前到期日）。
   - Status: `DONE`
18. `T5-18` 续费流程改造为“提醒 -> 复制到表单 -> 调整后确认”（Dashboard 待办与台账按钮统一打开续费确认表单）。
   - Status: `DONE`
19. `T5-19` Excel 原型映射回收：明确“总览 = 首 sheet / 详情 = 数字 sheet / 收费 = 周 (2)”的页面模型，并回写 `.sdd`。
   - Status: `DONE`
20. `T5-20` 客户开发、客户列表、客户档案按 Excel 原型收敛字段与布局，去掉过度产品化的首屏字段。
   - Status: `DONE`
21. `T5-21` 交互语义修正：客户开发公司名点击按状态进入线索详情或客户档案，详情页返回路径与来源页面一致。
   - Status: `DONE`

## Phase 6 - 多租户与备份（规划中）
1. `T6-1` 多租户基础模型（tenant / tenant_memberships）与 tenant_id 强制过滤。
   - Status: `TODO`
2. `T6-2` 账号删除升级为“软删除 + 回收站恢复 + 关联数据重分配”流程。
   - Status: `TODO`
3. `T6-3` PostgreSQL 备份体系（每日全量 + 15 分钟 WAL 增量 + 自动恢复演练）。
   - Status: `TODO`
4. `T6-4` 高风险操作审计增强（变更前后 diff、敏感事件分类）。
   - Status: `TODO`

## 当前迭代目标
1. 已完成“开发 -> 转化 -> 客户列表 -> 客户档案 -> 收费收款”闭环。
2. 当前界面收敛原则：总览页回到 Excel 首 sheet，详情页回到数字 sheet，系统规则字段不再主导首屏。
