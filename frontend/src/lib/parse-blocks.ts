/**
 * Splits streaming markdown into renderable segments: plain markdown,
 * ```jsx blocks (JSXPreview) and ```plan blocks (Plan). Works on incomplete
 * streams — an unterminated fence is treated as a streaming block.
 */

export type PlanStep = {
  title: string;
  status?: "pending" | "active" | "complete";
};

export type PlanData = {
  title?: string;
  description?: string;
  steps: PlanStep[];
};

export type TextSegment =
  | { kind: "markdown"; content: string }
  | { kind: "jsx"; content: string; streaming: boolean }
  | { kind: "plan"; plan: PlanData | null; raw: string; streaming: boolean };

const FENCE = /```(jsx|plan)\n/g;

export const parsePlan = (raw: string): PlanData | null => {
  try {
    const data = JSON.parse(raw) as PlanData;
    if (Array.isArray(data.steps)) return data;
    return null;
  } catch {
    return null;
  }
};

export const segmentText = (text: string, streaming: boolean): TextSegment[] => {
  const segments: TextSegment[] = [];
  let cursor = 0;
  FENCE.lastIndex = 0;
  let match = FENCE.exec(text);
  while (match) {
    if (match.index > cursor) {
      segments.push({ kind: "markdown", content: text.slice(cursor, match.index) });
    }
    const lang = match[1] as "jsx" | "plan";
    const bodyStart = match.index + match[0].length;
    const closeIndex = text.indexOf("\n```", bodyStart);
    const open = closeIndex === -1;
    const body = open ? text.slice(bodyStart) : text.slice(bodyStart, closeIndex);
    if (lang === "jsx") {
      segments.push({ kind: "jsx", content: body, streaming: open && streaming });
    } else {
      segments.push({
        kind: "plan",
        plan: parsePlan(body),
        raw: body,
        streaming: open && streaming,
      });
    }
    cursor = open ? text.length : closeIndex + 4;
    FENCE.lastIndex = cursor;
    match = FENCE.exec(text);
  }
  if (cursor < text.length) {
    segments.push({ kind: "markdown", content: text.slice(cursor) });
  }
  return segments;
};
