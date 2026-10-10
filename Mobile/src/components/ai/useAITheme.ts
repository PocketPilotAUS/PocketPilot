import { useMemo } from "react";

import { useDashboardTheme } from "../dashboard/useDashboardTheme";
import { createAIStyles } from "../../styles/AIStyles";

// Dashboard theme plus the AI screen styles
export function useAITheme() {
  const dashboard = useDashboardTheme();

  return useMemo(
    () => ({ ...dashboard, ai: createAIStyles(dashboard.palette) }),
    [dashboard]
  );
}
