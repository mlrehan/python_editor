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
} from 'lucide-react';
import { api } from '../services/api';

export interface OpenFileInfo {
  path: string;
  name: string;
  content: string;
  isDirty: boolean;
}

interface FileEditorPanelProps {
  file: OpenFileInfo | null;
  isOpen: boolean;
  onClose: () => void;
  onSave: (path: string, newContent: string) => Promise<void>;
  onContentChange: (newContent: string) => void;
  onOpenAsNotebook?: (path: string) => void;
}

export const FileEditorPanel: React.FC<FileEditorPanelProps> = ({
  file,
  isOpen,
  onClose,
  onSave,
  onContentChange,
  onOpenAsNotebook,
}) => {
  const [isSaving, setIsSaving] = useState(false);
  const [csvViewMode, setCsvViewMode] = useState<'table' | 'text'>('table');
  const [mdViewMode, setMdViewMode] = useState<'edit' | 'preview'>('preview');

  // Handle Ctrl+S / Cmd+S
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        if (isOpen && file) {
          e.preventDefault();
          handleSaveClick();
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, file]);

  if (!isOpen) {
    return null;
  }

  const handleSaveClick = async () => {
    if (!file) return;
    setIsSaving(true);
    try {
      await onSave(file.path, file.content);
    } catch (err) {
      console.error('Failed to save file:', err);
    } finally {
      setIsSaving(false);
    }
  };

  const ext = file ? file.name.split('.').pop()?.toLowerCase() || '' : '';
  const isPython = ext === 'py';
  const isCsv = ext === 'csv';
  const isMarkdown = ext === 'md';
  const isJson = ext === 'json';
  const isNotebook = ext === 'ipynb';
  const isImage = ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'].includes(ext);

  const getFileIcon = () => {
    if (isPython) return <FileCode size={16} color="#3b82f6" />;
    if (isCsv) return <FileSpreadsheet size={16} color="#10b981" />;
    if (isMarkdown) return <FileText size={16} color="#a855f7" />;
    if (isJson) return <FileCode size={16} color="#f59e0b" />;
    return <File size={16} color="#94a3b8" />;
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
      style={{
        width: '440px',
        maxWidth: '45vw',
        minWidth: '320px',
        backgroundColor: '#0f172a',
        borderLeft: '1px solid #1e293b',
        display: 'flex',
        flexDirection: 'column',
        height: 'calc(100vh - 56px)',
        zIndex: 20,
        boxShadow: '-4px 0 16px rgba(0,0,0,0.3)',
      }}
    >
      {/* Header Toolbar */}
      <div
        style={{
          height: '46px',
          backgroundColor: '#131d31',
          borderBottom: '1px solid #1e293b',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 12px',
          gap: '8px',
        }}
      >
        {/* File Name & Status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden', flex: 1 }}>
          {getFileIcon()}
          <span
            style={{
              fontSize: '13px',
              fontWeight: 600,
              color: '#f8fafc',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}
            title={file?.path || ''}
          >
            {file ? file.name : 'No file selected'}
          </span>
          {file && (
            <span
              style={{
                fontSize: '10px',
                padding: '2px 6px',
                borderRadius: '4px',
                backgroundColor: file.isDirty ? '#451a03' : '#064e3b',
                color: file.isDirty ? '#f59e0b' : '#10b981',
                display: 'flex',
                alignItems: 'center',
                gap: '3px',
              }}
            >
              {file.isDirty ? <AlertCircle size={10} /> : <CheckCircle2 size={10} />}
              {file.isDirty ? 'Unsaved' : 'Saved'}
            </span>
          )}
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
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
          {file && !isNotebook && !isImage && (
            <button
              onClick={handleSaveClick}
              disabled={isSaving || !file.isDirty}
              style={{
                backgroundColor: file.isDirty ? '#2563eb' : '#1e293b',
                border: '1px solid #334155',
                color: file.isDirty ? '#ffffff' : '#64748b',
                borderRadius: '4px',
                padding: '4px 8px',
                fontSize: '11px',
                fontWeight: 600,
                cursor: file.isDirty ? 'pointer' : 'default',
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
          {file && (
            <a
              href={api.getDownloadUrl(file.path)}
              download={file.name}
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
          )}

          {/* Close Panel Button */}
          <button
            onClick={onClose}
            style={{
              backgroundColor: 'transparent',
              border: 'none',
              color: '#94a3b8',
              padding: '4px',
              cursor: 'pointer',
              borderRadius: '4px',
              display: 'flex',
              alignItems: 'center',
            }}
            title="Close Preview (Keeps changes intact)"
          >
            <X size={16} />
          </button>
        </div>
      </div>

      {/* Editor / Preview Body */}
      <div style={{ flex: 1, overflowY: 'auto', backgroundColor: '#090d16', display: 'flex', flexDirection: 'column' }}>
        {!file ? (
          <div style={{ padding: '32px', textAlign: 'center', color: '#64748b', fontSize: '13px' }}>
            No file opened. Double-click a file in the left sidebar to preview and edit here.
          </div>
        ) : isImage ? (
          /* Image Preview */
          <div style={{ padding: '24px', display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
            <img
              src={`/api/v1/files/download?path=${encodeURIComponent(file.path)}`}
              alt={file.name}
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
                  onClick={() => onOpenAsNotebook(file.path)}
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
              const { headers, rows } = parseCsv(file.content);
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
            {file.content.split('\n').map((line, i) => {
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
                backgroundColor: '#070b13',
                borderRight: '1px solid #1e293b',
                color: '#475569',
                textAlign: 'right',
                userSelect: 'none',
                fontSize: '12.5px',
                lineHeight: 1.6,
              }}
            >
              {file.content.split('\n').map((_, i) => (
                <div key={i}>{i + 1}</div>
              ))}
            </div>

            {/* Editable code text area */}
            <textarea
              className="code-font"
              value={file.content}
              onChange={(e) => onContentChange(e.target.value)}
              style={{
                flex: 1,
                padding: '12px',
                backgroundColor: 'transparent',
                border: 'none',
                outline: 'none',
                color: isPython ? '#93c5fd' : isJson ? '#fde047' : '#f1f5f9',
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

      {/* Footer Info */}
      {file && (
        <div
          style={{
            height: '28px',
            backgroundColor: '#0b1120',
            borderTop: '1px solid #1e293b',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 12px',
            fontSize: '11px',
            color: '#64748b',
          }}
        >
          <span>{file.path}</span>
          <span>
            {file.content.split('\n').length} lines • {file.content.length} chars
          </span>
        </div>
      )}
    </aside>
  );
};

