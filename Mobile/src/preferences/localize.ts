import type { Language } from "./languages";
import { UI_TRANSLATIONS } from "./uiTranslations";

let currentLanguage: Language = "en";
export const setRuntimeLanguage = (language: Language) => { currentLanguage = language; };
export const getRuntimeLanguage = () => currentLanguage;
const normalize = (text: string) => text.replace(/\s+/g, " ").trim();
const catalog = new Map(UI_TRANSLATIONS.map(row => [normalize(row[0]), row]));
const escape = (text: string) => text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const patterns = UI_TRANSLATIONS.filter(row => /\{\d+\}/.test(row[0])).map(row => ({
  row, regex: new RegExp("^" + row[0].split(/(\{\d+\})/).map(piece => /^\{\d+\}$/.test(piece) ? "(.+?)" : escape(piece)).join("") + "$"),
}));
const fragments = [...catalog.keys()].filter(key => !/\{\d+\}/.test(key)).sort((a, b) => b.length - a.length);
// Boundaries keep category names out of longer words and financial identifiers.
const matcher = new RegExp(`(^|[^A-Za-z])(${fragments.map(escape).join("|")})(?=$|[^A-Za-z])`, "g");

export function localize(text: string, language: Language = currentLanguage): string {
  if (language !== "ar" && language !== "zh") return text;
  const column = language === "ar" ? 1 : 2;
  for (const pattern of patterns) {
    const match = pattern.regex.exec(normalize(text));
    if (match) return pattern.row[column].replace(/\{(\d+)\}/g, (_, index: string) => match[Number(index) + 1]);
  }
  const exact = catalog.get(normalize(text));
  if (exact) {
    const prefix = text.match(/^\s*/)?.[0] ?? "";
    const suffix = text.match(/\s*$/)?.[0] ?? "";
    return prefix + exact[column] + suffix;
  }
  return text.replace(matcher, (match, prefix: string, phrase: string) => prefix + (catalog.get(phrase)?.[column] ?? phrase));
}
