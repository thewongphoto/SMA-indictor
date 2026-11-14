import catalog from "./catalog.json" with { type: "json" };

// Resolve old cached identities against the same bundled catalogue as native.
// Never turn a logo field/import into an external image request.
export function logoUrl(security) {
  if (/^\/logos\/[a-z0-9-]+\.png$/i.test(security?.logo_url || "")) return security.logo_url;
  const symbol = String(security?.symbol || security?.ticker || "").toUpperCase();
  const key = catalog.etfs[symbol] || catalog.stocks[symbol] || catalog.stocks[symbol.replace(/\.SI$/, "")];
  return key ? `/logos/${key}.png` : "";
}
