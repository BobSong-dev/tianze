import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { compareOrWrite } from "./generate-api-types.mjs";

test("contract check detects JSON and type drift without writing", () => {
  const temporary = mkdtempSync(join(tmpdir(), "tianze-contract-"));
  try {
    const spec = join(temporary, "openapi.json");
    const types = join(temporary, "schema.d.ts");
    writeFileSync(spec, "old-json");
    writeFileSync(types, "old-types");
    const expected = [[spec, "new-json\n"], [types, "new-types\n"]];
    assert.deepEqual(compareOrWrite(expected, true), [spec, types]);
    assert.equal(readFileSync(spec, "utf8"), "old-json");
    assert.equal(readFileSync(types, "utf8"), "old-types");
    compareOrWrite(expected, false);
    assert.deepEqual(compareOrWrite(expected, true), []);
    writeFileSync(spec, "new-json\r\n");
    assert.deepEqual(compareOrWrite(expected, true), []);
  } finally {
    assert.equal(resolve(temporary).startsWith(resolve(tmpdir())), true);
    rmSync(temporary, { recursive: true, force: true });
  }
});
