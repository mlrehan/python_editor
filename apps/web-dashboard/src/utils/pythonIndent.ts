import { TextEdit } from './lineComments';

/**
 * Python-aware Enter, Backspace and ":" for a plain <textarea>, matching VS Code / PyCharm:
 *  - Enter keeps the statement's indentation, adds a level after a line ending in ":", continues
 *    inside open brackets (hanging indent, or aligned with the bracket's first argument), splits
 *    an empty bracket pair onto three lines, and dedents after return / pass / break / continue / raise.
 *  - Backspace in leading whitespace deletes back to the previous 4-space stop; between an empty
 *    pair such as "()" it deletes both characters. Anywhere else it is the normal Backspace.
 *  - Typing ":" after else / elif / except / finally moves the line to its "if" / "try" level.
 * All functions are pure: they return the new text and selection, or null for the default behaviour.
 */

export const INDENT_SIZE = 4;
const INDENT = ' '.repeat(INDENT_SIZE);

const OPENERS: Record<string, string> = { '(': ')', '[': ']', '{': '}' };
const CLOSERS: Record<string, string> = { ')': '(', ']': '[', '}': '{' };

interface OpenBracket {
  char: string;
  /** Offset of the bracket in the text */
  pos: number;
  /** Indentation (spaces) of the line holding the bracket */
  lineIndent: number;
  /** Column of the bracket in its line */
  col: number;
  /** Whether code follows the bracket on its own line */
  contentAfter: boolean;
}

interface ScanResult {
  stack: OpenBracket[];
  /** The cursor is inside a (triple-quoted) string */
  inString: boolean;
  /** Offset of the first line of the statement the cursor is in */
  statementStart: number;
}

const lineStartOf = (text: string, pos: number) => text.lastIndexOf('\n', pos - 1) + 1;
const indentOf = (line: string) => (line.match(/^[ \t]*/)?.[0] ?? '').replace(/\t/g, INDENT).length;

