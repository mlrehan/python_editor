import { stripAnsi } from './ansi';

/**
 * Source locations in a Python / IPython traceback, so the notebook can mark the failing line and
 * link each location to its cell or file.
 *
 * IPython 8+ writes notebook cells as "Cell In[3], line 5" and files as "File /path/to/x.py:12, in f()";
 * plain Python (and SyntaxErrors from %run) writes 'File "/path/to/x.py", line 12'.
 */
export interface TracebackLocation {
  kind: 'cell' | 'file';
  /** The cell's execution number, for kind "cell" */
  executionCount?: number;
  /** Path relative to the workspace, for kind "file" inside the workspace */
  path?: string;
  /** The path as the traceback shows it */
  rawPath?: string;
  line: number;
  /** Function name, when the traceback gives one */
  scope?: string;
}

// .../workspaces/guests/<id>/rest, .../workspaces/user_<id>/<project>/rest, .../workspaces/public/rest
const WORKSPACE_PREFIX = /[\\/]workspaces[\\/](?:guests[\\/][0-9a-f]{32}|user_[^\\/]+[\\/][^\\/]+|public)[\\/](.+)$/;

/** The workspace-relative path for a path in a traceback, or null for files outside the workspace. */
export function workspaceRelativePath(rawPath: string): string | null {
  const m = rawPath.match(WORKSPACE_PREFIX);
  if (m) return m[1].replace(/\\/g, '/');
  // Already relative (e.g. %run my_script.py) and not a library or interpreter location
  if (!/^([a-zA-Z]:)?[\\/]|^~|^</.test(rawPath) && !/site-packages|dist-packages/.test(rawPath)) {
    return rawPath.replace(/\\/g, '/').replace(/^\.\//, '');
  }
  return null;
}

export function parseTraceback(traceback: string[] | string): TracebackLocation[] {
  const text = stripAnsi(Array.isArray(traceback) ? traceback.join('\n') : traceback);
  const found: Array<TracebackLocation & { at: number }> = [];

  for (const m of text.matchAll(/Cell In\s*\[(\d+)\],\s*line (\d+)(?:,\s*in ([\w<>.]+))?/g)) {
    found.push({ kind: 'cell', executionCount: Number(m[1]), line: Number(m[2]), scope: m[3], at: m.index ?? 0 });
  }
  // File "path", line N[, in scope]
  for (const m of text.matchAll(/File "([^"\n]+)", line (\d+)(?:, in ([\w<>.]+))?/g)) {
    if (m[1].startsWith('<ipython-input')) continue;
    found.push({ kind: 'file', rawPath: m[1], path: workspaceRelativePath(m[1]) ?? undefined, line: Number(m[2]), scope: m[3], at: m.index ?? 0 });
  }
  // File path:N[, in scope(args)]  (IPython 8+; the scope shows the function's arguments)
  for (const m of text.matchAll(/^\s*File (?!")(.+?):(\d+)(?:, in ([\w<>.]+)(?:\(.*\))?)?\s*$/gm)) {
    found.push({ kind: 'file', rawPath: m[1].trim(), path: workspaceRelativePath(m[1].trim()) ?? undefined, line: Number(m[2]), scope: m[3], at: m.index ?? 0 });
  }
  return found.sort((a, b) => a.at - b.at).map(({ at: _at, ...loc }) => loc);
}

/**
 * The line of `executionCount`'s cell where the error happened: the innermost frame in that cell
 * (an error raised inside a function defined in the same cell points at the function's line).
 */
export function errorLineInCell(locations: TracebackLocation[], executionCount: number | null | undefined): number | null {
  const own = locations.filter((l) => l.kind === 'cell' && (executionCount == null || l.executionCount === executionCount));
  if (own.length) return own[own.length - 1].line;
  // Without the execution number: only when every cell frame names the same cell
  const cells = locations.filter((l) => l.kind === 'cell');
  if (cells.length && cells.every((c) => c.executionCount === cells[0].executionCount) && executionCount == null) {
    return cells[cells.length - 1].line;
  }
  return null;
}
