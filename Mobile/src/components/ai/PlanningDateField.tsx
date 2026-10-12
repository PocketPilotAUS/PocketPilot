import React, { useState } from "react";
import { Keyboard, Pressable } from "react-native";
import { Text, TextInput, View } from "../../preferences/LocalizedNative";
import { CalendarDays, ChevronLeft, ChevronRight } from "lucide-react-native";
import { useAITheme } from "./useAITheme";
import { createPlanningStyles } from "../../styles/PlanningStyles";
import { formatPlanningDate, localISODate, parsePlanningDate, planningMonthWeeks } from "../../utils/planningDate";

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const WEEKDAYS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"];

type Props = { value: string; onChange: (text: string) => void; error: string | null; disabled?: boolean };

export default function PlanningDateField({ value, onChange, error, disabled = false }: Props) {
  const { palette } = useAITheme();
  const s = createPlanningStyles(palette);
  const [open, setOpen] = useState(false);
  const [visible, setVisible] = useState(() => new Date());
  const today = new Date();
  const todayISO = localISODate(today);
  const selected = parsePlanningDate(value);
  const year = visible.getFullYear(), month = visible.getMonth();
  const firstMonth = year === today.getFullYear() && month === today.getMonth();

  const toggle = () => {
    Keyboard.dismiss();
    if (!open) {
      const date = selected && selected > todayISO ? selected : todayISO;
      const [y, m] = date.split("-").map(Number);
      setVisible(new Date(y, m - 1, 1));
    }
    setOpen(!open);
  };
  const moveMonth = (offset: number) => setVisible(new Date(year, month + offset, 1));

  return <View style={s.dateField}>
    <Text style={s.label}>Target date (DD/MM/YYYY)</Text>
    <TextInput
      style={s.input} value={value} onChangeText={onChange} editable={!disabled}
      placeholder="DD/MM/YYYY" placeholderTextColor={palette.textMuted}
      accessibilityLabel="Target date, day month year" maxLength={10}
      autoCorrect={false} autoCapitalize="none"
      onBlur={() => { if (selected) onChange(formatPlanningDate(selected)); }}
    />
    <Pressable style={[s.button, s.secondary, disabled && s.muted]} onPress={toggle}
      disabled={disabled} accessibilityRole="button" accessibilityState={{ expanded: open, disabled }}>
      <View style={s.datePickerLabel}><CalendarDays size={18} color={palette.text} /><Text style={s.secondaryText}>{open ? "Close calendar" : "Choose from calendar"}</Text></View>
    </Pressable>
    {!!error && <Text accessibilityRole="alert" style={s.error}>{error}</Text>}
    {open && <View style={s.dateCalendar}>
      <View style={s.dateCalendarHeader}>
        <Pressable style={[s.dateNavigation, (firstMonth || disabled) && s.muted]} disabled={firstMonth || disabled}
          accessibilityRole="button" accessibilityLabel="Previous month" onPress={() => moveMonth(-1)}><ChevronLeft color={palette.text} size={22} /></Pressable>
        <Text style={s.label}>{MONTHS[month]} {year}</Text>
        <Pressable style={[s.dateNavigation, (year === 9999 && month === 11 || disabled) && s.muted]} disabled={year === 9999 && month === 11 || disabled}
          accessibilityRole="button" accessibilityLabel="Next month" onPress={() => moveMonth(1)}><ChevronRight color={palette.text} size={22} /></Pressable>
      </View>
      <View style={s.dateWeek}>{WEEKDAYS.map(day => <Text key={day} style={s.dateWeekday}>{day}</Text>)}</View>
      {planningMonthWeeks(year, month).map((week, i) => <View key={i} style={s.dateWeek}>
        {week.map((day, column) => day ? <Pressable key={day}
          style={[s.dateDay, day === selected && s.selected, (day <= todayISO || disabled) && s.muted]}
          disabled={day <= todayISO || disabled} accessibilityRole="button"
          accessibilityLabel={formatPlanningDate(day)} accessibilityState={{ selected: day === selected, disabled: day <= todayISO || disabled }}
          onPress={() => { onChange(formatPlanningDate(day)); setOpen(false); }}>
          <Text style={s.secondaryText}>{Number(day.slice(8))}</Text>
        </Pressable> : <View key={column} style={s.dateDay} />)}
      </View>)}
      <Text style={s.text}>Select a future date. You can also type the date above.</Text>
    </View>}
  </View>;
}
