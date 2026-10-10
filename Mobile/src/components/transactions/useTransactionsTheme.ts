import { useMemo } from "react";

import { useDashboardTheme } from "../dashboard/useDashboardTheme";
import { createTransactionsStyles } from "../../styles/TransactionsStyles";

// Dashboard theme plus the Transactions-specific styles
export function useTransactionsTheme() {
  const dashboard = useDashboardTheme();

  return useMemo(
    () => ({ ...dashboard, tx: createTransactionsStyles(dashboard.palette) }),
    [dashboard]
  );
}
