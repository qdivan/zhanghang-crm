# 实机回归报告

## 基线
- 提交：`0216859`
- 报告状态：`DONE`
- 前端构建：`npm run build:web` 通过
- 后端测试：`46 passed, 2 warnings`
- 截图目录：`/Users/shangyifan/Documents/New project/output/playwright/real-device/`

## 设备
- 桌面：Chrome `1440x900`
- 移动：iPhone 类视口 `390x844`

## 角色
- `boss`
- `admin`
- `manager`
- `accountant`

## 结果表
| 编号 | 角色 | 设备 | 页面 | 操作 | 期望 | 实际 | 严重级别 | 截图路径 | 是否阻塞 Session A |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RD-001 | boss | 移动 | 登录页 | 打开登录页 | 白底低饱和、首屏无横向空白、登录入口清晰 | 通过，登录页首屏结构稳定，无横向滚动 | PASS | `/Users/shangyifan/Documents/New project/output/playwright/real-device/mobile-login.png` | 否 |
| RD-002 | boss | 桌面 | 登录页 | 正常登录 | 进入系统并跳转工作区 | 通过，`/login -> /leads` | PASS | `/Users/shangyifan/Documents/New project/output/playwright/real-device/desktop-login.png` | 否 |
| RD-003 | boss | 桌面 | 登录页 | 错误密码登录 | 停留登录页并提示错误 | 通过，返回 `401`，页面提示“账号或密码错误” | PASS | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T14-43-33-498Z.yml` | 否 |
| RD-004 | boss | 桌面 | 登录页 | 点击“查看公开资料” | 打开公开资料页 | 通过，跳转 `/library/public` | PASS | `/Users/shangyifan/Documents/New project/output/playwright/real-device/public-library.png` | 否 |
| RD-005 | boss | 桌面 | 客户开发 | 进入客户开发页 | 页面可加载并显示未成单线索 | 通过，页面加载正常 | PASS | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T14-26-20-728Z.yml` | 否 |
| RD-006 | boss | 桌面 | 客户开发 | 新增线索 | 新线索保存成功并出现在列表 | 通过，创建 `回归临时客户-20260324-A` 成功 | PASS | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T14-28-40-199Z.yml` | 否 |
| RD-007 | boss | 桌面 | 客户开发 | 新增跟进 | 跟进保存并回写列表 | 通过，保存“已报价，待确认” | PASS | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T14-29-21-863Z.yml` | 否 |
| RD-008 | boss | 桌面 | 客户开发 | 转化并打开收费录入 | 线索转客户并弹出收费录入 | 通过，转化成功并打开收费录入弹窗 | PASS | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T14-30-12-723Z.yml` | 否 |
| RD-009 | boss | 桌面 | 客户列表 | 打开客户列表并查看新客户 | 已成交客户可见 | 通过，新客户进入客户列表 | PASS | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T14-30-51-319Z.yml` | 否 |
| RD-010 | boss | 桌面 | 客户档案 | 打开客户档案 | 展示成交后客户信息与时间线 | 通过，客户档案与时间线正常显示 | PASS | `/Users/shangyifan/Documents/New project/output/playwright/real-device/desktop-customer-detail.png` | 否 |
| RD-011 | boss | 桌面 | 客户档案 | 新增客户事项记录 | 成交后事项写入时间线 | 通过，保存“回归记录：客户已确认继续推进” | PASS | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T14-31-43-367Z.yml` | 否 |
| RD-012 | boss | 桌面 | 客户档案 | 打开模板菜单 | 可见香港公司模板 | 通过，模板菜单中有“香港公司模板” | PASS | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T14-32-01-402Z.yml` | 否 |
| RD-013 | boss | 桌面 | 客户档案/开发来源 | 查看开发来源再返回 | 返回链路正确 | 通过，`客户档案 -> 开发来源 -> 返回客户档案` 正常 | PASS | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T14-32-33-251Z.yml` | 否 |
| RD-014 | boss | 桌面 | 收费明细 | 按客户筛选 | 汇总和列表随筛选联动 | 通过，筛到 `UI成交核验-20260306` 后列表为 `4 条` | PASS | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T14-37-58-525Z.yml` | 否 |
| RD-015 | boss | 桌面 | 收费明细 | 点击公司名称展开往来账 | 当前页直接展开该客户往来账 | 通过，展开 `往来账 - UI成交核验-20260306` | PASS | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T14-38-12-323Z.yml` | 否 |
| RD-016 | boss | 桌面 | 收费明细 | 新增催收日志 | 生成催收记录并保留下次跟进 | 通过，保存 `RD-016 催收跟进`，下次跟进为 `2026-03-25` | PASS | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T14-35-57-798Z.yml` | 否 |
| RD-017 | boss | 桌面 | 收费明细 | 新增收款日志并选择入账账户 | 收款入账并回写主表/账户汇总 | 通过，保存 `300` 到 `微信`，主表更新为 `贷方 800 / 余额 1600` | PASS | `/Users/shangyifan/Documents/New project/output/playwright/real-device/desktop-billing.png` | 否 |
| RD-018 | boss | 桌面 | 收费明细 | 打开续费入口 | 弹出确认续费表单 | 通过，打开 `确认续费 - UI成交核验-20260306` | PASS | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T14-38-46-501Z.yml` | 否 |
| RD-019 | boss | 桌面 | 收费明细 | 打开提前终止入口 | 弹出提前终止表单 | 通过，打开 `提前终止合同 - UI成交核验-20260306` | PASS | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-24T14-39-12-730Z.yml` | 否 |
| RD-020 | boss | 桌面 | 到账核对 | 切换到账账户 | 左侧账户汇总与右侧流水同步切换 | 通过，切到 `微信` 后为 `1 条流水 / 300` | PASS | `/Users/shangyifan/Documents/New project/output/playwright/real-device/desktop-receipt-reconciliation.png` | 否 |
| RD-021 | boss | 桌面 | 常用资料 | 切换资料范围过滤 | 范围过滤生效 | 通过，切到“可公开到官网”后当前 tab 显示 `0 条 / 暂无数据` | PASS | `/Users/shangyifan/Documents/New project/output/playwright/real-device/desktop-common-library.png` | 否 |
| RD-022 | boss | 桌面 | 公开资料页 | 直接访问公开资料页 | 无需登录即可访问公开资料 | 通过，显示 `2 条` 公开资料 | PASS | `/Users/shangyifan/Documents/New project/output/playwright/real-device/public-library.png` | 否 |
| RD-023 | boss | 桌面 | 管理员面板 | 查看用户管理与数据授权 | 用户列表可见部门经理，数据授权页可进入 | 通过，用户列表显示 `manager/部门经理`，数据授权 tab 可打开 | PASS | `/Users/shangyifan/Documents/New project/output/playwright/real-device/desktop-admin-users.png` | 否 |
| RD-024 | manager / accountant | 桌面 | 角色可见性 | 检查菜单与范围 | 部门经理可看收费/到账核对；会计仅看收费明细，无管理员/到账核对 | 通过，`manager` 显示 `收费明细/到账核对` 且无管理员面板；`accountant` 仅显示 `收费明细`，无到账核对/管理员面板 | PASS | `/Users/shangyifan/Documents/New project/output/playwright/real-device/desktop-manager-customers.png` | 否 |

