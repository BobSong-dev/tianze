import { execSync } from "node:child_process";
import { resolve } from "node:path";
const root = resolve(import.meta.dirname, "../..");
const check = process.argv.includes("--check");
const specPath = resolve(root, "apps/web/src/api/generated/openapi.json");
const tsPath = resolve(root, "apps/web/src/api/generated/schema.d.ts");
execSync(`cd "${root}" && .venv/Scripts/python -c "import sys;sys.path.insert(0,'.');from apps.api.main import app;import json;open('apps/web/src/api/generated/openapi.json','w').write(json.dumps(app.openapi(),indent=2))"`, { stdio: "pipe" });
execSync(`cd "${resolve(root, "apps/web")}" && npx openapi-typescript src/api/generated/openapi.json -o src/api/generated/schema.d.ts`, { stdio: "pipe" });
if (check) {
  const diff = execSync(`git diff --stat "apps/web/src/api/generated/schema.d.ts"`, { encoding: "utf-8", cwd: root }).trim();
  if (diff) { console.error("CONTRACT DRIFT:", diff); process.exit(1); }
  console.log("No drift.");
} else { console.log("Types generated."); }
