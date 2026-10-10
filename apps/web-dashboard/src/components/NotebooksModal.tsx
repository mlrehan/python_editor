import React, { useState, useEffect } from 'react';
import { BookOpen, Plus, Trash2, Download, Copy, Check, X, FileText, Calendar } from 'lucide-react';
import { api } from '../services/api';
import { NotebookDocument } from '../types';

interface NotebooksModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentNotebookId?: string;
  onSelectNotebook: (id: string) => void;
  onCreateNewNotebook: () => void;
  currentNotebookDoc?: NotebookDocument | null;
}

interface NotebookSummary {
  id: string;
  title: string;
  updated_at: string;
}

export const NotebooksModal: React.FC<NotebooksModalProps> = ({
  isOpen,
  onClose,
  currentNotebookId,
  onSelectNotebook,
  onCreateNewNotebook,
  currentNotebookDoc,
}) => {
  const [notebooks, setNotebooks] = useState<NotebookSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      loadNotebooks();
    }
  }, [isOpen]);

  const loadNotebooks = async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await api.listNotebooks();
      setNotebooks(list);
    } catch (err: any) {
      setError(err.message || 'Failed to load notebooks list');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: string, title: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm(`Delete notebook "${title}"? This cannot be undone.`)) return;
    try {
      await api.deleteNotebook(id);
      setNotebooks((prev) => prev.filter((n) => n.id !== id));
      if (currentNotebookId === id) {
        // If current was deleted, create new or reload
        onCreateNewNotebook();
      }
    } catch (err: any) {
      alert(`Failed to delete notebook: ${err.message}`);
    }
  };

  const handleExport = async (id: string, title: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      let doc: NotebookDocument;
      if (currentNotebookId === id && currentNotebookDoc) {
        doc = currentNotebookDoc;
      } else {
        doc = await api.getNotebook(id);
      }

      const ipynbContent = {
        nbformat: 4,
        nbformat_minor: 5,
        metadata: {
          kernelspec: {
            display_name: 'Python 3',
            language: 'python',
            name: doc.kernel_name || 'python3',
          },
          language_info: {
            name: 'python',
            version: '3.10',
          },
        },
        cells: doc.cells.map((c) => ({
          cell_type: c.cell_type,
          metadata: c.metadata || {},
          source: c.source.split('\n').map((line, idx, arr) => (idx < arr.length - 1 ? `${line}\n` : line)),
          outputs: c.outputs || [],
          execution_count: c.execution_count,
        })),
      };

      const blob = new Blob([JSON.stringify(ipynbContent, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${title.replace(/\s+/g, '_')}.ipynb`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err: any) {
      alert(`Export failed: ${err.message}`);
    }
  };

  const handleDuplicate = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      let doc: NotebookDocument;
      if (currentNotebookId === id && currentNotebookDoc) {
        doc = currentNotebookDoc;
      } else {
        doc = await api.getNotebook(id);
      }
      const newTitle = `${doc.title} (Copy)`;
      const created = await api.createNotebook(newTitle, doc.kernel_name);
      created.cells = doc.cells.map((c, i) => ({
        ...c,
        id: `cell-${i}-${Date.now()}`,
      }));
      await api.saveNotebook(created);
      await loadNotebooks();
      setCopiedId(created.id);
      setTimeout(() => setCopiedId(null), 3000);
    } catch (err: any) {
      alert(`Duplicate failed: ${err.message}`);
    }
  };

  if (!isOpen) return null;

  return (
    <div
      data-testid="notebooks-modal"
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.75)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        backdropFilter: 'blur(3px)',
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        style={{
          width: '640px',
          maxWidth: '92vw',
          maxHeight: '85vh',
          display: 'flex',
          flexDirection: 'column',
          backgroundColor: 'var(--bg-modal, #1e293b)',
          borderRadius: '12px',
          border: '1px solid var(--border-secondary, #334155)',
          boxShadow: '0 25px 50px rgba(0, 0, 0, 0.5)',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '16px 20px',
            borderBottom: '1px solid var(--border-main, #334155)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                backgroundColor: '#2563eb',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <BookOpen size={16} color="#ffffff" />
            </div>
            <div>
              <h2 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-main, #f8fafc)', margin: 0 }}>
                Notebooks Manager
              </h2>
              <span style={{ fontSize: '12px', color: 'var(--text-secondary, #94a3b8)' }}>
                Persistent workspace notebooks
              </span>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button
              onClick={() => {
                onCreateNewNotebook();
                onClose();
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 12px',
                backgroundColor: '#2563eb',
                color: '#ffffff',
                border: 'none',
                borderRadius: '6px',
                fontSize: '12.5px',
                fontWeight: 500,
                cursor: 'pointer',
              }}
              title="Create New Notebook"
            >
              <Plus size={14} /> New Notebook
            </button>
            <button
              onClick={onClose}
              style={{
                backgroundColor: 'transparent',
                border: 'none',
                color: 'var(--text-secondary, #94a3b8)',
                cursor: 'pointer',
                padding: '4px',
              }}
              title="Close"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Content List */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px 20px' }}>
          {loading && (
            <div style={{ textAlign: 'center', padding: '30px', color: 'var(--text-secondary, #94a3b8)' }}>
              Loading notebooks...
            </div>
          )}

          {error && (
            <div
              style={{
                padding: '10px 14px',
                backgroundColor: '#450a0a',
                border: '1px solid #ef4444',
                borderRadius: '6px',
                color: '#fca5a5',
                fontSize: '13px',
                marginBottom: '12px',
              }}
            >
              {error}
            </div>
          )}

          {!loading && notebooks.length === 0 && (
            <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--text-secondary, #94a3b8)' }}>
              <FileText size={36} style={{ margin: '0 auto 12px', opacity: 0.5 }} />
              <p style={{ margin: 0, fontSize: '14px' }}>No notebooks found</p>
              <p style={{ margin: '4px 0 0', fontSize: '12px' }}>Click "New Notebook" to create one.</p>
            </div>
          )}

          {!loading && notebooks.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {notebooks.map((nb) => {
                const isCurrent = nb.id === currentNotebookId;
                return (
                  <div
                    key={nb.id}
                    onClick={() => {
                      onSelectNotebook(nb.id);
                      onClose();
                    }}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '12px 16px',
                      backgroundColor: isCurrent ? 'var(--btn-secondary-bg, rgba(37, 99, 235, 0.15))' : 'var(--bg-input, rgba(255, 255, 255, 0.04))',
                      border: isCurrent ? '1px solid #3b82f6' : '1px solid var(--border-secondary, #334155)',
                      borderRadius: '8px',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', minWidth: 0, flex: 1 }}>
                      <FileText size={18} color={isCurrent ? '#3b82f6' : 'var(--text-secondary, #94a3b8)'} />
                      <div style={{ minWidth: 0 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span
                            style={{
                              fontSize: '14px',
                              fontWeight: 600,
                              color: isCurrent ? '#60a5fa' : 'var(--text-main, #f8fafc)',
                              whiteSpace: 'nowrap',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                            }}
                          >
                            {nb.title}
                          </span>
                          {isCurrent && (
                            <span
                              style={{
                                fontSize: '10px',
                                padding: '1px 6px',
                                backgroundColor: '#1d4ed8',
                                color: '#ffffff',
                                borderRadius: '4px',
                                fontWeight: 500,
                              }}
                            >
                              Active
                            </span>
                          )}
                          {copiedId === nb.id && (
                            <span
                              style={{
                                fontSize: '10px',
                                padding: '1px 6px',
                                backgroundColor: '#065f46',
                                color: '#6ee7b7',
                                borderRadius: '4px',
                                fontWeight: 500,
                                display: 'flex',
                                alignItems: 'center',
                                gap: '2px',
                              }}
                            >
                              <Check size={10} /> Copied
                            </span>
                          )}
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11.5px', color: 'var(--text-secondary, #94a3b8)', marginTop: '2px' }}>
                          <Calendar size={12} />
                          <span>Last modified: {new Date(nb.updated_at).toLocaleString()}</span>
                        </div>
                      </div>
                    </div>

                    {/* Actions */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginLeft: '12px' }}>
                      <button
                        onClick={(e) => handleDuplicate(nb.id, e)}
                        style={{
                          backgroundColor: 'transparent',
                          border: '1px solid var(--border-secondary, #334155)',
                          borderRadius: '6px',
                          color: 'var(--text-secondary, #94a3b8)',
                          padding: '5px 8px',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px',
                          fontSize: '11.5px',
                        }}
                        title="Duplicate Notebook"
                      >
                        <Copy size={13} />
                        <span className="hidden sm:inline">Duplicate</span>
                      </button>
                      <button
                        onClick={(e) => handleExport(nb.id, nb.title, e)}
                        style={{
                          backgroundColor: 'transparent',
                          border: '1px solid var(--border-secondary, #334155)',
                          borderRadius: '6px',
                          color: 'var(--text-secondary, #94a3b8)',
                          padding: '5px 8px',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px',
                          fontSize: '11.5px',
                        }}
                        title="Export as .ipynb"
                      >
                        <Download size={13} />
                        <span className="hidden sm:inline">Export</span>
                      </button>
                      <button
                        onClick={(e) => handleDelete(nb.id, nb.title, e)}
                        style={{
                          backgroundColor: 'transparent',
                          border: '1px solid var(--border-secondary, #334155)',
                          borderRadius: '6px',
                          color: '#ef4444',
                          padding: '5px 8px',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px',
                          fontSize: '11.5px',
                        }}
                        title="Delete Notebook"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

