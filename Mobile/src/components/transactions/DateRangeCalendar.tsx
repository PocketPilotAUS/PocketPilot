import React, { useState } from "react";
import { Pressable, Text, View } from "react-native";
import { ChevronLeft, ChevronRight } from "lucide-react-native";

import { useTransactionsTheme } from "./useTransactionsTheme";
import { formatShortDate, monthTitle, parseISODate, toISODate } from "../../utils/transactions";

const WEEKDAYS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"];

type Props = {
  start: string | null;
  end: string | null;
  today: Date;
  onChange: (start: string | null, end: string | null) => void;
};

// Month grid weeks (Monday first); null cells pad the first and last week
function monthWeeks(year: number, month: number): (string | null)[][] {
  const first = new Date(year, month, 1);
  const days = new Date(year, month + 1, 0).getDate();
  const cells: (string | null)[] = Array((first.getDay() + 6) % 7).fill(null);

  for (let day = 1; day <= days; day++) {
    cells.push(toISODate(new Date(year, month, day)));
  }

  while (cells.length % 7 !== 0) cells.push(null);

  const weeks: (string | null)[][] = [];
  for (let index = 0; index < cells.length; index += 7) weeks.push(cells.slice(index, index + 7));
  return weeks;
}

export default function DateRangeCalendar({ start, end, today, onChange }: Props) {
  const { tx, palette } = useTransactionsTheme();

  const initial = start ? parseISODate(start) : today;
  const [visible, setVisible] = useState({ year: initial.getFullYear(), month: initial.getMonth() });

  const todayISO = toISODate(today);
  const atCurrentMonth = visible.year === today.getFullYear() && visible.month === today.getMonth();

  const changeMonth = (offset: number) => {
    const date = new Date(visible.year, visible.month + offset, 1);
    setVisible({ year: date.getFullYear(), month: date.getMonth() });
  };

  // First tap sets the start; the second sets the end (swapped if earlier)
  const select = (day: string) => {
    if (!start || end) {
      onChange(day, null);
    } else if (day < start) {
      onChange(day, start);
    } else {
      onChange(start, day);
    }
  };

  const rangeEnd = end ?? start;

  return (
    <View style={tx.calendar}>
      <View style={tx.calendarHeader}>
        <Pressable
          onPress={() => changeMonth(-1)}
          style={tx.calendarNav}
          accessibilityRole="button"
          accessibilityLabel="Previous month"
        >
          <ChevronLeft size={20} color={palette.text} />
        </Pressable>

        <Text style={tx.calendarMonth}>{monthTitle(visible.year, visible.month)}</Text>

        <Pressable
          onPress={() => changeMonth(1)}
          disabled={atCurrentMonth}
          style={[tx.calendarNav, atCurrentMonth && tx.calendarNavDisabled]}
          accessibilityRole="button"
          accessibilityLabel="Next month"
        >
          <ChevronRight size={20} color={palette.text} />
        </Pressable>
      </View>

      <View style={tx.weekRow}>
        {WEEKDAYS.map((day) => (
          <Text key={day} style={tx.weekday}>{day}</Text>
        ))}
      </View>

      {monthWeeks(visible.year, visible.month).map((week, index) => (
        <View key={index} style={tx.weekRow}>
          {week.map((day, column) => {
            if (!day) return <View key={column} style={tx.dayCell} />;

            const future = day > todayISO;
            const isStart = day === start;
            const isEnd = day === rangeEnd;
            const inRange = !!start && !!rangeEnd && day >= start && day <= rangeEnd && start !== rangeEnd;

            return (
              <Pressable
                key={day}
                onPress={() => select(day)}
                disabled={future}
                style={[
                  tx.dayCell,
                  inRange && tx.dayInRange,
                  inRange && isStart && tx.dayRangeStart,
                  inRange && isEnd && tx.dayRangeEnd,
                ]}
                accessibilityRole="button"
                accessibilityLabel={formatShortDate(day, today)}
                accessibilityState={{ selected: isStart || isEnd, disabled: future }}
              >
                <View style={[tx.dayBubble, (isStart || isEnd) && tx.dayBubbleSelected]}>
                  <Text
                    style={[
                      tx.dayText,
                      future && tx.dayTextMuted,
                      day === todayISO && tx.dayTextToday,
                      (isStart || isEnd) && tx.dayTextSelected,
                    ]}
                  >
                    {Number(day.slice(8))}
                  </Text>
                </View>
              </Pressable>
            );
          })}
        </View>
      ))}

      <Text style={tx.rangeSummary}>
        {!start
          ? "Tap a start date"
          : !end
            ? `${formatShortDate(start, today)} – tap an end date`
            : `${formatShortDate(start, today)} – ${formatShortDate(end, today)}`}
      </Text>
    </View>
  );
}
