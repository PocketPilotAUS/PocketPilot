/** Dates stay in ISO format in profiles; only the user-facing field uses day first. */
export function formatPlanningDate(iso: string | null | undefined): string {
  if (!iso) return "";
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  return match ? `${match[3]}/${match[2]}/${match[1]}` : iso;
}

export function parsePlanningDate(text: string): string | null {
  const match = /^(\d{1,2})([\/\- ])(\d{1,2})\2(\d{4})$/.exec(text.trim());
  if (!match) return null;
  const day = Number(match[1]), month = Number(match[3]), year = Number(match[4]);
  if (year < 1000 || month < 1 || month > 12 || day < 1) return null;
  if (day > new Date(year, month, 0).getDate()) return null;
  return `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

export function localISODate(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

export function planningDateError(text: string, today = new Date()): string | null {
  if (!text.trim()) return "Choose a target date or enter one as DD/MM/YYYY.";
  const iso = parsePlanningDate(text);
  if (!iso) return "Enter a real date as DD/MM/YYYY, for example 11/10/2027.";
  return iso <= localISODate(today) ? "Choose a date after today." : null;
}

export function planningMonthWeeks(year: number, month: number): (string | null)[][] {
  const cells: (string | null)[] = Array((new Date(year, month, 1).getDay() + 6) % 7).fill(null);
  for (let day = 1; day <= new Date(year, month + 1, 0).getDate(); day++) {
    cells.push(localISODate(new Date(year, month, day)));
  }
  while (cells.length % 7) cells.push(null);
  const weeks: (string | null)[][] = [];
  for (let i = 0; i < cells.length; i += 7) weeks.push(cells.slice(i, i + 7));
  return weeks;
}
