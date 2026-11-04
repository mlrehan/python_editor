import { TextEdit } from './lineComments';

/**
 * Formatting for Markdown cells, applied to the selected text (or the current word / line), so
 * people can format notebooks without knowing Markdown. Every function returns the new text and
 * selection; the editor applies it through the browser's undo history.
 *
 * Formatting is toggled: applying Bold to bold text removes it, a heading level applied to a line
 * that already has it turns the line back into normal text, and the same for lists and quotes.
 */

export type InlineFormat = 'bold' | 'italic' | 'strike' | 'code' | 'highlight' | 'math';
export type BlockFormat = 'p' | 'h1' | 'h2' | 'h3';
export type ListKind = 'bullet' | 'number' | 'task';

const INLINE: Record<InlineFormat, { open: string; close: string; placeholder: string }> = {
  bold: { open: '**', close: '**', placeholder: 'bold text' },
  italic: { open: '*', close: '*', placeholder: 'italic text' },
  strike: { open: '~~', close: '~~', placeholder: 'struck text' },
  code: { open: '`', close: '`', placeholder: 'code' },
  highlight: { open: '<mark>', close: '</mark>', placeholder: 'highlighted text' },
  math: { open: '$', close: '$', placeholder: 'x^2' },
};

// List, quote and heading markers at the start of a line
const LIST_RE = /^(\s*)([-*+]\s+\[[ xX]\]\s+|[-*+]\s+|\d+[.)]\s+)/;
const HEADING_RE = /^(\s*)(#{1,6})\s+/;
const QUOTE_RE = /^(\s*)>\s?/;

interface LineRange {
  /** Offset of the first selected line's start */
  from: number;
  /** Offset of the last selected line's end */
  to: number;
  lines: string[];
}

function selectedLines(value: string, start: number, end: number): LineRange {
  const from = value.lastIndexOf('\n', start - 1) + 1;
  // A selection ending at the start of a line does not include that line
  const effectiveEnd = end > start && value[end - 1] === '\n' ? end - 1 : end;
  const nl = value.indexOf('\n', effectiveEnd);
  const to = nl === -1 ? value.length : nl;
  return { from, to, lines: value.substring(from, to).split('\n') };
}

/**
 * Replaces whole lines. A selection keeps covering the changed lines; a caret (nothing selected)
 * stays where it was in its text: line actions change only the start of a line (#, -, 1., >), so
 * the caret moves by that change and typing continues where it was.
 */
function replaceLines(value: string, range: LineRange, lines: string[], caret?: number): TextEdit {
  const text = lines.join('\n');
  const next = value.substring(0, range.from) + text + value.substring(range.to);
  if (caret === undefined || range.lines.length !== 1 || lines.length !== 1) {
    return { value: next, selectionStart: range.from, selectionEnd: range.from + text.length };
  }
  const moved = caret + (lines[0].length - range.lines[0].length);
  const pos = Math.min(range.from + text.length, Math.max(range.from, moved));
  return { value: next, selectionStart: pos, selectionEnd: pos };
}

/** Blank lines around a list or quote, so the text next to it is not pulled into it when shown */
function separateBlock(_value: string, edit: TextEdit, from: number, to: number, isPart: (line: string) => boolean): TextEdit {
  let next = edit.value;
  let { selectionStart, selectionEnd } = edit;
  const lineAfterStart = to + 1;
  if (to < next.length) {
    const nl = next.indexOf('\n', lineAfterStart);
    const after = next.substring(lineAfterStart, nl === -1 ? next.length : nl);
    if (after.trim() && !isPart(after)) next = next.substring(0, to) + '\n' + next.substring(to);
  }
  if (from > 0) {
    const prevStart = next.lastIndexOf('\n', from - 2) + 1;
    const before = next.substring(prevStart, from - 1);
    if (before.trim() && !isPart(before) && !HEADING_RE.test(before)) {
      next = next.substring(0, from) + '\n' + next.substring(from);
      selectionStart += 1;
      selectionEnd += 1;
    }
  }
  return { value: next, selectionStart, selectionEnd };
}

/** Bold, italic, strikethrough, inline code, highlight or inline maths (toggles) */
export function toggleInline(value: string, start: number, end: number, format: InlineFormat): TextEdit {
  const { open, close, placeholder } = INLINE[format];

  // Already formatted around the selection: remove the markers
  if (value.substring(start - open.length, start) === open && value.substring(end, end + close.length) === close) {
    // "*" must not match the inside of "**" (bold) when toggling italic
    const isBoldNotItalic = format === 'italic' && value[start - 2] === '*' && value[end + 1] === '*' && value.substring(start - 3, start) !== '***';
    if (!isBoldNotItalic) {
      const next = value.substring(0, start - open.length) + value.substring(start, end) + value.substring(end + close.length);
      return { value: next, selectionStart: start - open.length, selectionEnd: end - open.length };
    }
  }
  const selected = value.substring(start, end);
  if (selected.length > open.length + close.length && selected.startsWith(open) && selected.endsWith(close)) {
    const inner = selected.slice(open.length, selected.length - close.length);
    const next = value.substring(0, start) + inner + value.substring(end);
    return { value: next, selectionStart: start, selectionEnd: start + inner.length };
  }

  // Nothing selected: the word at the caret, or a placeholder to type over
  if (start === end) {
    const left = value.substring(0, start).match(/[\p{L}\p{N}_]+$/u)?.[0].length ?? 0;
    const right = value.substring(start).match(/^[\p{L}\p{N}_]+/u)?.[0].length ?? 0;
    if (left + right > 0) return toggleInline(value, start - left, start + right, format);
    const next = value.substring(0, start) + open + placeholder + close + value.substring(end);
    return { value: next, selectionStart: start + open.length, selectionEnd: start + open.length + placeholder.length };
  }

  // Across several lines: each line is formatted on its own (Markdown cannot span paragraphs)
  if (selected.includes('\n')) {
    const range = selectedLines(value, start, end);
    const lines = range.lines.map((line) => {
      const prefix = line.match(LIST_RE)?.[0] ?? line.match(HEADING_RE)?.[0] ?? line.match(QUOTE_RE)?.[0] ?? (line.match(/^\s*/)?.[0] ?? '');
      const body = line.substring(prefix.length);
      if (!body.trim()) return line;
      const trimmed = body.trimEnd();
      if (trimmed.startsWith(open) && trimmed.endsWith(close) && trimmed.length > open.length + close.length) {
        return prefix + trimmed.slice(open.length, trimmed.length - close.length) + body.substring(trimmed.length);
      }
      return prefix + open + trimmed + close + body.substring(trimmed.length);
    });
    return replaceLines(value, range, lines);
  }

  // Spaces at the edges of the selection stay outside the markers ("** text**" is not bold)
  const lead = selected.length - selected.trimStart().length;
  const trail = selected.length - selected.trimEnd().length;
  const s = start + lead;
  const e = end - trail;
  const next = value.substring(0, s) + open + value.substring(s, e) + close + value.substring(e);
  return { value: next, selectionStart: s + open.length, selectionEnd: e + open.length };
}

/** Text colour (an HTML span, which notebooks render) */
export function applyColor(value: string, start: number, end: number, color: string | null): TextEdit {
  const selected = value.substring(start, end);
  // Remove an existing colour around or inside the selection
  const around = /<span style="color:\s*[^"]*">$/.exec(value.substring(0, start));
  if (around && value.substring(end).startsWith('</span>')) {
    const s = start - around[0].length;
    const inner = value.substring(start, end);
    const wrapped = color ? `<span style="color: ${color}">${inner}</span>` : inner;
    const next = value.substring(0, s) + wrapped + value.substring(end + 7);
    const innerStart = color ? s + `<span style="color: ${color}">`.length : s;
    return { value: next, selectionStart: innerStart, selectionEnd: innerStart + inner.length };
  }
  const stripped = selected.replace(/<span style="color:\s*[^"]*">([\s\S]*?)<\/span>/g, '$1');
  if (!color) {
    const next = value.substring(0, start) + stripped + value.substring(end);
    return { value: next, selectionStart: start, selectionEnd: start + stripped.length };
  }
  const body = stripped || 'coloured text';
  const open = `<span style="color: ${color}">`;
  const next = value.substring(0, start) + open + body + '</span>' + value.substring(end);
  return { value: next, selectionStart: start + open.length, selectionEnd: start + open.length + body.length };
}

