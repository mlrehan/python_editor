import React, { useState, useRef, useEffect } from 'react';
import {
  Play,
  Plus,
  Trash2,
  ArrowUp,
  ArrowDown,
  FileText,
  AlertTriangle,
  Eye,
  Edit3,
  Copy,
  Eraser,
  Loader2,
  Keyboard,
  X,
  Download,
} from 'lucide-react';
import { NotebookCell, KernelOutput } from '../types';
import { PythonCellEditor } from './PythonCellEditor';
import { DataTableView } from './DataTableView';

interface NotebookEditorProps {
  cells: NotebookCell[];
  onUpdateCellSource: (cellId: string, newSource: string) => void;
  onRunCell: (cellId: string, sourceOverride?: string) => void;
  onAddCell: (index: number, cellType: 'code' | 'markdown') => void;
  onDeleteCell: (cellId: string) => void;
  onMoveCell: (cellId: string, direction: 'up' | 'down') => void;
  onDuplicateCell: (cellId: string) => void;
  onClearCellOutput: (cellId: string) => void;
  onClearAllOutputs: () => void;
  onRunCurrentCell: (cellId: string, sourceOverride?: string) => void;
  onRunAndAdvance: (cellId: string, sourceOverride?: string) => void;
  onRunAndInsertBelow: (cellId: string, sourceOverride?: string) => void;
  activeCellId: string | null;
  onSelectCell: (cellId: string) => void;
  sessionId?: string;
  onUpdateCellMetadata?: (cellId: string, metadata: Record<string, any>) => void;
}

