# 04 · 生产构建（PRODUCTION BUILD）

## 前端

```bash
cd apps/web && npm run build
```

产物：`apps/web/dist/`（~89KB，gzip ~33KB）

## API 启动

```bash
cd / && .venv/Scripts/python -m uvicorn apps.api.main:app --port 8000
```

## 全栈启动

```bash
python scripts/dev.py          # 并行启动 API :8000 + Web :5173
```

## Docker

`compose.yaml` 暂未提供（当前开发环境无 Docker 运行时，标记 `UNVERIFIED_IN_CURRENT_ENVIRONMENT`）。后续可增加最小 Dockerfile + compose，仅包含 api + web 两个服务。
