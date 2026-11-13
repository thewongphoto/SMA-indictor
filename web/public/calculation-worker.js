// Dedicated worker: Python scoring never blocks scrolling or the keyboard.
import { loadPyodide } from "/python-runtime/pyodide.mjs";
let engine;
async function initialize() {
  const py = await loadPyodide({ indexURL: "/python-runtime/" });
  await py.loadPackage("numpy");
  const manifest = await (await fetch("/python/manifest.json")).json();
  py.FS.mkdirTree("/sma/sma_analyzer");
  for (const file of manifest.files) {
    const bytes = await (await fetch("/python/" + file.path)).arrayBuffer();
    const hash = [
      ...new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)),
    ]
      .map((x) => x.toString(16).padStart(2, "0"))
      .join("");
    if (hash !== file.sha256)
      throw new Error(
        "Calculation files changed. Reload the app and try again.",
      );
    py.FS.writeFile("/sma/" + file.path, new Uint8Array(bytes));
  }
  py.runPython(
    "import sys; sys.path.insert(0, '/sma')\nimport json\nfrom browser import calculate",
  );
  return py;
}
self.onmessage = async ({ data: { id, payload } }) => {
  try {
    engine ||= initialize();
    const py = await engine;
    py.globals.set("request_json", JSON.stringify(payload));
    const result = py.runPython(
      "json.dumps(calculate(json.loads(request_json)), allow_nan=False)",
    );
    self.postMessage({ id, result: JSON.parse(result) });
  } catch (error) {
    self.postMessage({
      id,
      error:
        String(error.message || error)
          .split("\n")
          .filter(Boolean)
          .at(-1) || "Calculation failed.",
    });
  }
};