/** Heading 1-3 or normal text for the selected lines (toggles back to normal text) */
export function setBlock(value: string, start: number, end: number, block: BlockFormat): TextEdit {
  const range = selectedLines(value, start, end);
  const level = block === 'p' ? 0 : Number(block[1]);
  const allAlready = level > 0 && range.lines.every((l) => !l.trim() || (l.match(HEADING_RE)?.[2].length ?? 0) === level);
  const lines = range.lines.map((line) => {
    if (!line.trim()) return line;
    const indent = line.match(/^\s*/)?.[0] ?? '';
    let body = line.substring(indent.length).replace(/^#{1,6}\s+/, '').replace(/^>\s?/, '').replace(LIST_RE, '');
    body = body.replace(/^\s+/, '');
    if (level === 0 || allAlready) return body;
    return '#'.repeat(level) + ' ' + body;
  });
  return replaceLines(value, range, lines, start === end ? start : undefined);
}

/** Quote ("> ") the selected lines, or remove the quote */
export function toggleQuote(value: string, start: number, end: number): TextEdit {
  const range = selectedLines(value, start, end);
  const all = range.lines.every((l) => !l.trim() || QUOTE_RE.test(l));
  const lines = range.lines.map((l) => (all ? l.replace(QUOTE_RE, '$1') : l.trim() ? '> ' + l : l));
  const edit = replaceLines(value, range, lines, start === end ? start : undefined);
  if (all) return edit;
  return separateBlock(value, edit, range.from, range.from + lines.join('\n').length, (l) => QUOTE_RE.test(l));
}

/** Renumbers numbered list items from the first one, level by level (1. 2. 3. ...) */
function renumber(lines: string[], startAt = 1): string[] {
  const counters = new Map<number, number>();
  return lines.map((line) => {
    const m = line.match(/^(\s*)(\d+)([.)])(\s+)/);
    const indent = (line.match(/^\s*/)?.[0] ?? '').length;
    if (!line.trim()) return line;
    // A shallower line ends the deeper lists
    for (const level of [...counters.keys()]) if (level > indent) counters.delete(level);
    if (!m) {
      if (!LIST_RE.test(line)) counters.delete(indent);
      return line;
    }
    const n = counters.has(indent) ? counters.get(indent)! + 1 : indent === 0 ? startAt : 1;
    counters.set(indent, n);
    return m[1] + n + m[3] + m[4] + line.substring(m[0].length);
  });
}

