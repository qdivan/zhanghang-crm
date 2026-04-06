# 备份架构（当前单实例版）

## 1. 范围说明
- 当前阶段按 `单公司 / 单实例` 交付。
- `多租户` 已从当前计划中移除，暂不纳入这一轮架构设计。
- 本文只收口：`备份、恢复、演练、保留策略、实施入口`。

## 2. 当前部署形态
### 本地直接运行 API
- 数据库：SQLite
- 路径：`apps/api/daizhang.db`
- 适用：个人本地开发，不作为正式生产备份方案。

### Docker 开发环境
- 数据库：SQLite
- 路径：`infra/data/dev/api/daizhang-dev.db`
- 适用：联调与测试环境。

### 生产环境
- 数据库：PostgreSQL 16
- Compose：`infra/docker-compose.prd.yml`
- 数据卷目录：`infra/data/prd/postgres`
- 环境文件：
  - `infra/env/postgres.prd.env`
  - `infra/env/api.prd.env`

## 3. 当前建议的备份目标
生产环境至少备份以下三类内容：

1. 数据库逻辑备份
- 使用 `pg_dump -Fc` 导出 PostgreSQL 自定义格式备份。
- 优点：恢复稳定，可单库迁移，可离线保存。

2. 运行配置备份
- `infra/docker-compose.prd.yml`
- `infra/env/postgres.prd.env`
- `infra/env/api.prd.env`
- 这些文件决定了数据库连接、密钥和部署方式。

3. 宿主机目录级快照
- 对 `infra/data/prd/postgres` 做 Btrfs / NAS 快照。
- 用于覆盖“逻辑备份之外”的磁盘级回滚场景。

## 4. 备份策略建议
### 最小可用策略
- 每天 1 次数据库逻辑备份。
- 每天 1 次数据目录快照。
- 每周 1 次异地备份同步。
- 每季度至少做 1 次恢复演练。

### 保留策略
- 每日备份：保留 14 天。
- 每周备份：保留 8 周。
- 每月备份：保留 12 个月。

### RPO / RTO 建议
- RPO：`<= 24 小时`
- RTO：`<= 4 小时`

对于当前 MVP 阶段，这个目标已经足够实用，也便于后续再升级到更细的容灾能力。

## 5. 已落地的命令入口
### 生产备份
```bash
npm run backup:prd
```

或指定输出目录：

```bash
bash ./scripts/backup-prd-db.sh --output-dir /absolute/path/to/backup-dir
```

执行后会在 `backups/prd/<timestamp>/` 下生成：
- `postgres.dump`
- `config.tar.gz`
- `manifest.txt`

### 生产恢复
```bash
npm run restore:prd -- --dump backups/prd/20260406-220000/postgres.dump --confirm daizhang
```

说明：
- `--confirm` 必须与 `POSTGRES_DB` 完全一致，否则脚本会拒绝执行。
- 恢复前默认会先做一次 `pre-restore` 备份。
- 恢复会短暂停掉生产 `api/web`，完成后自动拉起。

## 6. 恢复演练建议
建议至少准备一个“恢复演练环境”，不要第一次在正式生产上验证恢复流程。

推荐流程：
1. 找到最近一份 `postgres.dump`。
2. 在测试机或测试栈上恢复。
3. 验证以下闭环：
   - 登录
   - 线索列表
   - 客户档案
   - 收费汇总
   - 收款录入
   - Todo / 管理员日志
4. 记录恢复耗时与问题点。

## 7. 安全要求
- `backups/` 已加入 `.gitignore`，避免误提交。
- 备份目录建议使用 `700` 权限；脚本已默认使用 `umask 077`。
- `config.tar.gz` 包含生产环境变量，若要离机保存，必须再做一次加密。
- 推荐把异地备份同步到受控对象存储或另一台 NAS。

## 8. 当前不做的事情
以下内容不在这一轮范围内：
- 多租户数据隔离
- 跨地域高可用
- PostgreSQL WAL / PITR
- 自动故障切换
- 完整资金系统级别的双向对账

## 9. 下一步可交给开发 AI 的任务
1. 增加定时清理与轮转脚本，按“14 天 / 8 周 / 12 月”保留。
2. 把 `backup:prd` 接到群晖计划任务或 `cron`。
3. 增加异地加密同步，例如对象存储或第二台 NAS。
4. 增加“最近一次备份时间”健康检查，超过 24 小时自动告警。
5. 补一个“恢复到测试环境”的一键演练脚本。
