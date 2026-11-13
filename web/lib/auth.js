import { createHmac, timingSafeEqual } from "node:crypto";
export const json = (data, status = 200, headers = {}) =>
  Response.json(data, {
    status,
    headers: { "Cache-Control": "no-store", ...headers },
  });
export const equal = (a, b) => {
  const x = Buffer.from(a),
    y = Buffer.from(b);
  return x.length === y.length && timingSafeEqual(x, y);
};
export const sign = (value) =>
  createHmac("sha256", process.env.AUTH_SECRET).update(value).digest("hex");
export function authenticated(req) {
  const cookie = (req.headers.get("cookie") || "")
    .split(";")
    .map((x) => x.trim())
    .find((x) => x.startsWith("sma_session="));
  if (!cookie || !process.env.AUTH_SECRET) return false;
  const [expires, mac] = cookie.slice(12).split(".");
  return Number(expires) > Date.now() && equal(mac || "", sign(expires));
}
export function sameOrigin(req) {
  const origin = req.headers.get("origin");
  try {
    return !origin || new URL(origin).host === req.headers.get("host");
  } catch {
    return false;
  }
}
export async function bodyObject(req, limit = 32768) {
  const text = await req.text();
  if (Buffer.byteLength(text) > limit) throw new Error("Request too large");
  const value = JSON.parse(text || "{}");
  if (!value || Array.isArray(value) || typeof value !== "object")
    throw new Error("Invalid request");
  return value;
}