/** Bulleted, numbered or checklist for the selected lines (toggles off when all already are) */
export function toggleList(value: string, start: number, end: number, kind: ListKind): TextEdit {
  const range = selectedLines(value, start, end);
  const isKind = (l: string) => {
    const marker = l.match(LIST_RE)?.[2] ?? '';
    if (kind === 'task') return /\[[ xX]\]/.test(marker);
    if (kind === 'number') return /^\d/.test(marker);
    return /^[-*+]\s+$/.test(marker) || (/^[-*+]/.test(marker) && !/\[/.test(marker));
  };
  const content = range.lines.filter((l) => l.trim());
  const remove = content.length > 0 && content.every(isKind);

  // Continue the numbering of a list just above the selection
  let startAt = 1;
  if (kind === 'number') {
    const before = value.substring(0, range.from).replace(/\n$/, '').split('\n');
    const prev = before[before.length - 1] ?? '';
    const m = prev.match(/^(\s*)(\d+)[.)]\s+/);
    if (m && m[1].length === 0) startAt = Number(m[2]) + 1;
  }
  let n = startAt;
  const lines = range.lines.map((line) => {
    if (!line.trim()) return line;
    const indent = line.match(/^\s*/)?.[0] ?? '';
    const body = line.substring(indent.length).replace(LIST_RE, '').replace(/^#{1,6}\s+/, '').replace(/^>\s?/, '');
    if (remove) return indent + body;
    const marker = kind === 'bullet' ? '- ' : kind === 'task' ? '- [ ] ' : `${n++}. `;
    return indent + marker + body;
  });
  const result = kind === 'number' && !remove ? renumber(lines, startAt) : lines;
  // One empty line with nothing selected: put the caret after the new marker
  if (start === end && range.lines.length === 1 && !range.lines[0].trim()) {
    const indent = range.lines[0];
    const marker = remove ? '' : kind === 'bullet' ? '- ' : kind === 'task' ? '- [ ] ' : `${startAt}. `;
    return replaceLines(value, range, [indent + marker], start);
  }
  const edit = replaceLines(value, range, result, start === end ? start : undefined);
  if (remove) return edit;
  return separateBlock(value, edit, range.from, range.from + result.join('\n').length, (l) => LIST_RE.test(l) || /^\s+\S/.test(l));
}

/** Indent (nest) or outdent the selected list lines by one level, renumbering numbered items */
export function shiftList(value: string, start: number, end: number, outdent: boolean): TextEdit {
  const range = selectedLines(value, start, end);
  const lines = range.lines.map((line) => {
    if (!line.trim()) return line;
    if (outdent) return line.replace(/^( {1,4}|\t)/, '');
    return '    ' + line;
  });
  // Renumber the whole list block around the selection so numbering stays right at every level
  const block = listBlock(value, range);
  const before = value.substring(block.from, range.from);
  const after = value.substring(range.to, block.to);
  const all = (before + lines.join('\n') + after).split('\n');
  const renumbered = renumber(all);
  const text = renumbered.join('\n');
  const next = value.substring(0, block.from) + text + value.substring(block.to);
  const selFrom = block.from + before.length;
  if (start === end && range.lines.length === 1) {
    const newLine = renumbered[before.split('\n').length - 1];
    const caret = Math.min(selFrom + newLine.length, Math.max(selFrom, start + (newLine.length - range.lines[0].length)));
    return { value: next, selectionStart: caret, selectionEnd: caret };
  }
  const selLen = renumbered.slice(before.split('\n').length - 1, before.split('\n').length - 1 + lines.length).join('\n').length;
  return { value: next, selectionStart: selFrom, selectionEnd: selFrom + selLen };
}

/** The contiguous list (lines that are list items or their continuation) around a range */
function listBlock(value: string, range: LineRange): { from: number; to: number } {
  let from = range.from;
  while (from > 0) {
    const prevStart = value.lastIndexOf('\n', from - 2) + 1;
    const prev = value.substring(prevStart, from - 1);
    if (!LIST_RE.test(prev) && !/^\s+\S/.test(prev)) break;
    from = prevStart;
  }
  let to = range.to;
  while (to < value.length) {
    const nl = value.indexOf('\n', to + 1);
    const nextEnd = nl === -1 ? value.length : nl;
    const next = value.substring(to + 1, nextEnd);
    if (!LIST_RE.test(next) && !/^\s+\S/.test(next)) break;
    to = nextEnd;
  }
  return { from, to };
}

/** True when the caret's line is a list item (Tab then nests it instead of inserting spaces) */
export function isListLine(value: string, pos: number): boolean {
  const from = value.lastIndexOf('\n', pos - 1) + 1;
  const nl = value.indexOf('\n', pos);
  return LIST_RE.test(value.substring(from, nl === -1 ? value.length : nl));
}

/**
 * Enter in a list or quote continues it ("- ", "2. ", "- [ ] ", "> "); Enter on an empty item ends
 * the list. Returns null when the caret is not in a list or quote.
 */
export function continueList(value: string, start: number, end: number): TextEdit | null {
  if (start !== end) return null;
  const from = value.lastIndexOf('\n', start - 1) + 1;
  const nl = value.indexOf('\n', start);
  const line = value.substring(from, nl === -1 ? value.length : nl);
  const list = line.match(/^(\s*)([-*+])(\s+)(\[[ xX]\]\s+)?/) ;
  const num = line.match(/^(\s*)(\d+)([.)])(\s+)/);
  const quote = line.match(/^(\s*>\s?)/);
  const marker = num?.[0] ?? list?.[0] ?? quote?.[0];
  if (!marker || start < from + marker.length) return null;
  // Empty item: end the list (remove the marker, leave an empty line)
  if (!line.substring(marker.length).trim()) {
    const next = value.substring(0, from) + value.substring(from + line.length);
    return { value: next, selectionStart: from, selectionEnd: from };
  }
  let nextMarker: string;
  if (num) nextMarker = `${num[1]}${Number(num[2]) + 1}${num[3]}${num[4]}`;
  else if (list) nextMarker = `${list[1]}${list[2]}${list[3]}${list[4] ? '[ ] ' : ''}`;
  else nextMarker = quote![1];
  let next = value.substring(0, start) + '\n' + nextMarker + value.substring(end);
  const caret = start + 1 + nextMarker.length;
  if (num) {
    // Renumber the following items of the same list (an item inserted in the middle shifts them)
    const newLineEnd = next.indexOf('\n', caret) === -1 ? next.length : next.indexOf('\n', caret);
    const block = listBlock(next, { from, to: newLineEnd, lines: [] });
    const text = renumber(next.substring(block.from, block.to).split('\n'), firstNumber(next, block.from)).join('\n');
    next = next.substring(0, block.from) + text + next.substring(block.to);
  }
  return { value: next, selectionStart: caret, selectionEnd: caret };
}

