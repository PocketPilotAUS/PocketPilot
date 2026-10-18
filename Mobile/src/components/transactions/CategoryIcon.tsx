import React from "react";
import { View } from "../../preferences/LocalizedNative";
import {
  Banknote,
  Car,
  Clapperboard,
  House,
  Receipt,
  Repeat,
  ShoppingBag,
  ShoppingCart,
  Tag,
  Utensils,
} from "lucide-react-native";

import { useTransactionsTheme } from "./useTransactionsTheme";

// Icons for the categories offered on the Add screen; custom categories
// fall back to a tag
const ICONS: Record<string, typeof Tag> = {
  rent: House,
  food: Utensils,
  groceries: ShoppingCart,
  transport: Car,
  shopping: ShoppingBag,
  subscriptions: Repeat,
  bills: Receipt,
  entertainment: Clapperboard,
  other: Banknote,
};

// Fixed colour slot per known category, so a category always looks the same
const COLOR_SLOTS: Record<string, number> = {
  rent: 0, food: 1, transport: 2, shopping: 3, bills: 4,
  entertainment: 5, subscriptions: 6, groceries: 7, other: 8,
};

function colorSlot(category: string, count: number): number {
  const key = category.trim().toLowerCase();

  if (key in COLOR_SLOTS) return COLOR_SLOTS[key] % count;

  // Stable colour for custom categories
  let hash = 0;
  for (const char of key) hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  return hash % count;
}

type Props = {
  category: string;
  size?: "row" | "large";
};

export default function CategoryIcon({ category, size = "row" }: Props) {
  const { tx, chartColors } = useTransactionsTheme();

  const Icon = ICONS[category.trim().toLowerCase()] ?? Tag;
  const color = chartColors[colorSlot(category, chartColors.length)];

  return (
    <View
      style={[
        size === "large" ? tx.detailIcon : tx.categoryIcon,
        // Same hue at low opacity behind the icon
        { backgroundColor: `${color}22` },
      ]}
    >
      <Icon size={size === "large" ? 28 : 19} color={color} strokeWidth={2} />
    </View>
  );
}
