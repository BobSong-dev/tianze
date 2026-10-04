# 03 · OpenAPI 契约（OPENAPI CONTRACT）

## 生成方式

```bash
cd apps/web && npm run api:generate   # FastAPI openapi.json → TypeScript schema.d.ts
npm run api:check                     # contract drift gate（非零退出码 = 有未提交变化）
```

## 工具链

- FastAPI `/openapi.json` → `openapi-typescript` → `apps/web/src/api/generated/schema.d.ts`
- 生成是确定性可重跑的；drift gate 通过 `git diff` 检测未提交变化

## 当前生成状态

- `openapi.json`：3 paths（health/meta/analyze）
- `schema.d.ts`：由 openapi-typescript v7.13.0 自动生成
- 前端 `api/tianze.ts` 使用 hand-maintained types（下一步切换到 generated types）

## Contract Drift Gate

`api:check` 如果 FastAPI 修改了 endpoint schema 但 TypeScript 类型未重新生成，则退出非零——阻止 contract drift。
