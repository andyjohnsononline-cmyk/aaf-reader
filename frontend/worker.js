let pyodide = null;

async function initPyodide(messageId) {
  if (pyodide) return pyodide;

  postMessage({ id: messageId, op: "progress", stage: "loading" });
  const py = await loadPyodide();

  postMessage({ id: messageId, op: "progress", stage: "installing" });
  await py.loadPackage("micropip");
  const micropip = py.pyimport("micropip");

  const wheelsBase = self.location.href.replace(/\/[^/]*$/, "/wheels/");
  await micropip.install(wheelsBase + "olefile-0.47-py2.py3-none-any.whl");
  await micropip.install(wheelsBase + "pyaaf2-1.7.1-py2.py3-none-any.whl");

  const parserBase = self.location.href.replace(/\/[^/]*$/, "/");
  const resp = await fetch(parserBase + "aaf_parser.py");
  const parserCode = await resp.text();
  py.FS.writeFile("/home/pyodide/aaf_parser.py", parserCode);

  pyodide = py;
  return pyodide;
}

self.onmessage = async function (e) {
  const { id, op, buffer } = e.data;

  if (op !== "parse") {
    postMessage({ id, ok: false, error: `Unknown operation: ${op}`, code: "UNKNOWN_OP" });
    return;
  }

  try {
    await initPyodide(id);

    postMessage({ id, op: "progress", stage: "parsing" });

    const bytes = new Uint8Array(buffer);
    pyodide.FS.writeFile("/tmp/input.aaf", bytes);

    const result = pyodide.runPython(`
import json
from aaf_parser import parse_aaf
_result = parse_aaf("/tmp/input.aaf")
json.dumps(_result)
`);

    pyodide.FS.unlink("/tmp/input.aaf");

    postMessage({ id, ok: true, result });
  } catch (err) {
    try { pyodide?.FS.unlink("/tmp/input.aaf"); } catch (_) {}

    let message = err.message || String(err);
    const pyMatch = message.match(/PythonError:\s*(.*?)(?:\n|$)/);
    if (pyMatch) message = pyMatch[1];

    postMessage({ id, ok: false, error: message, code: "PARSE_ERROR" });
  }
};

importScripts("https://cdn.jsdelivr.net/pyodide/v0.29.3/full/pyodide.js");
