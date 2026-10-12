import React from "react";
import Svg, { Circle, Path } from "react-native-svg";
import { donutSlice } from "../utils/planVisuals";
import type { incomeChart } from "../utils/incomeChart";

type Props = {
  chart: ReturnType<typeof incomeChart>; size: number; grey: string; danger: string;
  selected?: string | null; onSelect?: (label: string) => void;
};

export default function IncomeDonut({ chart, size, grey, danger, selected, onSelect }: Props) {
  let start = 0;
  return <Svg width={size} height={size} viewBox="0 0 200 200">
    <Circle cx={100} cy={100} r={78} stroke={chart.overBy > 0 ? danger : grey} strokeWidth={24} fill="none" />
    {chart.slices.filter(slice => slice.fraction > 0).map(slice => {
      const path = donutSlice(start, slice.fraction);
      start += slice.fraction;
      return <Path key={slice.label} d={path} fill={slice.color} fillRule="evenodd"
        opacity={selected && selected !== slice.label ? .3 : 1}
        onPress={onSelect ? () => onSelect(slice.label) : undefined}
        accessibilityLabel={`${slice.label}, ${slice.percentage?.toFixed(1)} percent of income`} />;
    })}
  </Svg>;
}
