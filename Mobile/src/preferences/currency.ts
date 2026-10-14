export type Currency = "AED" | "CNY";
export type ExchangeRate = { aedToCny: number; updatedAt: number; nextUpdateAt: number };
export type CurrencyPreference = { currency: Currency; rate: ExchangeRate | null };
let current: CurrencyPreference = { currency: "AED", rate: null };
export const getCurrencyPreference = () => current;
export function validRate(value: unknown): value is ExchangeRate {
  if (!value || typeof value !== "object") return false;
  const rate = value as ExchangeRate;
  return Number.isFinite(rate.aedToCny) && rate.aedToCny >= 0.0001 && rate.aedToCny < 1000
    && Number.isFinite(rate.updatedAt) && rate.updatedAt > 0 && rate.updatedAt <= Date.now() + 300000
    && Number.isFinite(rate.nextUpdateAt) && rate.nextUpdateAt > rate.updatedAt;
}
export function parseCurrencyPreference(raw: string | null): CurrencyPreference {
  try {
    const value = JSON.parse(raw || "null");
    const rate = validRate(value?.rate) ? value.rate : null;
    return { currency: value?.currency === "CNY" && rate ? "CNY" : "AED", rate };
  } catch { return { currency: "AED", rate: null }; }
}
export function setRuntimeCurrency(preference: CurrencyPreference) {
  if (preference.currency === "CNY" && !validRate(preference.rate)) throw new Error("A valid yuan exchange rate is required.");
  current = preference;
}
export const currencyCode = () => current.currency;
export const currencyFactor = () => current.currency === "CNY" ? current.rate!.aedToCny : 1;
export const toDisplayAmount = (aed: number) => Math.round((aed * currencyFactor() + Number.EPSILON) * 100) / 100;
export const amountDraft = (aed: number) => toDisplayAmount(aed).toFixed(2);
export function toAED(value: string | number, original?: number | null) {
  if (original != null && Number(value) === toDisplayAmount(original)) return original;
  return Math.round((Number(value) / currencyFactor() + Number.EPSILON) * 100) / 100;
}
/** Leave malformed drafts intact so the existing validators reject them. */
export function baseMoneyDraft(value: string, original?: number | null): string {
  return /^\d+(\.\d{1,2})?$/.test(value.trim()) ? String(toAED(value, original)) : value;
}
export function formatDisplayAmount(aed: number) { return grouped(toDisplayAmount(aed)); }
function grouped(value: number) {
  const [whole, cents] = Math.abs(value).toFixed(2).split(".");
  return `${value < 0 ? "-" : ""}${whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",")}.${cents}`;
}
/** For drafts that already contain the selected currency, never multiply twice. */
export const formatDraftMoney = (value: number) => `${value < 0 ? "-" : ""}${currencyCode()} ${grouped(Math.abs(value))}`;
const identity = (value: string) => value;
const MONEY_NUMBER = "(-?\\d[\\d,]*(?:\\.\\d+)?)";
const AED_RANGE = new RegExp(`\\bAED\\s+${MONEY_NUMBER}([–])${MONEY_NUMBER}`, "g");
const AED_PREFIX = new RegExp(`\\bAED\\s+${MONEY_NUMBER}`, "g");
const AED_SUFFIX = new RegExp(`${MONEY_NUMBER}\\s+AED\\b`, "g");
/** Convert canonical AED UI text before localization; user-entered text opts out. */
export function currencyText(text: string, translate: (value: string) => string = identity): string {
  if (current.currency !== "CNY") return translate(text);
  const convert = (value: string) => grouped(toDisplayAmount(Number(value.replace(/,/g, ""))));
  const converted = text
    .replace(AED_RANGE, (_, min: string, separator: string, max: string) => `__CNY_AMOUNT__ ${convert(min)}${separator}${convert(max)}`)
    .replace(AED_PREFIX, (_, value: string) => `__CNY_AMOUNT__ ${convert(value)}`)
    .replace(AED_SUFFIX, (_, value: string) => `${convert(value)} __CNY_AMOUNT__`)
    .replace(/__CNY_AMOUNT__/g, "AED");
  const result = translate(converted.replace(/\bCNY\b/g, "AED")).replace(/\bAED\b/g, "CNY");
  // Only rewrite localized unit labels after converting canonical source text.
  // Free-form old AI replies retain unparsed explicitly named currencies.
  return translate === identity ? result : result.replace(/UAE Dirham/g, "Chinese yuan").replace(/بالدرهم الإماراتي|بالدرهم|درهم/g, "باليوان الصيني");
}

const PROFILE_MONEY = ["income", "other_income", "target_amount", "current_amount"] as const;
export function displayProfile<T extends Record<string, unknown>>(profile: T): T {
  const result: Record<string, unknown> = { ...profile };
  for (const key of PROFILE_MONEY) if (profile[key] != null) result[key] = amountDraft(Number(profile[key]));
  if (profile.expenses) result.expenses = Object.fromEntries(Object.entries(profile.expenses as Record<string, unknown>).map(([key, value]) => [key, value == null ? value : amountDraft(Number(value))]));
  return result as T;
}
export function baseProfile<T extends Record<string, unknown>>(profile: T, original?: T): T {
  const result: Record<string, unknown> = { ...profile };
  for (const key of PROFILE_MONEY) if (profile[key] != null) result[key] = baseMoneyDraft(String(profile[key]), original?.[key] == null ? undefined : Number(original[key]));
  if (profile.expenses) result.expenses = Object.fromEntries(Object.entries(profile.expenses as Record<string, unknown>).map(([key, value]) => [key, value == null ? value : baseMoneyDraft(String(value), (original?.expenses as Record<string, number> | undefined)?.[key])]));
  return result as T;
}
