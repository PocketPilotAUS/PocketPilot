import React, { createContext, useContext, useEffect, useRef, useState } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { LANGUAGES, Language, Label, translate } from "./languages";
import { setRuntimeLanguage } from "./localize";
import { Currency, CurrencyPreference, parseCurrencyPreference, setRuntimeCurrency } from "./currency";
import { loadYuanRate } from "../services/currencyService";

type Preferences = { language: Language; currency: Currency; currencyPreference: CurrencyPreference; ready: boolean; setCurrency: (currency: Currency) => Promise<void>; setLanguage: (language: Language) => Promise<void>; t: (key: Label) => string };
const Context = createContext<Preferences | null>(null);
const KEY = "@pocketpilot_language";
const CURRENCY_KEY = "@pocketpilot_currency";
export function PreferencesProvider({ children }: { children: React.ReactNode }) {
  const [language, update] = useState<Language>("en");
  const [currencyPreference, updateCurrency] = useState<CurrencyPreference>({ currency: "AED", rate: null });
  const [ready, setReady] = useState(false);
  const changed = useRef(false);
  useEffect(() => { setRuntimeLanguage(language); }, [language]);
  useEffect(() => {
    let active = true;
    Promise.all([AsyncStorage.getItem(KEY), AsyncStorage.getItem(CURRENCY_KEY)]).then(([saved, currency]) => {
      if (!active) return;
      if (!changed.current && LANGUAGES.some(item => item.code === saved)) update(saved as Language);
      const restored = parseCurrencyPreference(currency);
      setRuntimeCurrency(restored); updateCurrency(restored);
    })
      .catch(() => {}).finally(() => { if (active) setReady(true); });
    return () => { active = false; };
  }, []);
  const setLanguage = async (next: Language) => {
    changed.current = true;
    await AsyncStorage.setItem(KEY, next);
    update(next);
  };
  const setCurrency = async (currency: Currency) => {
    const rate = currency === "CNY" ? await loadYuanRate(currencyPreference.rate) : currencyPreference.rate;
    const next = { currency, rate };
    // Commit storage and runtime together. A failed fetch/save keeps the old currency.
    await AsyncStorage.setItem(CURRENCY_KEY, JSON.stringify(next));
    setRuntimeCurrency(next); updateCurrency(next);
  };
  return <Context.Provider value={{ language, currency: currencyPreference.currency, currencyPreference, ready, setCurrency, setLanguage, t: key => translate(language, key) }}>{children}</Context.Provider>;
}
export function usePreferences() {
  const value = useContext(Context);
  if (!value) throw new Error("PreferencesProvider is required");
  return value;
}
