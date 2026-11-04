import React, { useCallback, useLayoutEffect, useRef, useState } from 'react';
import { MarkdownToolbar } from './MarkdownToolbar';
import { MarkdownView } from './MarkdownView';

interface MarkdownCellEditorProps {
  source: string;
  onChange: (value: string) => void;
  onFocus: () => void;
  onKeyDown: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  /** Receives the source editor (the notebook focuses it and reads its text) */
  editorRef: (el: HTMLTextAreaElement | null) => void;
  livePreview: boolean;
  onToggleLivePreview: () => void;
}

/**
 * Editing a text cell, as in Colab: a formatting toolbar, the Markdown source, and a live preview
 * of the result beside it (below it on narrow screens). The source is the cell's content, so
 * nothing is converted or lost: what is saved is exactly what is shown in the source editor.
 */
export const MarkdownCellEditor: React.FC<MarkdownCellEditorProps> = ({
  source,
  onChange,
  onFocus,
  onKeyDown,
  editorRef,
  livePreview,
  onToggleLivePreview,
}) => {
  const [editor, setEditor] = useState<HTMLTextAreaElement | null>(null);
  const editorRefProp = useRef(editorRef);
  editorRefProp.current = editorRef;
  // Stable, so React does not detach and re-attach the editor on every render
  const attach = useCallback((el: HTMLTextAreaElement | null) => {
    setEditor(el);
    editorRefProp.current(el);
  }, []);

  // Grows with its text (no inner scrollbar), like the code cells
  useLayoutEffect(() => {
    if (!editor) return;
    editor.style.height = 'auto';
    editor.style.height = `${Math.max(72, editor.scrollHeight + 2)}px`;
  }, [editor, source]);

  return (
    <div className="md-cell-editing" data-testid="markdown-cell-editing">
      <MarkdownToolbar editor={editor} onFallbackChange={onChange} showPreview={livePreview} onTogglePreview={onToggleLivePreview} />
      <div className={`md-edit-layout${livePreview ? ' has-preview' : ''}`}>
        <textarea
          ref={attach}
          data-testid="markdown-cell-editor"
          className="code-font markdown-cell-editor"
          aria-label="Text cell (Markdown)"
          value={source}
          onFocus={onFocus}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Write text here. Use the toolbar to add headings, lists, links, images and more."
          spellCheck
          autoComplete="off"
          autoCorrect="off"
          autoCapitalize="off"
          data-gramm="false"
        />
        {livePreview && (
          <div className="md-live-preview" aria-label="Preview" data-testid="markdown-live-preview">
            <MarkdownView source={source} emptyText="The formatted text appears here." />
          </div>
        )}
      </div>
    </div>
  );
};
