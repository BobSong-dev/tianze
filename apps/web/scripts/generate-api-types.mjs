import { execFileSync } from "node:child_process";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import openapiTS, { astToString, COMMENT_HEADER } from "openapi-typescript";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../../..");
const check = process.argv.includes("--check");
const localPython = resolve(root, process.platform === "win32" ? ".venv/Scripts/python.exe" : ".venv/bin/python");
const python = process.env.TIANZE_PYTHON || (existsSync(localPython) ? localPython : "python");

export function compareOrWrite(files, checkOnly) {
  const changed = [];
  for (const [path, expected] of files) {
    const actual = existsSync(path) ? readFileSync(path, "utf8").replace(/\r\n/g, "\n") : null;
    if (actual === expected) continue;
    changed.push(path);
    if (!checkOnly) writeFileSync(path, expected, "utf8");
  }
  return changed;
}

export async function generate() {
  const output = execFileSync(python, ["-c", "from apps.api.main import app; import json; print(json.dumps(app.openapi(), ensure_ascii=True))"], {
    cwd: root, encoding: "utf8", env: { ...process.env, PYTHONUTF8: "1", PYTHONIOENCODING: "utf-8" },
  });
  const spec = JSON.parse(output);
  const schema = COMMENT_HEADER + astToString(await openapiTS(spec));
  const changed = compareOrWrite([
    [resolve(root, "apps/web/src/api/generated/openapi.json"), JSON.stringify(spec, null, 2) + "\n"],
    [resolve(root, "apps/web/src/api/generated/schema.d.ts"), schema],
  ], check);
  if (check && changed.length) {
    console.error("CONTRACT DRIFT:\n" + changed.join("\n"));
    process.exitCode = 1;
  } else {
    console.log(check ? "No drift. Source files unchanged." : "Types generated.");
  }
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  await generate();
}
