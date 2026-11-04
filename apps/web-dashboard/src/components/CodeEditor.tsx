import React, { useEffect, useRef } from 'react';
import { EditorState, Extension, Transaction, Annotation, Prec } from '@codemirror/state';
import {
  EditorView,
  Command,
  keymap,
  lineNumbers,
  highlightActiveLineGutter,
  highlightSpecialChars,
  drawSelection,
  dropCursor,
  rectangularSelection,
  crosshairCursor,
  highlightActiveLine,
} from '@codemirror/view';
import { defaultKeymap, history, historyKeymap, indentWithTab, isolateHistory, redo, toggleComment } from '@codemirror/commands';
import {
  indentOnInput,
  indentUnit,
  bracketMatching,
  foldGutter,
  foldKeymap,
  syntaxHighlighting,
  HighlightStyle,
} from '@codemirror/language';
import { python } from '@codemirror/lang-python';
import { json } from '@codemirror/lang-json';
import { markdown } from '@codemirror/lang-markdown';
import { searchKeymap, highlightSelectionMatches } from '@codemirror/search';
import {
  autocompletion,
  completionKeymap,
  closeBrackets,
  closeBracketsKeymap,
  CompletionContext,
  CompletionResult,
  completionStatus,
} from '@codemirror/autocomplete';
import { linter, lintGutter, lintKeymap, Diagnostic } from '@codemirror/lint';
import { tags } from '@lezer/highlight';
import { api } from '../services/api';
import { smartEnter } from '../utils/pythonIndent';

/*
 * VS Code-style code editor (CodeMirror 6) for workspace files.
 *
 * One EditorView is reused; every open file has its own EditorState in `states`, so switching tabs
 * keeps each file's undo history, selection, folded regions and scroll position. Python files get
 * IntelliSense (/editor/complete) and live diagnostics (/editor/diagnostics), the same services the
 * notebook cells use.
 */

export interface StoredEditorState {
  state: EditorState;
  scrollTop: number;
  scrollLeft: number;
}

interface CodeEditorProps {
  path: string;
  value: string;
  onChange: (value: string) => void;
  /** Per-file editor states, owned by the caller so they outlive tab switches */
  states: Map<string, StoredEditorState>;
  /** Moves the caret to this line and scrolls to it (e.g. a traceback location); `nonce` repeats it */
  reveal?: { line: number; nonce: number };
}

// Marks changes that came from outside (props), so they are not echoed back through onChange
const External = Annotation.define<boolean>();

const highlightStyle = HighlightStyle.define([
  { tag: [tags.keyword, tags.controlKeyword, tags.operatorKeyword, tags.definitionKeyword, tags.moduleKeyword], color: 'var(--syn-keyword)' },
  { tag: [tags.comment, tags.lineComment, tags.blockComment], color: 'var(--syn-comment)', fontStyle: 'italic' },
  { tag: [tags.string, tags.special(tags.string), tags.docString], color: 'var(--syn-string)' },
  { tag: [tags.number, tags.integer, tags.float], color: 'var(--syn-number)' },
  { tag: [tags.bool, tags.null, tags.atom], color: 'var(--syn-constant)' },
  { tag: tags.self, color: 'var(--syn-self)', fontStyle: 'italic' },
  { tag: [tags.function(tags.definition(tags.variableName)), tags.function(tags.variableName), tags.function(tags.propertyName)], color: 'var(--syn-function)' },
  { tag: [tags.className, tags.definition(tags.className), tags.typeName], color: 'var(--syn-class)' },
  { tag: [tags.meta, tags.annotation], color: 'var(--syn-decorator)' },
  { tag: [tags.operator, tags.compareOperator, tags.arithmeticOperator, tags.logicOperator], color: 'var(--syn-operator)' },
  { tag: [tags.heading, tags.strong], fontWeight: '700', color: 'var(--syn-keyword)' },
  { tag: tags.emphasis, fontStyle: 'italic' },
  { tag: [tags.link, tags.url], color: 'var(--syn-string)', textDecoration: 'underline' },
  { tag: tags.propertyName, color: 'var(--syn-self)' },
]);

