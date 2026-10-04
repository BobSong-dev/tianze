# 07 · 开发指南（DEVELOPMENT）

## Python Core

```bash
python -m venv .venv && source .venv/Scripts/activate
pip install -e ".[dev]"
pytest -q
```

## SDK 使用

```python
from tianze import analyze, SimplifiedBirthInfo
result = analyze(SimplifiedBirthInfo(date="2003-08-18", time="14:30"))
```

## API 启动

```bash
pip install -e ".[api]"
uvicorn apps.api.main:app --port 8000
```

## Web 启动

```bash
cd apps/web && npm install && npm run dev
```

## 全栈一键启动

```bash
python scripts/dev.py        # API + Web 并行启动
python scripts/dev.py test-all  # 全量测试
python scripts/dev.py build     # 前端生产构建
```
