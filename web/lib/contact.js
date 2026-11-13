// Explicit opt-in contact signup, separate from market notifications and Gmail OAuth.
import { createHmac } from "node:crypto";
import { rpc, supabaseConfigured } from "./supabase.js";
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
  };
  if (!supabaseConfigured()) return { ...status, ready: false };
  try {
    Object.assign(status, await call("sma_contact_status"));
  } catch {}
  return {
    ...status,
    ready: status.provider_configured && status.schema_ready,
  };
}
export async function contactCapabilities() {
  if (!contactConfigured()) return { enabled: false };
  return { enabled: (await contactStatus()).ready };
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
  let email, install, request;
  try {
    email = normalizeEmail(body.email);
    install = identifier(body.install_id);
    request = identifier(body.request_id);
  } catch (error) {
    return { status: 400, payload: { error: error.message } };
  }
  const id = hash(install + "|" + request),
    installHash = hash(install),
    emailHash = hash(email.toLowerCase());
  let claim;
  try {
    claim = await call("sma_claim_contact", {
      p_id: id,
      p_install_hash: installHash,
      p_email_hash: emailHash,
      p_ip_hash: hash(ip.slice(0, 200)),
    });
  } catch {
    return {
      status: 503,
      payload: {
        error:
          "Signup storage is not ready. You can skip for now and try again later.",
      },
    };
  }
  if (claim.action === "accepted")
    return { status: 200, payload: { sent: true, already_accepted: true } };
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
  let response, value;
  try {
    response = await send("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        Authorization: "Bearer " + process.env.RESEND_API_KEY,
        "Content-Type": "application/json",
        "Idempotency-Key": "sma-contact/" + id,
      },
      body: JSON.stringify({
        from: process.env.CONTACT_FROM || DEFAULT_FROM,
        to: [CONTACT_RECIPIENT],
        reply_to: email,
        subject: "SMA Stock Analyzer — release-update signup",
        text: `A user voluntarily requested release updates.\n\nEmail: ${email}\nSignup reference: ${installHash.slice(0, 12)}\n\nThis email submission is forwarded to the developer. Count voluntary signups, not total downloads.\nNo market-alert email or automatic mailing-list campaign was requested.`,
      }),
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
    try {
      await call("sma_finish_contact", {
        p_id: id,
        p_accepted: false,
        p_error_code: response.status,
      });
    } catch {}
    const message = [401, 403].includes(response.status)
      ? "The email service did not accept this signup. The developer must check the Resend account, API key and sender. You can skip for now."
      : response.status === 429
        ? "The email service is limiting requests. Please try again later."
        : "The email service did not accept the signup. Try again later, or skip for now.";
    return { status: 503, payload: { error: message } };
  }
  try {
    await call("sma_finish_contact", {
      p_id: id,
      p_accepted: true,
      p_provider_id: value.id,
    });
  } catch {
    // Resend acceptance is confirmed. A lost retry is still deduplicated by its key.
  }
  return { status: 200, payload: { sent: true } };
}