function firstNumber(value: string, from: number): number {
  const m = value.substring(from).match(/^\s*(\d+)[.)]\s+/);
  return m ? Number(m[1]) : 1;
}

/** Inserts text as its own block (blank lines around it), replacing the selection */
function insertBlock(value: string, start: number, end: number, block: string, selectFrom = 0, selectTo = block.length): TextEdit {
  const before = value.substring(0, start);
  const after = value.substring(end);
  const lead = before === '' ? '' : before.endsWith('\n\n') ? '' : before.endsWith('\n') ? '\n' : '\n\n';
  const trail = after === '' ? '' : after.startsWith('\n\n') ? '' : after.startsWith('\n') ? '\n' : '\n\n';
  const next = before + lead + block + trail + after;
  const base = start + lead.length;
  return { value: next, selectionStart: base + selectFrom, selectionEnd: base + selectTo };
}

/** A code block in a language, around the selected lines or with a placeholder */
export function insertCodeBlock(value: string, start: number, end: number, language: string): TextEdit {
  const selected = value.substring(start, end);
  const body = selected || 'code';
  const open = '```' + language + '\n';
  const block = open + body.replace(/\n$/, '') + '\n```';
  return insertBlock(value, start, end, block, open.length, open.length + body.replace(/\n$/, '').length);
}

