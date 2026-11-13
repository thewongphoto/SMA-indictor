// Portable Yahoo HTTPS gateway. Local charts/calculations never run here.
import catalog from "./catalog.json" with { type: "json" };
const EXCHANGES = new Set([
  "NMS",
  "NGM",
  "NCM",
  "NYQ",
  "ASE",
  "PCX",
  "BTS",
  "NASDAQ",
  "NYSE",
  "NYSEARCA",
]);
const number = (value) =>
  typeof value === "number" && Number.isFinite(value) ? value : null;
export function symbolFromKey(key) {
  if (typeof key !== "string" || !key.startsWith("YAHOO:"))
    throw new Error("Choose a supported US or Singapore security.");
  const symbol = key.slice(6);
  if (!/^[A-Z0-9][A-Z0-9.^=-]{0,29}$/.test(symbol))
    throw new Error("Invalid security symbol");
  return symbol;
}
function words(value) {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}
export function securityFromQuote(quote) {
  const symbol = String(quote.symbol || "").toUpperCase(),
    exchange = String(quote.exchange || "").toUpperCase(),
    kind = String(quote.quoteType || "").toUpperCase();
  if (
    !symbol ||
    !["EQUITY", "ETF"].includes(kind) ||
    !/^[A-Z0-9][A-Z0-9.^=-]{0,29}$/.test(symbol)
  )
    return null;
  const region =
    symbol.endsWith(".SI") || ["SES", "SGX"].includes(exchange)
      ? "SG"
      : EXCHANGES.has(exchange)
        ? "US"
        : null;
  if (!region) return null;
  const name = String(quote.longname || quote.shortname || symbol),
    family = String(quote.fundFamily || "");
  let issuer = catalog.etfs[symbol];
  if (!issuer && kind === "ETF")
    issuer = catalog.issuers.find((item) =>
      [family, name].some((value) =>
        item.aliases.some(
          (alias) =>
            words(value) === alias || words(value).startsWith(alias + " "),
        ),
      ),
    )?.key;
  const logo =
    kind === "ETF"
      ? issuer
      : catalog.stocks[symbol] || catalog.stocks[symbol.replace(/\.SI$/, "")];
  return {
    key: "YAHOO:" + symbol,
    ticker: symbol,
    symbol,
    name,
    exchange: quote.exchDisp || exchange,
    initials: name
      .split(/\s+/)
      .slice(0, 2)
      .map((x) => x[0])
      .join(""),
    provider: "yahoo",
    region,
    timezone: region === "SG" ? "Asia/Singapore" : "America/New_York",
    currency: region === "SG" ? "SGD" : "USD",
    instrument_type: kind,
    issuer: issuer || "",
    logo_url: logo ? "/logos/" + logo + ".png" : "",
  };
}
export function dateInZone(milliseconds, zone) {
  const parts = Object.fromEntries(
    new Intl.DateTimeFormat("en-GB", {
      timeZone: zone,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hourCycle: "h23",
    })
      .formatToParts(new Date(milliseconds))
      .filter((x) => x.type !== "literal")
      .map((x) => [x.type, x.value]),
  );
  return {
    date: `${parts.year}-${parts.month}-${parts.day}`,
    minutes: Number(parts.hour) * 60 + Number(parts.minute),
  };
}
let anonymousSession = null,
  retryAfter = 0;
