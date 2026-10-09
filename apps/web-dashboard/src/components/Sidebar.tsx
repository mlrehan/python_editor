import React, { useState, useEffect } from 'react';
import { Files, BookOpen, GraduationCap, Plus, Folder, FileCode, FileSpreadsheet, RefreshCw } from 'lucide-react';
import { FileItem } from '../types';
import { api } from '../services/api';

interface SidebarProps {
  currentNotebookId: string;
  onSelectNotebook: (id: string) => void;
  onCreateNotebook: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentNotebookId,
  onSelectNotebook,
  onCreateNotebook,
}) => {
  const [activeTab, setActiveTab] = useState<'notebooks' | 'files' | 'classrooms'>('notebooks');
  const [notebookList, setNotebookList] = useState<Array<{ id: string; title: string; updated_at: string }>>([]);
  const [fileList, setFileList] = useState<FileItem[]>([]);

  const loadData = async () => {
    try {
      if (activeTab === 'notebooks') {
        const nbs = await api.listNotebooks();
        setNotebookList(nbs);
      } else if (activeTab === 'files') {
        const files = await api.listFiles();
        setFileList(files);
      }
    } catch (err) {
      console.warn('Failed to load sidebar data:', err);
    }
  };

  useEffect(() => {
    loadData();
  }, [activeTab]);

  return (
    <aside style={{
      width: '280px',
      backgroundColor: '#0f172a',
      borderRight: '1px solid #1e293b',
      display: 'flex',
      flexDirection: 'column',
      height: 'calc(100vh - 56px)'
    }}>
      {/* Tab Switcher */}
      <div style={{
        display: 'flex',
        borderBottom: '1px solid #1e293b',
        backgroundColor: '#0b1120'
      }}>
        <button
          onClick={() => setActiveTab('notebooks')}
          style={{
            flex: 1,
            padding: '10px 0',
            backgroundColor: 'transparent',
            border: 'none',
            borderBottom: activeTab === 'notebooks' ? '2px solid #3b82f6' : 'none',
            color: activeTab === 'notebooks' ? '#3b82f6' : '#64748b',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '6px',
            fontSize: '12px',
            fontWeight: 500,
            cursor: 'pointer'
          }}
        >
          <BookOpen size={15} />
          Notebooks
        </button>
        <button
          onClick={() => setActiveTab('files')}
          style={{
            flex: 1,
            padding: '10px 0',
            backgroundColor: 'transparent',
            border: 'none',
            borderBottom: activeTab === 'files' ? '2px solid #3b82f6' : 'none',
            color: activeTab === 'files' ? '#3b82f6' : '#64748b',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '6px',
            fontSize: '12px',
            fontWeight: 500,
            cursor: 'pointer'
          }}
        >
          <Files size={15} />
          Files
        </button>
        <button
          onClick={() => setActiveTab('classrooms')}
          style={{
            flex: 1,
            padding: '10px 0',
            backgroundColor: 'transparent',
            border: 'none',
            borderBottom: activeTab === 'classrooms' ? '2px solid #3b82f6' : 'none',
            color: activeTab === 'classrooms' ? '#3b82f6' : '#64748b',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '6px',
            fontSize: '12px',
            fontWeight: 500,
            cursor: 'pointer'
          }}
        >
          <GraduationCap size={15} />
          Classes
        </button>
      </div>

      {/* Action Header */}
      <div style={{
        padding: '10px 14px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        borderBottom: '1px solid #1e293b'
      }}>
        <span style={{ fontSize: '11px', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          {activeTab === 'notebooks' ? 'Your Notebooks' : activeTab === 'files' ? 'Workspace Files' : 'Classrooms'}
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          {activeTab === 'notebooks' && (
            <button
              onClick={onCreateNotebook}
              style={{
                backgroundColor: '#2563eb',
                color: '#ffffff',
                border: 'none',
                borderRadius: '4px',
                padding: '4px 8px',
                fontSize: '11px',
                fontWeight: 500,
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                cursor: 'pointer'
              }}
            >
              <Plus size={13} /> New
            </button>
          )}
          <button
            onClick={loadData}
            style={{
              backgroundColor: 'transparent',
              border: 'none',
              color: '#64748b',
              cursor: 'pointer',
              padding: '4px'
            }}
            title="Refresh"
          >
            <RefreshCw size={13} />
          </button>
        </div>
      </div>

      {/* Tab Content List */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '8px' }}>
        {activeTab === 'notebooks' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {notebookList.map((nb) => {
              const isSelected = nb.id === currentNotebookId;
              return (
                <div
                  key={nb.id}
                  onClick={() => onSelectNotebook(nb.id)}
                  style={{
                    padding: '8px 10px',
                    borderRadius: '6px',
                    backgroundColor: isSelected ? '#1e293b' : 'transparent',
                    border: isSelected ? '1px solid #3b82f6' : '1px solid transparent',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    color: isSelected ? '#ffffff' : '#94a3b8'
                  }}
                >
                  <FileCode size={15} color={isSelected ? '#3b82f6' : '#64748b'} />
                  <div style={{ flex: 1, overflow: 'hidden' }}>
                    <div style={{ fontSize: '13px', fontWeight: 500, whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>
                      {nb.title}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {activeTab === 'files' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {fileList.length === 0 ? (
              <div style={{ padding: '16px', textAlign: 'center', color: '#64748b', fontSize: '12px' }}>
                No files in workspace.<br />Uploaded CSVs and datasets will appear here.
              </div>
            ) : (
              fileList.map((file) => (
                <div
                  key={file.path}
                  style={{
                    padding: '6px 10px',
                    borderRadius: '4px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    fontSize: '12px',
                    color: '#cbd5e1'
                  }}
                >
                  {file.is_dir ? <Folder size={14} color="#f59e0b" /> : file.name.endsWith('.csv') ? <FileSpreadsheet size={14} color="#10b981" /> : <FileCode size={14} color="#94a3b8" />}
                  <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {file.name}
                  </span>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'classrooms' && (
          <div style={{ padding: '16px', color: '#94a3b8', fontSize: '12px' }}>
            <p style={{ marginBottom: '8px', fontWeight: 500, color: '#f8fafc' }}>Connected Courses</p>
            <p>Enroll in a classroom via join code or access instructor assigned exercises.</p>
          </div>
        )}
      </div>
    </aside>
  );
};
