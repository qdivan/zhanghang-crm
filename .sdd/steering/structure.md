# 仓库结构（当前与计划）

## 当前状态
仓库当前仅包含：
1. 历史 Excel 数据文件（客户开发、转化、收费）。
2. `.sdd/` 规范文档目录。

## 目标结构（实施后）
```text
.
├── .sdd/
│   ├── description.md
│   ├── target-spec.txt
│   ├── steering/
│   │   ├── product.md
│   │   ├── tech.md
│   │   └── structure.md
│   └── specs/
│       └── <spec-name>/
│           ├── requirements.md
│           ├── design.md
│           └── tasks.md
├── apps/
│   ├── web/                 # Vue3 前端
│   └── api/                 # FastAPI 后端
├── packages/
│   └── shared/              # 类型、常量、通用 schema
├── infra/
│   ├── docker-compose.yml
│   └── scripts/
└── README.md
```

## 约定
1. 所有需求变更先更新 `.sdd/specs/<spec>/` 后再改代码。
2. API 合同与枚举常量优先放 `packages/shared`，避免前后端漂移。
3. 数据迁移仅通过 Alembic 脚本，不直接手改线上库。
