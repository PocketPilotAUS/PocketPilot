import React from "react";
import { Text, View } from "react-native";

import { useAITheme } from "./useAITheme";
import { InlineSegment, parseMessage } from "../../utils/messageFormat";

// Renders an AI reply with paragraphs, headings, lists and bold text
export default function FormattedMessage({ content }: { content: string }) {
  const { ai } = useAITheme();

  const inline = (segments: InlineSegment[]) =>
    segments.map((segment, index) => (
      <Text key={index} style={segment.bold ? ai.bold : undefined}>
        {segment.text}
      </Text>
    ));

  return (
    <View>
      {parseMessage(content).map((block, index) => {
        const gap = index > 0 ? ai.blockGap : undefined;

        if (block.kind === "heading") {
          return (
            <Text key={index} selectable style={[ai.heading, gap]}>
              {inline(block.segments)}
            </Text>
          );
        }

        if (block.kind === "bullet" || block.kind === "numbered") {
          return (
            <View key={index} style={[ai.listRow, gap]}>
              <Text style={ai.listMarker}>{block.kind === "bullet" ? "•" : block.marker}</Text>
              <Text selectable style={[ai.assistantText, ai.listText]}>
                {inline(block.segments)}
              </Text>
            </View>
          );
        }

        return (
          <Text key={index} selectable style={[ai.assistantText, gap]}>
            {inline(block.segments)}
          </Text>
        );
      })}
    </View>
  );
}
