# SSO 升级部署说明（Keycloak）

## 目标
- 把账航 CRM 的登录入口切到 Keycloak OIDC。
- 保留本地 `users` 作为业务用户投影，不改现有业务外键。
- 本次升级只交付“可升级、可绑定、可验证”的能力，不执行历史账号批量迁移。

## 新增环境变量
以下变量由运维在外部环境配置，仓库内只保留示例，不提交真实密钥。

| 变量 | 说明 | 推荐值/规则 |
| --- | --- | --- |
| `SSO_ENABLED` | 是否启用企业单点登录 | `true` |
| `SSO_PROVIDER_LABEL` | 登录页主按钮文案 | `企业单点登录` |
| `OIDC_ISSUER` | Keycloak Realm Issuer | 形如 `https://<host>/realms/<realm>` |
| `OIDC_CLIENT_ID` | OIDC Client ID | 由 Keycloak client 提供 |
| `OIDC_CLIENT_SECRET` | OIDC Client Secret | 由 Keycloak client 提供 |
| `OIDC_SCOPES` | OIDC scopes | 默认 `openid profile email` |
| `APP_PUBLIC_BASE_URL` | 当前 CRM 对外访问基址 | 必须与本环境真实地址一致 |
| `OIDC_POST_LOGOUT_REDIRECT_URL` | Keycloak 退出后的回跳地址 | 可留空，默认回登录页 |
| `LOCAL_LOGIN_ENABLED` | 是否允许普通员工继续本地登录 | 迁移期建议 `true`，全部绑定后可改 `false` |

## Keycloak Client 侧核对项
- `Client Protocol` 使用 `openid-connect`
- `Standard Flow` 启用
- Redirect URI 必须覆盖当前环境的：
  - `{APP_PUBLIC_BASE_URL}/api/v1/auth/sso/callback`
  - `{APP_PUBLIC_BASE_URL}/login/sso`
- Logout Redirect URI 至少覆盖：
  - `{APP_PUBLIC_BASE_URL}/login`
- `Client ID / Secret / Issuer` 要与环境变量完全一致
- 建议保留 `openid profile email` scope，并确保 `email` claim 可返回

## 升级步骤
1. 备份当前数据库与环境配置
2. 拉取新版本代码
3. 配置上述 SSO 环境变量
4. 重启 API / Web 服务
5. 访问健康检查接口确认服务启动正常
6. 访问登录页，确认出现 `企业单点登录` 主按钮
7. 管理员登录后台，打开 `管理员面板 -> SSO / 身份绑定`

## 启动后检查项
- `GET /api/v1/health` 返回 `ok`
- `GET /api/v1/auth/providers` 返回：
  - `sso.enabled = true`
  - `local.enabled = true`
- 登录页展示：
  - `企业单点登录`
  - 本地登录折叠入口
- 管理员后台可以看到：
  - 已绑定账号
  - 未绑定本地用户
  - 待处理冲突

## 回滚方案
如果升级后 SSO 不满足预期，回滚顺序建议如下：
1. 保留现有数据库
2. 把 `SSO_ENABLED=false`
3. 保留 `LOCAL_LOGIN_ENABLED=true`
4. 重启服务，恢复为本地登录主路径

说明：
- 已新增的 `user_identities / sso_binding_conflicts / sso_login_tickets` 与 `users` 投影字段不会破坏现有业务关系
- 关闭 SSO 后，现有业务外键与本地用户体系仍然可用

## 外部环境 handoff 检查单
运维升级完成后，请管理员按下列顺序抽检：
1. 用应急本地管理员账号登录一次
2. 用已知可绑定的企业账号做一次 SSO 登录
3. 在后台确认该账号进入 `已绑定`
4. 再检查 `未绑定本地用户 / 待处理冲突` 两个列表是否可见
5. 若迁移期结束，再决定是否关闭普通员工本地登录
