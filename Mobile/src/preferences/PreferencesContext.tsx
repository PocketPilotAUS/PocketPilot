import React, { createContext, useContext, useEffect, useRef, useState } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { LANGUAGES, Language, Label, translate } from "./languages";
import { setRuntimeLanguage } from "./localize";

type Preferences = { language: Language; ready: boolean; setLanguage: (language: Language) => Promise<void>; t: (key: Label) => string };
const Context = createContext<Preferences | null>(null);
const KEY = "@pocketpilot_language";
export function PreferencesProvider({ children }: { children: React.ReactNode }) {
  const [language, update] = useState<Language>("en");
  const [ready, setReady] = useState(false);
  const changed = useRef(false);
  useEffect(() => { setRuntimeLanguage(language); }, [language]);
  useEffect(() => {
    let active = true;
    AsyncStorage.getItem(KEY).then(saved => { if (active && !changed.current && LANGUAGES.some(item => item.code === saved)) update(saved as Language); })
      .catch(() => {}).finally(() => { if (active) setReady(true); });
    return () => { active = false; };
  }, []);
  const setLanguage = async (next: Language) => {
    changed.current = true;
    await AsyncStorage.setItem(KEY, next);
    update(next);
  };
  return <Context.Provider value={{ language, ready, setLanguage, t: key => translate(language, key) }}>{children}</Context.Provider>;
}
export function usePreferences() {
  const value = useContext(Context);
  if (!value) throw new Error("PreferencesProvider is required");
  return value;
}
