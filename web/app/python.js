let worker,
  sequence = 0;
const waiting = new Map();
export function calculate(payload) {
  if (!worker) {
    worker = new Worker("/calculation-worker.js", { type: "module" });
    worker.onmessage = ({ data }) => {
      const request = waiting.get(data.id);
      if (request) {
        waiting.delete(data.id);
        data.error
          ? request.reject(new Error(data.error))
          : request.resolve(data.result);
      }
    };
    worker.onerror = () =>
      cancelCalculations(
        "The Python runtime could not load. Reconnect and try again.",
      );
  }
  return new Promise((resolve, reject) => {
    const id = ++sequence;
    waiting.set(id, { resolve, reject });
    worker.postMessage({ id, payload });
  });
}
export function cancelCalculations(message = "Calculation cancelled") {
  worker?.terminate();
  worker = null;
  for (const request of waiting.values()) request.reject(new Error(message));
  waiting.clear();
}
