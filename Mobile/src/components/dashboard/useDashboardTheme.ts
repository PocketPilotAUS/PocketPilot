import { useMemo } from "react";

import { useAppTheme } from "../../theme/ThemeContext";
import {
  createDashboardStyles,
  getChartColors,
  getDashboardPalette,
} from "../../styles/DashboardStyles";

export function useDashboardTheme() {
  const { mode } = useAppTheme();

  return useMemo(() => {
    const palette = getDashboardPalette(mode);

    return {
      mode,
      palette,
      styles: createDashboardStyles(palette),
      chartColors: getChartColors(mode),
    };
  }, [mode]);
}
