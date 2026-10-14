import React from "react";
import { Linking, Pressable, Text, View } from "react-native";
import { usePreferences } from "../preferences/PreferencesContext";
import { useAppTheme } from "../theme/ThemeContext";
import { createCurrencyStyles } from "../styles/CurrencyStyles";
import { localize } from "../preferences/localize";
import type { ExchangeRate } from "../preferences/currency";

export default function CurrencyNotice({ always = false, rateOverride }: { always?: boolean; rateOverride?: ExchangeRate }) {
  const { currency, currencyPreference, language } = usePreferences();
  const { colors } = useAppTheme();
  const s = createCurrencyStyles(colors);
  const rate = rateOverride ?? currencyPreference.rate;
  if (!rate || (!always && currency !== "CNY")) return null;
  const updated = new Date(rate.updatedAt);
  const date = `${updated.getFullYear()}-${String(updated.getMonth() + 1).padStart(2, "0")}-${String(updated.getDate()).padStart(2, "0")}`;
  return <View style={s.notice}>
    <Text style={s.text}>{`1 AED ≈ ${rate.aedToCny.toFixed(4)} CNY · ${date}`}{Date.now() >= rate.nextUpdateAt ? ` · ${localize("Cached rate", language)}` : ""}</Text>
    <Pressable onPress={() => { void Linking.openURL("https://www.exchangerate-api.com").catch(() => {}); }} accessibilityRole="link" accessibilityLabel="Rates By Exchange Rate API">
      <Text style={s.link}>Rates By Exchange Rate API</Text>
    </Pressable>
  </View>;
}
