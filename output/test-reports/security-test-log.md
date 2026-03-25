# 安全性测试日志

## 环境
- Web：`http://127.0.0.1:32080`
- API：`http://127.0.0.1:32000/api/v1`
- 计划：`/Users/shangyifan/Documents/New project/.sdd/specs/2026-02-26-daizhang-mvp/execution-plan-security-performance.md`

## 记录规则
- 每个失败项必须新增一行。
- 未发现问题时不要伪造问题；保留“暂无”占位即可。
- 如果出现 `P0/P1`，暂停继续试运行，先修缺陷。

## 第 1 轮执行结果
- 执行日期：`2026-03-25`
- 结果总览：`PASS 14 / FAIL 0`
- 原始结果：`/Users/shangyifan/Documents/New project/output/test-reports/security-check-results-2026-03-25.json`

### 已覆盖场景
1. 未登录访问受保护接口
2. 无效 token 访问受保护接口
3. 错误密码与错误信息泄漏检查
4. 本地账号 IP 锁定与不同 IP 恢复登录
5. `ADMIN / MANAGER / ACCOUNTANT` 访问 `/users`
6. `MANAGER / ACCOUNTANT` 访问到账核对接口
7. 公开资料接口只返回 `PUBLIC`
8. 非法客户 ID 访问不返回 `500`
9. 会计越权新增收费单被拒绝

### 本轮结论
- `P0`：0
- `P1`：0
- `P2`：0
- 当前没有发现会阻塞继续试运行的安全问题。

## 问题表
| 编号 | 日期 | 场景 | 角色 | 接口或页面 | 操作 | 期望 | 实际 | 严重级别 | 证据 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 暂无 | - | - | - | - | - | - | - | - | - | - |

## 建议覆盖清单
1. 错误密码与 IP 锁定
2. 停用账号与删除账号访问
3. 退出登录后访问受保护页面
4. `OWNER / ADMIN / MANAGER / ACCOUNTANT` 越权访问
5. 公开资料接口边界
6. 文本字段脚本片段展示
7. 非法 ID / 空 payload / 异常日期
