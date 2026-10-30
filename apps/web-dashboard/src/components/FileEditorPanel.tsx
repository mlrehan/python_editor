import React, { useState, useEffect, useLayoutEffect, useMemo, useRef } from 'react';
import {
  X,
  Save,
  Download,
  FileCode,
  FileSpreadsheet,
  FileText,
  File,
  Table,
  Code,
  Eye,
  Edit3,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  AlertTriangle,
  ChevronDown,
  Check,
} from 'lucide-react';
import { api } from '../services/api';
import { isToggleCommentShortcut, toggleLineComments } from '../utils/lineComments';
import { applyTabIndent, INDENT } from '../utils/indentation';
import { applyTextareaEdit } from '../utils/textareaEdit';
import { tokenizePython, findBracketPair, renderHighlightedLines } from '../utils/pythonSyntax';
import { Modal, ModalHeader, ModalBody, ModalFooter } from './Modal';

export interface OpenFileInfo {
  path: string;
  name: string;
  content: string;
  isDirty: boolean;
}

/** docked: desktop side panel; drawer: overlay on tablets; fullscreen: the whole workspace on phones */
export type FileEditorLayout = 'docked' | 'drawer' | 'fullscreen';

interface FileEditorPanelProps {
  // Support both multi-tab and single file modes
  openFiles?: OpenFileInfo[];
  activeFilePath?: string | null;
  file?: OpenFileInfo | null;
  isOpen: boolean;
  onClose: () => void;
  onSelectTab?: (path: string) => void;
  onCloseTab?: (path: string) => void;
  onSave: (path: string, newContent: string) => Promise<void>;
  onContentChange: (newContent: string, path?: string) => void;
  onOpenAsNotebook?: (path: string) => void;
  width?: number;
  layout?: FileEditorLayout;
}

// Cursor, selection and scroll position of a file, kept while the user works in another tab
interface EditorViewState {
  selectionStart: number;
  selectionEnd: number;
  scrollTop: number;
  scrollLeft: number;
}

