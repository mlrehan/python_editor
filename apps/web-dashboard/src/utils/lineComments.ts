export interface TextEdit {
  value: string;
  selectionStart: number;
  selectionEnd: number;
}

// Ctrl+/ (Colab / VS Code): true for Ctrl+/ or Cmd+/, including layouts where "/" needs Shift
// (e.code identifies the physical key) and the numpad divide key.
export function isToggleCommentShortcut(e: { ctrlKey: boolean; metaKey: boolean; altKey: boolean; key: string; code: string }): boolean {
  if (!(e.ctrlKey || e.metaKey) || e.altKey) return false;
  return e.key === '/' || e.code === 'Slash' || e.code === 'NumpadDivide';
}

/**
 * Toggles Python line comments (`# `) on every line touched by the selection, or on the cursor's
 * line when nothing is selected. If every non-blank line is already commented the comments are
 * removed, otherwise all non-blank lines are commented at their common indentation. Blank lines are
 * left alone, and the selection is mapped so it keeps covering the same text.
 */
export function toggleLineComments(value: string, selectionStart: number, selectionEnd: number): TextEdit {
  const start = Math.min(selectionStart, selectionEnd);
  let end = Math.max(selectionStart, selectionEnd);
  // A selection ending at the start of a line (after a newline) does not include that line
  if (end > start && value[end - 1] === '\n') end -= 1;

  const blockStart = value.lastIndexOf('\n', start - 1) + 1;
  const nextNewline = value.indexOf('\n', end);
  const blockEnd = nextNewline === -1 ? value.length : nextNewline;
  const lines = value.substring(blockStart, blockEnd).split('\n');

  const nonBlank = lines.filter((line) => line.trim() !== '');
  const indentOf = (line: string) => (line.match(/^[ \t]*/) as RegExpMatchArray)[0].length;
  const uncomment = nonBlank.length > 0 && nonBlank.every((line) => /^[ \t]*#/.test(line));
  const commentColumn = nonBlank.length > 0 ? Math.min(...nonBlank.map(indentOf)) : indentOf(lines[0]);

  // Per line: column where text was inserted (+) or removed (-), and how many characters
  const changes: Array<{ column: number; delta: number }> = [];
  const newLines = lines.map((line) => {
    if (uncomment) {
      const match = line.match(/^([ \t]*)# ?/);
      if (!match) {
        changes.push({ column: 0, delta: 0 });
        return line;
      }
      const column = match[1].length;
      changes.push({ column, delta: -(match[0].length - column) });
      return line.substring(0, column) + line.substring(match[0].length);
    }
    // Commenting: skip blank lines, except a lone blank line (Ctrl+/ on an empty line adds "# ")
    if (line.trim() === '' && !(lines.length === 1)) {
      changes.push({ column: 0, delta: 0 });
      return line;
    }
    const column = Math.min(commentColumn, line.length);
    changes.push({ column, delta: 2 });
    return line.substring(0, column) + '# ' + line.substring(column);
  });

  // keepBeforeInsert: the start of a selection range stays in front of a "# " inserted exactly at
  // it, so the selection grows to cover the new comment markers (a cursor or range end moves past)
  const mapPosition = (pos: number, keepBeforeInsert = false): number => {
    let lineStartOffset = blockStart;
    let shift = 0;
    for (let i = 0; i < lines.length; i++) {
      const lineEndOffset = lineStartOffset + lines[i].length;
      const { column, delta } = changes[i];
      if (pos <= lineEndOffset || i === lines.length - 1) {
        const col = pos - lineStartOffset;
        if (col < 0) return pos + shift;
        if (delta > 0) return pos + shift + (col > column || (col === column && !keepBeforeInsert) ? delta : 0);
        if (delta < 0) {
          if (col <= column) return pos + shift;
          return pos + shift + Math.max(delta, column - col);
        }
        return pos + shift;
      }
      shift += delta;
      lineStartOffset = lineEndOffset + 1;
    }
    return pos + shift;
  };

  const newValue = value.substring(0, blockStart) + newLines.join('\n') + value.substring(blockEnd);
  const isRange = selectionStart !== selectionEnd;
  return {
    value: newValue,
    selectionStart: mapPosition(selectionStart, isRange),
    selectionEnd: mapPosition(selectionEnd),
  };
}
