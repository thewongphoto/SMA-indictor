// Separate from disposable chart snapshots: signing out never deletes saved lines.
export async function localValue(key, value) {
  const db = await new Promise((resolve, reject) => {
    const request = indexedDB.open("sma-local-data", 1);
    request.onupgradeneeded = () => request.result.createObjectStore("values");
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
  try {
    return await new Promise((resolve, reject) => {
      const tx = db.transaction(
          "values",
          value === undefined ? "readonly" : "readwrite",
        ),
        store = tx.objectStore("values");
      const request =
        value === undefined
          ? store.get(key)
          : value === null
            ? store.delete(key)
            : store.put(value, key);
      tx.oncomplete = () => resolve(request.result);
      tx.onerror = () => reject(tx.error);
    });
  } finally {
    db.close();
  }
}
export async function clearHistories() {
  const db = await new Promise((resolve, reject) => {
    const r = indexedDB.open("sma-local-data", 1);
    r.onsuccess = () => resolve(r.result);
    r.onerror = () => reject(r.error);
  });
  try {
    await new Promise((resolve, reject) => {
      const tx = db.transaction("values", "readwrite"),
        cursor = tx.objectStore("values").openCursor();
      cursor.onsuccess = () => {
        const item = cursor.result;
        if (item) {
          if (String(item.key).startsWith("history:")) item.delete();
          item.continue();
        }
      };
      tx.oncomplete = resolve;
      tx.onerror = () => reject(tx.error);
    });
  } finally {
    db.close();
  }
}
