import { readFile, writeFile } from "node:fs/promises";

const databaseId = process.argv[2]?.trim();
if (!/^[0-9a-f-]{36}$/i.test(databaseId || "")) {
  console.error("사용법: node scripts/configure-d1.mjs <D1_DATABASE_ID>");
  process.exit(1);
}

const path = new URL("../wrangler.jsonc", import.meta.url);
const source = await readFile(path, "utf8");
const updated = source.replace(
  /"database_id"\s*:\s*"[^"]+"/,
  `"database_id": "${databaseId}"`,
);
await writeFile(path, updated, "utf8");
console.log("wrangler.jsonc의 D1 database_id를 반영했습니다.");
