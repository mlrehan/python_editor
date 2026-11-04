import { useSyncExternalStore } from 'react';

/**
 * Editor typography shared by notebook cells, Markdown cells and the file editor.
 * JetBrains Mono is bundled with the app (self-hosted, so the Content-Security-Policy allows it);
 * the fallbacks are the platforms' own coding fonts.
 */
export const CODE_FONT_FAMILY =
  "'JetBrains Mono Variable', 'JetBrains Mono', ui-monospace, 'Cascadia Code', 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace";

export const DEFAULT_FONT_SIZE = 14;
export const MIN_FONT_SIZE = 11;
export const MAX_FONT_SIZE = 22;
const STORAGE_KEY = 'pcs_editor_font_size';

/** Line height for a font size: about 1.6, rounded to whole pixels so text layers line up exactly. */
export const lineHeightFor = (fontSize: number) => Math.round(fontSize * 1.6);

const clamp = (n: number) => Math.min(MAX_FONT_SIZE, Math.max(MIN_FONT_SIZE, Math.round(n)));

function readStored(): number {
  try {
    const n = Number(localStorage.getItem(STORAGE_KEY));
    return Number.isFinite(n) && n > 0 ? clamp(n) : DEFAULT_FONT_SIZE;
  } catch {
    return DEFAULT_FONT_SIZE;
  }
}

let fontSize = readStored();
const listeners = new Set<() => void>();

function applyCssVariables() {
  if (typeof document === 'undefined') return;
  const root = document.documentElement.style;
  root.setProperty('--code-font-family', CODE_FONT_FAMILY);
  root.setProperty('--code-font-size', `${fontSize}px`);
  root.setProperty('--code-line-height', `${lineHeightFor(fontSize)}px`);
}
applyCssVariables();

export function setEditorFontSize(next: number): void {
  const value = clamp(next);
  if (value === fontSize) return;
  fontSize = value;
  try {
    if (value === DEFAULT_FONT_SIZE) localStorage.removeItem(STORAGE_KEY);
    else localStorage.setItem(STORAGE_KEY, String(value));
  } catch {
    /* private mode: the choice lasts for this page */
  }
  applyCssVariables();
  listeners.forEach((l) => l());
}

export function getEditorFontSize(): number {
  return fontSize;
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** The current editor font size and its line height; components re-render when it changes. */
export function useEditorFont(): { fontSize: number; lineHeight: number } {
  const size = useSyncExternalStore(subscribe, getEditorFontSize, getEditorFontSize);
  return { fontSize: size, lineHeight: lineHeightFor(size) };
}
