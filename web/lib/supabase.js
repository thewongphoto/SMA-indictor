export function supabaseConfigured() {
  return Boolean(process.env.SUPABASE_URL && process.env.SUPABASE_SECRET_KEY);
}
export async function database(
  path,
  { method = "GET", body, prefer = "return=representation" } = {},
) {
  if (!supabaseConfigured())
    throw new Error("Supabase connection is not configured.");
  const base = new URL(process.env.SUPABASE_URL);
  if (base.protocol !== "https:" || base.username || base.password)
    throw new Error("Use the HTTPS Supabase project URL.");
  const response = await fetch(`${base.origin}/rest/v1/${path}`, {
    method,
    headers: {
      apikey: process.env.SUPABASE_SECRET_KEY,
      ...(process.env.SUPABASE_SECRET_KEY.startsWith("eyJ")
        ? { Authorization: `Bearer ${process.env.SUPABASE_SECRET_KEY}` }
        : {}),
      "Content-Type": "application/json",
      Prefer: prefer,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
    signal: AbortSignal.timeout(12000),
  });
  if (!response.ok) {
    const error = new Error(
      "The alert database is unavailable or setup SQL has not been applied.",
    );
    error.status = response.status;
    throw error;
  }
  return response.status === 204 ? null : response.json();
}
export const rpc = (name, body = {}) =>
  database("rpc/" + name, { method: "POST", body });
export async function readiness() {
  if (!supabaseConfigured())
    return {
      database_configured: false,
      schema_ready: false,
      scheduled_jobs: 0,
    };
  try {
    return { database_configured: true, ...(await rpc("sma_setup_status")) };
  } catch {
    return {
      database_configured: true,
      schema_ready: false,
      scheduled_jobs: 0,
    };
  }
}
