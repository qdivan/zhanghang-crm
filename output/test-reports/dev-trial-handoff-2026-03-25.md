# Dev 试运行交接说明（2026-03-25）

## 当前状态
- dev 环境：运行中
- Web：`http://127.0.0.1:32080`
- API：`http://127.0.0.1:32000`
- Health：`http://127.0.0.1:32000/api/v1/health`
- 自动化巡检：已完成
- UAT：已完成
- 安全性专项：通过
- 性能专项：通过
- 当前阻塞：无

## 建议今天开始的真实试运行顺序
1. `boss`
- 登录
- 新增线索
- 跟进一条线索
- 转化为客户
- 查看客户档案
- 查看收费明细
- 查看到账核对

2. `accountant`
- 登录
- 打开客户列表
- 打开客户档案并查看时间线
- 打开收费明细
- 处理催收/收款
- 查看常用资料

3. `manager`
- 登录
- 查看自己下属范围内的客户列表
- 查看收费明细
- 查看到账核对

4. `admin`
- 登录
- 打开管理员面板
- 查看用户、授权、LDAP 设置

## 发现问题时怎么记
- 统一写到：
  - `/Users/shangyifan/Documents/New project/output/test-reports/dev-trial-feedback-log.md`
- 每条至少写清楚：
  - 日期
  - 角色
  - 页面
  - 操作路径
  - 期望
  - 实际
  - 严重级别
  - 是否阻塞继续试用
  - 截图路径

## 严重级别
- `P0`：核心流程走不通
- `P1`：结果错误，但流程还能走
- `P2`：界面、文案、局部交互问题
- `P3`：建议优化

## 当前事实来源
- 试运行计划：`/Users/shangyifan/Documents/New project/.sdd/specs/2026-02-26-daizhang-mvp/execution-plan-dev-trial.md`
- 反馈日志：`/Users/shangyifan/Documents/New project/output/test-reports/dev-trial-feedback-log.md`
- 每日清单：`/Users/shangyifan/Documents/New project/output/test-reports/dev-trial-daily-checklist.md`
- 数据基线：`/Users/shangyifan/Documents/New project/output/test-reports/dev-trial-baseline-2026-03-25.md`
- 安全/性能汇总：`/Users/shangyifan/Documents/New project/output/test-reports/security-performance-summary.md`
