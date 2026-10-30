import React from 'react';

/*
 * Terminal text for notebook outputs: ANSI SGR colours (IPython tracebacks, pip, coloured logs) become
 * styled spans, other escape sequences are dropped, and carriage returns overwrite the current line
 * the way a terminal does (tqdm and pip progress bars).
 */

const COLORS = ['#475569', '#ef4444', '#22c55e', '#eab308', '#3b82f6', '#a855f7', '#06b6d4', '#cbd5e1'];
const BRIGHT = ['#64748b', '#f87171', '#4ade80', '#facc15', '#60a5fa', '#c084fc', '#22d3ee', '#f8fafc'];

interface Style {
  color?: string;
  background?: string;
  bold?: boolean;
  italic?: boolean;
  underline?: boolean;
}

// eslint-disable-next-line no-control-regex
const ESCAPE = /\x1b\[([\d;]*)([A-Za-z])|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[()][\w]/g;

function color256(n: number): string | undefined {
  if (n < 8) return COLORS[n];
  if (n < 16) return BRIGHT[n - 8];
  if (n < 232) {
    const v = n - 16;
    const c = (x: number) => (x === 0 ? 0 : 55 + x * 40);
    return `rgb(${c(Math.floor(v / 36))},${c(Math.floor(v / 6) % 6)},${c(v % 6)})`;
  }
  const g = 8 + (n - 232) * 10;
  return `rgb(${g},${g},${g})`;
}

function applySgr(params: number[], style: Style): Style {
  const next = { ...style };
  for (let i = 0; i < params.length; i++) {
    const p = params[i];
    if (p === 0) {
      Object.keys(next).forEach((k) => delete (next as Record<string, unknown>)[k]);
    } else if (p === 1) next.bold = true;
    else if (p === 3) next.italic = true;
    else if (p === 4) next.underline = true;
    else if (p === 22) next.bold = false;
    else if (p === 23) next.italic = false;
    else if (p === 24) next.underline = false;
    else if (p >= 30 && p <= 37) next.color = COLORS[p - 30];
    else if (p >= 90 && p <= 97) next.color = BRIGHT[p - 90];
    else if (p === 39) delete next.color;
    else if (p >= 40 && p <= 47) next.background = COLORS[p - 40];
    else if (p >= 100 && p <= 107) next.background = BRIGHT[p - 100];
    else if (p === 49) delete next.background;
    else if ((p === 38 || p === 48) && params[i + 1] === 5) {
      const c = color256(params[i + 2] ?? 0);
      if (p === 38) next.color = c;
      else next.background = c;
      i += 2;
    } else if ((p === 38 || p === 48) && params[i + 1] === 2) {
      const c = `rgb(${params[i + 2] ?? 0},${params[i + 3] ?? 0},${params[i + 4] ?? 0})`;
      if (p === 38) next.color = c;
      else next.background = c;
      i += 4;
    }
  }
  return next;
}

/** A carriage return (not part of \r\n) restarts the line: keep only what was written after it. */
export function applyCarriageReturns(text: string): string {
  if (!text.includes('\r')) return text;
  return text
    .replace(/\r\n/g, '\n')
    .split('\n')
    .map((line) => {
      const parts = line.split('\r');
      // A trailing \r (progress bar about to redraw) keeps the last complete content
      for (let i = parts.length - 1; i >= 0; i--) if (parts[i]) return parts[i];
      return '';
    })
    .join('\n');
}

export function stripAnsi(text: string): string {
  return text.replace(ESCAPE, '');
}

export function renderAnsi(text: string): React.ReactNode[] {
  const source = applyCarriageReturns(text);
  const nodes: React.ReactNode[] = [];
  let style: Style = {};
  let last = 0;
  let key = 0;
  const push = (chunk: string) => {
    if (!chunk) return;
    if (!style.color && !style.background && !style.bold && !style.italic && !style.underline) {
      nodes.push(chunk);
      return;
    }
    nodes.push(
      <span
        key={key++}
        style={{
          color: style.color,
          backgroundColor: style.background,
          fontWeight: style.bold ? 700 : undefined,
          fontStyle: style.italic ? 'italic' : undefined,
          textDecoration: style.underline ? 'underline' : undefined,
        }}
      >
        {chunk}
      </span>
    );
  };
  ESCAPE.lastIndex = 0;
  let m: RegExpExecArray | null;
  while ((m = ESCAPE.exec(source))) {
    push(source.slice(last, m.index));
    last = m.index + m[0].length;
    if (m[2] === 'm') {
      const params = (m[1] || '0').split(';').map((x) => parseInt(x || '0', 10));
      style = applySgr(params, style);
    }
  }
  push(source.slice(last));
  return nodes;
}
