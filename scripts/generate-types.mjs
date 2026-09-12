import { compile } from "json-schema-to-typescript";
import { readFile, writeFile } from "node:fs/promises";

const schema = JSON.parse(
  await readFile("packages/contracts/generated/contracts.schema.json", "utf8"),
);
const output = await compile(schema, "JockyContracts", {
  bannerComment:
    "/* Generated from JOCKY Pydantic contracts. Do not edit. Runtime validation is required. */",
  unreachableDefinitions: true,
  unknownAny: true,
  maxItems: 0,
});
const target = "packages/contracts/generated/contracts.d.ts";
if (process.argv.includes("--check")) {
  if ((await readFile(target, "utf8")) !== output)
    throw new Error("TypeScript contract drift. Run make contracts.");
} else await writeFile(target, output);
