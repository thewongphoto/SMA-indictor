// Explicit opt-in contact signup, separate from market notifications and Gmail OAuth.
import { createHmac } from "node:crypto";
import { rpc, supabaseConfigured } from "./supabase.js";
import { contactMessage } from "./contact-message.js";
export const CONTACT_RECIPIENT = "kelwong98@gmail.com";
const DEFAULT_FROM = "SMA Stock Analyzer <onboarding@resend.dev>";
export function normalizeEmail(value) {
  if (typeof value !== "string")
    throw new Error("Enter a valid email address, like name@example.com.");
  const email = value.trim();
  if (
    email.length > 254 ||
    !email ||
    /[\s\r\n,;<>]/.test(email) ||
    email.split("@").length !== 2 ||
    email.includes("..")
  )
    throw new Error("Enter a valid email address, like name@example.com.");
  const [local, domain] = email.split("@");
  if (
    !local ||
    local.length > 64 ||
    !domain.includes(".") ||
    domain.startsWith(".") ||
    domain.endsWith(".") ||
    !/^[a-zA-Z0-9.-]+$/.test(domain)
  )
    throw new Error("Enter a valid email address, like name@example.com.");
  return email;
}
function identifier(value) {
  if (
    typeof value !== "string" ||
    !/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(
      value,
    )
  )
    throw new Error("Invalid signup identifier. Reload and try again.");
  return value.toLowerCase();
}
export function contactConfigured() {
  if (
    !process.env.RESEND_API_KEY?.startsWith("re_") ||
    !process.env.AUTH_SECRET ||
    !supabaseConfigured()
  )
    return false;
  try {
    const from = process.env.CONTACT_FROM || DEFAULT_FROM;
    if (/[\r\n]/.test(from)) return false;
    normalizeEmail(from.match(/<([^<>]+)>$/)?.[1] || from);
    return true;
  } catch {
    return false;
  }
}
export async function contactStatus(call = rpc) {
  const status = {
    provider: "resend",
    provider_configured: contactConfigured(),
    recipient: CONTACT_RECIPIENT,
    sender: process.env.CONTACT_FROM || DEFAULT_FROM,
    schema_ready: false,
    signed_up_installations: 0,
    accepted_submissions: 0,
    protocol: 0,
  };
  if (!supabaseConfigured()) return { ...status, ready: false };
  try {
    Object.assign(status, await call("sma_contact_status"));
  } catch {}
  status.schema_ready = status.schema_ready && status.protocol >= 2;
  return {
    ...status,
    ready: status.provider_configured && status.schema_ready,
  };
}
export async function contactCapabilities() {
  if (!contactConfigured()) return { enabled: false };
  return { enabled: (await contactStatus()).ready, protocol: 2 };
}
function hash(value) {
  return createHmac("sha256", process.env.AUTH_SECRET)
    .update(value)
    .digest("hex");
}
export async function submitContact(
  body,
  { ip = "unknown", call = rpc, send = fetch } = {},
) {
  if (!contactConfigured())
    return {
      status: 503,
      payload: {
        error:
          "Release-update signup is not configured yet. You can skip for now.",
      },
    };
  let email, install, request, operation, source, version;
  try {
    email = normalizeEmail(body.email);
    install = identifier(body.install_id);
    request = identifier(body.request_id);
    operation = body.operation || "save";
    if (!["save", "remove"].includes(operation)) throw new Error("Invalid email change.");
    source = ["android", "ios-web", "web"].includes(body.platform) ? body.platform : "unknown";
    version = typeof body.version === "string" && /^[0-9A-Za-z.+_-]{1,40}$/.test(body.version) ? body.version : "unknown";
  } catch (error) {
    return { status: 400, payload: { error: error.message } };
  }
  const id = hash(install + "|" + request),
    installHash = hash(install),
    emailHash = hash(email.toLowerCase());
  let claim;
  try {
    claim = await call("sma_prepare_contact", {
      p_id: id,
      p_install_hash: installHash,
      p_email_hash: emailHash,
      p_ip_hash: hash(ip.slice(0, 200)),
      p_email: email,
      p_operation: operation,
      p_source: source,
      p_version: version,
    });
  } catch {
    return {
      status: 503,
      payload: {
        error:
          "Email tracking is not ready. The developer must rerun the latest email SQL on /setup/email. You can skip for now.",
      },
    };
  }
  if (claim.action === "accepted")
    return { status: 200, payload: { sent: true, already_accepted: true, change: claim.change } };
  if (claim.action === "unchanged")
    return { status: 200, payload: { sent: true, unchanged: true, change: claim.change } };
  if (claim.action === "pending_change")
    return { status: 409, payload: { code: "pending_change", error: "An earlier email change is awaiting confirmation. Retry that change before making another." } };
  if (claim.action === "stale")
    return { status: 409, payload: { error: "The saved address changed in another session. Open Settings there to manage the current address." } };
  if (claim.action === "busy")
    return {
      status: 429,
      payload: {
        error:
          "This signup is still being processed. Please wait 45 seconds before retrying.",
      },
    };
  if (["rate_limited", "attempt_limit"].includes(claim.action))
    return {
      status: 429,
      payload: {
        error:
          "The signup limit has been reached. Please try again later, or skip for now.",
      },
    };
  if (claim.action === "expired")
    return {
      status: 410,
      payload: {
        code: "expired",
        error:
          "The earlier request expired without confirmation. Submit again to start a new request.",
      },
    };
  if (claim.action !== "send")
    return {
      status: 400,
      payload: {
        error:
          "This request does not match the earlier signup. Reload the page and try again.",
      },
    };
  let message;
  try {
    message = claim.message || await call("sma_contact_message", {
      p_id: id,
      p_message: contactMessage(claim.event, { from: process.env.CONTACT_FROM || DEFAULT_FROM, to: CONTACT_RECIPIENT }),
    });
    // Registry data and prepared messages stay server-only, with a fixed destination.
    if (!message || JSON.stringify(message.to) !== JSON.stringify([CONTACT_RECIPIENT])) throw new Error("Invalid destination");
  } catch {
    return { status: 503, payload: { error: "The notification could not be prepared. Retry this email change later." } };
  }
  let response, value;
  try {
    response = await send("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        Authorization: "Bearer " + process.env.RESEND_API_KEY,
        "Content-Type": "application/json",
        "Idempotency-Key": "sma-contact/" + id,
      },
      body: JSON.stringify(message),
      signal: AbortSignal.timeout(15000),
    });
    value = await response.json();
  } catch {
    // Keep the durable claim pending: retry the SAME idempotency key, not a new mail.
    return {
      status: 503,
      payload: {
        error:
          "Email acceptance could not be confirmed. Retry with the same address, or skip for now.",
      },
    };
  }
  if (!response.ok || typeof value?.id !== "string") {
    // Only explicit rejection permits another intent. A 5xx, concurrent request
    // or malformed success can conceal acceptance, so keep its claim pending.
    if ([400, 401, 403, 404, 422, 429].includes(response.status)) {
      try {
        await call("sma_finish_contact", {
          p_id: id,
          p_accepted: false,
          p_error_code: response.status,
        });
      } catch {}
    }
    const message = [401, 403].includes(response.status)
      ? "The email service did not accept this signup. The developer must check the Resend account, API key and sender. You can skip for now."
      : response.status === 429
        ? "The email service is limiting requests. Please try again later."
        : "Email acceptance could not be confirmed. Retry the pending change later, or skip for now.";
    return { status: 503, payload: { error: message } };
  }
  try {
    const finished = await call("sma_finish_contact", {
      p_id: id,
      p_accepted: true,
      p_provider_id: value.id,
    });
    if (finished !== true) throw new Error("Change not recorded");
  } catch {
    return { status: 503, payload: { error: "The email service accepted the notification, but saving the change could not be confirmed. Retry the same change; its delivery ID prevents another email." } };
  }
  return { status: 200, payload: { sent: true, change: claim.event.action } };
}
