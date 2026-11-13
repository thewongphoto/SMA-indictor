import {
  authenticated,
  sameOrigin,
  json,
  bodyObject,
  equal,
} from "../../../../lib/auth";
import {
  pushConfig,
  syncDevice,
  disableDevice,
  testPush,
  runAlerts,
  vapidReady,
  deviceId,
} from "../../../../lib/push";
import { database } from "../../../../lib/supabase";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 60;
async function handler(req, { params }) {
  const { action } = await params;
  if (action === "check") {
    if (req.method !== "POST")
      return json({ error: "Method not allowed" }, 405);
    const secret = process.env.CRON_SECRET;
    if (
      !secret ||
      secret.length < 32 ||
      !equal(req.headers.get("authorization") || "", "Bearer " + secret)
    )
      return json({ error: "Scheduler authentication required" }, 401);
    if (process.env.VERCEL_ENV && process.env.VERCEL_ENV !== "production")
      return json({ error: "Scheduled delivery is disabled in previews" }, 403);
    if (!vapidReady())
      return json({ error: "Notification keys are not configured" }, 503);
    try {
      return json(await runAlerts(new URL(req.url).searchParams.get("job")));
    } catch {
      return json(
        {
          error:
            "The alert check could not complete. Inspect server setup and the run journal.",
        },
        503,
      );
    }
  }
  if (!authenticated(req))
    return json({ error: "Sign in to your private app." }, 401);
  if (req.method !== "GET" && !sameOrigin(req))
    return json({ error: "Origin not allowed" }, 403);
  try {
    if (action === "config" && req.method === "GET")
      return json(
        await pushConfig(
          `${req.headers.get("x-forwarded-proto") || new URL(req.url).protocol.replace(":", "")}://${req.headers.get("host")}`,
        ),
      );
    if (action === "status" && req.method === "GET")
      return json({
        runs: await database(
          "sma_alert_runs?order=started_at.desc&limit=12&select=job,due,status,checked,posted,finished_at",
        ),
      });
    if (action === "sync" && req.method === "POST")
      return json(await syncDevice(await bodyObject(req, 131072)));
    if (action === "disable" && req.method === "POST")
      return json(await disableDevice(await bodyObject(req)));
    if (action === "test" && req.method === "POST")
      return json(await testPush(await bodyObject(req)));
    return json({ error: "Method or action not supported" }, 405);
  } catch (error) {
    return json(
      { error: error.message || "Notification setup is incomplete." },
      error.status === 400 ? 400 : 503,
    );
  }
}
export { handler as GET, handler as POST };