/** Tracks brackets, strings and comments from the start of the cell up to `end`. */
function scan(text: string, end: number): ScanResult {
  const stack: OpenBracket[] = [];
  let quote: string | null = null; // ', ", ''' or """
  let statementStart = 0;
  let lineStart = 0;
  let i = 0;
  while (i < end) {
    const ch = text[i];
    if (quote) {
      if (ch === '\\') {
        i += 2;
        continue;
      }
      if (text.startsWith(quote, i)) {
        i += quote.length;
        quote = null;
        continue;
      }
      if (ch === '\n') {
        lineStart = i + 1;
        if (quote.length === 1) quote = null; // unterminated one-line string ends at the line
      }
      i++;
      continue;
    }
    if (ch === '#') {
      const nl = text.indexOf('\n', i);
      i = nl === -1 || nl > end ? end : nl;
      continue;
    }
    if (ch === '"' || ch === "'") {
      quote = text.startsWith(ch.repeat(3), i) ? ch.repeat(3) : ch;
      i += quote.length;
      continue;
    }
    if (ch === '\n') {
      lineStart = i + 1;
      // A new statement starts on a line that is not inside brackets or after a backslash
      if (stack.length === 0 && text[i - 1] !== '\\') statementStart = lineStart;
      i++;
      continue;
    }
    if (OPENERS[ch]) {
      const lineEnd = text.indexOf('\n', i);
      const rest = text.substring(i + 1, lineEnd === -1 || lineEnd > end ? end : lineEnd);
      stack.push({
        char: ch,
        pos: i,
        lineIndent: indentOf(text.substring(lineStart, i)),
        col: i - lineStart,
        contentAfter: rest.replace(/#.*$/, '').trim().length > 0,
      });
    } else if (CLOSERS[ch] && stack.length && stack[stack.length - 1].char === CLOSERS[ch]) {
      stack.pop();
    }
    i++;
  }
  return { stack, inString: quote !== null && quote.length === 3, statementStart };
}

/** Enter: a new line with the indentation Python expects. */
export function smartEnter(value: string, selectionStart: number, selectionEnd: number): TextEdit {
  const start = Math.min(selectionStart, selectionEnd);
  const end = Math.max(selectionStart, selectionEnd);
  const lineStart = lineStartOf(value, start);
  const before = value.substring(lineStart, start);
  const lineEnd = value.indexOf('\n', end);
  const after = value.substring(end, lineEnd === -1 ? value.length : lineEnd);
  const { stack, inString, statementStart } = scan(value, start);

  const insert = (text: string, caretOffset = text.length, trimAfter = true): TextEdit => {
    // Spaces between the caret and the rest of the line would land in front of the new indentation
    const skip = trimAfter ? (after.match(/^[ \t]*/)?.[0].length ?? 0) : 0;
    const next = value.substring(0, start) + text + value.substring(end + skip);
    const caret = start + caretOffset;
    return { value: next, selectionStart: caret, selectionEnd: caret };
  };

  // Caret in the leading whitespace: keep exactly that much indentation
  if (/^[ \t]*$/.test(before)) return insert('\n' + before, undefined, false);
  // Inside a docstring / triple-quoted string: keep the line's indentation
  if (inString) return insert('\n' + ' '.repeat(indentOf(before)), undefined, false);

  const top = stack[stack.length - 1];
  if (top) {
    const closer = OPENERS[top.char];
    const opensHere = value.substring(top.pos + 1, start).trim() === '';
    const closesNext = after.trimStart().startsWith(closer);
    if (opensHere && closesNext) {
      // f(|)  ->  f(\n    |\n)
      const inner = '\n' + ' '.repeat(top.lineIndent + INDENT_SIZE);
      return insert(inner + '\n' + ' '.repeat(top.lineIndent), inner.length);
    }
    if (closesNext) return insert('\n' + ' '.repeat(top.lineIndent));
    if (!top.contentAfter) return insert('\n' + ' '.repeat(top.lineIndent + INDENT_SIZE));
    // Aligned with the first argument (PEP 8 visual indent)
    return insert('\n' + ' '.repeat(top.col + 1));
  }

  const statementLine = value.substring(statementStart, value.indexOf('\n', statementStart) === -1 ? value.length : value.indexOf('\n', statementStart));
  let indent = indentOf(statementLine);
  const code = before.replace(/#.*$/, '').trimEnd();
  if (code.endsWith(':')) {
    indent += INDENT_SIZE;
  } else if (code.endsWith('\\')) {
    indent = indentOf(before) + (statementStart === lineStart ? INDENT_SIZE : 0);
  } else if (/^\s*(return|pass|break|continue|raise)\b/.test(statementLine) && after.trim() === '') {
    indent = Math.max(0, indent - INDENT_SIZE);
  }
  return insert('\n' + ' '.repeat(indent));
}

/** Backspace: to the previous indentation stop in leading spaces; both halves of an empty pair. */
export function smartBackspace(value: string, selectionStart: number, selectionEnd: number): TextEdit | null {
  if (selectionStart !== selectionEnd || selectionStart === 0) return null;
  const pos = selectionStart;
  const lineStart = lineStartOf(value, pos);
  const before = value.substring(lineStart, pos);
  if (before.length > 0 && /^ +$/.test(before)) {
    const target = lineStart + Math.floor((before.length - 1) / INDENT_SIZE) * INDENT_SIZE;
    return { value: value.substring(0, target) + value.substring(pos), selectionStart: target, selectionEnd: target };
  }
  const pairs: Record<string, string> = { '(': ')', '[': ']', '{': '}', '"': '"', "'": "'" };
  const prev = value[pos - 1];
  if (pairs[prev] && value[pos] === pairs[prev]) {
    // Not for the last quote of a string such as 'abc'| -> only when the pair was just opened
    if ((prev === '"' || prev === "'") && /\w/.test(value[pos - 2] ?? '')) return null;
    return { value: value.substring(0, pos - 1) + value.substring(pos + 1), selectionStart: pos - 1, selectionEnd: pos - 1 };
  }
  return null;
}

const DEDENT_OPENERS: Record<string, RegExp> = {
  else: /^(if|elif|for|while|try|except|async\s+for)\b/,
  elif: /^(if|elif)\b/,
  except: /^(try|except)\b/,
  finally: /^(try|except|else)\b/,
};

/** ":" after else / elif / except / finally: the line moves to the level of its if / try. */
export function electricColon(value: string, selectionStart: number, selectionEnd: number): TextEdit | null {
  if (selectionStart !== selectionEnd) return null;
  const pos = selectionStart;
  const lineStart = lineStartOf(value, pos);
  const lineEnd = value.indexOf('\n', pos);
  if (value.substring(pos, lineEnd === -1 ? value.length : lineEnd).trim() !== '') return null;
  const before = value.substring(lineStart, pos);
  const keyword = before.trim().match(/^(else|elif|except|finally)\b/)?.[1];
  if (!keyword || (keyword === 'else' || keyword === 'finally' ? before.trim() !== keyword : false)) return null;
  const current = indentOf(before);
  if (current === 0) return null;

  // Walk up: skip the block's body; the first line at a lower level must be the matching statement
  let target: number | null = null;
  let cursor = lineStart - 1;
  while (cursor > 0) {
    const prevStart = lineStartOf(value, cursor);
    const line = value.substring(prevStart, cursor);
    cursor = prevStart - 1;
    const stripped = line.trim();
    if (!stripped || stripped.startsWith('#')) continue;
    const level = indentOf(line);
    if (level === current && DEDENT_OPENERS[keyword].test(stripped)) return null; // already aligned
    if (level < current) {
      if (DEDENT_OPENERS[keyword].test(stripped)) target = level;
      break;
    }
  }
  if (target === null || target >= current) return null;
  const newLine = ' '.repeat(target) + before.trimStart() + ':';
  const next = value.substring(0, lineStart) + newLine + value.substring(pos);
  const caret = lineStart + newLine.length;
  return { value: next, selectionStart: caret, selectionEnd: caret };
}
