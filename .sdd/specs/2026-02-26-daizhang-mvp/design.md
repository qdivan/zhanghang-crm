# Design - 代账客户开发与收款系统 MVP（Excel 对齐）

## 1. Design Inputs
1. `requirements.md`（全字段覆盖要求）
2. `excel-analysis.md`（字段、含义、逻辑盘点）

## 2. Architecture

### 2.1 Modules
1. `auth-rbac`：本地登录 + 角色权限。
2. `lead-board`：客户总览（两套模板字段并存）。
3. `lead-followup`：按客户跟进明细。
4. `lead-detail`：线索独立详情页（Excel 明细视角）。
5. `customer-registry`：已转化客户列表。
6. `customer-detail`：客户档案页（基础信息 + 来源线索 + 跟进历史）。
7. `address-resource`：地址资源池（转化前线索资源）。
8. `billing-register`：收费台账（周/周(2) 语义）。
9. `billing-activity`：催收与收款日志。
10. `user-admin`：管理员面板（用户管理 + 登录时间 + 操作日志）。
11. `ldap-sync`：LDAP 配置与账号同步（兼容群晖 LDAP）。
12. `import-mapper`：Excel 导入预览与映射。

### 2.2 Data Flow
1. 客户开发：总览字段录入 -> 跟进明细 -> 更新最后跟进日期/提醒值。
2. 线索详情：从总览进入独立页，展示固定字段与跟进列表。
3. 客户转化：线索转化 -> 客户分配会计 -> 可覆盖客户基础信息（名称/联系人/电话）-> 前端跳转客户档案页。
   - 转化时必须选 `ACCOUNTANT`，不允许分配为 `OWNER/ADMIN`。
4. 转化撤销：若误转化可撤销（无收费记录前提下）；有收费记录时禁止撤销。
5. 客户管理：客户列表检索 -> 打开客户档案 -> 编辑/继续跟进。
   - 已分配会计可在客户档案直接新增跟进记录。
6. 地址资源：录入资源 -> 作为线索来源引用。
7. 收费台账：维护总费用/月费用/周期/到期日/付款方式/备注。
8. 催收/收款：对台账记录追加日志 -> 自动更新已收/未收与台账状态。
   - `REMINDER` 类型金额固定 `0`，`PAYMENT` 才允许金额入账。
9. 状态语义：由“颜色”迁移为结构化状态字段（清账/全欠/部分收费）。
10. 用户管理：`ADMIN` 管理所有本地账号；`OWNER` 仅管理非管理员账号。
11. LDAP 同步：管理员保存 LDAP 连接参数 -> 手动触发同步 -> 新增/更新本地账号。
12. 审计日志：核心写操作与登录写入 `operation_logs`，管理员面板可检索。

## 3. Data Model（MVP）

### 3.1 `leads`
用于承载两套模板字段：
1. 通用：
   - `id`, `template_type(FOLLOWUP|CONVERSION)`, `status`, `owner_id`
   - `name`, `grade`, `contact_name`, `phone`, `next_reminder_at`, `last_followup_date`, `reminder_value`
2. 跟进模板字段：
   - `country`, `service_start_text`, `company_nature`, `service_mode`
   - `contact_wechat`, `other_contact`, `main_business`, `intro`, `fee_standard`, `first_billing_period`
3. 转化模板字段：
   - `region`, `contact_start_date`, `fax`, `reserve_2`, `reserve_3`, `reserve_4`
4. 其他：
   - `source`, `last_feedback`, `notes`, `created_at`, `updated_at`

### 3.2 `lead_followups`
1. `lead_id`, `followup_at`, `feedback`, `next_reminder_at`, `notes`, `created_by`

### 3.3 `address_resources`
1. `category`, `contact_info`, `description`, `next_action`, `notes`

### 3.4 `customers`
1. `name`, `contact_name`, `phone`, `assigned_accountant_id`, `source_lead_id`
2. 查询接口附带：`accountant_username`, `source_lead_grade`, `source_lead_last_followup_date`

### 3.5 `billing_records`
对齐 `周 (2)`：
1. `serial_no(数字)`, `customer_id`, `customer_name`
2. `total_fee`, `monthly_fee`
3. `billing_cycle_text`
4. `due_date_text`（字段名当前沿用 `due_month`，语义为到期日）
5. `payment_method`
6. `status(CLEARED|FULL_ARREARS|PARTIAL)`, `received_amount`, `outstanding_amount`
7. `note`, `extra_note`
8. `color_tag`（保留历史颜色，业务判断以后续状态字段为准）

### 3.6 `billing_activities`
1. `billing_record_id`
2. `activity_type(REMINDER|PAYMENT)`
3. `occurred_at`, `actor_id`
4. `amount`（收款时可填）
5. `payment_nature`（MONTHLY|YEARLY|ONE_OFF）
6. `is_prepay`, `is_settlement`
7. `content`, `next_followup_at`, `note`

### 3.7 `users`
1. `username`, `password_hash`, `role`, `is_active`
2. 管理规则：
   - `ADMIN` 可创建/编辑全部角色账号
   - `OWNER` 不能创建/编辑 `ADMIN` 账号
   - 用户不能停用自己，也不能修改自己的角色

### 3.8 `operation_logs`
1. `actor_id`, `action`, `entity_type`, `entity_id`, `detail`, `created_at`
2. 记录动作：登录、用户管理、线索/客户/收费核心写操作、LDAP 设置与同步

### 3.9 `ldap_settings`
1. `enabled`, `server_url`, `bind_dn`, `bind_password`
2. `base_dn`, `user_base_dn`, `user_filter`
3. `username_attr`, `display_name_attr`, `default_role`

