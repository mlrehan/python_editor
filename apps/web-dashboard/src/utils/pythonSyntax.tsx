import React from 'react';

/*
 * Python syntax highlighting for the textarea-based editors. The editor draws this layer underneath
 * a textarea whose own text is transparent, with identical font metrics, so the colours follow every
 * edit immediately (typing, paste, Ctrl+/, undo/redo). Tokens: comments, strings (incl. triple-quoted
 * across lines, prefixes such as f/r/b), numbers, keywords, builtins, constants, self/cls,
 * decorators, def/class names, calls, IPython magics (%, %%, !). Bracket pairs can be marked.
 */

export type TokenKind =
  | 'comment'
  | 'string'
  | 'number'
  | 'keyword'
  | 'builtin'
  | 'constant'
  | 'self'
  | 'decorator'
  | 'function'
  | 'class'
  | 'call'
  | 'magic'
  | 'operator'
  | 'bracket'
  | 'text';

interface Token {
  kind: TokenKind;
  start: number;
  end: number;
}

const KEYWORDS = new Set([
  'and', 'as', 'assert', 'async', 'await', 'break', 'class', 'continue', 'def', 'del', 'elif', 'else', 'except',
  'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is', 'lambda', 'nonlocal', 'not', 'or', 'pass',
  'raise', 'return', 'try', 'while', 'with', 'yield', 'match', 'case',
]);
const CONSTANTS = new Set(['True', 'False', 'None', 'NotImplemented', 'Ellipsis', '__name__', '__file__']);
const BUILTINS = new Set([
  'abs', 'all', 'any', 'ascii', 'bin', 'bool', 'breakpoint', 'bytearray', 'bytes', 'callable', 'chr', 'classmethod',
  'compile', 'complex', 'delattr', 'dict', 'dir', 'divmod', 'enumerate', 'eval', 'exec', 'filter', 'float', 'format',
  'frozenset', 'getattr', 'globals', 'hasattr', 'hash', 'help', 'hex', 'id', 'input', 'int', 'isinstance',
  'issubclass', 'iter', 'len', 'list', 'locals', 'map', 'max', 'memoryview', 'min', 'next', 'object', 'oct', 'open',
  'ord', 'pow', 'print', 'property', 'range', 'repr', 'reversed', 'round', 'set', 'setattr', 'slice', 'sorted',
  'staticmethod', 'str', 'sum', 'super', 'tuple', 'type', 'vars', 'zip', 'display',
  'Exception', 'ValueError', 'TypeError', 'KeyError', 'IndexError', 'AttributeError', 'RuntimeError',
  'ZeroDivisionError', 'ImportError', 'ModuleNotFoundError', 'FileNotFoundError', 'StopIteration', 'OSError',
  'NotImplementedError', 'AssertionError', 'KeyboardInterrupt', 'BaseException',
]);

