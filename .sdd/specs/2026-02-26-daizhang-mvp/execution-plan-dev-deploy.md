# Dev 部署执行计划

## 基线
- 基线提交：`732cbf1`
- 上游结论：`UAT Round 1 / Round 2 全通过`
- 当前事实来源：本文件 + `/Users/shangyifan/Documents/New project/output/test-reports/dev-trial-preflight.md`

## 目标
- 把当前系统部署到 dev 环境
- 让老板 + 1 位会计进入连续试运行
- 记录试运行反馈，不在部署过程中继续改业务代码

## 部署前提
1. 已准备 dev 环境变量文件
- `infra/env/api.dev.env`

2. 已确认实际镜像地址
- `API_IMAGE`
- `WEB_IMAGE`

3. 已确认目标机器端口可用
- `32000`
- `32080`

## 执行步骤
1. 在目标机器复制并填写：
- `infra/env/api.dev.env`

2. 设定镜像：
- `API_IMAGE=<实际镜像>`
- `WEB_IMAGE=<实际镜像>`

3. 启动：
```bash
cd /path/to/project
API_IMAGE=<实际镜像> WEB_IMAGE=<实际镜像> docker compose -f infra/docker-compose.dev.yml up -d
```

4. 健康检查：
- `http://<host>:32080`
- `http://<host>:32000/api/v1/health`

5. 试运行名单：
- `boss`
- `1 位会计`

6. 试运行周期：
- `3~7 天`

## 成功标准
1. Web 与 API 均可访问
2. 老板可登录并完成主流程
3. 会计可完成收费明细、客户事项、催收/收款主流程
4. 试运行期间无 `P0 / P1`

## 当前状态
- Dev 部署执行计划：`DONE`
- 阻塞项 1：`无`
- 阻塞项 2：`无`
- 部署结果：`本机 dev 已启动并通过健康检查`
- 下一步：`开始真实试运行，收集反馈`
