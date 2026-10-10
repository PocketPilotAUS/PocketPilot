import { useMemo } from "react";

import { useDashboardTheme } from "../dashboard/useDashboardTheme";
import { createInsightsStyles } from "../../styles/InsightsStyles";

// Dashboard theme plus the Insights screen styles
export function useInsightsTheme() {
  const dashboard = useDashboardTheme();

  return useMemo(
    () => ({ ...dashboard, ins: createInsightsStyles(dashboard.palette) }),
    [dashboard]
  );
}