export const FileEditorPanel: React.FC<FileEditorPanelProps> = ({
  openFiles = [],
  activeFilePath,
  file,
  isOpen,
  onClose,
  onSelectTab,
  onCloseTab,
  onSave,
  onContentChange,
  onOpenAsNotebook,
  width = 420,
  layout = 'docked',
}) => {
  const [isSaving, setIsSaving] = useState(false);
  const [csvViewMode, setCsvViewMode] = useState<'table' | 'text'>('table');
  const [mdViewMode, setMdViewMode] = useState<'edit' | 'preview'>('preview');
  const [isSwitcherOpen, setIsSwitcherOpen] = useState(false);
  const viewStatesRef = useRef<Map<string, EditorViewState>>(new Map());
  const tabStripRef = useRef<HTMLDivElement>(null);
  const switcherRef = useRef<HTMLDivElement>(null);

  // Unsaved Changes Confirmation Modal state
  const [confirmCloseFile, setConfirmCloseFile] = useState<OpenFileInfo | null>(null);

  // Normalize files list: if openFiles provided, use it, else fallback to single file
  const filesList: OpenFileInfo[] = openFiles.length > 0 ? openFiles : file ? [file] : [];
  const currentFile: OpenFileInfo | null =
    filesList.find((f) => f.path === activeFilePath) ||
    (filesList.length > 0 ? filesList[0] : file || null);

  // Editor keys: Tab / Shift+Tab indent and dedent (whole lines when a multi-line selection exists),
  // Enter keeps the current indentation and adds a level after a trailing ':' in Python files.
  const handleEditorKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (!currentFile || e.nativeEvent.isComposing) return;
    const el = e.currentTarget;
    const value = el.value;
    const start = el.selectionStart;
    const end = el.selectionEnd;

    // Through the browser's native editing history, so Ctrl+Z / Ctrl+Shift+Z undo and redo it
    const applyEdit = (newValue: string, selStart: number, selEnd: number) => {
      e.preventDefault();
      applyTextareaEdit(el, newValue, selStart, selEnd);
      onContentChange(el.value, currentFile.path);
    };

    // Ctrl+/ toggles Python comments on the selected lines or the current line
    if (isToggleCommentShortcut(e) && currentFile.path.toLowerCase().endsWith('.py')) {
      e.stopPropagation();
      const edit = toggleLineComments(value, start, end);
      applyEdit(edit.value, edit.selectionStart, edit.selectionEnd);
      return;
    }

    if (e.key === 'Tab' && !e.ctrlKey && !e.metaKey && !e.altKey) {
      const edit = applyTabIndent(value, start, end, e.shiftKey);
      applyEdit(edit.value, edit.selectionStart, edit.selectionEnd);
      return;
    }

    if (e.key === 'Enter' && !e.shiftKey && !e.ctrlKey && !e.metaKey && !e.altKey) {
      const lineBeforeCursor = value.substring(0, start).split('\n').pop() || '';
      const currentIndent = lineBeforeCursor.match(/^[ \t]*/)?.[0] ?? '';
      const isPython = currentFile.path.toLowerCase().endsWith('.py');
      const extraIndent = isPython && lineBeforeCursor.trimEnd().endsWith(':') ? INDENT : '';
      if (currentIndent || extraIndent) {
        const insertText = '\n' + currentIndent + extraIndent;
        applyEdit(value.substring(0, start) + insertText + value.substring(end), start + insertText.length, start + insertText.length);
      }
    }
  };

  // Handle Ctrl+S / Cmd+S while focus is in this panel (elsewhere, Ctrl+S saves the notebook)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && !e.altKey && (e.key.toLowerCase() === 's' || e.code === 'KeyS')) {
        const focusInPanel = !!(document.activeElement as HTMLElement | null)?.closest(
          '[data-testid="right-file-editor-panel"]'
        );
        if (isOpen && currentFile && focusInPanel) {
          e.preventDefault();
          handleSaveClick();
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, currentFile]);

  // Keep the active tab visible in the scrolling tab strip
  const currentPath = currentFile?.path;
  useEffect(() => {
    if (!currentPath || !tabStripRef.current) return;
    const tab = tabStripRef.current.querySelector<HTMLElement>(`[data-path="${CSS.escape(currentPath)}"]`);
    tab?.scrollIntoView({ block: 'nearest', inline: 'nearest' });
  }, [currentPath, filesList.length]);

  // Forget the view state of files that were closed
  useEffect(() => {
    const open = new Set(filesList.map((f) => f.path));
    for (const path of viewStatesRef.current.keys()) {
      if (!open.has(path)) viewStatesRef.current.delete(path);
    }
  }, [filesList]);

  // The open-files switcher closes on outside press or Escape
  useEffect(() => {
    if (!isSwitcherOpen) return;
    const onPointerDown = (e: PointerEvent) => {
      if (switcherRef.current && !switcherRef.current.contains(e.target as Node)) setIsSwitcherOpen(false);
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        setIsSwitcherOpen(false);
      }
    };
    document.addEventListener('pointerdown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('pointerdown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [isSwitcherOpen]);

  if (!isOpen) {
    return null;
  }

  const handleSaveClick = async () => {
    if (!currentFile) return;
    setIsSaving(true);
    try {
      await onSave(currentFile.path, currentFile.content);
    } catch (err) {
      console.error('Failed to save file:', err);
    } finally {
      setIsSaving(false);
    }
  };

  // Close tab trigger
  const handleRequestCloseTab = (f: OpenFileInfo, e: React.MouseEvent) => {
    e.stopPropagation();
    if (f.isDirty) {
      setConfirmCloseFile(f);
    } else {
      executeCloseTab(f.path);
    }
  };

  const executeCloseTab = (path: string) => {
    if (onCloseTab) {
      onCloseTab(path);
    } else {
      onClose();
    }
  };

  // Unsaved dialog actions
  const handleModalSaveAndClose = async () => {
    if (!confirmCloseFile) return;
    setIsSaving(true);
    try {
      await onSave(confirmCloseFile.path, confirmCloseFile.content);
      executeCloseTab(confirmCloseFile.path);
      setConfirmCloseFile(null);
    } catch (err) {
      console.error('Failed to save before closing:', err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleModalDiscardAndClose = () => {
    if (!confirmCloseFile) return;
    executeCloseTab(confirmCloseFile.path);
    setConfirmCloseFile(null);
  };

  const handleModalCancel = () => {
    setConfirmCloseFile(null);
  };

  const ext = currentFile ? currentFile.name.split('.').pop()?.toLowerCase() || '' : '';
  const isCsv = ext === 'csv';
  const isMarkdown = ext === 'md';
  const isNotebook = ext === 'ipynb';
  const isImage = ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'].includes(ext);

  const getFileIcon = (fileName: string) => {
    const fExt = fileName.split('.').pop()?.toLowerCase() || '';
    if (fExt === 'py') return <FileCode size={14} color="#3b82f6" />;
    if (fExt === 'csv') return <FileSpreadsheet size={14} color="#10b981" />;
    if (fExt === 'md') return <FileText size={14} color="#a855f7" />;
    if (fExt === 'json') return <FileCode size={14} color="#f59e0b" />;
    return <File size={14} color="#94a3b8" />;
  };

  // Parse CSV into rows and columns
  const parseCsv = (csvText: string) => {
    const lines = csvText.trim().split(/\r?\n/);
    if (lines.length === 0 || !lines[0]) return { headers: [], rows: [] };
    const headers = lines[0].split(',').map((h) => h.trim().replace(/^["']|["']$/g, ''));
    const rows = lines.slice(1).map((line) => line.split(',').map((c) => c.trim().replace(/^["']|["']$/g, '')));
    return { headers, rows };
  };

  const isDocked = layout === 'docked';
  const directory = currentFile && currentFile.path.includes('/') ? currentFile.path.slice(0, currentFile.path.lastIndexOf('/')) : '';

  return (
    <aside
      data-testid="right-file-editor-panel"
      data-layout={layout}
      className={`fe-panel fe-panel--${layout}`}
      aria-label="File editor"
      style={{
        width: isDocked ? `${width}px` : '100%',
        maxWidth: isDocked ? `${width}px` : '100%',
        minWidth: isDocked ? `${width}px` : 0,
        backgroundColor: 'var(--bg-sidebar)',
        borderLeft: isDocked ? '1px solid var(--border-main)' : 'none',
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        zIndex: 20,
        boxShadow: isDocked ? '-4px 0 16px rgba(0,0,0,0.3)' : 'none',
        flexShrink: 0,
        position: 'relative',
      }}
    >
      {/* 1. Multi-Tab Bar: scrolling tab strip, open-files switcher, close panel */}
      <div data-testid="file-tabs-bar" className="fe-tabs-bar">
        <div ref={tabStripRef} className="fe-tab-strip" role="tablist" aria-label="Open files">
          {filesList.map((f) => {
            const isActive = currentFile?.path === f.path;
            return (
              <div
                key={f.path}
                data-testid={`file-tab-${f.name}`}
                data-path={f.path}
                role="tab"
                aria-selected={isActive}
                tabIndex={isActive ? 0 : -1}
                className={`fe-tab${isActive ? ' is-active' : ''}`}
                onClick={() => onSelectTab && onSelectTab(f.path)}
                onKeyDown={(e) => {
                  if ((e.key === 'Enter' || e.key === ' ') && onSelectTab) {
                    e.preventDefault();
                    onSelectTab(f.path);
                  }
                }}
                title={f.path}
              >
                {getFileIcon(f.name)}
                <span className="fe-tab-name">{f.name}</span>

                {/* Unsaved dirty dot indicator */}
                {f.isDirty && (
                  <span data-testid={`dirty-indicator-${f.name}`} className="fe-dirty-dot" title="Unsaved changes" />
                )}

                {/* Tab Close (X) button */}
                <button
                  type="button"
                  data-testid={`close-tab-${f.name}`}
                  className="fe-tab-close"
                  onClick={(e) => handleRequestCloseTab(f, e)}
                  title={`Close ${f.name}`}
                  aria-label={`Close ${f.name}`}
                >
                  <X size={13} />
                </button>
              </div>
            );
          })}
        </div>

        {/* Open-files switcher: every open file in one list, for when the tabs do not fit */}
        {filesList.length > 1 && (
          <div className="fe-switcher" ref={switcherRef}>
            <button
              type="button"
              className={`fe-icon-btn fe-switcher-btn${isSwitcherOpen ? ' is-active' : ''}`}
              onClick={() => setIsSwitcherOpen((open) => !open)}
              aria-haspopup="listbox"
              aria-expanded={isSwitcherOpen}
              aria-label={`Switch file (${filesList.length} open)`}
              title="Switch between open files"
              data-testid="open-files-switcher"
            >
              <span className="fe-switcher-count">{filesList.length}</span>
              <ChevronDown size={14} />
            </button>
            {isSwitcherOpen && (
              <div className="fe-switcher-menu" role="listbox" aria-label="Open files" data-testid="open-files-menu">
                {filesList.map((f) => {
                  const isActive = currentFile?.path === f.path;
                  return (
                    <div
                      key={f.path}
                      role="option"
                      aria-selected={isActive}
                      className={`fe-switcher-item${isActive ? ' is-active' : ''}`}
                      data-testid={`open-file-option-${f.name}`}
                    >
                      <button
                        type="button"
                        className="fe-switcher-select"
                        onClick={() => {
                          onSelectTab && onSelectTab(f.path);
                          setIsSwitcherOpen(false);
                        }}
                      >
                        {getFileIcon(f.name)}
                        <span className="fe-switcher-text">
                          <span className="fe-switcher-name">{f.name}</span>
                          <span className="fe-switcher-path">{f.path}</span>
                        </span>
                        {f.isDirty && <span className="fe-dirty-dot" title="Unsaved changes" />}
                        {isActive && <Check size={14} className="fe-switcher-check" />}
                      </button>
                      <button
                        type="button"
                        className="fe-tab-close"
                        onClick={(e) => handleRequestCloseTab(f, e)}
                        aria-label={`Close ${f.name}`}
                        title={`Close ${f.name}`}
                      >
                        <X size={13} />
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Global Close Panel Button */}
        <button
          type="button"
          onClick={onClose}
          data-testid="close-panel-btn"
          className="fe-icon-btn fe-close-panel"
          title="Collapse Panel"
          aria-label={layout === 'fullscreen' ? 'Close editor and return to the notebook' : 'Collapse Panel'}
        >
          <X size={15} />
        </button>
      </div>

      {/* 2. File Toolbar: active file, save state, actions */}
      {currentFile && (
        <div className="fe-toolbar">
          <div className="fe-active-file" data-testid="active-file-indicator">
            {getFileIcon(currentFile.name)}
            <div className="fe-active-file-text">
              <span className="fe-active-file-name" title={currentFile.path}>
                {currentFile.name}
              </span>
              {directory && <span className="fe-active-file-dir">{directory}</span>}
            </div>
            <span className={`fe-status${currentFile.isDirty ? ' is-dirty' : ''}`}>
              {currentFile.isDirty ? <AlertCircle size={10} /> : <CheckCircle2 size={10} />}
              {currentFile.isDirty ? 'Unsaved Changes' : 'Saved'}
            </span>
          </div>

          {/* Action Controls */}
          <div className="fe-actions">
            {/* CSV view toggle */}
            {isCsv && (
              <button
                type="button"
                className="fe-btn"
                onClick={() => setCsvViewMode(csvViewMode === 'table' ? 'text' : 'table')}
                title="Toggle Table / Text View"
              >
                {csvViewMode === 'table' ? <Code size={12} /> : <Table size={12} />}
                {csvViewMode === 'table' ? 'Raw Text' : 'Table'}
              </button>
            )}

            {/* Markdown view toggle */}
            {isMarkdown && (
              <button
                type="button"
                className="fe-btn"
                onClick={() => setMdViewMode(mdViewMode === 'preview' ? 'edit' : 'preview')}
                title="Toggle Preview / Edit"
              >
                {mdViewMode === 'preview' ? <Edit3 size={12} /> : <Eye size={12} />}
                {mdViewMode === 'preview' ? 'Edit' : 'Preview'}
              </button>
            )}

            {/* Save Button */}
            {!isNotebook && !isImage && (
              <button
                type="button"
                className={`fe-btn${currentFile.isDirty ? ' fe-btn--primary' : ''}`}
                onClick={handleSaveClick}
                disabled={isSaving || !currentFile.isDirty}
                title="Save Changes (Ctrl+S)"
                data-testid="file-save-btn"
              >
                <Save size={12} />
                {isSaving ? 'Saving...' : 'Save'}
              </button>
            )}

            {/* Download Button */}
            <a
              href={api.getDownloadUrl(currentFile.path)}
              download={currentFile.name}
              className="fe-btn fe-btn--icon"
              title="Download File"
              aria-label="Download File"
            >
              <Download size={13} />
            </a>
          </div>
        </div>
      )}

      {/* 3. Editor / Preview Body */}
      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', backgroundColor: 'var(--bg-panel)', display: 'flex', flexDirection: 'column' }}>
        {!currentFile ? (
          <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
            No file opened. Double-click a file in the left sidebar to preview and edit here.
          </div>
        ) : isImage ? (
          /* Image Preview */
          <div style={{ padding: '24px', display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
            <img
              src={`/api/v1/files/download?path=${encodeURIComponent(currentFile.path)}`}
              alt={currentFile.name}
              style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain', borderRadius: '6px', border: '1px solid var(--border-main)' }}
            />
          </div>
        ) : isNotebook ? (
          /* Notebook file notice & quick open */
          <div style={{ padding: '20px', color: 'var(--text-main)', fontSize: '13px', lineHeight: 1.6 }}>
            <div style={{ padding: '16px', backgroundColor: 'var(--bg-card)', borderRadius: '8px', border: '1px solid var(--border-secondary)' }}>
              <div style={{ fontWeight: 600, color: 'var(--accent)', fontSize: '15px', marginBottom: '8px' }}>
                Jupyter Notebook (.ipynb)
              </div>
              <p style={{ marginBottom: '16px', color: 'var(--text-secondary)' }}>
                This is a native Jupyter Notebook document with interactive executable cells and outputs.
              </p>
              {onOpenAsNotebook && (
                <button
                  type="button"
                  className="pcs-btn pcs-btn--primary"
                  onClick={() => onOpenAsNotebook(currentFile.path)}
                >
                  <ExternalLink size={14} /> Open in Active Notebook Studio
                </button>
              )}
            </div>
          </div>
        ) : isCsv && csvViewMode === 'table' ? (
          /* CSV Table Preview */
          <div style={{ flex: 1, overflow: 'auto', padding: '12px' }}>
            {(() => {
              const { headers, rows } = parseCsv(currentFile.content);
              if (headers.length === 0) {
                return <div style={{ color: 'var(--text-muted)', fontSize: '13px', padding: '12px' }}>Empty CSV file</div>;
              }
              return (
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', color: 'var(--text-main)' }}>
                  <thead>
                    <tr style={{ backgroundColor: 'var(--bg-card)', borderBottom: '2px solid var(--border-secondary)' }}>
                      {headers.map((h, i) => (
                        <th key={i} style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, color: 'var(--accent)', whiteSpace: 'nowrap' }}>
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row, rIdx) => (
                      <tr
                        key={rIdx}
                        style={{
                          borderBottom: '1px solid var(--border-main)',
                          backgroundColor: rIdx % 2 === 0 ? 'var(--bg-panel)' : 'var(--bg-cell-header)',
                        }}
                      >
                        {row.map((cell, cIdx) => (
                          <td key={cIdx} style={{ padding: '6px 12px', whiteSpace: 'nowrap' }}>
                            {cell}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              );
            })()}
          </div>
        ) : isMarkdown && mdViewMode === 'preview' ? (
          /* Markdown Rendered Preview */
          <div style={{ padding: '20px', color: 'var(--text-main)', fontSize: '13.5px', lineHeight: 1.7, overflowWrap: 'anywhere' }}>
            {currentFile.content.split('\n').map((line, i) => {
              if (line.startsWith('# ')) return <h1 key={i} style={{ fontSize: '20px', fontWeight: 700, margin: '12px 0 6px 0', color: 'var(--accent)' }}>{line.slice(2)}</h1>;
              if (line.startsWith('## ')) return <h2 key={i} style={{ fontSize: '16px', fontWeight: 600, margin: '10px 0 4px 0', color: 'var(--accent)' }}>{line.slice(3)}</h2>;
              if (line.startsWith('### ')) return <h3 key={i} style={{ fontSize: '14px', fontWeight: 600, margin: '8px 0 4px 0', color: 'var(--text-main)' }}>{line.slice(4)}</h3>;
              if (line.startsWith('- ')) return <li key={i} style={{ marginLeft: '16px' }}>{line.slice(2)}</li>;
              if (line.startsWith('```')) return <pre key={i} className="code-font" style={{ backgroundColor: 'var(--bg-card)', padding: '8px', borderRadius: '4px', margin: '8px 0', color: 'var(--accent)', fontSize: '12px', overflowX: 'auto' }}>{line}</pre>;
              return <p key={i} style={{ margin: '4px 0' }}>{line}</p>;
            })}
          </div>
        ) : (
          /* Standard Code / Text Editor with Line Numbers. Keyed by path: each file gets a fresh
             textarea whose cursor, selection and scroll position are restored from viewStatesRef. */
          <CodeTextEditor
            key={currentFile.path}
            file={currentFile}
            viewStates={viewStatesRef.current}
            onChange={(value) => onContentChange(value, currentFile.path)}
            onKeyDown={handleEditorKeyDown}
          />
        )}
      </div>

      {/* 4. Footer Info */}
      {currentFile && (
        <div className="fe-footer">
          <span className="fe-footer-path">{currentFile.path}</span>
          <span style={{ flexShrink: 0 }}>
            {currentFile.content.split('\n').length} lines • {currentFile.content.length} chars
          </span>
        </div>
      )}

      {/* 5. UNSAVED CHANGES CONFIRMATION MODAL */}
      {confirmCloseFile && (
        <Modal
          onClose={handleModalCancel}
          label="Unsaved changes"
          size="sm"
          testId="unsaved-changes-modal"
        >
          <ModalHeader
            icon={<AlertTriangle size={17} />}
            iconBackground="#d97706"
            title="Unsaved Changes"
            subtitle={confirmCloseFile.name}
            onClose={handleModalCancel}
          />
          <ModalBody>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              Do you want to save the changes you made to <strong>"{confirmCloseFile.name}"</strong> before closing?
            </p>
          </ModalBody>
          <ModalFooter>
            <button type="button" className="pcs-btn" onClick={handleModalCancel} data-testid="modal-cancel-btn">
              Cancel
            </button>
            <button
              type="button"
              className="pcs-btn pcs-btn--danger"
              onClick={handleModalDiscardAndClose}
              data-testid="modal-discard-changes-btn"
            >
              Discard Changes
            </button>
            <button
              type="button"
              className="pcs-btn pcs-btn--primary"
              onClick={handleModalSaveAndClose}
              disabled={isSaving}
              data-testid="modal-save-and-close-btn"
            >
              Save and Close
            </button>
          </ModalFooter>
        </Modal>
      )}
    </aside>
  );
};

interface CodeTextEditorProps {
  file: OpenFileInfo;
  viewStates: Map<string, EditorViewState>;
  onChange: (value: string) => void;
  onKeyDown: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
}

/*
 * Line-numbered text editor for one file. The textarea owns the scrolling; the gutter follows its
 * vertical scroll, so line numbers stay aligned on any screen size and with long files. Python files
 * get syntax highlighting: a coloured layer under the textarea (whose own text is transparent) that
 * follows both scroll axes.
 */
const CodeTextEditor: React.FC<CodeTextEditorProps> = ({ file, viewStates, onChange, onKeyDown }) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const gutterInnerRef = useRef<HTMLDivElement>(null);
  const highlightInnerRef = useRef<HTMLDivElement>(null);
  const [caret, setCaret] = useState<number | null>(null);
  const lineCount = file.content.split('\n').length;
  const isPython = file.path.toLowerCase().endsWith('.py');
  const tokens = useMemo(() => (isPython ? tokenizePython(file.content) : []), [isPython, file.content]);
  const highlighted = useMemo(() => {
    if (!isPython) return null;
    const pair = caret === null ? null : findBracketPair(file.content, tokens, caret);
    return renderHighlightedLines(file.content, tokens, pair ?? []);
  }, [isPython, file.content, tokens, caret]);

  const syncGutter = () => {
    const el = textareaRef.current;
    if (!el) return;
    if (gutterInnerRef.current) gutterInnerRef.current.style.transform = `translateY(${-el.scrollTop}px)`;
    if (highlightInnerRef.current) highlightInnerRef.current.style.transform = `translate(${-el.scrollLeft}px, ${-el.scrollTop}px)`;
  };

  const remember = () => {
    const el = textareaRef.current;
    if (!el) return;
    viewStates.set(file.path, {
      selectionStart: el.selectionStart,
      selectionEnd: el.selectionEnd,
      scrollTop: el.scrollTop,
      scrollLeft: el.scrollLeft,
    });
  };

  // Restore where the user was in this file; remember it again when switching away
  useLayoutEffect(() => {
    const el = textareaRef.current;
    const saved = viewStates.get(file.path);
    if (el && saved) {
      el.setSelectionRange(saved.selectionStart, saved.selectionEnd);
      el.scrollTop = saved.scrollTop;
      el.scrollLeft = saved.scrollLeft;
      syncGutter();
    }
    return remember;
    // Runs once per mounted file (the component is keyed by path)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="fe-code-editor">
      {/* Line numbers gutter */}
      <div className="fe-gutter code-font" aria-hidden="true">
        <div ref={gutterInnerRef} className="fe-gutter-inner">
          {Array.from({ length: lineCount }, (_, i) => (
            <div key={i}>{i + 1}</div>
          ))}
        </div>
      </div>

      <div className="fe-code-area">
      {highlighted && (
        <div className="fe-highlight code-font" aria-hidden="true" data-testid="file-highlight-layer">
          <div ref={highlightInnerRef} className="fe-highlight-inner">
            {highlighted}
          </div>
        </div>
      )}

      {/* Editable code text area */}
      <textarea
        ref={textareaRef}
        className={`code-font fe-textarea${highlighted ? ' fe-textarea--highlighted' : ''}`}
        value={file.content}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={onKeyDown}
        onScroll={() => {
          syncGutter();
          remember();
        }}
        onSelect={(e) => {
          remember();
          const el = e.currentTarget;
          setCaret(el.selectionStart === el.selectionEnd ? el.selectionStart : null);
        }}
        onBlur={() => setCaret(null)}
        aria-label={`Edit ${file.name}`}
        data-testid="file-editor-textarea"
        placeholder="Start typing file content..."
        spellCheck={false}
        autoComplete="off"
        autoCorrect="off"
        autoCapitalize="off"
      />
      </div>
    </div>
  );
};
