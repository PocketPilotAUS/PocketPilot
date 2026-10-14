import { ExchangeRate, validRate } from "../preferences/currency";

// Public daily reference rates. No account data, records or credentials are sent.
export async function loadYuanRate(cached: ExchangeRate | null): Promise<ExchangeRate> {
  if (validRate(cached) && Date.now() < cached.nextUpdateAt) return cached;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 12000);
  try {
    const response = await fetch("https://open.er-api.com/v6/latest/AED", { signal: controller.signal });
    if (!response.ok) throw new Error("Exchange rates are unavailable. Please try again.");
    const data = await response.json();
    const rate: ExchangeRate = { aedToCny: data.rates?.CNY, updatedAt: data.time_last_update_unix * 1000, nextUpdateAt: data.time_next_update_unix * 1000 };
    if (data.result !== "success" || data.base_code !== "AED" || !validRate(rate)) throw new Error("The exchange service returned an invalid yuan rate.");
    return rate;
  } finally { clearTimeout(timeout); }
}