export const NotebookEditor: React.FC<NotebookEditorProps> = ({
  cells,
  onUpdateCellSource,
  onRunCell,
  onAddCell,
  onDeleteCell,
  onMoveCell,
  onDuplicateCell,
  onClearCellOutput,
  onClearAllOutputs,
  onRunCurrentCell,
  onRunAndAdvance,
  onRunAndInsertBelow,
  activeCellId,
  onSelectCell,
  sessionId,
  onUpdateCellMetadata,
}) => {
  const [markdownPreviews, setMarkdownPreviews] = useState<Record<string, boolean>>({});
  const [showShortcutsModal, setShowShortcutsModal] = useState(false);
  const textareaRefs = useRef<Record<string, HTMLTextAreaElement | null>>({});

  // Detect macOS
  const isMac =
    typeof navigator !== 'undefined' &&
    /(Mac|iPhone|iPod|iPad)/i.test(navigator.userAgent || navigator.platform);

  const toggleMarkdownPreview = (cellId: string) => {
    setMarkdownPreviews((prev) => ({ ...prev, [cellId]: !prev[cellId] }));
  };

  // Focus active cell textarea when activeCellId changes
  useEffect(() => {
    if (activeCellId && textareaRefs.current[activeCellId]) {
      const el = textareaRefs.current[activeCellId];
      if (document.activeElement !== el) {
        el?.focus();
      }
    }
  }, [activeCellId]);

  // Global shortcut handler for active cell execution anywhere in the notebook
  useEffect(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      // Don't intercept if user is typing in a modal or text input
      const activeEl = document.activeElement;
      const tag = activeEl?.tagName?.toLowerCase();
      if (tag === 'input') return;

      const isCtrlOrCmdEnter = (e.ctrlKey || e.metaKey) && e.key === 'Enter' && !e.shiftKey && !e.altKey;
      const isShiftEnter = e.shiftKey && e.key === 'Enter' && !e.ctrlKey && !e.metaKey && !e.altKey;
      const isAltEnter = e.altKey && e.key === 'Enter' && !e.ctrlKey && !e.metaKey;

      if (!isCtrlOrCmdEnter && !isShiftEnter && !isAltEnter) return;

      // Find active cell or fallback to first code cell
      const targetCell =
        (activeCellId ? cells.find((c) => c.id === activeCellId) : null) ||
        cells.find((c) => c.cell_type === 'code') ||
        cells[0];
      if (!targetCell) return;

      e.preventDefault();
      e.stopPropagation();

      const currentVal = textareaRefs.current[targetCell.id]?.value ?? targetCell.source;

      if (isCtrlOrCmdEnter) {
        if (targetCell.cell_type === 'markdown') {
          setMarkdownPreviews((prev) => ({ ...prev, [targetCell.id]: true }));
        } else {
          onRunCurrentCell(targetCell.id, currentVal);
        }
      } else if (isShiftEnter) {
        if (targetCell.cell_type === 'markdown') {
          setMarkdownPreviews((prev) => ({ ...prev, [targetCell.id]: true }));
          const idx = cells.findIndex((c) => c.id === targetCell.id);
          if (idx >= 0 && idx < cells.length - 1) {
            onSelectCell(cells[idx + 1].id);
          }
        } else {
          onRunAndAdvance(targetCell.id, currentVal);
        }
      } else if (isAltEnter) {
        onRunAndInsertBelow(targetCell.id, currentVal);
      }
    };

    window.addEventListener('keydown', handleGlobalKeyDown, true);
    return () => {
      window.removeEventListener('keydown', handleGlobalKeyDown, true);
    };
  }, [cells, activeCellId, onRunCurrentCell, onRunAndAdvance, onRunAndInsertBelow]);

  // Code editor keyboard event handler (Shortcuts, Auto-indent, Bracket pairing, Tab)
  const handleEditorKeyDown = (
    e: React.KeyboardEvent<HTMLTextAreaElement>,
    cell: NotebookCell
  ) => {
    const target = e.currentTarget;

    // 1. Cross-Platform Execution Shortcuts
    // Ctrl + Enter (Win/Linux) or Command + Enter (macOS): Run current cell and retain focus
    const isCtrlOrCmdEnter =
      (e.ctrlKey || e.metaKey) && e.key === 'Enter' && !e.shiftKey && !e.altKey;

    if (isCtrlOrCmdEnter) {
      e.preventDefault();
      e.stopPropagation();
      if (cell.cell_type === 'markdown') {
        setMarkdownPreviews((prev) => ({ ...prev, [cell.id]: true }));
      } else {
        onRunCurrentCell(cell.id, target.value);
      }
      return;
    }

    // Shift + Enter: Run current cell (or render markdown) and advance to next cell
    if (e.shiftKey && e.key === 'Enter' && !e.ctrlKey && !e.metaKey && !e.altKey) {
      e.preventDefault();
      e.stopPropagation();
      if (cell.cell_type === 'markdown') {
        setMarkdownPreviews((prev) => ({ ...prev, [cell.id]: true }));
        const idx = cells.findIndex((c) => c.id === cell.id);
        if (idx >= 0 && idx < cells.length - 1) {
          onSelectCell(cells[idx + 1].id);
        }
      } else {
        onRunAndAdvance(cell.id, target.value);
      }
      return;
    }

    // Alt + Enter (Win/Linux) or Option + Enter (macOS): Run and insert new cell below
    if (e.altKey && e.key === 'Enter' && !e.ctrlKey && !e.metaKey) {
      e.preventDefault();
      e.stopPropagation();
      onRunAndInsertBelow(cell.id, target.value);
      return;
    }

    // 2. Tab key handling: Insert 4 spaces instead of losing focus
    if (e.key === 'Tab') {
      e.preventDefault();
      const start = target.selectionStart;
      const end = target.selectionEnd;
      const val = target.value;
      const updated = val.substring(0, start) + '    ' + val.substring(end);
      onUpdateCellSource(cell.id, updated);
      requestAnimationFrame(() => {
        target.selectionStart = target.selectionEnd = start + 4;
      });
      return;
    }

    // 3. Auto-indent on Enter
    if (e.key === 'Enter' && !e.shiftKey && !e.ctrlKey && !e.altKey && !e.metaKey) {
      const start = target.selectionStart;
      const val = target.value;
      const currentLine = val.substring(0, start).split('\n').pop() || '';
      const leadingSpaces = currentLine.match(/^\s*/)?.[0] || '';
      const extraIndent = currentLine.trimEnd().endsWith(':') ? '    ' : '';
      const indent = leadingSpaces + extraIndent;

      if (indent.length > 0) {
        e.preventDefault();
        const updated = val.substring(0, start) + '\n' + indent + val.substring(target.selectionEnd);
        onUpdateCellSource(cell.id, updated);
        requestAnimationFrame(() => {
          target.selectionStart = target.selectionEnd = start + 1 + indent.length;
        });
        return;
      }
    }

    // 4. Bracket & Quote pairing
    const pairs: Record<string, string> = {
      '(': ')',
      '[': ']',
      '{': '}',
      '"': '"',
      "'": "'",
    };
    if (pairs[e.key] && !e.ctrlKey && !e.metaKey && !e.altKey) {
      const start = target.selectionStart;
      const end = target.selectionEnd;
      const val = target.value;
      if (start === end) {
        e.preventDefault();
        const closing = pairs[e.key];
        const updated = val.substring(0, start) + e.key + closing + val.substring(end);
        onUpdateCellSource(cell.id, updated);
        requestAnimationFrame(() => {
          target.selectionStart = target.selectionEnd = start + 1;
        });
        return;
      }
    }
  };

  const renderOutput = (output: KernelOutput, idx: number) => {
    if (output.output_type === 'stream') {
      const isErr = output.name === 'stderr';
      return (
        <pre
          key={idx}
          style={{
            color: isErr ? '#f87171' : 'var(--text-main)',
            fontSize: '13px',
            fontFamily: "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
            lineHeight: 1.5,
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            margin: '4px 0',
          }}
        >
          {output.text}
        </pre>
      );
    }

    if (output.output_type === 'display_data' || output.output_type === 'execute_result') {
      const data = output.data || {};
      const imgPng = data['image/png'];
      const imgJpeg = data['image/jpeg'];
      const imgSvg = data['image/svg+xml'];

      if (imgPng || imgJpeg || imgSvg) {
        const imgSrc = imgPng
          ? `data:image/png;base64,${imgPng}`
          : imgJpeg
          ? `data:image/jpeg;base64,${imgJpeg}`
          : `data:image/svg+xml;utf8,${encodeURIComponent(imgSvg)}`;
        const downloadName = `plot_cell_${idx + 1}.${imgSvg ? 'svg' : imgJpeg ? 'jpg' : 'png'}`;

        return (
          <div
            key={idx}
            data-testid="plot-output-container"
            style={{
              margin: '10px 0',
              borderRadius: '6px',
              overflow: 'hidden',
              backgroundColor: '#ffffff',
              display: 'inline-block',
              padding: '12px',
              boxShadow: '0 4px 14px rgba(0,0,0,0.25)',
              position: 'relative',
              maxWidth: '100%',
            }}
          >
            {/* Top Toolbar for Figure */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'flex-end',
                marginBottom: '6px',
                paddingBottom: '4px',
                borderBottom: '1px solid #f1f5f9',
              }}
            >
              <a
                href={imgSrc}
                download={downloadName}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  fontSize: '11px',
                  fontWeight: 600,
                  color: '#475569',
                  textDecoration: 'none',
                  backgroundColor: '#f8fafc',
                  border: '1px solid #cbd5e1',
                  borderRadius: '4px',
                  padding: '3px 8px',
                  cursor: 'pointer',
                }}
                title="Download Figure to disk"
              >
                <Download size={12} /> Download Plot
              </a>
            </div>

            <img
              src={imgSrc}
              alt="Matplotlib Visualization"
              style={{ maxWidth: '100%', height: 'auto', display: 'block', margin: '0 auto' }}
            />
          </div>
        );
      }
      if (data['text/html']) {
        const htmlStr = data['text/html'];
        if (htmlStr.includes('<table')) {
          return <DataTableView key={idx} html={htmlStr} />;
        }
        return (
          <div
            key={idx}
            style={{
              margin: '8px 0',
              overflowX: 'auto',
              color: 'var(--text-main)',
              fontSize: '13px',
            }}
            dangerouslySetInnerHTML={{ __html: htmlStr }}
          />
        );
      }
      if (data['text/plain']) {
        return (
          <pre
            key={idx}
            style={{
              color: 'var(--text-main)',
              fontSize: '13px',
              fontFamily: "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
              lineHeight: 1.5,
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              margin: '4px 0',
            }}
          >
            {data['text/plain']}
          </pre>
        );
      }
    }

    if (output.output_type === 'error') {
      return (
        <div
          key={idx}
          style={{
            margin: '6px 0',
            padding: '12px',
            backgroundColor: '#450a0a',
            borderLeft: '4px solid #ef4444',
            borderRadius: '4px',
          }}
        >
          <div
            style={{
              color: '#f87171',
              fontWeight: 600,
              fontSize: '13px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <AlertTriangle size={15} />
            {output.ename}: {output.evalue}
          </div>
          {output.traceback && output.traceback.length > 0 && (
            <pre
              style={{
                color: '#fca5a5',
                fontSize: '12px',
                marginTop: '8px',
                whiteSpace: 'pre-wrap',
                overflowX: 'auto',
                fontFamily: "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
              }}
            >
              {output.traceback.join('\n')}
            </pre>
          )}
        </div>
      );
    }

    return null;
  };

  return (
    <div
      data-testid="notebook-editor-container"
      style={{
        flex: 1,
        width: '100%',
        minWidth: 0,
        height: 'calc(100vh - 56px)',
        overflowY: 'auto',
        overflowX: 'hidden',
        backgroundColor: 'var(--bg-panel)',
        padding: '12px 16px 80px 16px',
        boxSizing: 'border-box',
      }}
    >
      <div
        style={{
          width: '100%',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
          boxSizing: 'border-box',
        }}
      >
        {/* Notebook Top Toolbar: Add Code, Add Text, Clear All Outputs, Keyboard Help */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '8px 12px',
            backgroundColor: 'var(--bg-card)',
            border: '1px solid var(--border-main)',
            borderRadius: '8px',
            marginBottom: '4px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button
              onClick={() => onAddCell(0, 'code')}
              style={{
                padding: '5px 10px',
                backgroundColor: 'var(--btn-secondary-bg)',
                border: '1px solid var(--btn-secondary-border)',
                borderRadius: '5px',
                color: 'var(--border-accent)',
                fontSize: '12px',
                fontWeight: 500,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
              }}
              title="Insert Code Cell at Top"
            >
              <Plus size={13} /> Code
            </button>
            <button
              onClick={() => onAddCell(0, 'markdown')}
              style={{
                padding: '5px 10px',
                backgroundColor: 'var(--btn-secondary-bg)',
                border: '1px solid var(--btn-secondary-border)',
                borderRadius: '5px',
                color: 'var(--text-secondary)',
                fontSize: '12px',
                fontWeight: 500,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
              }}
              title="Insert Text Cell at Top"
            >
              <Plus size={13} /> Text
            </button>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {/* Clear All Outputs Button */}
            <button
              onClick={onClearAllOutputs}
              style={{
                padding: '5px 10px',
                backgroundColor: 'var(--btn-secondary-bg)',
                border: '1px solid var(--btn-secondary-border)',
                borderRadius: '5px',
                color: 'var(--text-main)',
                fontSize: '12px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
              }}
              title="Clear all cell outputs (Preserves code & kernel)"
            >
              <Eraser size={13} color="#f59e0b" /> Clear All Outputs
            </button>

            {/* Keyboard Shortcuts Help */}
            <button
              onClick={() => setShowShortcutsModal(true)}
              style={{
                padding: '5px 10px',
                backgroundColor: 'var(--btn-secondary-bg)',
                border: '1px solid var(--btn-secondary-border)',
                borderRadius: '5px',
                color: 'var(--text-secondary)',
                fontSize: '12px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
              }}
              title="View Keyboard Shortcuts"
            >
              <Keyboard size={13} /> Shortcuts
            </button>
          </div>
        </div>

        {/* Cells List */}
        {cells.map((cell, index) => {
          const isActive = cell.id === activeCellId;
          const isMarkdownPreview = cell.cell_type === 'markdown' && !!markdownPreviews[cell.id];
          const hasOutputs = cell.outputs && cell.outputs.length > 0;

          return (
            <div
              key={cell.id}
              onClick={() => onSelectCell(cell.id)}
              className={`cell-wrapper ${isActive ? 'active' : ''}`}
              style={{
                borderRadius: '8px',
                border: isActive ? '1px solid var(--border-accent)' : '1px solid var(--border-main)',
                backgroundColor: 'var(--bg-cell-wrapper)',
                overflow: isActive ? 'visible' : 'hidden',
                zIndex: isActive ? 40 : 1,
                boxShadow: isActive ? '0 0 0 1px var(--border-accent)' : 'none',
                transition: 'border-color 0.15s ease, box-shadow 0.15s ease',
                position: 'relative',
              }}
            >
              {/* Cell Header / Action Menu Toolbar */}
              <div
                style={{
                  height: '32px',
                  backgroundColor: 'var(--bg-cell-header)',
                  borderBottom: '1px solid var(--border-main)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '0 10px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  {cell.cell_type === 'code' ? (
                    <span
                      style={{
                        fontSize: '11px',
                        fontWeight: 600,
                        color: cell.is_running ? '#f59e0b' : 'var(--border-accent)',
                        fontFamily: "'JetBrains Mono', monospace",
                      }}
                    >
                      {cell.is_running ? '[*]' : cell.execution_count ? `[${cell.execution_count}]` : '[ ]'}
                    </span>
                  ) : (
                    <span style={{ fontSize: '11px', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <FileText size={12} /> Markdown
                    </span>
                  )}
                </div>

                {/* Top-Right Contextual Action Menu */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  {/* Markdown Toggle */}
                  {cell.cell_type === 'markdown' && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleMarkdownPreview(cell.id);
                      }}
                      style={{
                        padding: '3px 7px',
                        backgroundColor: 'var(--btn-secondary-bg)',
                        border: '1px solid var(--btn-secondary-border)',
                        borderRadius: '4px',
                        color: 'var(--btn-secondary-text)',
                        fontSize: '11px',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                      }}
                      title="Toggle Preview / Edit"
                    >
                      {isMarkdownPreview ? <><Edit3 size={11} /> Edit</> : <><Eye size={11} /> Preview</>}
                    </button>
                  )}

                  {/* Move Cell Up */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onMoveCell(cell.id, 'up');
                    }}
                    disabled={index === 0}
                    style={{
                      backgroundColor: 'transparent',
                      border: 'none',
                      color: index === 0 ? 'var(--text-muted)' : 'var(--text-secondary)',
                      cursor: index === 0 ? 'default' : 'pointer',
                      padding: '3px 5px',
                    }}
                    title="Move Cell Up"
                  >
                    <ArrowUp size={13} />
                  </button>

                  {/* Move Cell Down */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onMoveCell(cell.id, 'down');
                    }}
                    disabled={index === cells.length - 1}
                    style={{
                      backgroundColor: 'transparent',
                      border: 'none',
                      color: index === cells.length - 1 ? 'var(--text-muted)' : 'var(--text-secondary)',
                      cursor: index === cells.length - 1 ? 'default' : 'pointer',
                      padding: '3px 5px',
                    }}
                    title="Move Cell Down"
                  >
                    <ArrowDown size={13} />
                  </button>

                  {/* Duplicate Cell */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDuplicateCell(cell.id);
                    }}
                    style={{
                      backgroundColor: 'transparent',
                      border: 'none',
                      color: 'var(--text-secondary)',
                      cursor: 'pointer',
                      padding: '3px 5px',
                    }}
                    title="Duplicate Cell"
                  >
                    <Copy size={13} />
                  </button>

                  {/* Clear Output (for code cells) */}
                  {cell.cell_type === 'code' && hasOutputs && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onClearCellOutput(cell.id);
                      }}
                      style={{
                        backgroundColor: 'transparent',
                        border: 'none',
                        color: '#f59e0b',
                        cursor: 'pointer',
                        padding: '3px 5px',
                      }}
                      title="Clear Cell Output"
                    >
                      <Eraser size={13} />
                    </button>
                  )}

                  {/* Delete Cell */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteCell(cell.id);
                    }}
                    style={{
                      backgroundColor: 'transparent',
                      border: 'none',
                      color: '#ef4444',
                      cursor: 'pointer',
                      padding: '3px 5px',
                    }}
                    title="Delete Cell"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              </div>

              {/* Cell Main Container (Google Colab Left Run Button + Code Textarea) */}
              <div style={{ display: 'flex', backgroundColor: 'var(--bg-cell)' }}>
                {/* Left Gutter: Circular Colab-style Run Button */}
                {cell.cell_type === 'code' ? (
                  <div
                    style={{
                      width: '48px',
                      paddingTop: '10px',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      flexShrink: 0,
                      backgroundColor: 'var(--bg-cell-run-btn-gutter)',
                      borderRight: '1px solid var(--border-main)',
                    }}
                  >
                    <button
                      data-testid="cell-run-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        const currentSource = textareaRefs.current[cell.id]?.value ?? cell.source;
                        onRunCell(cell.id, currentSource);
                      }}
                      disabled={cell.is_running}
                      style={{
                        width: '30px',
                        height: '30px',
                        borderRadius: '50%',
                        backgroundColor: cell.is_running ? 'var(--dropdown-item-selected)' : 'var(--btn-secondary-bg)',
                        border: cell.is_running ? '1px solid var(--border-accent)' : '1px solid var(--btn-secondary-border)',
                        color: 'var(--text-main)',
                        cursor: cell.is_running ? 'default' : 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        transition: 'all 0.15s ease',
                      }}
                      title={
                        cell.is_running
                           ? 'Executing cell...'
                           : isMac
                           ? 'Run cell (⌘+Enter)'
                           : 'Run cell (Ctrl+Enter)'
                      }
                    >
                      {cell.is_running ? (
                        <Loader2 size={15} color="#60a5fa" className="animate-spin" />
                      ) : (
                        <Play size={13} fill="currentColor" style={{ marginLeft: '2px' }} />
                      )}
                    </button>
                  </div>
                ) : (
                  <div
                    style={{
                      width: '32px',
                      flexShrink: 0,
                      backgroundColor: 'var(--bg-cell-run-btn-gutter)',
                      borderRight: '1px solid var(--border-main)',
                    }}
                  />
                )}

                {/* Editor Body */}
                <div style={{ flex: 1, padding: cell.cell_type === 'code' ? '0' : '10px 14px' }}>
                  {cell.cell_type === 'markdown' && isMarkdownPreview ? (
                    <div
                      style={{
                        color: 'var(--text-main)',
                        fontSize: '14px',
                        lineHeight: 1.6,
                        minHeight: '36px',
                        cursor: 'pointer',
                      }}
                      onDoubleClick={() => toggleMarkdownPreview(cell.id)}
                      title="Double click to edit Markdown"
                    >
                      {cell.source.split('\n').map((line, i) => {
                        if (line.startsWith('# '))
                          return <h1 key={i} style={{ fontSize: '20px', fontWeight: 700, margin: '8px 0', color: 'var(--border-accent)' }}>{line.slice(2)}</h1>;
                        if (line.startsWith('## '))
                          return <h2 key={i} style={{ fontSize: '17px', fontWeight: 600, margin: '6px 0', color: 'var(--border-accent)' }}>{line.slice(3)}</h2>;
                        if (line.startsWith('### '))
                          return <h3 key={i} style={{ fontSize: '15px', fontWeight: 600, margin: '4px 0', color: 'var(--text-main)' }}>{line.slice(4)}</h3>;
                        return <p key={i} style={{ margin: '4px 0' }}>{line || '\u00A0'}</p>;
                      })}
                    </div>
                  ) : cell.cell_type === 'code' ? (
                    <PythonCellEditor
                      cellId={cell.id}
                      code={cell.source}
                      customHeight={cell.metadata?.custom_height}
                      onHeightChange={(id, height) => onUpdateCellMetadata && onUpdateCellMetadata(id, { custom_height: height })}
                      onChange={(newCode) => onUpdateCellSource(cell.id, newCode)}
                      onRunCurrentCell={(id, codeVal) => onRunCurrentCell(id, codeVal)}
                      onRunAndAdvance={(id, codeVal) => onRunAndAdvance(id, codeVal)}
                      onRunAndInsertBelow={(id, codeVal) => onRunAndInsertBelow(id, codeVal)}
                      onFocus={() => onSelectCell(cell.id)}
                      notebookContext={cells
                        .slice(0, index)
                        .filter((c) => c.cell_type === 'code')
                        .map((c) => c.source)}
                      sessionId={sessionId}
                      editorRef={(el) => {
                        textareaRefs.current[cell.id] = el;
                      }}
                    />
                  ) : (
                    <textarea
                      ref={(el) => {
                        textareaRefs.current[cell.id] = el;
                      }}
                      data-testid="markdown-cell-editor"
                      className="code-font markdown-cell-editor"
                      value={cell.source}
                      onFocus={() => onSelectCell(cell.id)}
                      onChange={(e) => onUpdateCellSource(cell.id, e.target.value)}
                      onKeyDown={(e) => handleEditorKeyDown(e, cell)}
                      placeholder="Write Markdown text here..."
                      spellCheck={false}
                      autoComplete="off"
                      autoCorrect="off"
                      autoCapitalize="off"
                      data-gramm="false"
                      style={{
                        width: '100%',
                        minHeight: '64px',
                        backgroundColor: 'transparent',
                        border: 'none',
                        outline: 'none',
                        color: 'var(--code-text)',
                        fontSize: '13.5px',
                        fontFamily: "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
                        lineHeight: 1.6,
                        resize: 'vertical',
                      }}
                    />
                  )}
                </div>
              </div>

              {/* Cell Output Area (Beneath the code editor) */}
              {hasOutputs && (
                <div
                  data-testid="cell-output-container"
                  style={{
                    padding: '12px 16px 12px 52px',
                    backgroundColor: 'var(--bg-output)',
                    borderTop: '1px solid var(--border-main)',
                  }}
                >
                  {cell.outputs.map((out, oIdx) => renderOutput(out, oIdx))}
                </div>
              )}
            </div>
          );
        })}

        {/* Bottom Cell Inserter */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'center',
            gap: '12px',
            marginTop: '16px',
          }}
        >
          <button
            onClick={() => onAddCell(cells.length, 'code')}
            style={{
              padding: '8px 16px',
              backgroundColor: 'var(--btn-secondary-bg)',
              color: 'var(--border-accent)',
              border: '1px solid var(--btn-secondary-border)',
              borderRadius: '6px',
              fontSize: '13px',
              fontWeight: 500,
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              cursor: 'pointer',
            }}
          >
            <Plus size={15} /> Add Code Cell
          </button>
          <button
            onClick={() => onAddCell(cells.length, 'markdown')}
            style={{
              padding: '8px 16px',
              backgroundColor: 'var(--btn-secondary-bg)',
              color: 'var(--text-secondary)',
              border: '1px solid var(--btn-secondary-border)',
              borderRadius: '6px',
              fontSize: '13px',
              fontWeight: 500,
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              cursor: 'pointer',
            }}
          >
            <Plus size={15} /> Add Text Cell
          </button>
        </div>
      </div>

      {/* Keyboard Shortcuts Help Modal */}
      {showShortcutsModal && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0,0,0,0.65)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 150,
          }}
          onClick={() => setShowShortcutsModal(false)}
        >
          <div
            style={{
              width: '460px',
              backgroundColor: 'var(--bg-modal)',
              border: '1px solid var(--border-secondary)',
              borderRadius: '8px',
              padding: '24px',
              boxShadow: '0 16px 32px rgba(0,0,0,0.4)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: '16px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Keyboard size={18} color="var(--border-accent)" />
                <h3 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-main)', margin: 0 }}>
                  Keyboard Shortcuts ({isMac ? 'macOS' : 'Windows / Linux'})
                </h3>
              </div>
              <button
                onClick={() => setShowShortcutsModal(false)}
                style={{
                  backgroundColor: 'transparent',
                  border: 'none',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer',
                  padding: '4px',
                }}
              >
                <X size={16} />
              </button>
            </div>

            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-secondary)', textAlign: 'left', color: 'var(--text-secondary)' }}>
                  <th style={{ padding: '8px 4px' }}>Action</th>
                  <th style={{ padding: '8px 4px', textAlign: 'right' }}>Shortcut</th>
                </tr>
              </thead>
              <tbody style={{ color: 'var(--text-main)' }}>
                <tr style={{ borderBottom: '1px solid var(--border-main)' }}>
                  <td style={{ padding: '8px 4px' }}>Run Current Cell (Keep Focus)</td>
                  <td style={{ padding: '8px 4px', textAlign: 'right' }}>
                    <kbd style={{ backgroundColor: 'var(--btn-secondary-bg)', padding: '2px 6px', borderRadius: '4px', border: '1px solid var(--btn-secondary-border)', color: 'var(--text-main)' }}>
                      {isMac ? '⌘ + Enter' : 'Ctrl + Enter'}
                    </kbd>
                  </td>
                </tr>
                <tr style={{ borderBottom: '1px solid var(--border-main)' }}>
                  <td style={{ padding: '8px 4px' }}>Run & Advance to Next Cell</td>
                  <td style={{ padding: '8px 4px', textAlign: 'right' }}>
                    <kbd style={{ backgroundColor: 'var(--btn-secondary-bg)', padding: '2px 6px', borderRadius: '4px', border: '1px solid var(--btn-secondary-border)', color: 'var(--text-main)' }}>
                      Shift + Enter
                    </kbd>
                  </td>
                </tr>
                <tr style={{ borderBottom: '1px solid var(--border-main)' }}>
                  <td style={{ padding: '8px 4px' }}>Run & Insert Code Cell Below</td>
                  <td style={{ padding: '8px 4px', textAlign: 'right' }}>
                    <kbd style={{ backgroundColor: 'var(--btn-secondary-bg)', padding: '2px 6px', borderRadius: '4px', border: '1px solid var(--btn-secondary-border)', color: 'var(--text-main)' }}>
                      {isMac ? '⌥ + Enter' : 'Alt + Enter'}
                    </kbd>
                  </td>
                </tr>
                <tr style={{ borderBottom: '1px solid var(--border-main)' }}>
                  <td style={{ padding: '8px 4px' }}>Save Notebook / File</td>
                  <td style={{ padding: '8px 4px', textAlign: 'right' }}>
                    <kbd style={{ backgroundColor: 'var(--btn-secondary-bg)', padding: '2px 6px', borderRadius: '4px', border: '1px solid var(--btn-secondary-border)', color: 'var(--text-main)' }}>
                      {isMac ? '⌘ + S' : 'Ctrl + S'}
                    </kbd>
                  </td>
                </tr>
                <tr>
                  <td style={{ padding: '8px 4px' }}>Toggle Files Sidebar</td>
                  <td style={{ padding: '8px 4px', textAlign: 'right' }}>
                    <kbd style={{ backgroundColor: 'var(--btn-secondary-bg)', padding: '2px 6px', borderRadius: '4px', border: '1px solid var(--btn-secondary-border)', color: 'var(--text-main)' }}>
                      {isMac ? '⌘ + B' : 'Ctrl + B'}
                    </kbd>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
