# v0.4.0 发布步骤与回滚方案（供人工授权后执行）

> 状态：本地 RC 就绪（HEAD 629c787，0.4.0.dev0）。以下步骤需**人工授权**执行；
> 在此之前不 push、不建正式 tag、不建 GitHub Release。

## A. 发布前检查（自动化，可重复）

```bash
python tools/quality_gate.py        # 23 步 ALL PASS
python tools/release_check.py       # P0-P7 ALL PASS
python -m build --outdir dist-release .
python tools/install_smoke.py
```

## B. 版本提升（发布分支上）

1. 建 `release/0.4.0` 分支：`git checkout -b release/0.4.0`
2. `tianze/__init__.py`：`__version__ = "0.4.0"`（唯一事实源，pyproject dynamic）
3. 同步断言（4 处）：`tests/test_packaging.py`、`tests/test_smoke.py`、
   `tools/install_smoke.py`、`tests/test_release_check.py`（version 动态断言无需改）
4. 重跑 A 部分全部检查 + `python -m pytest tests apps/api/tests`
5. `python tools/sync_package_data.py` 后重新 build

## C. 发布执行（需授权）

```bash
git push origin main release/0.4.0          # 1. 推送分支
git push origin v0.3.0                      # 2. 推送冻结的旧 tag
git tag -a v0.4.0 -m "Tianze v0.4.0"        # 3. 新正式 tag（绝不移动 v0.3.0）
git push origin v0.4.0
# 4. GitHub Release：Notes 用 docs/release-notes-v0.4.0.md，
#    附件 dist-release/ 的 wheel+sdist
```

## D. 发布后验证

1. 观察三平台 CI 矩阵（ubuntu/windows/macos × py3.12/3.13）首跑；
   平台差异按 failing job 修复（不预判）。
2. `pip install tianze-bazi==0.4.0` 干净环境冒烟。
3. GitHub Release 页核对工件校验和与 dist-release 一致。

## E. 回滚方案

- **tag/Release 误发**：GitHub Release 可删除；tag 已推送时需强制删除远端 tag
  （`git push origin :refs/tags/vX`）并重打——**v0.3.0 永不参与回滚操作**。
- **PyPI（如发布）**：`pip uninstall`/`pip install tianze-bazi==0.3.0` 降级；
  版本号只前进不复用（0.4.1 修复版）。
- **代码回滚**：`git revert` 发布分支 commit（禁止 force-push main）；
  数据 Schema 全部 additive，回滚代码不破坏新数据可读性（旧字段忽略新字段）。

## F. 环境变量清单

| 变量 | 用途 | 默认 |
|---|---|---|
| TIANZE_LLM_API_KEY | AI 解读（可选） | 空 → /interpret 503 |
| TIANZE_LLM_BASE_URL | OpenAI 兼容端点 | openai.com/v1 |
| TIANZE_LLM_MODEL | 模型名 | gpt-4o-mini |
| TIANZE_DATA_DIR | 数据目录覆盖 | repo knowledge/ |
| TIANZE_CORS_ORIGINS | API CORS | localhost:5173 |
