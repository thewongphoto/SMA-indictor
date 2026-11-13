// Allowlist shared pure Python modules; no credentials, databases or Kivy code.
import {
  readFile,
  mkdir,
  writeFile,
  copyFile,
  readdir,
} from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { resolve, dirname, join } from "node:path";
import { createHash } from "node:crypto";
const web = resolve(dirname(fileURLToPath(import.meta.url)), ".."),
  repo = resolve(web, "..");
const out = join(web, "public/python");
await mkdir(join(out, "sma_analyzer"), { recursive: true });
const files = [
  "__init__",
  "engine",
  "policy",
  "settings",
  "backtest",
  "backtest_text",
];
const manifest = {
  files: [],
  version: JSON.parse(await readFile(join(web, "package.json"), "utf8"))
    .version,
};
for (const name of files) {
  const content =
    name === "__init__"
      ? Buffer.from("")
      : await readFile(join(repo, "sma_analyzer", name + ".py"));
  const path = "sma_analyzer/" + name + ".py";
  await writeFile(join(out, path), content);
  manifest.files.push({
    path,
    sha256: createHash("sha256").update(content).digest("hex"),
  });
}
const adapter = await readFile(join(web, "python/browser.py"));
await writeFile(join(out, "browser.py"), adapter);
manifest.files.push({
  path: "browser.py",
  sha256: createHash("sha256").update(adapter).digest("hex"),
});
await writeFile(join(out, "manifest.json"), JSON.stringify(manifest));
const runtime = join(web, "public/python-runtime");
await mkdir(runtime, { recursive: true });
for (const name of [
  "pyodide.mjs",
  "pyodide.asm.js",
  "pyodide.asm.wasm",
  "python_stdlib.zip",
  "pyodide-lock.json",
])
  await copyFile(join(web, "node_modules/pyodide", name), join(runtime, name));
console.log("Staged shared Python engine and pinned Pyodide runtime.");
const lock = JSON.parse(
  await readFile(join(runtime, "pyodide-lock.json"), "utf8"),
);
for (const name of ["numpy"]) {
  const pkg = lock.packages[name],
    path = join(runtime, pkg.file_name);
  let bytes;
  try {
    bytes = await readFile(path);
  } catch {}
  if (
    !bytes ||
    createHash("sha256").update(bytes).digest("hex") !== pkg.sha256
  ) {
    const response = await fetch(
      "https://cdn.jsdelivr.net/pyodide/v0.29.5/full/" + pkg.file_name,
    );
    if (!response.ok)
      throw new Error(
        "Cannot download the pinned Python numerical package. Retry the build.",
      );
    bytes = Buffer.from(await response.arrayBuffer());
    if (createHash("sha256").update(bytes).digest("hex") !== pkg.sha256)
      throw new Error("Python package checksum mismatch");
    await writeFile(path, bytes);
  }
}
await mkdir(join(web, "public/setup"), { recursive: true });
await copyFile(
  join(web, "setup/supabase.sql"),
  join(web, "public/setup/supabase.sql"),
);

await copyFile(
  join(web, "setup/contact.sql"),
  join(web, "public/setup/contact.sql"),
);