## 缺陷汇总
- `P0`：无
- `P1`：无
- `P2`：无


## 追加移动端 smoke（390x844）
- `MS-001` 工作台：首屏统计卡、系统待办卡片无横向空白，按钮可点击。
  - 截图：`/Users/shangyifan/Documents/New project/output/playwright/real-device/mobile-dashboard.png`
- `MS-002` 客户档案：信息卡、按钮区、时间线首屏布局正常，无回到旧式大表格。
  - 截图：`/Users/shangyifan/Documents/New project/output/playwright/real-device/mobile-customer-detail.png`
- `MS-003` 收费明细：汇总区、筛选区、收费卡片在手机宽度下无明显挤压或横向空白。
  - 截图：`/Users/shangyifan/Documents/New project/output/playwright/real-device/mobile-billing.png`
- `MS-004` 到账核对：账户汇总与流水入口在手机宽度下可读，筛选区无挤压溢出。
  - 截图：`/Users/shangyifan/Documents/New project/output/playwright/real-device/mobile-receipt-reconciliation.png`
- 结论：补测未发现新的 `P0/P1/P2`。

## 备注
- 本轮以“页面收敛 + 实机回归”为主，没有扩新模块。
- 公开资料页已补做白底低饱和收口，现已和登录页/工作台方向一致。
- 移动端已确认登录页首屏布局稳定；主要业务流程的功能回归以桌面端为主完成。
