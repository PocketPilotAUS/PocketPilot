// Turns an AI reply's plain-text/Markdown-style formatting into simple
// blocks for display. Text only: nothing is ever interpreted as code or HTML.

export type InlineSegment = { text: string; bold: boolean };

export type MessageBlock =
  | { kind: "paragraph"; segments: InlineSegment[] }
  | { kind: "heading"; segments: InlineSegment[] }
  | { kind: "bullet"; segments: InlineSegment[] }
  | { kind: "numbered"; marker: string; segments: InlineSegment[] };

// Support model-generated bold markers, including escaped/triple markers.
// Incomplete double markers should not leak into conversational display.
export function parseInline(text: string): InlineSegment[] {
  text = text.replace(/\\\*/g, "*");
  const segments: InlineSegment[] = [];
  const pattern = /\*{2,3}([^*]+?)\*{2,3}/g;
  let last = 0;

  for (const match of text.matchAll(pattern)) {
    if (match.index > last) segments.push({ text: text.slice(last, match.index).replace(/\*{2,}/g, ""), bold: false });
    segments.push({ text: match[1], bold: true });
    last = match.index + match[0].length;
  }

  if (last < text.length) segments.push({ text: text.slice(last).replace(/\*{2,}/g, ""), bold: false });

  return segments.length ? segments : [{ text: text.replace(/\*{2,}/g, ""), bold: false }];
}

export function parseMessage(content: string): MessageBlock[] {
  const blocks: MessageBlock[] = [];
  let paragraph: string[] = [];

  const flush = () => {
    if (paragraph.length) {
      blocks.push({ kind: "paragraph", segments: parseInline(paragraph.join(" ")) });
      paragraph = [];
    }
  };

  for (const rawLine of content.replace(/\r\n/g, "\n").split("\n")) {
    const line = rawLine.trim();

    if (!line) {
      flush();
      continue;
    }

    const heading = line.match(/^#{1,6}\s+(.*)$/);
    const bullet = line.match(/^[-*•]\s+(.*)$/);
    const numbered = line.match(/^(\d{1,3})[.)]\s+(.*)$/);

    if (heading) {
      flush();
      blocks.push({ kind: "heading", segments: parseInline(heading[1]) });
    } else if (bullet) {
      flush();
      blocks.push({ kind: "bullet", segments: parseInline(bullet[1]) });
    } else if (numbered) {
      flush();
      blocks.push({ kind: "numbered", marker: `${numbered[1]}.`, segments: parseInline(numbered[2]) });
    } else {
      paragraph.push(line);
    }
  }

  flush();

  return blocks;
}
