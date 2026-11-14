// Owner-only notification template. Never returned by the public signup API.
export function sourceLabel(source) {
  return { android: "Android APK", "ios-web": "iOS web app", web: "Web app" }[source] || "Unknown (older client)";
}
const escape = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
function timestamp(value) {
  return new Intl.DateTimeFormat("en-SG", { timeZone: "Asia/Singapore", dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) + " SGT";
}
export function contactMessage(event, { from, to }) {
  const records = event.records || [], active = records.filter((row) => row.active), removed = records.filter((row) => !row.active);
  const details = [
    ["Last change", event.action],
    ["Previous email", event.before || "None"],
    ["Current email", event.after || "None — removed from release updates"],
    ["Source", sourceLabel(event.source)],
    ["App version", event.version || "Unknown"],
    ["Changed", timestamp(event.changed_at)],
    ["Installation reference", event.reference],
  ];
  function textRows(rows) {
    return rows.length ? rows.map((row) => `${row.email} | ${sourceLabel(row.source)} | ${row.version || "Unknown"} | ${row.last_action} | ${timestamp(row.changed_at)} | ${row.reference}`).join("\n") : "None";
  }
  function table(rows) {
    return rows.length ? `<table style="border-collapse:collapse;width:100%;font-size:13px"><thead><tr>${["Email", "Source", "Version", "Last change", "Changed (SGT)", "Reference"].map((label) => `<th style="text-align:left;padding:8px;border-bottom:1px solid #ccd">${label}</th>`).join("")}</tr></thead><tbody>${rows.map((row) => `<tr>${[row.email, sourceLabel(row.source), row.version || "Unknown", row.last_action, timestamp(row.changed_at), row.reference].map((value) => `<td style="padding:8px;border-bottom:1px solid #dde">${escape(value)}</td>`).join("")}</tr>`).join("")}</tbody></table>` : "<p>None</p>";
  }
  const note = "Summary snapshot: previously accepted changes plus the change above. Rows identify app installations; one address can appear on multiple devices. A replaced address is listed as removed with last change modify. Removed addresses are history only and must not receive release updates.";
  const legacy = event.legacy_accepted ? `Earlier hash-only submissions (${event.legacy_accepted}) cannot be listed until those users explicitly save their address again.` : "";
  const columns = "Email | Source | Version | Last change | Changed (SGT) | Reference";
  return {
    from, to: [to], reply_to: event.email,
    subject: `SMA Stock Analyzer — email ${event.action}`,
    text: ["Release-update email change", ...details.map(([key, value]) => `${key}: ${value}`), "", `EXISTING USERS (${active.length})`, columns, textRows(active), "", `REMOVED EMAILS (${removed.length})`, columns, textRows(removed), "", note, legacy].filter((line) => line !== "").join("\n"),
    html: `<div style="font-family:Arial,sans-serif;color:#16232a;max-width:1000px;margin:auto"><h1>Email ${escape(event.action)}</h1>${details.map(([key, value]) => `<p><strong>${key}:</strong> ${escape(value)}</p>`).join("")}<hr><h2>Existing users (${active.length})</h2>${table(active)}<h2>Removed emails (${removed.length})</h2>${table(removed)}<p style="color:#526570;font-size:12px">${escape(note)}</p>${legacy ? `<p style="color:#526570;font-size:12px">${escape(legacy)}</p>` : ""}</div>`,
  };
}