const editorTheme = EditorView.theme({
  '&': {
    height: '100%',
    fontSize: 'var(--code-font-size, 14px)',
    color: 'var(--code-text)',
    backgroundColor: 'var(--bg-panel)',
  },
  '.cm-scroller': {
    fontFamily: 'var(--code-font-family)',
    lineHeight: 'var(--code-line-height, 22px)',
    overscrollBehavior: 'contain',
  },
  '.cm-content': { padding: '8px 0', caretColor: 'var(--border-accent)' },
  '.cm-line': { padding: '0 12px 0 6px' },
  '.cm-gutters': {
    backgroundColor: 'var(--bg-cell-gutter)',
    color: 'var(--text-muted)',
    borderRight: '1px solid var(--border-main)',
  },
  '.cm-lineNumbers .cm-gutterElement': { padding: '0 6px 0 10px', minWidth: '28px' },
  '.cm-activeLine': { backgroundColor: 'var(--cm-active-line)' },
  '.cm-activeLineGutter': { backgroundColor: 'var(--cm-active-line)', color: 'var(--text-main)' },
  '&.cm-focused': { outline: 'none' },
  '&.cm-focused .cm-cursor': { borderLeftColor: 'var(--border-accent)', borderLeftWidth: '2px' },
  '.cm-selectionBackground, &.cm-focused > .cm-scroller > .cm-selectionLayer .cm-selectionBackground': {
    backgroundColor: 'var(--editor-selection)',
  },
  '.cm-selectionMatch': { backgroundColor: 'var(--cm-selection-match)' },
  // Subtle grey box (as in VS Code) so the caret stays visible next to and between brackets
  '&.cm-focused .cm-matchingBracket': { backgroundColor: 'var(--syn-bracket-match-bg)', boxShadow: 'inset 0 0 0 1px var(--syn-bracket-match-border)' },
  '&.cm-focused .cm-nonmatchingBracket': { backgroundColor: 'var(--status-danger-bg)' },
  '.cm-foldGutter .cm-gutterElement': { padding: '0 4px', cursor: 'pointer' },
  '.cm-foldPlaceholder': { backgroundColor: 'var(--bg-hover)', border: '1px solid var(--border-secondary)', color: 'var(--text-secondary)' },
  '.cm-tooltip': {
    backgroundColor: 'var(--dropdown-bg)',
    border: '1px solid var(--dropdown-border)',
    color: 'var(--text-main)',
    borderRadius: '6px',
    boxShadow: 'var(--shadow-popover)',
  },
  '.cm-tooltip.cm-tooltip-autocomplete > ul': { fontFamily: 'var(--code-font-family)', maxHeight: '260px' },
  '.cm-tooltip.cm-tooltip-autocomplete > ul > li': { padding: '3px 8px' },
  '.cm-tooltip.cm-tooltip-autocomplete > ul > li[aria-selected]': {
    backgroundColor: 'var(--dropdown-item-selected)',
    color: 'var(--dropdown-item-selected-text)',
  },
  '.cm-completionDetail': { color: 'var(--text-muted)', fontStyle: 'normal', marginLeft: '8px' },
  '.cm-completionInfo': { maxWidth: '360px', whiteSpace: 'pre-wrap', fontSize: '12px' },
  '.cm-panels': { backgroundColor: 'var(--bg-sidebar-header)', color: 'var(--text-main)' },
  '.cm-panels.cm-panels-top': { borderBottom: '1px solid var(--border-main)' },
  '.cm-search': { fontSize: '12.5px', padding: '6px 8px' },
  '.cm-search input, .cm-search button, .cm-textfield, .cm-button': {
    backgroundColor: 'var(--bg-input)',
    backgroundImage: 'none',
    border: '1px solid var(--border-secondary)',
    color: 'var(--text-main)',
    borderRadius: '4px',
  },
  '.cm-searchMatch': { backgroundColor: 'var(--cm-search-match)', outline: '1px solid var(--cm-search-match-border)' },
  '.cm-searchMatch.cm-searchMatch-selected': { backgroundColor: 'var(--cm-search-match-selected)' },
  '.cm-lintRange-error': { backgroundImage: 'none', textDecoration: 'underline wavy #ef4444', textUnderlineOffset: '3px' },
  '.cm-lintRange-warning': { backgroundImage: 'none', textDecoration: 'underline wavy #f59e0b', textUnderlineOffset: '3px' },
  '.cm-diagnostic': { padding: '4px 8px' },
  '.cm-gutter-lint': { width: '14px' },
});

function languageFor(path: string): Extension[] {
  const ext = path.split('.').pop()?.toLowerCase() || '';
  if (ext === 'py' || ext === 'pyw' || ext === 'pyi') return [python(), pythonIntelligence(), Prec.high(keymap.of([{ key: 'Enter', run: pythonEnter }]))];
  if (ext === 'json' || ext === 'ipynb') return [json()];
  if (ext === 'md' || ext === 'markdown') return [markdown()];
  return [];
}

