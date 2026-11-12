export async function stored(key, value) {
  const db = await new Promise((resolve, reject) => {
    const request = indexedDB.open("sma-private-cache", 1);
    request.onupgradeneeded = () =>
      request.result.createObjectStore("snapshots");
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
  try {
    return await new Promise((resolve, reject) => {
      const tx = db.transaction(
        "snapshots",
        value === undefined ? "readonly" : "readwrite",
      );
      const request =
        value === undefined
          ? tx.objectStore("snapshots").get(key)
          : tx.objectStore("snapshots").put(value, key);
      tx.oncomplete = () => resolve(request.result);
      tx.onerror = () => reject(tx.error);
    });
  } finally {
    db.close();
  }
}

export async function clearSnapshots() {
  const db = await new Promise((resolve, reject) => {
    const request = indexedDB.open("sma-private-cache", 1);
    request.onupgradeneeded = () =>
      request.result.createObjectStore("snapshots");
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
  try {
    await new Promise((resolve, reject) => {
      const tx = db.transaction("snapshots", "readwrite");
      tx.objectStore("snapshots").clear();
      tx.oncomplete = resolve;
      tx.onerror = () => reject(tx.error);
    });
  } finally {
    db.close();
  }
}
