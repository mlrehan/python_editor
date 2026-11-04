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
  Edit3,
  FilePlus,
} from 'lucide-react';
import { FileItem, UserProfile } from '../types';
import { api } from '../services/api';
import { Modal, ModalHeader, ModalBody, ModalFooter } from './Modal';

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
  // Pointer type of the last press on a tree row (touch taps open files directly)
  const lastPointerTypeRef = useRef<string>('mouse');

  // Contents of expanded folders, keyed by folder path (root items live in `files`)
  const [folderChildren, setFolderChildren] = useState<Record<string, FileItem[]>>({});
  const expandedFoldersRef = useRef(expandedFolders);
  expandedFoldersRef.current = expandedFolders;

  const loadFolder = async (folderPath: string) => {
    try {
      const items = await api.listFiles(folderPath);
      setFolderChildren((prev) => ({ ...prev, [folderPath]: items }));
    } catch (err) {
      // Folder was moved or deleted: forget it
      setFolderChildren((prev) => {
        const next = { ...prev };
        delete next[folderPath];
        return next;
      });
      setExpandedFolders((prev) => {
        const next = { ...prev };
        delete next[folderPath];
        return next;
      });
    }
  };

  const loadFiles = async () => {
    try {
      const items = await api.listFiles();
      setFiles(items);
    } catch (err) {
      console.warn('Failed to load files:', err);
    }
    const openFolders = Object.keys(expandedFoldersRef.current).filter((p) => expandedFoldersRef.current[p]);
    await Promise.all(openFolders.map((p) => loadFolder(p)));
  };

  const toggleFolder = (folderPath: string) => {
    const willExpand = !expandedFolders[folderPath];
    setExpandedFolders((prev) => ({ ...prev, [folderPath]: willExpand }));
    if (willExpand) loadFolder(folderPath);
  };

  // Expands a folder and (re)loads its contents; no-op for the root
  const revealFolder = async (folderPath: string) => {
    if (!folderPath) return;
    setExpandedFolders((prev) => ({ ...prev, [folderPath]: true }));
    await loadFolder(folderPath);
  };

  // Items directly inside a folder ('' is the workspace root)
  const itemsIn = (folderPath: string): FileItem[] => (folderPath ? folderChildren[folderPath] || [] : files);

  useEffect(() => {
    setSelectedPath(null);
    setActiveDirectory('');
    setExpandedFolders({});
    setFolderChildren({});
    expandedFoldersRef.current = {};
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
  // clickCount is MouseEvent.detail: 1 for a single click, 2 for the second click of a double-click
  const handleItemClick = (file: FileItem, clickCount = 1) => {
    setSelectedPath(file.path);
    if (file.is_dir) {
      setActiveDirectory(file.path);
      // One click opens or closes a folder (VS Code / Colab behaviour); ignore the extra
      // clicks of a double-click so it does not open and immediately close again
      if (clickCount <= 1) toggleFolder(file.path);
    }
  };

  const handleItemDoubleClick = (file: FileItem) => {
    if (file.is_dir) {
      return;
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
      // Like VS Code: right-clicking empty space acts on the workspace root, not the last selected folder
      targetDir: '',
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
    // Every trigger passes its folder explicitly; '' means the workspace root
    const targetFolder = uploadTargetFolder;

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
        if (itemsIn(folder).some((f) => f.path.toLowerCase() === fullPath.toLowerCase())) {
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
        await revealFolder(folder);
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

        if (itemsIn(folder).some((f) => f.path.toLowerCase() === fullPath.toLowerCase())) {
          alert(`A folder named "${folderName}" already exists.`);
          return;
        }

        await api.createFolder(fullPath);
        await loadFiles();
        await revealFolder(folder);
        await revealFolder(fullPath);
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
        notifyPathMoved(target.path, newPath);
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

  // Tells the rest of the app (open editor tabs) that a file or folder changed path
  const notifyPathMoved = (oldPath: string, newPath: string) => {
    window.dispatchEvent(new CustomEvent('pcs-file-moved', { detail: { oldPath, newPath } }));
  };

  const parentOf = (path: string) => (path.includes('/') ? path.substring(0, path.lastIndexOf('/')) : '');

  // Moves a file or folder into targetFolder ('' = workspace root), VS Code explorer style
  const moveItem = async (sourcePath: string, targetFolder: string) => {
    const name = sourcePath.split('/').pop() || sourcePath;
    if (targetFolder === sourcePath || targetFolder.startsWith(`${sourcePath}/`)) {
      alert('A folder cannot be moved into itself.');
      return;
    }
    if (parentOf(sourcePath) === targetFolder) return;
    const newPath = targetFolder ? `${targetFolder}/${name}` : name;
    try {
      await api.renameFile(sourcePath, newPath);
    } catch (err: any) {
      alert(err.message || 'Move failed');
      return;
    }
    notifyPathMoved(sourcePath, newPath);
    // Carry expanded state of a moved folder (and its subfolders) over to the new location
    setExpandedFolders((prev) => {
      const next: Record<string, boolean> = {};
      for (const [p, open] of Object.entries(prev)) {
        if (p === sourcePath || p.startsWith(`${sourcePath}/`)) {
          next[newPath + p.substring(sourcePath.length)] = open;
        } else {
          next[p] = open;
        }
      }
      expandedFoldersRef.current = next;
      return next;
    });
    if (selectedPath === sourcePath) setSelectedPath(newPath);
    if (activeDirectory === sourcePath) setActiveDirectory(newPath);
    await loadFiles();
    await revealFolder(targetFolder);
  };

  const DRAG_MIME = 'application/x-pcs-path';
  const [draggingPath, setDraggingPath] = useState<string | null>(null);
  const [dropTargetFolder, setDropTargetFolder] = useState<string | null>(null);

  const uploadFiles = async (fileList: FileList, targetFolder: string) => {
    for (const file of Array.from(fileList)) {
      try {
        await api.uploadFile(file, targetFolder);
      } catch (err) {
        console.error('Upload failed:', err);
      }
    }
    await loadFiles();
    await revealFolder(targetFolder);
  };

  // Drop onto a folder row: move workspace items, or upload files from the computer into that folder
  const handleFolderDragOver = (e: React.DragEvent, folder: FileItem) => {
    const isInternal = e.dataTransfer.types.includes(DRAG_MIME);
    const isExternal = e.dataTransfer.types.includes('Files');
    if (!isInternal && !isExternal) return;
    if (isInternal && draggingPath && (folder.path === draggingPath || folder.path.startsWith(`${draggingPath}/`))) {
      // Invalid target (the folder itself or one of its subfolders): refuse the drop here and
      // stop the event from reaching the sidebar background, which would move the item to the root
      e.stopPropagation();
      e.dataTransfer.dropEffect = 'none';
      if (dropTargetFolder !== null) setDropTargetFolder(null);
      return;
    }
    e.preventDefault();
    e.stopPropagation();
    e.dataTransfer.dropEffect = isInternal ? 'move' : 'copy';
    setIsDragOver(false);
    if (dropTargetFolder !== folder.path) setDropTargetFolder(folder.path);
  };

  const handleFolderDrop = async (e: React.DragEvent, folder: FileItem) => {
    e.preventDefault();
    e.stopPropagation();
    setDropTargetFolder(null);
    setIsDragOver(false);
    const sourcePath = e.dataTransfer.getData(DRAG_MIME);
    setDraggingPath(null);
    if (sourcePath) {
      await moveItem(sourcePath, folder.path);
    } else if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      await uploadFiles(e.dataTransfer.files, folder.path);
    }
  };

  // Drag and drop on the sidebar background: move to workspace root, or upload into the active folder
  const [isDragOver, setIsDragOver] = useState(false);
  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    setDropTargetFolder(null);
    const sourcePath = e.dataTransfer.getData(DRAG_MIME);
    setDraggingPath(null);
    if (sourcePath) {
      await moveItem(sourcePath, '');
      return;
    }
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      await uploadFiles(e.dataTransfer.files, activeDirectory || '');
    }
  };

  // Visible rows: nested tree of expanded folders, or a flat list of loaded items while searching
  const query = searchQuery.trim().toLowerCase();
  const visibleRows: Array<{ file: FileItem; depth: number }> = [];
  if (query) {
    const all = [...files, ...Object.values(folderChildren).flat()];
    const seen = new Set<string>();
    for (const f of all) {
      if (!seen.has(f.path) && f.name.toLowerCase().includes(query)) {
        seen.add(f.path);
        visibleRows.push({ file: f, depth: 0 });
      }
    }
  } else {
    const addRows = (items: FileItem[], depth: number) => {
      for (const f of items) {
        visibleRows.push({ file: f, depth });
        if (f.is_dir && expandedFolders[f.path]) addRows(folderChildren[f.path] || [], depth + 1);
      }
    };
    addRows(files, 0);
  }

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
        height: '100%',
        position: 'relative',
        userSelect: 'none',
        flexShrink: 0,
        transition: 'background-color 0.15s ease, border-color 0.15s ease',
      }}
      onDragOver={(e) => {
        e.preventDefault();
        // Upload overlay only for files dragged in from the computer, not for moves inside the tree
        if (e.dataTransfer.types.includes('Files')) setIsDragOver(true);
        if (dropTargetFolder !== null) setDropTargetFolder(null);
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
              title={user ? (user.role === 'super_admin' ? 'SuperAdmin Workspace' : 'Private Workspace') : 'Guest workspace (private, saved in this browser)'}
            >
              {user ? (user.role === 'super_admin' ? 'Admin' : 'Private') : 'Guest'}
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
        {visibleRows.length === 0 ? (
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
          visibleRows.map(({ file, depth }) => {
            const isSelected = selectedPath === file.path;
            const isActive = activeFilePath === file.path;
            const isDropTarget = file.is_dir && dropTargetFolder === file.path;

            return (
              <div
                key={file.path}
                data-testid="file-tree-item"
                className="file-tree-row"
                data-path={file.path}
                draggable
                onDragStart={(e) => {
                  e.dataTransfer.setData(DRAG_MIME, file.path);
                  e.dataTransfer.effectAllowed = 'move';
                  setDraggingPath(file.path);
                }}
                onDragEnd={() => {
                  setDraggingPath(null);
                  setDropTargetFolder(null);
                }}
                onDragOver={file.is_dir ? (e) => handleFolderDragOver(e, file) : undefined}
                onDrop={file.is_dir ? (e) => handleFolderDrop(e, file) : undefined}
                onPointerDown={(e) => {
                  lastPointerTypeRef.current = e.pointerType;
                }}
                onClick={(e) => {
                  handleItemClick(file, e.detail);
                  // Touch screens have no reliable double-click: a tap opens the file
                  if (lastPointerTypeRef.current === 'touch' && !file.is_dir) handleItemDoubleClick(file);
                }}
                onDoubleClick={() => {
                  if (lastPointerTypeRef.current !== 'touch') handleItemDoubleClick(file);
                }}
                onContextMenu={(e) => handleItemContextMenu(e, file)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: `5px 8px 5px ${8 + depth * 16}px`,
                  margin: '1px 0',
                  borderRadius: '4px',
                  backgroundColor: isDropTarget
                    ? 'rgba(37, 99, 235, 0.18)'
                    : isSelected || isActive
                    ? 'var(--dropdown-item-selected)'
                    : 'transparent',
                  outline: isDropTarget ? '1px dashed var(--border-accent)' : 'none',
                  opacity: draggingPath === file.path ? 0.5 : 1,
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
                className="pcs-menu-item"
                style={{
                  padding: '7px 12px',
                  fontSize: '12px',
                  color: 'var(--text-main)',
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
                className="pcs-menu-item"
                style={{
                  padding: '7px 12px',
                  fontSize: '12px',
                  color: 'var(--text-main)',
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
                className="pcs-menu-item"
                style={{
                  padding: '7px 12px',
                  fontSize: '12px',
                  color: 'var(--text-main)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                }}
              >
                <FolderPlus size={14} color="#f59e0b" /> New Folder
              </div>

              <div style={{ height: '1px', backgroundColor: 'var(--dropdown-border)', margin: '4px 0' }} />

              <div
                onClick={() => {
                  loadFiles();
                  setContextMenu({ visible: false, x: 0, y: 0, target: null, targetDir: '' });
                }}
                className="pcs-menu-item"
                style={{
                  padding: '7px 12px',
                  fontSize: '12px',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                }}
              >
                <RefreshCw size={13} color="var(--text-secondary)" /> Refresh
              </div>
            </>
          )}

          {/* 2. If right-clicked on a folder */}
          {contextMenu.target && contextMenu.target.is_dir && (
            <>
              <div
                onClick={() => {
                  toggleFolder(contextMenu.target!.path);
                  setActiveDirectory(contextMenu.target!.path);
                  setContextMenu({ visible: false, x: 0, y: 0, target: null, targetDir: '' });
                }}
                className="pcs-menu-item"
                style={{
                  padding: '7px 12px',
                  fontSize: '12px',
                  color: 'var(--text-main)',
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
                className="pcs-menu-item"
                style={{
                  padding: '7px 12px',
                  fontSize: '12px',
                  color: 'var(--text-main)',
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
                className="pcs-menu-item"
                style={{
                  padding: '7px 12px',
                  fontSize: '12px',
                  color: 'var(--text-main)',
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
                className="pcs-menu-item"
                style={{
                  padding: '7px 12px',
                  fontSize: '12px',
                  color: 'var(--text-main)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                }}
              >
                <Upload size={14} color="#38bdf8" /> Upload File Here
              </div>

              <div style={{ height: '1px', backgroundColor: 'var(--dropdown-border)', margin: '4px 0' }} />

              <div
                onClick={() => {
                  setModalState({
                    type: 'rename',
                    target: contextMenu.target!,
                    inputValue: contextMenu.target!.name,
                  });
                  setContextMenu({ visible: false, x: 0, y: 0, target: null, targetDir: '' });
                }}
                className="pcs-menu-item"
                style={{
                  padding: '7px 12px',
                  fontSize: '12px',
                  color: 'var(--text-secondary)',
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
                className="pcs-menu-item"
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

              <div style={{ height: '1px', backgroundColor: 'var(--dropdown-border)', margin: '4px 0' }} />

              <div
                onClick={() => {
                  loadFiles();
                  setContextMenu({ visible: false, x: 0, y: 0, target: null, targetDir: '' });
                }}
                className="pcs-menu-item"
                style={{
                  padding: '7px 12px',
                  fontSize: '12px',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                }}
              >
                <RefreshCw size={13} color="var(--text-secondary)" /> Refresh
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
                className="pcs-menu-item"
                style={{
                  padding: '7px 12px',
                  fontSize: '12px',
                  color: 'var(--text-main)',
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
                className="pcs-menu-item"
                style={{
                  padding: '7px 12px',
                  fontSize: '12px',
                  color: 'var(--text-secondary)',
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
                className="pcs-menu-item"
                style={{
                  padding: '7px 12px',
                  fontSize: '12px',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  textDecoration: 'none',
                }}
              >
                <Download size={14} /> Download
              </a>

              <div style={{ height: '1px', backgroundColor: 'var(--dropdown-border)', margin: '4px 0' }} />

              <div
                onClick={() => {
                  setModalState({
                    type: 'delete',
                    target: contextMenu.target!,
                  });
                  setContextMenu({ visible: false, x: 0, y: 0, target: null, targetDir: '' });
                }}
                className="pcs-menu-item"
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

              <div style={{ height: '1px', backgroundColor: 'var(--dropdown-border)', margin: '4px 0' }} />

              <div
                onClick={() => {
                  loadFiles();
                  setContextMenu({ visible: false, x: 0, y: 0, target: null, targetDir: '' });
                }}
                className="pcs-menu-item"
                style={{
                  padding: '7px 12px',
                  fontSize: '12px',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                }}
              >
                <RefreshCw size={13} color="var(--text-secondary)" /> Refresh
              </div>
            </>
          )}
        </div>
      )}

      {/* Modal Dialog for Create/Rename/Delete */}
      {modalState.type && (
        <Modal
          onClose={() => setModalState({ type: null })}
          label={
            modalState.type === 'new_file'
              ? 'Create new file'
              : modalState.type === 'new_folder'
              ? 'Create new folder'
              : modalState.type === 'rename'
              ? 'Rename'
              : 'Confirm deletion'
          }
          size="sm"
          testId="file-action-modal"
        >
          <ModalHeader
            icon={
              modalState.type === 'delete' ? (
                <Trash2 size={16} />
              ) : modalState.type === 'new_folder' ? (
                <FolderPlus size={16} />
              ) : modalState.type === 'rename' ? (
                <Edit3 size={16} />
              ) : (
                <FilePlus size={16} />
              )
            }
            iconBackground={modalState.type === 'delete' ? '#dc2626' : undefined}
            title={
              <>
                {modalState.type === 'new_file' && 'Create New File'}
                {modalState.type === 'new_folder' && 'Create New Folder'}
                {modalState.type === 'rename' && 'Rename'}
                {modalState.type === 'delete' && 'Confirm Deletion'}
              </>
            }
            onClose={() => setModalState({ type: null })}
          />
          <ModalBody>
            {modalState.type === 'delete' ? (
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                Are you sure you want to permanently delete{' '}
                <strong style={{ color: '#ef4444' }}>{modalState.target?.name}</strong>?
                {modalState.target?.is_dir && ' All enclosed files will also be removed.'}
              </p>
            ) : (
              <div>
                <p style={{ fontSize: '11.5px', color: 'var(--text-muted)', marginBottom: '6px' }}>
                  {modalState.type === 'new_file' && 'Supports .py, .ipynb, .csv, .md, .txt, .json'}
                  {modalState.type === 'new_folder' && 'Folder will be created in current active directory'}
                  {modalState.type === 'rename' && `Renaming: ${modalState.target?.name}`}
                </p>
                <input
                  type="text"
                  autoFocus
                  className="pcs-input"
                  value={modalState.inputValue || ''}
                  onChange={(e) => setModalState({ ...modalState, inputValue: e.target.value })}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleConfirmModal();
                  }}
                  placeholder={
                    modalState.type === 'new_file'
                      ? 'e.g. script.py, dataset.csv, analysis.ipynb'
                      : 'Folder name'
                  }
                />
              </div>
            )}
          </ModalBody>
          <ModalFooter>
            <button type="button" className="pcs-btn" onClick={() => setModalState({ type: null })}>
              Cancel
            </button>
            <button
              type="button"
              className={`pcs-btn ${modalState.type === 'delete' ? 'pcs-btn--danger' : 'pcs-btn--primary'}`}
              onClick={handleConfirmModal}
            >
              {modalState.type === 'delete' ? 'Delete' : 'Confirm'}
            </button>
          </ModalFooter>
        </Modal>
      )}
    </aside>
  );
};
