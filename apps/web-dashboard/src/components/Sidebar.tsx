import React, { useState, useEffect, useRef } from 'react';
import {
  Folder,
  FolderOpen,
  FolderPlus,
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
import { FileItem, UserProfile } from '../types';
import { api } from '../services/api';

interface SidebarProps {
  onOpenFile: (file: FileItem) => void;
  onOpenNotebookFile: (path: string) => void;
  onCreateNewNotebook: () => void;
  activeFilePath?: string;
  width?: number;
  user?: UserProfile | null;
}

export const Sidebar: React.FC<SidebarProps> = ({
  onOpenFile,
  onOpenNotebookFile,
  onCreateNewNotebook,
  activeFilePath,
  width = 280,
  user,
}) => {
  const [files, setFiles] = useState<FileItem[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [activeDirectory, setActiveDirectory] = useState<string>('');
  const [expandedFolders, setExpandedFolders] = useState<Record<string, boolean>>({});

  // Context Menu State
  const [contextMenu, setContextMenu] = useState<{
    visible: boolean;
    x: number;
    y: number;
    target: FileItem | null; // null represents empty area / background
    targetDir: string;
  }>({ visible: false, x: 0, y: 0, target: null, targetDir: '' });

  // Dialog Modals State
  const [modalState, setModalState] = useState<{
    type: 'new_file' | 'new_folder' | 'rename' | 'delete' | null;
    target?: FileItem;
    targetFolder?: string;
    inputValue?: string;
  }>({ type: null });

  const [uploadTargetFolder, setUploadTargetFolder] = useState<string>('');
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
    setSelectedPath(null);
    setActiveDirectory('');
    setExpandedFolders({});
    loadFiles();
  }, [user]);

  useEffect(() => {
    const handleRefresh = () => {
      loadFiles();
    };
    window.addEventListener('pcs-refresh-files', handleRefresh);
    return () => {
      window.removeEventListener('pcs-refresh-files', handleRefresh);
    };
  }, []);

  // Close context menu and modals on outside click or Escape key
  useEffect(() => {
    const handleWindowClick = () => {
      if (contextMenu.visible) {
        setContextMenu({ visible: false, x: 0, y: 0, target: null, targetDir: '' });
      }
    };
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (contextMenu.visible) {
          setContextMenu({ visible: false, x: 0, y: 0, target: null, targetDir: '' });
        }
        if (modalState.type) {
          setModalState({ type: null });
        }
      }
    };

    window.addEventListener('click', handleWindowClick);
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('click', handleWindowClick);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [contextMenu.visible, modalState.type]);

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
    if (file.is_dir) {
      setActiveDirectory(file.path);
    }
  };

  const handleItemDoubleClick = (file: FileItem) => {
    if (file.is_dir) {
      setExpandedFolders((prev) => ({ ...prev, [file.path]: !prev[file.path] }));
      setActiveDirectory(file.path);
    } else if (file.name.endsWith('.ipynb')) {
      onOpenNotebookFile(file.path);
    } else {
      onOpenFile(file);
    }
  };

  // Right-click on existing file or folder
  const handleItemContextMenu = (e: React.MouseEvent, file: FileItem) => {
    e.preventDefault();
    e.stopPropagation();
    setSelectedPath(file.path);
    if (file.is_dir) {
      setActiveDirectory(file.path);
    }

    const menuWidth = 190;
    const menuHeight = file.is_dir ? 260 : 210;
    const x = Math.min(e.clientX, window.innerWidth - menuWidth - 10);
    const y = Math.min(e.clientY, window.innerHeight - menuHeight - 10);

    const targetDir = file.is_dir
      ? file.path
      : file.path.includes('/')
      ? file.path.substring(0, file.path.lastIndexOf('/'))
      : '';

    setContextMenu({
      visible: true,
      x,
      y,
      target: file,
      targetDir,
    });
  };

  // Right-click on empty area / background of the Files panel
  const handleBackgroundContextMenu = (e: React.MouseEvent) => {
    e.preventDefault();
    const menuWidth = 190;
    const menuHeight = 180;
    const x = Math.min(e.clientX, window.innerWidth - menuWidth - 10);
    const y = Math.min(e.clientY, window.innerHeight - menuHeight - 10);

    setContextMenu({
      visible: true,
      x,
      y,
      target: null, // empty background
      targetDir: activeDirectory || '',
    });
  };

  // Upload trigger
  const triggerUpload = (targetFolder: string = '') => {
    setUploadTargetFolder(targetFolder);
    fileInputRef.current?.click();
  };

  // File Upload handler
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files) return;
    const uploadedFiles = Array.from(e.target.files);
    const targetFolder = uploadTargetFolder || activeDirectory || '';

    for (const file of uploadedFiles) {
      try {
        await api.uploadFile(file, targetFolder);
      } catch (err: any) {
        alert(`Failed to upload "${file.name}": ${err.message || 'Error'}`);
      }
    }
    await loadFiles();
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  // Modal actions (Confirm New File, New Folder, Rename, Delete)
  const handleConfirmModal = async () => {
    const { type, target, targetFolder, inputValue } = modalState;
    if (!type) return;

    try {
      if (type === 'new_file' && inputValue?.trim()) {
        const inputName = inputValue.trim();
        if (inputName.includes('/') || inputName.includes('\\') || inputName.includes('..')) {
          alert('Invalid filename. Cannot contain path separators or "..".');
          return;
        }

        const folder = targetFolder !== undefined ? targetFolder : activeDirectory;
        const fullPath = folder ? `${folder}/${inputName}` : inputName;

        // Check if file already exists
        if (files.some((f) => f.path.toLowerCase() === fullPath.toLowerCase())) {
          alert(`A file or folder named "${inputName}" already exists.`);
          return;
        }

        let initialContent = '';
        if (inputName.endsWith('.ipynb')) {
          initialContent = JSON.stringify(
            {
              cells: [
                {
                  cell_type: 'code',
                  execution_count: null,
                  metadata: {},
                  outputs: [],
                  source: [],
                },
              ],
              metadata: {
                kernelspec: {
                  display_name: 'Python 3',
                  language: 'python',
                  name: 'python3',
                },
                language_info: {
                  name: 'python',
                  version: '3.14.0',
                },
              },
              nbformat: 4,
              nbformat_minor: 5,
            },
            null,
            2
          );
        } else if (inputName.endsWith('.py')) {
          initialContent = `# ${inputName}\n`;
        } else if (inputName.endsWith('.csv')) {
          initialContent = `id,name,value\n1,Alpha,100\n`;
        } else if (inputName.endsWith('.md')) {
          initialContent = `# ${inputName.replace('.md', '')}\n\n`;
        }

        await api.writeFile(fullPath, initialContent);
        await loadFiles();
        setSelectedPath(fullPath);

        if (fullPath.endsWith('.ipynb')) {
          onOpenNotebookFile(fullPath);
        } else {
          onOpenFile({
            name: inputName,
            path: fullPath,
            is_dir: false,
            size: initialContent.length,
            modified_at: Date.now() / 1000,
          });
        }
      } else if (type === 'new_folder' && inputValue?.trim()) {
        const folderName = inputValue.trim();
        if (folderName.includes('/') || folderName.includes('\\') || folderName.includes('..')) {
          alert('Invalid folder name. Cannot contain path separators or "..".');
          return;
        }

        const folder = targetFolder !== undefined ? targetFolder : activeDirectory;
        const fullPath = folder ? `${folder}/${folderName}` : folderName;

        if (files.some((f) => f.path.toLowerCase() === fullPath.toLowerCase())) {
          alert(`A folder named "${folderName}" already exists.`);
          return;
        }

        await api.createFolder(fullPath);
        await loadFiles();
        setExpandedFolders((prev) => ({ ...prev, [fullPath]: true }));
      } else if (type === 'rename' && target && inputValue?.trim()) {
        const newName = inputValue.trim();
        if (newName.includes('/') || newName.includes('\\') || newName.includes('..')) {
          alert('Invalid name. Cannot contain path separators or "..".');
          return;
        }

        const parts = target.path.split('/');
        parts.pop();
        const parent = parts.join('/');
        const newPath = parent ? `${parent}/${newName}` : newName;

        await api.renameFile(target.path, newPath);
        await loadFiles();
      } else if (type === 'delete' && target) {
        await api.deleteFile(target.path);
        await loadFiles();
        if (selectedPath === target.path) setSelectedPath(null);
        if (activeDirectory === target.path) setActiveDirectory('');
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
      const targetFolder = activeDirectory || '';
      for (const file of droppedFiles) {
        try {
          await api.uploadFile(file, targetFolder);
        } catch (err) {
          console.error('Upload failed:', err);
        }
      }
      await loadFiles();
    }
  };

  const filteredFiles = files.filter((f) =>
    f.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <aside
      data-testid="left-sidebar"
      style={{
        width: `${width}px`,
        minWidth: `${width}px`,
        maxWidth: `${width}px`,
        backgroundColor: 'var(--bg-sidebar)',
        borderRight: '1px solid var(--border-main)',
        display: 'flex',
        flexDirection: 'column',
        height: 'calc(100vh - 56px)',
        position: 'relative',
        userSelect: 'none',
        flexShrink: 0,
        transition: 'background-color 0.15s ease, border-color 0.15s ease',
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
          borderBottom: '1px solid var(--border-main)',
          backgroundColor: 'var(--bg-sidebar-header)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-main)', letterSpacing: '0.04em', textTransform: 'uppercase' }}>
              Files
            </span>
            <span
              data-testid="workspace-badge"
              style={{
                fontSize: '10px',
                padding: '1px 6px',
                borderRadius: '4px',
                backgroundColor: user
                  ? user.role === 'super_admin'
                    ? 'rgba(168, 85, 247, 0.15)'
                    : 'rgba(59, 130, 246, 0.15)'
                  : 'rgba(234, 179, 8, 0.15)',
                color: user
                  ? user.role === 'super_admin'
                    ? '#c084fc'
                    : '#60a5fa'
                  : '#fbbf24',
                fontWeight: 600,
                border: user
                  ? user.role === 'super_admin'
                    ? '1px solid rgba(168, 85, 247, 0.3)'
                    : '1px solid rgba(59, 130, 246, 0.3)'
                  : '1px solid rgba(234, 179, 8, 0.3)',
              }}
              title={user ? (user.role === 'super_admin' ? 'SuperAdmin Workspace' : 'Private Workspace') : 'Public Workspace (Guest)'}
            >
              {user ? (user.role === 'super_admin' ? 'Admin' : 'Private') : 'Public'}
            </span>
            {activeDirectory && (
              <span
                onClick={() => setActiveDirectory('')}
                style={{
                  fontSize: '10px',
                  color: 'var(--border-accent)',
                  backgroundColor: 'var(--btn-secondary-bg)',
                  padding: '1px 5px',
                  borderRadius: '3px',
                  cursor: 'pointer',
                  maxWidth: '100px',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
                title={`Active: ${activeDirectory} (Click to reset to Root)`}
              >
                /{activeDirectory}
              </span>
            )}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            {/* New File */}
            <button
              onClick={() => setModalState({ type: 'new_file', targetFolder: activeDirectory, inputValue: '' })}
              style={{
                backgroundColor: 'var(--btn-secondary-bg)',
                border: '1px solid var(--btn-secondary-border)',
                color: 'var(--btn-secondary-text)',
                padding: '4px 6px',
                borderRadius: '4px',
                fontSize: '11px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '3px',
              }}
              title="New File (.py, .csv, .md, .ipynb, .txt)"
            >
              <Plus size={12} /> File
            </button>

            {/* New Folder */}
            <button
              onClick={() => setModalState({ type: 'new_folder', targetFolder: activeDirectory, inputValue: '' })}
              style={{
                backgroundColor: 'var(--btn-secondary-bg)',
                border: '1px solid var(--btn-secondary-border)',
                color: 'var(--btn-secondary-text)',
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
              <FolderPlus size={12} /> Folder
            </button>

            {/* Upload File */}
            <button
              onClick={() => triggerUpload(activeDirectory)}
              style={{
                backgroundColor: 'var(--btn-secondary-bg)',
                border: '1px solid var(--btn-secondary-border)',
                color: 'var(--btn-secondary-text)',
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
                color: 'var(--text-muted)',
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
          <Search size={13} color="var(--text-muted)" style={{ position: 'absolute', left: '8px' }} />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search workspace files..."
            style={{
              width: '100%',
              padding: '6px 8px 6px 26px',
              backgroundColor: 'var(--bg-input)',
              border: '1px solid var(--border-secondary)',
              borderRadius: '6px',
              color: 'var(--text-main)',
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

      {/* File Tree List — Right-click empty area triggers custom background context menu */}
      <div
        data-testid="file-tree-container"
        onContextMenu={handleBackgroundContextMenu}
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '6px 4px',
          minHeight: '200px',
        }}
      >
        {filteredFiles.length === 0 ? (
          <div
            style={{ padding: '24px 16px', textAlign: 'center', color: '#64748b', fontSize: '12px' }}
          >
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
                onContextMenu={(e) => handleItemContextMenu(e, file)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '5px 8px',
                  margin: '1px 0',
                  borderRadius: '4px',
                  backgroundColor: isSelected || isActive ? 'var(--dropdown-item-selected)' : 'transparent',
                  borderLeft: isActive ? '3px solid var(--border-accent)' : '3px solid transparent',
                  cursor: 'pointer',
                  color: isSelected || isActive ? 'var(--dropdown-item-selected-text)' : 'var(--text-main)',
                  fontSize: '12.5px',
                  transition: 'background-color 0.1s ease',
                }}
                title={file.path}
              >
                {/* Folder expand caret */}
                {file.is_dir ? (
                  expandedFolders[file.path] ? (
                    <ChevronDown size={14} color="var(--text-muted)" />
                  ) : (
                    <ChevronRight size={14} color="var(--text-muted)" />
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
                  onClick={(e) => handleItemContextMenu(e, file)}
                  style={{
                    backgroundColor: 'transparent',
                    border: 'none',
                    color: 'var(--text-muted)',
                    padding: '2px',
                    cursor: 'pointer',
                    display: isSelected ? 'flex' : 'none',
                  }}
                  title="Actions"
                >
                  <MoreVertical size={13} />
                </button>
              </div>
            );
          })
        )}
      </div>

      {/* Google Colab–Style Custom Right-Click Context Menu */}
      {contextMenu.visible && (
        <div
          style={{
            position: 'fixed',
            top: contextMenu.y,
            left: contextMenu.x,
            backgroundColor: 'var(--dropdown-bg)',
            border: '1px solid var(--dropdown-border)',
            borderRadius: '6px',
            boxShadow: '0 12px 32px rgba(0,0,0,0.3)',
            zIndex: 100,
            minWidth: '170px',
            padding: '4px 0',
            userSelect: 'none',
          }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* 1. If right-clicked on an empty background area */}
          {contextMenu.target === null && (
            <>
              <div
                onClick={() => {
                  triggerUpload(contextMenu.targetDir);
                  setContextMenu({ visible: false, x: 0, y: 0, target: null, targetDir: '' });
                }}
                style={{
                  padding: '7px 12px',
                  fontSize: '12px',
                  color: '#f8fafc',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                }}
              >
                <Upload size={14} color="#38bdf8" /> Upload File
              </div>

              <div
                onClick={() => {
                  setModalState({
                    type: 'new_file',
                    targetFolder: contextMenu.targetDir,
                    inputValue: '',
                  });
                  setContextMenu({ visible: false, x: 0, y: 0, target: null, targetDir: '' });
                }}
                style={{
                  padding: '7px 12px',
                  fontSize: '12px',
                  color: '#f8fafc',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                }}
              >
                <Plus size={14} color="#10b981" /> New File
              </div>

              <div
                onClick={() => {
                  setModalState({
                    type: 'new_folder',
                    targetFolder: contextMenu.targetDir,
                    inputValue: '',
                  });
                  setContextMenu({ visible: false, x: 0, y: 0, target: null, targetDir: '' });
                }}
                style={{
                  padding: '7px 12px',
                  fontSize: '12px',
                  color: '#f8fafc',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                }}
              >
                <FolderPlus size={14} color="#f59e0b" /> New Folder
              </div>

              <div style={{ height: '1px', backgroundColor: '#334155', margin: '4px 0' }} />

              <div
                onClick={() => {
                  loadFiles();
                  setContextMenu({ visible: false, x: 0, y: 0, target: null, targetDir: '' });
                }}
                style={{
                  padding: '7px 12px',
                  fontSize: '12px',
                  color: '#cbd5e1',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                }}
              >
                <RefreshCw size={13} color="#94a3b8" /> Refresh
              </div>
            </>
          )}

          {/* 2. If right-clicked on a folder */}
          {contextMenu.target && contextMenu.target.is_dir && (
            <>
              <div
                onClick={() => {
                  handleItemDoubleClick(contextMenu.target!);
                  setContextMenu({ visible: false, x: 0, y: 0, target: null, targetDir: '' });
                }}
                style={{
                  padding: '7px 12px',
                  fontSize: '12px',
                  color: '#f8fafc',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                }}
              >
                <FolderOpen size={14} color="#f59e0b" /> Open / Toggle
              </div>

              <div
                onClick={() => {
                  setModalState({
                    type: 'new_file',
                    targetFolder: contextMenu.target!.path,
                    inputValue: '',
                  });
                  setContextMenu({ visible: false, x: 0, y: 0, target: null, targetDir: '' });
                }}
                style={{
                  padding: '7px 12px',
                  fontSize: '12px',
                  color: '#f8fafc',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                }}
              >
                <Plus size={14} color="#10b981" /> New File Here
              </div>

              <div
                onClick={() => {
                  setModalState({
                    type: 'new_folder',
                    targetFolder: contextMenu.target!.path,
                    inputValue: '',
                  });
                  setContextMenu({ visible: false, x: 0, y: 0, target: null, targetDir: '' });
                }}
                style={{
                  padding: '7px 12px',
                  fontSize: '12px',
                  color: '#f8fafc',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                }}
              >
                <FolderPlus size={14} color="#f59e0b" /> New Folder Here
              </div>

              <div
                onClick={() => {
                  triggerUpload(contextMenu.target!.path);
                  setContextMenu({ visible: false, x: 0, y: 0, target: null, targetDir: '' });
                }}
                style={{
                  padding: '7px 12px',
                  fontSize: '12px',
                  color: '#f8fafc',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                }}
              >
                <Upload size={14} color="#38bdf8" /> Upload File Here
              </div>

              <div style={{ height: '1px', backgroundColor: '#334155', margin: '4px 0' }} />

              <div
                onClick={() => {
                  setModalState({
                    type: 'rename',
                    target: contextMenu.target!,
                    inputValue: contextMenu.target!.name,
                  });
                  setContextMenu({ visible: false, x: 0, y: 0, target: null, targetDir: '' });
                }}
                style={{
                  padding: '7px 12px',
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
                  setContextMenu({ visible: false, x: 0, y: 0, target: null, targetDir: '' });
                }}
                style={{
                  padding: '7px 12px',
                  fontSize: '12px',
                  color: '#ef4444',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                }}
              >
                <Trash2 size={14} color="#ef4444" /> Delete Folder
              </div>

              <div style={{ height: '1px', backgroundColor: '#334155', margin: '4px 0' }} />

              <div
                onClick={() => {
                  loadFiles();
                  setContextMenu({ visible: false, x: 0, y: 0, target: null, targetDir: '' });
                }}
                style={{
                  padding: '7px 12px',
                  fontSize: '12px',
                  color: '#cbd5e1',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                }}
              >
                <RefreshCw size={13} color="#94a3b8" /> Refresh
              </div>
            </>
          )}

          {/* 3. If right-clicked on a file */}
          {contextMenu.target && !contextMenu.target.is_dir && (
            <>
              <div
                onClick={() => {
                  handleItemDoubleClick(contextMenu.target!);
                  setContextMenu({ visible: false, x: 0, y: 0, target: null, targetDir: '' });
                }}
                style={{
                  padding: '7px 12px',
                  fontSize: '12px',
                  color: '#f8fafc',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                }}
              >
                <FolderOpen size={14} color="#38bdf8" /> Open
              </div>

              <div
                onClick={() => {
                  setModalState({
                    type: 'rename',
                    target: contextMenu.target!,
                    inputValue: contextMenu.target!.name,
                  });
                  setContextMenu({ visible: false, x: 0, y: 0, target: null, targetDir: '' });
                }}
                style={{
                  padding: '7px 12px',
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

              <a
                href={api.getDownloadUrl(contextMenu.target.path)}
                download={contextMenu.target.name}
                onClick={() => setContextMenu({ visible: false, x: 0, y: 0, target: null, targetDir: '' })}
                style={{
                  padding: '7px 12px',
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

              <div style={{ height: '1px', backgroundColor: '#334155', margin: '4px 0' }} />

              <div
                onClick={() => {
                  setModalState({
                    type: 'delete',
                    target: contextMenu.target!,
                  });
                  setContextMenu({ visible: false, x: 0, y: 0, target: null, targetDir: '' });
                }}
                style={{
                  padding: '7px 12px',
                  fontSize: '12px',
                  color: '#ef4444',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                }}
              >
                <Trash2 size={14} color="#ef4444" /> Delete
              </div>

              <div style={{ height: '1px', backgroundColor: '#334155', margin: '4px 0' }} />

              <div
                onClick={() => {
                  loadFiles();
                  setContextMenu({ visible: false, x: 0, y: 0, target: null, targetDir: '' });
                }}
                style={{
                  padding: '7px 12px',
                  fontSize: '12px',
                  color: '#cbd5e1',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                }}
              >
                <RefreshCw size={13} color="#94a3b8" /> Refresh
              </div>
            </>
          )}
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
            backgroundColor: 'rgba(0,0,0,0.65)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 150,
          }}
          onClick={() => setModalState({ type: null })}
        >
          <div
            style={{
              width: '380px',
              backgroundColor: 'var(--bg-modal)',
              border: '1px solid var(--border-secondary)',
              borderRadius: '8px',
              padding: '20px',
              boxShadow: '0 16px 32px rgba(0,0,0,0.3)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-main)', marginBottom: '8px' }}>
              {modalState.type === 'new_file' && 'Create New File'}
              {modalState.type === 'new_folder' && 'Create New Folder'}
              {modalState.type === 'rename' && 'Rename'}
              {modalState.type === 'delete' && 'Confirm Deletion'}
            </h3>

            {modalState.type === 'delete' ? (
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '20px', lineHeight: 1.5 }}>
                Are you sure you want to permanently delete{' '}
                <strong style={{ color: '#ef4444' }}>{modalState.target?.name}</strong>?
                {modalState.target?.is_dir && ' All enclosed files will also be removed.'}
              </p>
            ) : (
              <div style={{ marginBottom: '18px' }}>
                <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '6px' }}>
                  {modalState.type === 'new_file' && 'Supports .py, .ipynb, .csv, .md, .txt, .json'}
                  {modalState.type === 'new_folder' && 'Folder will be created in current active directory'}
                  {modalState.type === 'rename' && `Renaming: ${modalState.target?.name}`}
                </p>
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
                      ? 'e.g. script.py, dataset.csv, analysis.ipynb'
                      : 'Folder name'
                  }
                  style={{
                    width: '100%',
                    padding: '8px 10px',
                    backgroundColor: 'var(--bg-input)',
                    border: '1px solid var(--border-secondary)',
                    borderRadius: '6px',
                    color: 'var(--text-main)',
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
                  backgroundColor: 'var(--btn-secondary-bg)',
                  border: '1px solid var(--btn-secondary-border)',
                  color: 'var(--btn-secondary-text)',
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
