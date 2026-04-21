# SSO 用户创建与 CRM 绑定模板

填完下面的表格发给我即可。我会按表执行：

1. 在 Keycloak 创建用户
2. 给用户分配对应的 CRM 组
3. 绑定到现有 CRM 本地账号
4. 按需发送账号初始化/激活邮件

## 字段说明

| 列名 | 必填 | 说明 |
| --- | --- | --- |
| `crm_username` | 是 | CRM 里现有用户名。绑定时以它为准。 |
| `display_name` | 是 | 中文姓名或你方便识别的名字。 |
| `email` | 是 | 该员工真实邮箱。用于 Keycloak 账号和发送邮件。 |
| `keycloak_username` | 否 | 想要的 SSO 登录名。留空时默认使用邮箱前缀。 |
| `target_group` | 是 | 只能填：`crm-owner` / `crm-admin` / `crm-manager` / `crm-accountant` |
| `send_email` | 是 | 是否发邮件。填：`yes` / `no` |
| `force_reset_password` | 是 | 是否首次登录后强制改密码。填：`yes` / `no` |
| `note` | 否 | 备注。可写部门、职位、老板/会计等，方便我核对。 |

## 建议规则

- 老板：`crm-owner`
- 系统管理员：`crm-admin`
- 业务经理：`crm-manager`
- 会计/执行：`crm-accountant`

## 填写模板

| crm_username | display_name | email | keycloak_username | target_group | send_email | force_reset_password | note |
| --- | --- | --- | --- | --- | --- | --- | --- |
| boss | 张三 | zhangsan@example.com | zhangsan | crm-owner | yes | yes | 老板 |
| admin | 李四 | lisi@example.com |  | crm-admin | yes | yes | 系统管理员 |
| manager1 | 王五 | wangwu@example.com |  | crm-manager | yes | yes | 销售经理 |
| accountant1 | 赵六 | zhaoliu@example.com |  | crm-accountant | yes | yes | 会计 |

## 注意

- `crm_username` 必须已经存在于 CRM。
- 如果 `email` 已经在 Keycloak 里存在，我会优先做绑定，不重复建人。
- 如果 `target_group` 与 CRM 当前角色不一致，我会先停下来告诉你，不会直接乱改。
- 如果你希望某些人先建账号但不发邮件，可以把 `send_email` 填成 `no`。
