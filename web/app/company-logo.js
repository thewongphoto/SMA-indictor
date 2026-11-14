"use client";
import { useState } from "react";
import { logoUrl } from "../lib/brand";
export default function CompanyLogo({ security }) {
  const [failed, setFailed] = useState("");
  const url = logoUrl(security);
  const initials = security?.initials || (security?.name || "Security").split(/\s+/).slice(0, 2).map((word) => word[0]).join("");
  return <span className="company-logo" aria-hidden="true">
    {url && failed !== url ? <img src={url} alt="" onError={() => setFailed(url)} /> : <span>{initials}</span>}
  </span>;
}