// Enter in Python files: the same indentation rules as notebook cells (blocks, brackets, dedent after
// return / pass / break...). An open suggestion list keeps Enter for accepting the suggestion.
const pythonEnter: Command = (view) => {
  const { state } = view;
  if (completionStatus(state) === 'active' || state.selection.ranges.length !== 1 || state.readOnly) return false;
  const { from, to } = state.selection.main;
  const doc = state.doc.toString();
  const edit = smartEnter(doc, from, to);
  // Only the changed span is replaced, so undo and other extensions see a minimal edit
  let start = 0;
  while (start < doc.length && start < edit.value.length && doc[start] === edit.value[start]) start++;
  let endOld = doc.length;
  let endNew = edit.value.length;
  while (endOld > start && endNew > start && doc[endOld - 1] === edit.value[endNew - 1]) {
    endOld--;
    endNew--;
  }
  view.dispatch({
    changes: { from: start, to: endOld, insert: edit.value.slice(start, endNew) },
    selection: { anchor: edit.selectionStart },
    scrollIntoView: true,
    userEvent: 'input',
  });
  return true;
};

// IntelliSense and diagnostics for Python files, from the backend language service
function pythonIntelligence(): Extension[] {
  const complete = async (context: CompletionContext): Promise<CompletionResult | null> => {
    const word = context.matchBefore(/[\w.]*/);
    if (!word) return null;
    const afterDot = word.text.includes('.');
    if (!context.explicit && word.from === word.to) return null;
    if (!context.explicit && !afterDot && word.text.length < 1) return null;
    const line = context.state.doc.lineAt(context.pos);
    try {
      const res = await api.getCompletions(context.state.doc.toString(), line.number, context.pos - line.from);
      if (context.aborted) return null;
      const from = afterDot ? word.from + word.text.lastIndexOf('.') + 1 : word.from;
      return {
        from,
        options: res.completions.map((c) => ({
          label: c.label,
          type: c.type === 'module' ? 'namespace' : c.type === 'instance' || c.type === 'statement' ? 'variable' : c.type,
          detail: c.detail || undefined,
          info: c.documentation || undefined,
          apply: c.insert_text || c.label,
        })),
        validFor: /^\w*$/,
      };
    } catch {
      return null;
    }
  };

  const diagnose = linter(
    async (view) => {
      const doc = view.state.doc;
      try {
        const res = await api.getDiagnostics(doc.toString());
        return res.diagnostics.flatMap((d): Diagnostic[] => {
          if (d.from_line < 1 || d.from_line > doc.lines) return [];
          const fromLine = doc.line(d.from_line);
          const toLine = doc.line(Math.min(Math.max(d.to_line || d.from_line, d.from_line), doc.lines));
          const from = Math.min(fromLine.from + Math.max(0, d.from_col), fromLine.to);
          let to = Math.min(toLine.from + Math.max(0, d.to_col), toLine.to);
          if (to <= from) to = Math.min(from + 1, fromLine.to);
          return [{ from, to: Math.max(to, from), severity: d.severity === 'warning' ? 'warning' : d.severity === 'info' ? 'info' : 'error', message: d.message }];
        });
      } catch {
        return [];
      }
    },
    { delay: 600 }
  );

  return [autocompletion({ override: [complete], activateOnTyping: true, icons: true }), diagnose, lintGutter()];
}

// Ctrl+/ as its own undo step (like VS Code): without isolation, CodeMirror merges it with typing
// done in the previous half second, and one Ctrl+Z would undo both
const toggleCommentIsolated: Command = (view) =>
  toggleComment({
    state: view.state,
    dispatch: (tr) =>
      view.dispatch({
        changes: tr.changes,
        selection: tr.selection,
        scrollIntoView: true,
        annotations: [isolateHistory.of('full'), Transaction.userEvent.of('input.comment')],
      }),
  });

