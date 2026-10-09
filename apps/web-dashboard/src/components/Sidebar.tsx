import React, { useState, useEffect, useRef } from 'react';
import {
  Folder,
  FolderOpen,
  FileCode,
  FileSpreadsheet,
  FileText,
  File,
  Plus,
  Upload,
  RefreshCw,
  Search,
  MoreVertical,
  Trash2,
  Edit2,
  Download,
  BookOpen,
  ChevronRight,
  ChevronDown,
} from 'lucide-react';
import { FileItem } from '../types';
import { api } from '../services/api';

interface SidebarProps {
  onOpenFile: (file: FileItem) => void;
  onOpenNotebookFile: (path: string) => void;
  onCreateNewNotebook: () => void;
  activeFilePath?: string;
}

export const Sidebar: React.FC<SidebarProps> = ({
  onOpenFile,
  onOpenNotebookFile,
  onCreateNewNotebook,
  activeFilePath,
}) => {
  const [files, setFiles] = useState<FileItem[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [expandedFolders, setExpandedFolders] = useState<Record<string, boolean>>({});

  // Context Menu State
  const [contextMenu, setContextMenu] = useState<{
    visible: boolean;
    x: number;
    y: number;
    target: FileItem | null;
  }>({ visible: false, x: 0, y: 0, target: null });

  // Dialog Modals State
  const [modalState, setModalState] = useState<{
    type: 'new_file' | 'new_folder' | 'rename' | 'delete' | null;
    target?: FileItem;
    inputValue?: string;
  }>({ type: null });

  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadFiles = async () => {
    try {
      const items = await api.listFiles();
      setFiles(items);
    } catch (err) {
      console.warn('Failed to load files:', err);
    }
  };

  useEffect(() => {
    loadFiles();
  }, []);

  // Close context menu on outside click
  useEffect(() => {
    const handleWindowClick = () => {
      if (contextMenu.visible) {
        setContextMenu({ visible: false, x: 0, y: 0, target: null });
      }
    };
    window.addEventListener('click', handleWindowClick);
    return () => window.removeEventListener('click', handleWindowClick);
  }, [contextMenu.visible]);

  // File Icon resolver
  const renderFileIcon = (file: FileItem) => {
    if (file.is_dir) {
      const isExpanded = expandedFolders[file.path];
      return isExpanded ? <FolderOpen size={16} color="#f59e0b" /> : <Folder size={16} color="#f59e0b" />;
    }
    const ext = file.name.split('.').pop()?.toLowerCase() || '';
    if (ext === 'py') return <FileCode size={15} color="#3b82f6" />;
    if (ext === 'csv') return <FileSpreadsheet size={15} color="#10b981" />;
    if (ext === 'md') return <FileText size={15} color="#a855f7" />;
    if (ext === 'ipynb') return <BookOpen size={15} color="#f97316" />;
    return <File size={15} color="#94a3b8" />;
  };

  // Click & Double Click Handlers
  const handleItemClick = (file: FileItem) => {
    setSelectedPath(file.path);
  };

  const handleItemDoubleClick = (file: FileItem) => {
    if (file.is_dir) {
      setExpandedFolders((prev) => ({ ...prev, [file.path]: !prev[file.path] }));
    } else if (file.name.endsWith('.ipynb')) {
      onOpenNotebookFile(file.path);
    } else {
      onOpenFile(file);
    }
  };

  const handleContextMenu = (e: React.MouseEvent, file: FileItem) => {
    e.preventDefault();
    e.stopPropagation();
    setSelectedPath(file.path);
    setContextMenu({
      visible: true,
      x: e.clientX,
      y: e.clientY,
      target: file,
    });
  };

  // Upload handler
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files) return;
    const uploadedFiles = Array.from(e.target.files);
    for (const file of uploadedFiles) {
      try {
        await api.uploadFile(file);
      } catch (err) {
        console.error('Failed to upload file:', err);
      }
    }
    loadFiles();
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  // Modal actions
  const handleConfirmModal = async () => {
    const { type, target, inputValue } = modalState;
    if (!type) return;

    try {
      if (type === 'new_file' && inputValue?.trim()) {
        const fname = inputValue.trim();
        await api.writeFile(fname, '');
        await loadFiles();
        if (fname.endsWith('.ipynb')) {
          onOpenNotebookFile(fname);
        } else {
          onOpenFile({
            name: fname,
            path: fname,
            is_dir: false,
            size: 0,
            modified_at: Date.now() / 1000,
          });
        }
      } else if (type === 'new_folder' && inputValue?.trim()) {
        await api.createFolder(inputValue.trim());
        await loadFiles();
      } else if (type === 'rename' && target && inputValue?.trim()) {
        const parts = target.path.split('/');
        parts.pop();
        const parent = parts.join('/');
        const newPath = parent ? `${parent}/${inputValue.trim()}` : inputValue.trim();
        await api.renameFile(target.path, newPath);
        await loadFiles();
      } else if (type === 'delete' && target) {
        await api.deleteFile(target.path);
        await loadFiles();
      }
    } catch (err: any) {
      alert(err.message || 'Operation failed');
    } finally {
      setModalState({ type: null });
    }
  };

  // Drag and drop upload
  const [isDragOver, setIsDragOver] = useState(false);
  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const droppedFiles = Array.from(e.dataTransfer.files);
      for (const file of droppedFiles) {
        try {
          await api.uploadFile(file);
        } catch (err) {
          console.error('Upload failed:', err);
        }
      }
      loadFiles();
    }
  };

  const filteredFiles = files.filter((f) =>
    f.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <aside
      style={{
        width: '280px',
        backgroundColor: '#0f172a',
        borderRight: '1px solid #1e293b',
        display: 'flex',
        flexDirection: 'column',
        height: 'calc(100vh - 56px)',
        position: 'relative',
        userSelect: 'none',
      }}
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragOver(true);
      }}
      onDragLeave={() => setIsDragOver(false)}
      onDrop={handleDrop}
    >
      {/* Top Header: Title and Primary Actions */}
      <div
        style={{
          padding: '12px 14px 8px 14px',
          borderBottom: '1px solid #1e293b',
          backgroundColor: '#0c1322',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
          <span style={{ fontSize: '12px', fontWeight: 700, color: '#f8fafc', letterSpacing: '0.04em', textTransform: 'uppercase' }}>
            Files
          </span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            {/* New File */}
            <button
              onClick={() => setModalState({ type: 'new_file', inputValue: '' })}
              style={{
                backgroundColor: '#1e293b',
                border: '1px solid #334155',
                color: '#cbd5e1',
                padding: '4px 6px',
                borderRadius: '4px',
                fontSize: '11px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '3px',
              }}
              title="New File (.py, .csv, .md, .txt)"
            >
              <Plus size={12} /> File
            </button>

            {/* New Folder */}
            <button
              onClick={() => setModalState({ type: 'new_folder', inputValue: '' })}
              style={{
                backgroundColor: '#1e293b',
                border: '1px solid #334155',
                color: '#cbd5e1',
                padding: '4px 6px',
                borderRadius: '4px',
                fontSize: '11px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '3px',
              }}
              title="New Folder"
            >
              <Folder size={12} /> Folder
            </button>

            {/* Upload File */}
            <button
              onClick={() => fileInputRef.current?.click()}
              style={{
                backgroundColor: '#1e293b',
                border: '1px solid #334155',
                color: '#cbd5e1',
                padding: '4px 6px',
                borderRadius: '4px',
                fontSize: '11px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
              }}
              title="Upload File"
            >
              <Upload size={12} />
            </button>

            {/* Refresh */}
            <button
              onClick={loadFiles}
              style={{
                backgroundColor: 'transparent',
                border: 'none',
                color: '#64748b',
                padding: '4px',
                cursor: 'pointer',
              }}
              title="Refresh Files"
            >
              <RefreshCw size={13} />
            </button>
          </div>
        </div>

        {/* Search input */}
        <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
          <Search size={13} color="#64748b" style={{ position: 'absolute', left: '8px' }} />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search workspace files..."
            style={{
              width: '100%',
              padding: '6px 8px 6px 26px',
              backgroundColor: '#1e293b',
              border: '1px solid #334155',
              borderRadius: '6px',
              color: '#f8fafc',
              fontSize: '12px',
              outline: 'none',
            }}
          />
        </div>
      </div>

      {/* Hidden file input */}
      <input
        type="file"
        multiple
        ref={fileInputRef}
        onChange={handleFileUpload}
        style={{ display: 'none' }}
      />

      {/* Drag & Drop Overlay indicator */}
      {isDragOver && (
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(37, 99, 235, 0.25)',
            border: '2px dashed #3b82f6',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#93c5fd',
            fontSize: '14px',
            fontWeight: 600,
            zIndex: 15,
            pointerEvents: 'none',
          }}
        >
          Drop files to upload into workspace
        </div>
      )}

      {/* File Tree List */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '6px 4px' }}>
        {filteredFiles.length === 0 ? (
          <div style={{ padding: '24px 16px', textAlign: 'center', color: '#64748b', fontSize: '12px' }}>
            {searchQuery ? 'No matching files found.' : 'Workspace is empty.'}
            <div style={{ marginTop: '8px' }}>
              <button
                onClick={onCreateNewNotebook}
                style={{
                  backgroundColor: '#2563eb',
                  border: 'none',
                  color: '#ffffff',
                  borderRadius: '4px',
                  padding: '4px 10px',
                  fontSize: '11px',
                  cursor: 'pointer',
                }}
              >
                + Create Notebook (.ipynb)
              </button>
            </div>
          </div>
        ) : (
          filteredFiles.map((file) => {
            const isSelected = selectedPath === file.path;
            const isActive = activeFilePath === file.path;

            return (
              <div
                key={file.path}
                onClick={() => handleItemClick(file)}
                onDoubleClick={() => handleItemDoubleClick(file)}
                onContextMenu={(e) => handleContextMenu(e, file)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '5px 8px',
                  margin: '1px 0',
                  borderRadius: '4px',
                  backgroundColor: isSelected ? '#1e293b' : isActive ? '#1e293b' : 'transparent',
                  borderLeft: isActive ? '3px solid #3b82f6' : '3px solid transparent',
                  cursor: 'pointer',
                  color: isSelected || isActive ? '#f8fafc' : '#cbd5e1',
                  fontSize: '12.5px',
                  transition: 'background-color 0.1s ease',
                }}
                title={file.path}
              >
                {/* Folder expand caret */}
                {file.is_dir ? (
                  expandedFolders[file.path] ? (
                    <ChevronDown size={14} color="#64748b" />
                  ) : (
                    <ChevronRight size={14} color="#64748b" />
                  )
                ) : (
                  <span style={{ width: '14px' }} />
                )}

                {renderFileIcon(file)}

                <span
                  style={{
                    flex: 1,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                    fontWeight: file.is_dir ? 600 : 400,
                  }}
                >
                  {file.name}
                </span>

                {/* More action dots */}
                <button
                  onClick={(e) => handleContextMenu(e, file)}
                  style={{
                    backgroundColor: 'transparent',
                    border: 'none',
                    color: '#64748b',
                    padding: '2px',
                    cursor: 'pointer',
                    display: isSelected ? 'flex' : 'none',
                  }}
                >
                  <MoreVertical size={13} />
                </button>
              </div>
            );
          })
        )}
      </div>

      {/* Context Menu Popup */}
      {contextMenu.visible && contextMenu.target && (
        <div
          style={{
            position: 'fixed',
            top: contextMenu.y,
            left: contextMenu.x,
            backgroundColor: '#1e293b',
            border: '1px solid #334155',
            borderRadius: '6px',
            boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
            zIndex: 100,
            minWidth: '150px',
            padding: '4px 0',
          }}
          onClick={(e) => e.stopPropagation()}
        >
          <div
            onClick={() => {
              handleItemDoubleClick(contextMenu.target!);
              setContextMenu({ visible: false, x: 0, y: 0, target: null });
            }}
            style={{
              padding: '6px 12px',
              fontSize: '12px',
              color: '#f8fafc',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <FolderOpen size={14} /> Open
          </div>

          {!contextMenu.target.is_dir && (
            <a
              href={api.getDownloadUrl(contextMenu.target.path)}
              download={contextMenu.target.name}
              onClick={() => setContextMenu({ visible: false, x: 0, y: 0, target: null })}
              style={{
                padding: '6px 12px',
                fontSize: '12px',
                color: '#cbd5e1',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                textDecoration: 'none',
              }}
            >
              <Download size={14} /> Download
            </a>
          )}

          <div
            onClick={() => {
              setModalState({
                type: 'rename',
                target: contextMenu.target!,
                inputValue: contextMenu.target!.name,
              });
              setContextMenu({ visible: false, x: 0, y: 0, target: null });
            }}
            style={{
              padding: '6px 12px',
              fontSize: '12px',
              color: '#cbd5e1',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <Edit2 size={14} /> Rename
          </div>

          <div
            onClick={() => {
              setModalState({
                type: 'delete',
                target: contextMenu.target!,
              });
              setContextMenu({ visible: false, x: 0, y: 0, target: null });
            }}
            style={{
              padding: '6px 12px',
              fontSize: '12px',
              color: '#ef4444',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              borderTop: '1px solid #334155',
            }}
          >
            <Trash2 size={14} /> Delete
          </div>
        </div>
      )}

      {/* Modal Dialog for Create/Rename/Delete */}
      {modalState.type && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0,0,0,0.6)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 150,
          }}
          onClick={() => setModalState({ type: null })}
        >
          <div
            style={{
              width: '360px',
              backgroundColor: '#0f172a',
              border: '1px solid #334155',
              borderRadius: '8px',
              padding: '20px',
              boxShadow: '0 16px 32px rgba(0,0,0,0.5)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ fontSize: '15px', fontWeight: 600, color: '#f8fafc', marginBottom: '12px' }}>
              {modalState.type === 'new_file' && 'Create New File'}
              {modalState.type === 'new_folder' && 'Create New Folder'}
              {modalState.type === 'rename' && 'Rename'}
              {modalState.type === 'delete' && 'Confirm Deletion'}
            </h3>

            {modalState.type === 'delete' ? (
              <p style={{ fontSize: '13px', color: '#94a3b8', marginBottom: '20px' }}>
                Are you sure you want to permanently delete{' '}
                <strong style={{ color: '#ef4444' }}>{modalState.target?.name}</strong>?
              </p>
            ) : (
              <div style={{ marginBottom: '18px' }}>
                <input
                  type="text"
                  autoFocus
                  value={modalState.inputValue || ''}
                  onChange={(e) => setModalState({ ...modalState, inputValue: e.target.value })}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleConfirmModal();
                    if (e.key === 'Escape') setModalState({ type: null });
                  }}
                  placeholder={
                    modalState.type === 'new_file'
                      ? 'e.g. script.py or dataset.csv'
                      : 'Folder name'
                  }
                  style={{
                    width: '100%',
                    padding: '8px 10px',
                    backgroundColor: '#1e293b',
                    border: '1px solid #334155',
                    borderRadius: '6px',
                    color: '#f8fafc',
                    fontSize: '13px',
                    outline: 'none',
                  }}
                />
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
              <button
                onClick={() => setModalState({ type: null })}
                style={{
                  padding: '6px 12px',
                  backgroundColor: 'transparent',
                  border: '1px solid #334155',
                  color: '#cbd5e1',
                  borderRadius: '4px',
                  fontSize: '12px',
                  cursor: 'pointer',
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmModal}
                style={{
                  padding: '6px 14px',
                  backgroundColor: modalState.type === 'delete' ? '#dc2626' : '#2563eb',
                  border: 'none',
                  color: '#ffffff',
                  borderRadius: '4px',
                  fontSize: '12px',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                {modalState.type === 'delete' ? 'Delete' : 'Confirm'}
              </button>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
};