// Sticky (y) patterns tried at the current position, in order
const RE_COMMENT = /#[^\n]*/y;
const RE_TRIPLE = /[rRbBuUfF]{0,2}("""|''')[\s\S]*?(?:\1|$)/y;
const RE_STRING = /[rRbBuUfF]{0,2}(["'])(?:\\[\s\S]|(?!\1)[^\\\n])*\1?/y;
const RE_NUMBER = /(?:0[xX][\da-fA-F_]+|0[bB][01_]+|0[oO][0-7_]+|(?:\d[\d_]*\.?[\d_]*|\.\d[\d_]*)(?:[eE][+-]?\d+)?[jJ]?)/y;
const RE_IDENT = /[A-Za-z_À-￿][\wÀ-￿]*/y;
const RE_DECORATOR = /@[A-Za-z_][\w.]*/y;
const RE_MAGIC = /(?:%%?|!)[^\n]*/y;
const RE_SPACE = /[ \t]+/y;
const RE_OPERATOR = /[-+*/%=<>!&|^~@:.,;]+/y;

function matchAt(re: RegExp, text: string, pos: number): number {
  re.lastIndex = pos;
  return re.test(text) ? re.lastIndex : -1;
}

export function tokenizePython(code: string): Token[] {
  const tokens: Token[] = [];
  let pos = 0;
  let lineStart = true; // only whitespace so far on this line
  let prevWord = '';
  const push = (kind: TokenKind, end: number) => {
    tokens.push({ kind, start: pos, end });
    pos = end;
  };
  while (pos < code.length) {
    const ch = code[pos];
    if (ch === '\n') {
      push('text', pos + 1);
      lineStart = true;
      continue;
    }
    let end = matchAt(RE_SPACE, code, pos);
    if (end > 0) {
      push('text', end);
      continue;
    }
    if (lineStart && (ch === '%' || ch === '!') && (end = matchAt(RE_MAGIC, code, pos)) > 0) {
      push('magic', end);
      continue;
    }
    if (lineStart && ch === '@' && (end = matchAt(RE_DECORATOR, code, pos)) > 0) {
      push('decorator', end);
      lineStart = false;
      continue;
    }
    lineStart = false;
    if (ch === '#') {
      push('comment', matchAt(RE_COMMENT, code, pos));
      continue;
    }
    if ((end = matchAt(RE_TRIPLE, code, pos)) > 0 || (end = matchAt(RE_STRING, code, pos)) > 0) {
      // A word starting with a string prefix letter (e.g. "for", "bar") is not a string
      const quote = code.slice(pos, end).search(/["']/);
      if (quote <= 2 && quote >= 0 && (quote === 0 || /^[rRbBuUfF]+$/.test(code.slice(pos, pos + quote)))) {
        push('string', end);
        prevWord = '';
        continue;
      }
    }
    if (/[0-9]/.test(ch) || (ch === '.' && /[0-9]/.test(code[pos + 1] || ''))) {
      end = matchAt(RE_NUMBER, code, pos);
      if (end > pos) {
        push('number', end);
        prevWord = '';
        continue;
      }
    }
    if ((end = matchAt(RE_IDENT, code, pos)) > 0) {
      const word = code.slice(pos, end);
      let kind: TokenKind = 'text';
      if (prevWord === 'def') kind = 'function';
      else if (prevWord === 'class') kind = 'class';
      else if (KEYWORDS.has(word)) kind = 'keyword';
      else if (CONSTANTS.has(word)) kind = 'constant';
      else if (word === 'self' || word === 'cls') kind = 'self';
      else if (BUILTINS.has(word) && code[pos - 1] !== '.') kind = 'builtin';
      else if (/^\s*\(/.test(code.slice(end, end + 8))) kind = 'call';
      push(kind, end);
      prevWord = word;
      continue;
    }
    if ('()[]{}'.includes(ch)) {
      push('bracket', pos + 1);
      prevWord = '';
      continue;
    }
    if ((end = matchAt(RE_OPERATOR, code, pos)) > 0) {
      push('operator', end);
      if (code.slice(tokens[tokens.length - 1].start, end) !== '.') prevWord = '';
      continue;
    }
    push('text', pos + 1);
  }
  return tokens;
}

const OPEN = '([{';
const CLOSE = ')]}';

/** Positions of the bracket at/before the cursor and its partner (outside strings and comments). */
export function findBracketPair(code: string, tokens: Token[], cursor: number): [number, number] | null {
  const bracketAt = (i: number) => tokens.find((t) => t.kind === 'bracket' && t.start === i);
  const candidates = [cursor - 1, cursor];
  for (const i of candidates) {
    if (i < 0 || i >= code.length || !bracketAt(i)) continue;
    const ch = code[i];
    const open = OPEN.indexOf(ch);
    const close = CLOSE.indexOf(ch);
    const brackets = tokens.filter((t) => t.kind === 'bracket');
    const idx = brackets.findIndex((t) => t.start === i);
    let depth = 0;
    if (open >= 0) {
      for (let k = idx; k < brackets.length; k++) {
        const c = code[brackets[k].start];
        if (c === OPEN[open]) depth++;
        else if (c === CLOSE[open] && --depth === 0) return [i, brackets[k].start];
      }
    } else if (close >= 0) {
      for (let k = idx; k >= 0; k--) {
        const c = code[brackets[k].start];
        if (c === CLOSE[close]) depth++;
        else if (c === OPEN[close] && --depth === 0) return [brackets[k].start, i];
      }
    }
    return null;
  }
  return null;
}

/**
 * Highlighted lines (one element per source line, matching the textarea's line boxes).
 * `marks` are character positions to outline (matching brackets).
 */
export function renderHighlightedLines(code: string, tokens: Token[], marks: number[] = [], lineHeight?: string): React.ReactNode[] {
  const lines: React.ReactNode[][] = [[]];
  let key = 0;
  const markSet = new Set(marks);
  const emit = (kind: TokenKind, text: string, start: number) => {
    // Split at newlines (strings and comments can span lines) and at marked positions
    let offset = 0;
    for (const part of text.split('\n')) {
      if (offset > 0) lines.push([]);
      const current = lines[lines.length - 1];
      const partStart = start + offset;
      let i = 0;
      while (i < part.length) {
        const markIdx = [...markSet].filter((m) => m >= partStart + i && m < partStart + part.length).sort((a, b) => a - b)[0];
        if (markIdx === undefined) {
          current.push(kind === 'text' ? part.slice(i) : <span key={key++} className={`tok-${kind}`}>{part.slice(i)}</span>);
          break;
        }
        const rel = markIdx - partStart;
        if (rel > i) current.push(kind === 'text' ? part.slice(i, rel) : <span key={key++} className={`tok-${kind}`}>{part.slice(i, rel)}</span>);
        current.push(<span key={key++} className={`tok-${kind} tok-bracket-match`}>{part[rel]}</span>);
        i = rel + 1;
      }
      offset += part.length + 1;
    }
  };
  for (const t of tokens) emit(t.kind, code.slice(t.start, t.end), t.start);
  return lines.map((parts, i) => (
    <div key={i} style={lineHeight ? { height: lineHeight } : undefined}>
      {parts.length ? parts : ' '}
    </div>
  ));
}
