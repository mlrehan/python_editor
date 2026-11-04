import React, { useEffect, useMemo, useRef } from 'react';
import { renderMarkdown, typesetMath } from '../utils/markdown';

interface MarkdownViewProps {
  source: string;
  /** Shown when the cell has no text yet */
  emptyText?: string;
  className?: string;
  testId?: string;
  onDoubleClick?: () => void;
  title?: string;
}

/** A rendered Markdown cell: sanitised HTML, maths typeset with KaTeX */
export const MarkdownView: React.FC<MarkdownViewProps> = ({ source, emptyText, className, testId, onDoubleClick, title }) => {
  const html = useMemo(() => renderMarkdown(source), [source]);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (ref.current) void typesetMath(ref.current);
  }, [html]);

  if (!source.trim()) {
    return (
      <div className={`md-render md-render--empty ${className ?? ''}`} data-testid={testId} onDoubleClick={onDoubleClick} title={title}>
        {emptyText}
      </div>
    );
  }
  return (
    <div
      ref={ref}
      className={`md-render ${className ?? ''}`}
      data-testid={testId}
      onDoubleClick={onDoubleClick}
      title={title}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
};