/** Display maths ($$ ... $$) */
export function insertMathBlock(value: string, start: number, end: number): TextEdit {
  const body = value.substring(start, end) || 'E = mc^2';
  return insertBlock(value, start, end, `$$\n${body}\n$$`, 3, 3 + body.length);
}

/** A horizontal divider */
export function insertDivider(value: string, _start: number, end: number): TextEdit {
  const at = value.indexOf('\n', end) === -1 ? value.length : value.indexOf('\n', end);
  const r = insertBlock(value, at, at, '---');
  return { ...r, selectionStart: r.selectionEnd, selectionEnd: r.selectionEnd };
}

/** A link: [text](url) replacing the selection */
export function insertLink(value: string, start: number, end: number, text: string, url: string): TextEdit {
  const label = (text || url).replace(/([[\]])/g, '\\$1');
  const md = `[${label}](${encodeUrl(url)})`;
  const next = value.substring(0, start) + md + value.substring(end);
  return { value: next, selectionStart: start + md.length, selectionEnd: start + md.length };
}

/** An image: ![alt text](url) */
export function insertImage(value: string, start: number, end: number, alt: string, url: string): TextEdit {
  const md = `![${(alt || 'image').replace(/([[\]])/g, '\\$1')}](${encodeUrl(url)})`;
  const next = value.substring(0, start) + md + value.substring(end);
  return { value: next, selectionStart: start + md.length, selectionEnd: start + md.length };
}

/** The link around the caret, for editing it ([text](url) -> its parts and range) */
export function linkAt(value: string, pos: number): { from: number; to: number; text: string; url: string } | null {
  const re = /(?<!!)\[((?:\\.|[^\]])*)\]\(([^)\s]*)\)/g;
  for (const m of value.matchAll(re)) {
    const from = m.index ?? 0;
    const to = from + m[0].length;
    if (pos >= from && pos <= to) return { from, to, text: m[1].replace(/\\([[\]])/g, '$1'), url: m[2] };
  }
  return null;
}

// Spaces and parentheses would end the link early
const encodeUrl = (url: string) => url.trim().replace(/ /g, '%20').replace(/\(/g, '%28').replace(/\)/g, '%29');