function createState(path: string, doc: string, onChangeRef: React.MutableRefObject<(value: string) => void>): EditorState {
  return EditorState.create({
    doc,
    extensions: [
      lineNumbers(),
      highlightActiveLineGutter(),
      foldGutter(),
      highlightSpecialChars(),
      history(),
      drawSelection(),
      dropCursor(),
      EditorState.allowMultipleSelections.of(true),
      indentOnInput(),
      indentUnit.of('    '),
      EditorState.tabSize.of(4),
      syntaxHighlighting(highlightStyle),
      bracketMatching(),
      closeBrackets(),
      rectangularSelection(),
      crosshairCursor(),
      highlightActiveLine(),
      highlightSelectionMatches(),
      keymap.of([
        { key: 'Mod-/', run: toggleCommentIsolated },
        ...closeBracketsKeymap,
        ...defaultKeymap,
        ...searchKeymap,
        ...historyKeymap,
        ...foldKeymap,
        ...completionKeymap,
        ...lintKeymap,
        indentWithTab,
      ]),
      ...languageFor(path),
      editorTheme,
      // VS Code redoes with Ctrl+Shift+Z on every platform (CodeMirror binds it only on Linux/macOS).
      // Matched by physical key, so it works whatever character the layout reports for Shift+Z.
      Prec.highest(EditorView.domEventHandlers({
        keydown: (event, view) => {
          if ((event.ctrlKey || event.metaKey) && event.shiftKey && !event.altKey && event.code === 'KeyZ') {
            event.preventDefault();
            return redo(view);
          }
          return false;
        },
      })),
      EditorView.contentAttributes.of({
        'aria-label': `Edit ${path.split('/').pop()}`,
        'data-testid': 'file-editor-content',
        autocapitalize: 'off',
        autocorrect: 'off',
        spellcheck: 'false',
      }),
      EditorView.updateListener.of((update) => {
        if (!update.docChanged) return;
        if (update.transactions.some((tr) => tr.annotation(External))) return;
        onChangeRef.current(update.state.doc.toString());
      }),
    ],
  });
}

export const CodeEditor: React.FC<CodeEditorProps> = ({ path, value, onChange, states, reveal }) => {
  const hostRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);
  const pathRef = useRef(path);
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;

  // Create the view once; dispose it (saving the current file's state) on unmount
  useEffect(() => {
    if (!hostRef.current) return;
    const stored = states.get(path);
    const view = new EditorView({
      parent: hostRef.current,
      state: stored && stored.state.doc.toString() === value ? stored.state : createState(path, value, onChangeRef),
    });
    viewRef.current = view;
    if (stored) {
      requestAnimationFrame(() => {
        view.scrollDOM.scrollTop = stored.scrollTop;
        view.scrollDOM.scrollLeft = stored.scrollLeft;
      });
    }
    // Tests and tools can reach the editor through its DOM element
    (view.dom as HTMLElement & { cmView?: EditorView }).cmView = view;
    return () => {
      states.set(pathRef.current, { state: view.state, scrollTop: view.scrollDOM.scrollTop, scrollLeft: view.scrollDOM.scrollLeft });
      view.destroy();
      viewRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Switching files: keep the old file's state, restore (or create) the new one
  useEffect(() => {
    const view = viewRef.current;
    if (!view || pathRef.current === path) return;
    states.set(pathRef.current, { state: view.state, scrollTop: view.scrollDOM.scrollTop, scrollLeft: view.scrollDOM.scrollLeft });
    pathRef.current = path;
    const stored = states.get(path);
    if (stored && stored.state.doc.toString() === value) {
      view.setState(stored.state);
      requestAnimationFrame(() => {
        view.scrollDOM.scrollTop = stored.scrollTop;
        view.scrollDOM.scrollLeft = stored.scrollLeft;
      });
    } else {
      view.setState(createState(path, value, onChangeRef));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path]);

  // Content changed outside the editor (reload, discard, another tool): apply it as one change
  useEffect(() => {
    const view = viewRef.current;
    if (!view || pathRef.current !== path) return;
    const current = view.state.doc.toString();
    if (current === value) return;
    view.dispatch({
      changes: { from: 0, to: current.length, insert: value },
      annotations: [External.of(true), Transaction.addToHistory.of(false)],
    });
  }, [value, path]);

  // Go to a line (traceback links): select it, centre it and give the editor the focus
  useEffect(() => {
    const view = viewRef.current;
    if (!view || !reveal || pathRef.current !== path) return;
    const lineNo = Math.min(Math.max(1, reveal.line), view.state.doc.lines);
    const line = view.state.doc.line(lineNo);
    const indent = line.text.length - line.text.trimStart().length;
    view.dispatch({
      selection: { anchor: line.from + indent, head: line.to },
      effects: EditorView.scrollIntoView(line.from, { y: 'center' }),
    });
    view.focus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reveal?.nonce, path]);

  return <div ref={hostRef} className="fe-cm-host" data-testid="file-code-editor" />;
};