## 4. API Contracts

### 4.1 Auth
1. `POST /api/v1/auth/login`
2. `GET /api/v1/auth/me`

### 4.2 Leads
1. `GET /api/v1/leads`
2. `POST /api/v1/leads`
3. `GET /api/v1/leads/{lead_id}`
4. `PATCH /api/v1/leads/{lead_id}`
5. `POST /api/v1/leads/{lead_id}/followups`
6. `GET /api/v1/leads/{lead_id}/followups`
7. `POST /api/v1/leads/{lead_id}/convert`
8. `POST /api/v1/leads/{lead_id}/unconvert`

### 4.3 Customers
1. `GET /api/v1/customers`
2. `GET /api/v1/customers/{customer_id}`
3. `PATCH /api/v1/customers/{customer_id}`

### 4.4 Address Resource
1. `GET /api/v1/address-resources`
2. `POST /api/v1/address-resources`
3. `PATCH /api/v1/address-resources/{resource_id}`

### 4.5 Billing Register
1. `GET /api/v1/billing-records`
2. `POST /api/v1/billing-records`（OWNER/ADMIN）
3. `PATCH /api/v1/billing-records/{record_id}`（OWNER/ADMIN）
4. `GET /api/v1/billing-records/summary`
5. `GET /api/v1/billing-records/{record_id}/activities`
6. `POST /api/v1/billing-records/{record_id}/activities`

### 4.6 Import（下一迭代）
1. `POST /api/v1/import/excel/preview`
2. `POST /api/v1/import/excel/commit`

### 4.7 Users
1. `GET /api/v1/users`（OWNER/ADMIN；支持 `role`、`keyword`、`include_inactive`）
2. `POST /api/v1/users`（OWNER/ADMIN；OWNER 不可创建 ADMIN）
3. `PATCH /api/v1/users/{user_id}`（OWNER/ADMIN；OWNER 不可修改 ADMIN）

### 4.8 Admin
1. `GET /api/v1/admin/operation-logs`
2. `GET /api/v1/admin/ldap/settings`
3. `PUT /api/v1/admin/ldap/settings`
4. `POST /api/v1/admin/ldap/sync`

## 5. Frontend IA（按 Excel 习惯）
1. 客户开发页：
   - 查询条件：关键词、状态、模板类型
   - 首页表头保留核心字段：公司名、联系人、电话、来源、状态、提醒、最后跟进反馈
   - 完整字段放入线索详情页，降低首页复杂度
   - 默认排序：跟进中 -> 新线索 -> 已丢失 -> 已转化（置底）
   - 新增弹窗：覆盖两套模板字段
   - 详情入口：进入线索独立档案页
   - 流程说明弹窗：解释状态、流程、模板筛选用途
2. 线索详情页：
   - 上半区：固定字段（公司、等级、联系方式、服务/备注）
   - 下半区：跟进记录表（跟进日期、反馈、备注、提醒）
3. 客户列表页：
   - 已转化客户宽表：客户名、联系人、电话、会计、等级、最后跟进
   - 详情入口：进入客户档案页
4. 客户档案页：
   - 客户基础信息 + 来源线索详情 + 跟进历史
   - 可直接新增跟进
5. 地址资源页：
   - 表头：分类、联系方式、资源说明、后续动作
   - 可快速新增并作为线索来源填写
6. 收费收款页：
   - 结构贴合 `周 (2)`：总费用、月费用、代账周期、到期日、付款方式、备注
   - 客户字段与“客户列表”绑定，名称可点击进入客户档案
   - 会计字段由客户分配关系自动带出
   - 新增状态列：清账/全欠/部分收费
   - 记录详情：催收日志 + 收款日志
   - 统计卡：总记录数、总费用、月费用合计
7. 日期输入：
   - 所有日期控件采用 `DatePicker + 可编辑输入`，支持弹出选择和键盘录入（`YYYYMMDD` / `YYMMDD`）。
8. 管理员面板：
   - 用户宽表：账号、角色、状态、创建时间
   - 登录时间：显示最近登录时间
   - 筛选：关键词、角色、状态
   - 操作：新增本地用户、编辑角色/状态、重置密码
   - LDAP：连接配置 + 手动同步
   - 审计：操作日志宽表（时间、操作人、动作、对象、详情）
   - 菜单显隐：仅 OWNER/ADMIN 可见

## 6. Testing Strategy
1. 后端：
   - 登录鉴权
   - 线索创建/详情/跟进/转化
   - 客户列表/客户详情（权限过滤）
   - 地址资源查询/创建/编辑
   - 收费记录查询/创建/汇总
   - 催收/收款日志创建后台账状态联动
2. 前端：
   - 登录后路由守卫
   - 客户开发页字段提交流程与详情跳转
   - 线索详情页加载与跟进提交流程
   - 客户列表页/客户档案页加载流程
   - 地址资源页加载与新增流程
   - 收费台账页加载、新增、日志录入流程
   - 管理员面板（入口显隐、用户增改、角色边界）
   - LDAP 设置保存与同步流程
   - 操作日志筛选流程

## 7. Risks & Mitigations
1. 历史 Excel 有自由文本字段：采用“结构化字段 + 备注扩展”并存。
2. 颜色语义不稳定：使用 `status` 字段承载业务状态，颜色仅做回显。
3. 模板字段较多：通过 `template_type` 分组展示，降低会计录入负担。
4. 收款流程复杂：先保证“日志+余额联动”可追溯，再迭代自动化规则。
