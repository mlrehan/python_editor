import { TextEdit } from './lineComments';

export const INDENT = '    ';

/**
 * Tab / Shift+Tab in a code editor.
 * - Tab with no multi-line selection inserts four spaces at the cursor (replacing any selection).
 * - Tab with a multi-line selection indents every selected line; Shift+Tab outdents the selected
 *   lines (or the cursor's line) by up to four spaces or one tab character.
 * The selection is mapped so it keeps covering the same text.
 */
export function applyTabIndent(value: string, selectionStart: number, selectionEnd: number, outdent: boolean): TextEdit {
  const start = Math.min(selectionStart, selectionEnd);
  const end = Math.max(selectionStart, selectionEnd);
  const lineStart = value.lastIndexOf('\n', start - 1) + 1;
  const selectedText = value.substring(start, end);

  // Plain Tab with no multi-line selection: insert spaces at the cursor
  if (!outdent && !selectedText.includes('\n')) {
    const caret = start + INDENT.length;
    return { value: value.substring(0, start) + INDENT + value.substring(end), selectionStart: caret, selectionEnd: caret };
  }

  // Indent or outdent every line touched by the selection
  const blockEnd = end > start && value[end - 1] === '\n' ? end - 1 : end;
  const lineEndIndex = value.indexOf('\n', blockEnd);
  const blockStop = lineEndIndex === -1 ? value.length : lineEndIndex;
  const lines = value.substring(lineStart, blockStop).split('\n');
  let firstLineDelta = 0;
  let totalDelta = 0;
  const changed = lines.map((line, i) => {
    let delta: number;
    let next: string;
    if (outdent) {
      const removable = line.match(/^( {1,4}|\t)/)?.[0].length ?? 0;
      next = line.substring(removable);
      delta = -removable;
    } else {
      next = INDENT + line;
      delta = INDENT.length;
    }
    if (i === 0) firstLineDelta = delta;
    totalDelta += delta;
    return next;
  });
  const newValue = value.substring(0, lineStart) + changed.join('\n') + value.substring(blockStop);
  return {
    value: newValue,
    selectionStart: Math.max(lineStart, start + firstLineDelta),
    selectionEnd: Math.max(lineStart, end + totalDelta),
  };
}