const HEADERS = {
  "User-Agent": "SMAStockAnalyzer/0.15.0 (private personal research)",
  Accept: "application/json",
};
async function get(url, headers = {}) {
  if (Date.now() < retryAfter)
    throw new Error(
      "The market data provider is limiting requests. Wait before trying again.",
    );
  const response = await fetch(url, {
    headers: { ...HEADERS, ...headers },
    redirect: "manual",
    cache: "no-store",
    signal: AbortSignal.timeout(18000),
  });
  if (response.status === 429) {
    const wait = Number(response.headers.get("Retry-After"));
    retryAfter =
      Date.now() + Math.max(60000, Math.min(3600000, (wait || 60) * 1000));
  }
  return response;
}
async function yahoo(path, parameters) {
  const url = new URL("https://query2.finance.yahoo.com" + path);
  for (const [key, value] of Object.entries(parameters))
    url.searchParams.set(key, String(value));
  const request = async () => {
    if (anonymousSession) url.searchParams.set("crumb", anonymousSession.crumb);
    return get(url, {
      ...(anonymousSession ? { Cookie: anonymousSession.cookie } : {}),
    });
  };
  let response = await request();
  if (response.status === 401) {
    const bootstrap = await get("https://fc.yahoo.com");
    if (![200, 404].includes(bootstrap.status))
      throw new Error(
        "The market data provider could not start a data session.",
      );
    const cookies = bootstrap.headers.getSetCookie?.() || [
      bootstrap.headers.get("set-cookie") || "",
    ];
    const cookie = cookies
      .map((x) => x.split(";")[0])
      .filter(Boolean)
      .join("; ");
    const token = await get(
      "https://query1.finance.yahoo.com/v1/test/getcrumb",
      { Cookie: cookie },
    );
    const crumb = (await token.text()).trim();
    if (!token.ok || !crumb || crumb.length > 256 || /[\s<>"{}]/.test(crumb))
      throw new Error(
        "The market data provider could not start a data session.",
      );
    anonymousSession = { cookie, crumb };
    response = await request();
  }
  if (!response.ok)
    throw new Error(
      response.status === 429
        ? "The market data provider is limiting requests. Please wait before retrying."
        : "The market data source did not respond. Downloaded charts are retained.",
    );
  return response.json();
}
export async function searchMarket(query) {
  const text = String(query || "").trim();
  if (!text || text.length > 128)
    throw new Error("Enter a company name or ticker (up to 128 characters).");
  const payload = await yahoo("/v1/finance/search", {
    q: text,
    quotesCount: 20,
    newsCount: 0,
    listsCount: 0,
    recommendedCount: 0,
    enableFuzzyQuery: false,
    enableCb: false,
    enableNavLinks: false,
    enableResearchReports: false,
  });
  if (!Array.isArray(payload.quotes))
    throw new Error(
      "The market data source returned an invalid search response.",
    );
  return { results: payload.quotes.map(securityFromQuote).filter(Boolean) };
}
export function parseHistory(payload, symbol, now = Date.now()) {
  const chart = payload.chart;
  if (chart?.error)
    throw new Error("History is currently unavailable for this security.");
  const item = chart?.result?.[0],
    meta = item?.meta;
  if (meta?.dataGranularity && meta.dataGranularity !== "1d")
    throw new Error("The data source did not return daily observations.");
  if (
    !meta ||
    String(meta.symbol).toUpperCase() !== symbol ||
    !Array.isArray(item.timestamp)
  )
    throw new Error("The data source returned invalid history.");
  const security = securityFromQuote({
    symbol,
    exchange: meta.exchangeName,
    quoteType: meta.instrumentType,
    longname: meta.longName || meta.shortName,
  });
  if (!security)
    throw new Error(
      "This listing is outside the supported US/Singapore stocks and ETFs.",
    );
  security.currency = String(meta.currency || security.currency);
  security.timezone = String(meta.exchangeTimezoneName || security.timezone);
  const timestamps = item.timestamp,
    quote = item.indicators?.quote?.[0],
    adjusted = item.indicators?.adjclose?.[0]?.adjclose;
  if (
    !quote ||
    !Array.isArray(adjusted) ||
    adjusted.length !== timestamps.length ||
    !Array.isArray(quote.close) ||
    quote.close.length !== timestamps.length
  )
    throw new Error(
      "Adjusted closing prices are missing. Ordinary closes will not be substituted.",
    );
  const local = dateInZone(now, security.timezone),
    fallback = security.region === "SG" ? 1050 : 990;
  const regular = meta.currentTradingPeriod?.regular;
  let ready = local.minutes >= fallback;
  if (
    number(regular?.end) !== null &&
    dateInZone(regular.end * 1000, security.timezone).date === local.date
  )
    ready = ready && now >= (regular.end + 900) * 1000;
  const bars = new Map();
  for (let i = 0; i < timestamps.length; i++) {
    const stamp = number(timestamps[i]);
    if (stamp === null) throw new Error("Invalid session timestamp");
    const date = dateInZone(stamp * 1000, security.timezone).date;
    if (date > local.date || (date === local.date && !ready)) continue;
    const close = number(quote.close[i]),
      price = number(adjusted[i]);
    if (close !== null && price === null)
      throw new Error(
        "The source omitted adjusted closes; the prior download is retained.",
      );
    bars.set(date, {
      date,
      price: price !== null && price > 0 ? price : null,
      close,
    });
  }
  const ordered = [...bars.values()].sort((a, b) =>
    a.date.localeCompare(b.date),
  );
  if (ordered.length < 4)
    throw new Error("Not enough completed adjusted closes are available.");
  return {
    security,
    prices: ordered.map((x) => x.price),
    dates: ordered.map((x) => x.date),
    currency: security.currency,
    scenario: "Yahoo EOD",
    preview: false,
    stale: false,
    source: "yahoo",
    fetched_at: now / 1000,
  };
}
export async function historyMarket(key) {
  const symbol = symbolFromKey(key),
    now = Date.now();
  const parameters = {
    interval: "1d",
    events: "div,splits,capitalGains",
    includePrePost: false,
    includeAdjustedClose: true,
    period1: Math.floor(now / 1000) - 3122064000,
    period2: Math.floor(now / 1000),
  };
  let payload = await yahoo(
    "/v8/finance/chart/" + encodeURIComponent(symbol),
    parameters,
  );
  const first = payload.chart?.result?.[0]?.meta?.firstTradeDate;
  if (number(first) !== null && first < parameters.period1) {
    parameters.period1 = first;
    payload = await yahoo(
      "/v8/finance/chart/" + encodeURIComponent(symbol),
      parameters,
    );
  }
  return parseHistory(payload, symbol, now);
}
