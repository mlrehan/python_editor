import React, { useState, useEffect } from 'react';
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
} from 'lucide-react';
import { api } from '../services/api';

export interface OpenFileInfo {
  path: string;
  name: string;
  content: string;
  isDirty: boolean;
}

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
}) => {
  const [isSaving, setIsSaving] = useState(false);
  const [csvViewMode, setCsvViewMode] = useState<'table' | 'text'>('table');
  const [mdViewMode, setMdViewMode] = useState<'edit' | 'preview'>('preview');

  // Unsaved Changes Confirmation Modal state
  const [confirmCloseFile, setConfirmCloseFile] = useState<OpenFileInfo | null>(null);

  // Normalize files list: if openFiles provided, use it, else fallback to single file
  const filesList: OpenFileInfo[] = openFiles.length > 0 ? openFiles : file ? [file] : [];
  const currentFile: OpenFileInfo | null =
    filesList.find((f) => f.path === activeFilePath) ||
    (filesList.length > 0 ? filesList[0] : file || null);

  // Handle Ctrl+S / Cmd+S
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        if (isOpen && currentFile) {
          e.preventDefault();
          handleSaveClick();
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, currentFile]);

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

  return (
    <aside
      data-testid="right-file-editor-panel"
      style={{
        width: `${width}px`,
        maxWidth: `${width}px`,
        minWidth: `${width}px`,
        backgroundColor: 'var(--bg-sidebar)',
        borderLeft: '1px solid var(--border-main)',
        display: 'flex',
        flexDirection: 'column',
        height: 'calc(100vh - 56px)',
        zIndex: 20,
        boxShadow: '-4px 0 16px rgba(0,0,0,0.3)',
        flexShrink: 0,
        position: 'relative',
      }}
    >
      {/* 1. Multi-Tab Bar */}
      <div
        data-testid="file-tabs-bar"
        style={{
          height: '38px',
          backgroundColor: 'var(--bg-sidebar-header)',
          borderBottom: '1px solid var(--border-main)',
          display: 'flex',
          alignItems: 'center',
          overflowX: 'auto',
          overflowY: 'hidden',
          scrollbarWidth: 'none',
          position: 'relative',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', flex: 1, minWidth: 0 }}>
          {filesList.map((f) => {
            const isActive = currentFile?.path === f.path;
            return (
              <div
                key={f.path}
                data-testid={`file-tab-${f.name}`}
                onClick={() => onSelectTab && onSelectTab(f.path)}
                style={{
                  height: '38px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '0 12px',
                  backgroundColor: isActive ? 'var(--bg-card)' : 'transparent',
                  borderRight: '1px solid var(--border-main)',
                  borderTop: isActive ? '2px solid var(--border-accent)' : '2px solid transparent',
                  color: isActive ? 'var(--text-main)' : 'var(--text-secondary)',
                  fontSize: '12px',
                  fontWeight: isActive ? 600 : 400,
                  cursor: 'pointer',
                  userSelect: 'none',
                  whiteSpace: 'nowrap',
                  maxWidth: '180px',
                  transition: 'background-color 0.1s ease',
                }}
                title={f.path}
              >
                {getFileIcon(f.name)}
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{f.name}</span>

                {/* Unsaved dirty dot indicator */}
                {f.isDirty && (
                  <span
                    data-testid={`dirty-indicator-${f.name}`}
                    style={{
                      width: '7px',
                      height: '7px',
                      borderRadius: '50%',
                      backgroundColor: '#f59e0b',
                      flexShrink: 0,
                      marginLeft: '2px',
                    }}
                    title="Unsaved changes"
                  />
                )}

                {/* Tab Close (X) button */}
                <button
                  data-testid={`close-tab-${f.name}`}
                  onClick={(e) => handleRequestCloseTab(f, e)}
                  style={{
                    backgroundColor: 'transparent',
                    border: 'none',
                    color: '#64748b',
                    padding: '2px',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    marginLeft: '4px',
                    flexShrink: 0,
                  }}
                  onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.color = '#ef4444')}
                  onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.color = '#64748b')}
                  title={`Close ${f.name}`}
                >
                  <X size={13} />
                </button>
              </div>
            );
          })}
        </div>

        {/* Global Close Panel Button */}
        <button
          onClick={onClose}
          data-testid="close-panel-btn"
          style={{
            height: '38px',
            backgroundColor: '#090d16',
            border: 'none',
            borderLeft: '1px solid #1e293b',
            color: '#94a3b8',
            padding: '0 10px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}
          title="Collapse Panel"
        >
          <X size={15} />
        </button>
      </div>

      {/* 2. File Toolbar */}
      {currentFile && (
        <div
          style={{
            height: '42px',
            backgroundColor: 'var(--bg-sidebar-header)',
            borderBottom: '1px solid var(--border-main)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 12px',
            gap: '8px',
          }}
        >
          {/* File Status */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden', flex: 1 }}>
            <span
              style={{
                fontSize: '10px',
                padding: '2px 6px',
                borderRadius: '4px',
                backgroundColor: currentFile.isDirty ? '#451a03' : '#064e3b',
                color: currentFile.isDirty ? '#f59e0b' : '#10b981',
                display: 'flex',
                alignItems: 'center',
                gap: '3px',
              }}
            >
              {currentFile.isDirty ? <AlertCircle size={10} /> : <CheckCircle2 size={10} />}
              {currentFile.isDirty ? 'Unsaved Changes' : 'Saved'}
            </span>
          </div>

          {/* Action Controls */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            {/* CSV view toggle */}
            {isCsv && (
              <button
                onClick={() => setCsvViewMode(csvViewMode === 'table' ? 'text' : 'table')}
                style={{
                  backgroundColor: '#1e293b',
                  border: '1px solid #334155',
                  color: '#cbd5e1',
                  borderRadius: '4px',
                  padding: '4px 8px',
                  fontSize: '11px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                }}
                title="Toggle Table / Text View"
              >
                {csvViewMode === 'table' ? <Code size={12} /> : <Table size={12} />}
                {csvViewMode === 'table' ? 'Raw Text' : 'Table'}
              </button>
            )}

            {/* Markdown view toggle */}
            {isMarkdown && (
              <button
                onClick={() => setMdViewMode(mdViewMode === 'preview' ? 'edit' : 'preview')}
                style={{
                  backgroundColor: '#1e293b',
                  border: '1px solid #334155',
                  color: '#cbd5e1',
                  borderRadius: '4px',
                  padding: '4px 8px',
                  fontSize: '11px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                }}
                title="Toggle Preview / Edit"
              >
                {mdViewMode === 'preview' ? <Edit3 size={12} /> : <Eye size={12} />}
                {mdViewMode === 'preview' ? 'Edit' : 'Preview'}
              </button>
            )}

            {/* Save Button */}
            {!isNotebook && !isImage && (
              <button
                onClick={handleSaveClick}
                disabled={isSaving || !currentFile.isDirty}
                style={{
                  backgroundColor: currentFile.isDirty ? '#2563eb' : '#1e293b',
                  border: '1px solid #334155',
                  color: currentFile.isDirty ? '#ffffff' : '#64748b',
                  borderRadius: '4px',
                  padding: '4px 8px',
                  fontSize: '11px',
                  fontWeight: 600,
                  cursor: currentFile.isDirty ? 'pointer' : 'default',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                }}
                title="Save Changes (Ctrl+S)"
              >
                <Save size={12} />
                {isSaving ? 'Saving...' : 'Save'}
              </button>
            )}

            {/* Download Button */}
            <a
              href={api.getDownloadUrl(currentFile.path)}
              download={currentFile.name}
              style={{
                backgroundColor: '#1e293b',
                border: '1px solid #334155',
                color: '#94a3b8',
                borderRadius: '4px',
                padding: '4px 6px',
                display: 'flex',
                alignItems: 'center',
                cursor: 'pointer',
                textDecoration: 'none',
              }}
              title="Download File"
            >
              <Download size={13} />
            </a>
          </div>
        </div>
      )}

      {/* 3. Editor / Preview Body */}
      <div style={{ flex: 1, overflowY: 'auto', backgroundColor: 'var(--bg-panel)', display: 'flex', flexDirection: 'column' }}>
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
              style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain', borderRadius: '6px', border: '1px solid #1e293b' }}
            />
          </div>
        ) : isNotebook ? (
          /* Notebook file notice & quick open */
          <div style={{ padding: '28px', color: '#cbd5e1', fontSize: '13px', lineHeight: 1.6 }}>
            <div style={{ padding: '16px', backgroundColor: '#1e293b', borderRadius: '8px', border: '1px solid #334155' }}>
              <div style={{ fontWeight: 600, color: '#38bdf8', fontSize: '15px', marginBottom: '8px' }}>
                Jupyter Notebook (.ipynb)
              </div>
              <p style={{ marginBottom: '16px', color: '#94a3b8' }}>
                This is a native Jupyter Notebook document with interactive executable cells and outputs.
              </p>
              {onOpenAsNotebook && (
                <button
                  onClick={() => onOpenAsNotebook(currentFile.path)}
                  style={{
                    backgroundColor: '#2563eb',
                    border: 'none',
                    color: '#ffffff',
                    borderRadius: '6px',
                    padding: '8px 14px',
                    fontSize: '13px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                  }}
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
                return <div style={{ color: '#64748b', fontSize: '13px', padding: '12px' }}>Empty CSV file</div>;
              }
              return (
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', color: '#e2e8f0' }}>
                  <thead>
                    <tr style={{ backgroundColor: '#1e293b', borderBottom: '2px solid #334155' }}>
                      {headers.map((h, i) => (
                        <th key={i} style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, color: '#38bdf8' }}>
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row, rIdx) => (
                      <tr key={rIdx} style={{ borderBottom: '1px solid #1e293b', backgroundColor: rIdx % 2 === 0 ? '#0b1120' : '#0f172a' }}>
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
          <div style={{ padding: '20px', color: '#e2e8f0', fontSize: '13.5px', lineHeight: 1.7 }}>
            {currentFile.content.split('\n').map((line, i) => {
              if (line.startsWith('# ')) return <h1 key={i} style={{ fontSize: '20px', fontWeight: 700, margin: '12px 0 6px 0', color: '#38bdf8' }}>{line.slice(2)}</h1>;
              if (line.startsWith('## ')) return <h2 key={i} style={{ fontSize: '16px', fontWeight: 600, margin: '10px 0 4px 0', color: '#60a5fa' }}>{line.slice(3)}</h2>;
              if (line.startsWith('### ')) return <h3 key={i} style={{ fontSize: '14px', fontWeight: 600, margin: '8px 0 4px 0', color: '#93c5fd' }}>{line.slice(4)}</h3>;
              if (line.startsWith('- ')) return <li key={i} style={{ marginLeft: '16px' }}>{line.slice(2)}</li>;
              if (line.startsWith('```')) return <pre key={i} className="code-font" style={{ backgroundColor: '#1e293b', padding: '8px', borderRadius: '4px', margin: '8px 0', color: '#38bdf8', fontSize: '12px' }}>{line}</pre>;
              return <p key={i} style={{ margin: '4px 0' }}>{line}</p>;
            })}
          </div>
        ) : (
          /* Standard Code / Text Editor with Line Numbers */
          <div style={{ display: 'flex', flex: 1, minHeight: '100%', position: 'relative' }}>
            {/* Line numbers gutter */}
            <div
              className="code-font"
              style={{
                width: '42px',
                padding: '12px 6px',
                backgroundColor: 'var(--bg-cell-gutter)',
                borderRight: '1px solid var(--border-main)',
                color: 'var(--text-muted)',
                textAlign: 'right',
                userSelect: 'none',
                fontSize: '12.5px',
                lineHeight: 1.6,
              }}
            >
              {currentFile.content.split('\n').map((_, i) => (
                <div key={i}>{i + 1}</div>
              ))}
            </div>

            {/* Editable code text area */}
            <textarea
              className="code-font"
              value={currentFile.content}
              onChange={(e) => onContentChange(e.target.value, currentFile.path)}
              style={{
                flex: 1,
                padding: '12px',
                backgroundColor: 'transparent',
                border: 'none',
                outline: 'none',
                color: 'var(--code-text)',
                fontSize: '12.5px',
                lineHeight: 1.6,
                resize: 'none',
                whiteSpace: 'pre',
                overflowWrap: 'normal',
                overflowX: 'auto',
              }}
              placeholder="Start typing file content..."
              spellCheck={false}
            />
          </div>
        )}
      </div>

      {/* 4. Footer Info */}
      {currentFile && (
        <div
          style={{
            height: '28px',
            backgroundColor: 'var(--bg-sidebar-header)',
            borderTop: '1px solid var(--border-main)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 12px',
            fontSize: '11px',
            color: 'var(--text-muted)',
          }}
        >
          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '240px' }}>
            {currentFile.path}
          </span>
          <span>
            {currentFile.content.split('\n').length} lines • {currentFile.content.length} chars
          </span>
        </div>
      )}

      {/* 5. UNSAVED CHANGES CONFIRMATION MODAL */}
      {confirmCloseFile && (
        <div
          data-testid="unsaved-changes-modal"
          style={{
            position: 'absolute',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.7)',
            backdropFilter: 'blur(2px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '20px',
            zIndex: 100,
          }}
        >
          <div
            style={{
              backgroundColor: 'var(--bg-modal)',
              border: '1px solid var(--border-secondary)',
              borderRadius: '8px',
              padding: '20px',
              width: '100%',
              maxWidth: '360px',
              boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.4)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
              <AlertTriangle size={18} color="#f59e0b" />
              <h3 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-main)' }}>Unsaved Changes</h3>
            </div>
            <p style={{ fontSize: '12.5px', color: 'var(--text-secondary)', lineHeight: 1.5, marginBottom: '20px' }}>
              Do you want to save the changes you made to <strong>"{confirmCloseFile.name}"</strong> before closing?
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <button
                onClick={handleModalSaveAndClose}
                disabled={isSaving}
                data-testid="modal-save-and-close-btn"
                style={{
                  backgroundColor: '#2563eb',
                  border: 'none',
                  color: '#ffffff',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  fontSize: '12px',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Save and Close
              </button>
              <button
                onClick={handleModalDiscardAndClose}
                data-testid="modal-discard-changes-btn"
                style={{
                  backgroundColor: '#450a0a',
                  border: '1px solid #7f1d1d',
                  color: '#f87171',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  fontSize: '12px',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Discard Changes
              </button>
              <button
                onClick={handleModalCancel}
                data-testid="modal-cancel-btn"
                style={{
                  backgroundColor: 'var(--btn-secondary-bg)',
                  border: '1px solid var(--btn-secondary-border)',
                  color: 'var(--text-secondary)',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  fontSize: '12px',
                  cursor: 'pointer',
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
};
