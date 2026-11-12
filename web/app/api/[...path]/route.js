import { createHmac, timingSafeEqual } from "node:crypto";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";
const json = (data, status = 200, headers = {}) =>
  Response.json(data, {
    status,
    headers: { "Cache-Control": "no-store", ...headers },
  });
const equal = (a, b) => {
  const x = Buffer.from(a),
    y = Buffer.from(b);
  return x.length === y.length && timingSafeEqual(x, y);
};
const sign = (value) =>
  createHmac("sha256", process.env.AUTH_SECRET).update(value).digest("hex");
function authenticated(req) {
  const cookie = (req.headers.get("cookie") || "")
    .split(";")
    .map((x) => x.trim())
    .find((x) => x.startsWith("sma_session="));
  if (!cookie || !process.env.AUTH_SECRET) return false;
  const [expires, mac] = cookie.slice(12).split(".");
  return Number(expires) > Date.now() && equal(mac || "", sign(expires));
}
async function handler(req, { params }) {
  const path = (await params).path.join("/");
  const readOnly = ["state", "log", "contact-capabilities"].includes(path);
  const methods = path.startsWith("jobs/")
    ? ["GET", "DELETE"]
    : readOnly
      ? ["GET"]
      : ["POST"];
  if (!methods.includes(req.method))
    return json({ error: "Method not allowed" }, 405);
  if (req.method !== "GET") {
    const origin = req.headers.get("origin");
    try {
      if (origin && new URL(origin).host !== req.headers.get("host"))
        return json({ error: "Origin not allowed" }, 403);
    } catch {
      return json({ error: "Origin not allowed" }, 403);
    }
  }
  if (path === "login") {
    if (!process.env.APP_PASSWORD || !process.env.AUTH_SECRET)
      return json({ error: "Private access has not been configured." }, 503);
    let body;
    try {
      body = await req.json();
    } catch {
      return json({ error: "Invalid request" }, 400);
    }
    if (!equal(String(body.password || ""), process.env.APP_PASSWORD))
      return json({ error: "Incorrect access password" }, 401);
    const expires = String(Date.now() + 7 * 86400000);
    return json({ ok: true }, 200, {
      "Set-Cookie": `sma_session=${expires}.${sign(expires)}; HttpOnly; SameSite=Strict; Path=/; Max-Age=604800${process.env.NODE_ENV === "production" ? "; Secure" : ""}`,
    });
  }
  if (path === "logout")
    return json({ ok: true }, 200, {
      "Set-Cookie":
        "sma_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0",
    });
  if (
    !["contact-capabilities", "contact-email"].includes(path) &&
    !authenticated(req)
  )
    return json({ error: "Sign in to your private app." }, 401);
  if (!process.env.PYTHON_API_URL || !process.env.PYTHON_API_TOKEN)
    return json(
      { error: "The calculation service is not configured yet." },
      503,
    );
  const allowed = [
    "contact-capabilities",
    "contact-email",
    "state",
    "search",
    "chart",
    "optimize",
    "save",
    "line",
    "restore",
    "settings",
    "clear-cache",
    "log",
  ];
  if (!allowed.includes(path) && !/^jobs\/[\w-]+$/.test(path))
    return json({ error: "Unknown operation" }, 404);
  try {
    const body = req.method === "GET" ? undefined : await req.text();
    if (body && body.length > 32768)
      return json({ error: "Request too large" }, 413);
    const result = await fetch(
      `${process.env.PYTHON_API_URL.replace(/\/$/, "")}/${path}`,
      {
        method: req.method,
        body,
        headers: {
          Authorization: `Bearer ${process.env.PYTHON_API_TOKEN}`,
          "Content-Type": "application/json",
        },
        cache: "no-store",
        signal: AbortSignal.timeout(45000),
      },
    );
    return json(await result.json(), result.status);
  } catch {
    return json(
      {
        error:
          "The data service did not respond. Your saved lines are retained.",
      },
      503,
    );
  }
}
export { handler as GET, handler as POST, handler as DELETE };
