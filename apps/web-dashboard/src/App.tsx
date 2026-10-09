import React, { useState, useEffect, useRef } from 'react';
import { Navbar } from './components/Navbar';
import { Sidebar } from './components/Sidebar';
import { NotebookEditor } from './components/NotebookEditor';
import { FileEditorPanel, OpenFileInfo } from './components/FileEditorPanel';
import { AdminDashboard } from './components/AdminDashboard';
import { ErrorBoundary } from './components/ErrorBoundary';
import { RightPanel } from './components/RightPanel';
import { NotebookDocument, NotebookCell, KernelStatus, UserProfile, FileItem } from './types';
import { api } from './services/api';
import { KernelWebSocketClient } from './services/websocket';
import { Globe, X, Lock, LogIn } from 'lucide-react';

export const App: React.FC = () => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [showGuestBanner, setShowGuestBanner] = useState<boolean>(() => {
    return sessionStorage.getItem('pcs_guest_banner_dismissed') !== 'true';
  });
  const [authEmail, setAuthEmail] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [authName, setAuthName] = useState('');
  const [isRegisterMode, setIsRegisterMode] = useState(false);
  const [authError, setAuthError] = useState('');

  // Notebook State
  const [notebook, setNotebook] = useState<NotebookDocument | null>(null);
  const [activeCellId, setActiveCellId] = useState<string | null>(null);
  const [kernelStatus, setKernelStatus] = useState<KernelStatus>('disconnected');
  const [isSaving, setIsSaving] = useState(false);

  // Sidebar Layout State (Right sidebar COLLAPSED by default)
  const [isLeftSidebarOpen, setIsLeftSidebarOpen] = useState<boolean>(() => {
    return localStorage.getItem('pcs_left_sidebar') !== 'false';
  });
  const [isRightSidebarOpen, setIsRightSidebarOpen] = useState<boolean>(false);

  // Panel Resizing State (min 200/max 600 for left, min 280/max 800 for right)
  const [leftSidebarWidth, setLeftSidebarWidth] = useState<number>(() => {
    const saved = localStorage.getItem('pcs_left_sidebar_width');
    return saved ? Math.max(200, Math.min(600, parseInt(saved, 10))) : 280;
  });
  const [rightSidebarWidth, setRightSidebarWidth] = useState<number>(() => {
    const saved = localStorage.getItem('pcs_right_sidebar_width');
    return saved ? Math.max(280, Math.min(800, parseInt(saved, 10))) : 420;
  });
  const [isDraggingLeft, setIsDraggingLeft] = useState(false);
  const [isDraggingRight, setIsDraggingRight] = useState(false);

  // Right Sidebar Active Files & Multi-Tab State
  const [openFiles, setOpenFiles] = useState<OpenFileInfo[]>([]);
  const [activeFilePath, setActiveFilePath] = useState<string | null>(null);
  const [rightSidebarTab, setRightSidebarTab] = useState<'editor' | 'tools'>('editor');
  const [isAdminOpen, setIsAdminOpen] = useState(false);

  const wsClientRef = useRef<KernelWebSocketClient | null>(null);

  // Mouse drag handler for vertical resizers
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isDraggingLeft) {
        e.preventDefault();
        const newWidth = Math.max(200, Math.min(600, e.clientX));
        setLeftSidebarWidth(newWidth);
        localStorage.setItem('pcs_left_sidebar_width', String(newWidth));
      } else if (isDraggingRight) {
        e.preventDefault();
        const newWidth = Math.max(280, Math.min(800, window.innerWidth - e.clientX));
        setRightSidebarWidth(newWidth);
        localStorage.setItem('pcs_right_sidebar_width', String(newWidth));
      }
    };

    const handleMouseUp = () => {
      setIsDraggingLeft(false);
      setIsDraggingRight(false);
    };

    if (isDraggingLeft || isDraggingRight) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isDraggingLeft, isDraggingRight]);

  const handleMouseDownLeft = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsDraggingLeft(true);
  };

  const handleMouseDownRight = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsDraggingRight(true);
  };

  // Save left sidebar preference
  const toggleLeftSidebar = () => {
    setIsLeftSidebarOpen((prev) => {
      const next = !prev;
      localStorage.setItem('pcs_left_sidebar', String(next));
      return next;
    });
  };

  const toggleRightSidebar = () => {
    setIsRightSidebarOpen((prev) => !prev);
  };

  const dismissGuestBanner = () => {
    setShowGuestBanner(false);
    sessionStorage.setItem('pcs_guest_banner_dismissed', 'true');
  };

  // Initialize auth or enter Guest Mode on mount (Zero Login Wall)
  useEffect(() => {
    const initAuth = async () => {
      const token = api.getToken();
      if (token) {
        try {
          const profile = await api.getMe();
          setUser(profile);
          await loadOrCreateInitialNotebook();
          return;
        } catch {
          api.clearToken();
        }
      }
      // Zero Login Wall: Initialize Guest session in Public Workspace
      try {
        await api.initGuestSession();
      } catch (e) {
        console.warn('Guest session init error:', e);
      }
      await loadOrCreateInitialNotebook();
    };
    initAuth();
  }, []);

  const loadOrCreateInitialNotebook = async () => {
    try {
      const nbs = await api.listNotebooks();
      if (nbs.length > 0) {
        const loaded = await api.getNotebook(nbs[0].id);
        setNotebook(loaded);
        if (loaded.cells.length > 0) setActiveCellId(loaded.cells[0].id);
      } else {
        const created = await api.createNotebook('Welcome to Python Cloud Studio');
        setNotebook(created);
        if (created.cells.length > 0) setActiveCellId(created.cells[0].id);
      }
    } catch (err) {
      console.error('Failed to initialize notebook:', err);
    }
  };

  // Connect WebSocket when notebook is ready (works for both guests and authenticated users)
  useEffect(() => {
    if (!notebook) return;

    const token = api.getToken() || api.getGuestToken();
    const sessionId = `session-${notebook.id}`;
    const wsClient = new KernelWebSocketClient(
      sessionId,
      token,
      // onOutput
      (cellId, output) => {
        setNotebook((prev) => {
          if (!prev) return prev;
          return {
            ...prev,
            cells: prev.cells.map((c) => {
              if (c.id === cellId) {
                return {
                  ...c,
                  outputs: [...c.outputs, output],
                };
              }
              return c;
            }),
          };
        });
      },
      // onStatus
      (status) => {
        setKernelStatus(status);
      },
      // onComplete
      (cellId, reply) => {
        setNotebook((prev) => {
          if (!prev) return prev;
          return {
            ...prev,
            cells: prev.cells.map((c) => {
              if (c.id === cellId) {
                return {
                  ...c,
                  is_running: false,
                  execution_count: reply.execution_count ?? c.execution_count,
                };
              }
              return c;
            }),
          };
        });
      }
    );

    wsClient.connect();
    wsClientRef.current = wsClient;

    return () => {
      wsClient.disconnect();
    };
  }, [notebook?.id, user?.id]);

  // Open file in right sidebar (called on double-click from File Explorer)
  const handleOpenFile = async (fileItem: FileItem) => {
    // If file is already open in tabs, select its tab
    const existing = openFiles.find((f) => f.path === fileItem.path);
    if (existing) {
      setActiveFilePath(fileItem.path);
      setRightSidebarTab('editor');
      setIsRightSidebarOpen(true);
      return;
    }

    try {
      const res = await api.readFile(fileItem.path);
      const newFile: OpenFileInfo = {
        path: res.path,
        name: fileItem.name,
        content: res.content,
        isDirty: false,
      };
      setOpenFiles((prev) => [...prev, newFile]);
      setActiveFilePath(fileItem.path);
      setRightSidebarTab('editor');
      // Automatically expand right sidebar on double-click!
      setIsRightSidebarOpen(true);
    } catch (err) {
      // If binary or special file
      const newFile: OpenFileInfo = {
        path: fileItem.path,
        name: fileItem.name,
        content: '',
        isDirty: false,
      };
      setOpenFiles((prev) => [...prev, newFile]);
      setActiveFilePath(fileItem.path);
      setRightSidebarTab('editor');
      setIsRightSidebarOpen(true);
    }
  };

  const handleSelectTab = (path: string) => {
    setActiveFilePath(path);
  };

  const handleCloseTab = (path: string) => {
    setOpenFiles((prev) => {
      const remaining = prev.filter((f) => f.path !== path);
      if (activeFilePath === path) {
        const nextActive = remaining.length > 0 ? remaining[remaining.length - 1].path : null;
        setActiveFilePath(nextActive);
        if (!nextActive) {
          setIsRightSidebarOpen(false);
        }
      }
      return remaining;
    });
  };

  // Open .ipynb notebook file directly in workspace
  const handleOpenNotebookFile = async (path: string) => {
    try {
      const res = await api.readFile(path);
      const parsed = JSON.parse(res.content);
      const fname = path.split('/').pop()?.replace('.ipynb', '') || 'Notebook';

      // Load cells from valid .ipynb JSON
      const cells: NotebookCell[] = (parsed.cells || []).map((c: any, idx: number) => ({
        id: `cell-${idx}-${Date.now()}`,
        cell_type: c.cell_type || 'code',
        source: Array.isArray(c.source) ? c.source.join('') : c.source || '',
        outputs: c.outputs || [],
        execution_count: c.execution_count ?? null,
      }));

      // Find or create notebook in DB
      const existingList = await api.listNotebooks();
      const match = existingList.find((n) => n.title === fname);
      if (match) {
        const loaded = await api.getNotebook(match.id);
        setNotebook(loaded);
      } else {
        const created = await api.createNotebook(fname, parsed.metadata?.kernelspec?.name || 'python3');
        created.cells = cells;
        setNotebook(created);
        await api.saveNotebook(created);
      }
    } catch (err) {
      console.error('Failed to open notebook file:', err);
    }
  };

  // Create new notebook
  const handleCreateNewNotebook = async () => {
    try {
      const title = `Notebook_${Date.now().toString().slice(-4)}`;
      const created = await api.createNotebook(title);
      setNotebook(created);
      if (created.cells.length > 0) setActiveCellId(created.cells[0].id);
    } catch (err) {
      console.error('Failed to create notebook:', err);
    }
  };

  // File save handler in right sidebar
  const handleSaveOpenFile = async (path: string, newContent: string) => {
    await api.writeFile(path, newContent);
    setOpenFiles((prev) =>
      prev.map((f) => (f.path === path ? { ...f, content: newContent, isDirty: false } : f))
    );
  };

  const handleContentChange = (newContent: string, path?: string) => {
    const targetPath = path || activeFilePath;
    if (!targetPath) return;
    setOpenFiles((prev) =>
      prev.map((f) => (f.path === targetPath ? { ...f, content: newContent, isDirty: true } : f))
    );
  };

  const handleUpdateTitle = (newTitle: string) => {
    if (!notebook) return;
    setNotebook({ ...notebook, title: newTitle });
  };

  const handleUpdateCellSource = (cellId: string, newSource: string) => {
    if (!notebook) return;
    setNotebook({
      ...notebook,
      cells: notebook.cells.map((c) => (c.id === cellId ? { ...c, source: newSource } : c)),
    });
  };

  const handleRunCell = (cellId: string, sourceOverride?: string) => {
    if (!notebook) return;
    const targetCell = notebook.cells.find((c) => c.id === cellId);
    if (!targetCell || targetCell.cell_type !== 'code') return;

    const codeToExecute =
      sourceOverride !== undefined && sourceOverride.trim().length > 0
        ? sourceOverride
        : targetCell.source;

    // Reset cell output and mark running, updating source if override provided
    setNotebook((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        cells: prev.cells.map((c) =>
          c.id === cellId
            ? {
                ...c,
                source: codeToExecute,
                outputs: [],
                is_running: true,
              }
            : c
        ),
      };
    });

    if (wsClientRef.current && wsClientRef.current.isOpen()) {
      try {
        wsClientRef.current.execute(cellId, codeToExecute);
        return;
      } catch (err) {
        console.warn('WebSocket execution failed, using REST fallback:', err);
      }
    }

    // Direct REST execution fallback
    api
      .runCode(`session-${notebook.id}`, codeToExecute)
      .then((res) => {
        setNotebook((prev) => {
          if (!prev) return prev;
          return {
            ...prev,
            cells: prev.cells.map((c) =>
              c.id === cellId
                ? {
                    ...c,
                    outputs: res.outputs,
                    execution_count: res.execution_count,
                    is_running: false,
                  }
                : c
            ),
          };
        });
      })
      .catch((err) => {
        setNotebook((prev) => {
          if (!prev) return prev;
          return {
            ...prev,
            cells: prev.cells.map((c) =>
              c.id === cellId
                ? {
                    ...c,
                    outputs: [
                      {
                        output_type: 'error',
                        ename: 'ExecutionError',
                        evalue: err.message || 'Execution failed',
                        traceback: [],
                      },
                    ],
                    is_running: false,
                  }
                : c
            ),
          };
        });
      });
  };

  const handleRunAll = () => {
    if (!notebook) return;
    const codeCells = notebook.cells.filter((c) => c.cell_type === 'code');
    for (const cell of codeCells) {
      handleRunCell(cell.id);
    }
  };

  const handleRestartKernel = () => {
    if (wsClientRef.current) {
      wsClientRef.current.restart();
    }
  };

  const handleInterruptKernel = () => {
    if (wsClientRef.current) {
      wsClientRef.current.interrupt();
    }
  };

  const handleSaveNotebook = async () => {
    if (!notebook) return;
    setIsSaving(true);
    try {
      await api.saveNotebook(notebook);
    } catch (err) {
      console.error('Failed to save notebook:', err);
    } finally {
      setTimeout(() => setIsSaving(false), 500);
    }
  };

  const handleAddCell = (index: number, cellType: 'code' | 'markdown') => {
    if (!notebook) return;
    const newCell: NotebookCell = {
      id: `cell-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
      cell_type: cellType,
      source: cellType === 'code' ? 'print("New cell")' : '### New Notes',
      outputs: [],
    };
    const updated = [...notebook.cells];
    updated.splice(index, 0, newCell);
    setNotebook({ ...notebook, cells: updated });
    setActiveCellId(newCell.id);
  };

  const handleDeleteCell = (cellId: string) => {
    if (!notebook) return;
    const updated = notebook.cells.filter((c) => c.id !== cellId);
    setNotebook({ ...notebook, cells: updated });
  };

  const handleMoveCell = (cellId: string, direction: 'up' | 'down') => {
    if (!notebook) return;
    const idx = notebook.cells.findIndex((c) => c.id === cellId);
    if (idx < 0) return;
    if (direction === 'up' && idx === 0) return;
    if (direction === 'down' && idx === notebook.cells.length - 1) return;

    const targetIdx = direction === 'up' ? idx - 1 : idx + 1;
    const updated = [...notebook.cells];
    const [moved] = updated.splice(idx, 1);
    updated.splice(targetIdx, 0, moved);
    setNotebook({ ...notebook, cells: updated });
  };

  // Duplicate a cell
  const handleDuplicateCell = (cellId: string) => {
    if (!notebook) return;
    const idx = notebook.cells.findIndex((c) => c.id === cellId);
    if (idx < 0) return;
    const target = notebook.cells[idx];
    const duplicated: NotebookCell = {
      id: `cell-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
      cell_type: target.cell_type,
      source: target.source,
      outputs: [],
      execution_count: null,
    };
    const updated = [...notebook.cells];
    updated.splice(idx + 1, 0, duplicated);
    setNotebook({ ...notebook, cells: updated });
    setActiveCellId(duplicated.id);
  };

  // Clear output of a single cell
  const handleClearCellOutput = (cellId: string) => {
    if (!notebook) return;
    setNotebook({
      ...notebook,
      cells: notebook.cells.map((c) =>
        c.id === cellId ? { ...c, outputs: [], execution_count: null } : c
      ),
    });
  };

  // Clear all outputs across the notebook
  const handleClearAllOutputs = () => {
    if (!notebook) return;
    setNotebook({
      ...notebook,
      cells: notebook.cells.map((c) => ({
        ...c,
        outputs: [],
        execution_count: null,
      })),
    });
  };

  // Update cell metadata (e.g. custom_height)
  const handleUpdateCellMetadata = (cellId: string, metadata: Record<string, any>) => {
    if (!notebook) return;
    setNotebook({
      ...notebook,
      cells: notebook.cells.map((c) =>
        c.id === cellId ? { ...c, metadata: { ...c.metadata, ...metadata } } : c
      ),
    });
  };

  // Run current cell (retain focus)
  const handleRunCurrentCell = (cellId: string, sourceOverride?: string) => {
    handleRunCell(cellId, sourceOverride);
    setActiveCellId(cellId);
  };

  // Run cell & advance to next cell (or append new code cell if at end)
  const handleRunAndAdvance = (cellId: string, sourceOverride?: string) => {
    if (!notebook) return;
    handleRunCell(cellId, sourceOverride);
    const idx = notebook.cells.findIndex((c) => c.id === cellId);
    if (idx >= 0 && idx < notebook.cells.length - 1) {
      setActiveCellId(notebook.cells[idx + 1].id);
    } else if (idx === notebook.cells.length - 1) {
      const newCell: NotebookCell = {
        id: `cell-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
        cell_type: 'code',
        source: '',
        outputs: [],
      };
      setNotebook((prev) => (prev ? { ...prev, cells: [...prev.cells, newCell] } : prev));
      setActiveCellId(newCell.id);
    }
  };

  // Run cell & insert new code cell below
  const handleRunAndInsertBelow = (cellId: string, sourceOverride?: string) => {
    if (!notebook) return;
    handleRunCell(cellId, sourceOverride);
    const idx = notebook.cells.findIndex((c) => c.id === cellId);
    const newCell: NotebookCell = {
      id: `cell-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
      cell_type: 'code',
      source: '',
      outputs: [],
    };
    setNotebook((prev) => {
      if (!prev) return prev;
      const updated = [...prev.cells];
      const insertIdx = idx >= 0 ? idx + 1 : updated.length;
      updated.splice(insertIdx, 0, newCell);
      return { ...prev, cells: updated };
    });
    setActiveCellId(newCell.id);
  };

  const handleInsertCodeSnippet = (code: string) => {
    if (!notebook) return;
    handleAddCell(notebook.cells.length, 'code');
    setTimeout(() => {
      setNotebook((prev) => {
        if (!prev) return prev;
        const last = prev.cells[prev.cells.length - 1];
        return {
          ...prev,
          cells: prev.cells.map((c) => (c.id === last.id ? { ...c, source: code } : c)),
        };
      });
    }, 50);
  };

  const handleLogout = async () => {
    api.clearToken();
    setUser(null);
    try {
      await api.initGuestSession();
    } catch (err) {
      console.warn('Guest session init error:', err);
    }
    await loadOrCreateInitialNotebook();
  };

  const handleAuthSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError('');
    try {
      if (isRegisterMode) {
        await api.register(authEmail, authPassword, authName || 'Student', 'student');
      } else {
        await api.login(authEmail, authPassword);
      }
      const profile = await api.getMe();
      setUser(profile);
      setIsAuthModalOpen(false);
      // Load user's private notebooks
      await loadOrCreateInitialNotebook();
    } catch (err: any) {
      setAuthError(err.message || 'Authentication failed');
    }
  };

  return (
    <div style={{ height: '100vh', width: '100vw', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <Navbar
        title={notebook?.title || 'Untitled Notebook'}
        onTitleChange={handleUpdateTitle}
        kernelStatus={kernelStatus}
        isSaving={isSaving}
        user={user}
        onRunAll={handleRunAll}
        onRestartKernel={handleRestartKernel}
        onInterruptKernel={handleInterruptKernel}
        onClearAllOutputs={handleClearAllOutputs}
        onSave={handleSaveNotebook}
        onLogout={handleLogout}
        isLeftSidebarOpen={isLeftSidebarOpen}
        onToggleLeftSidebar={toggleLeftSidebar}
        isRightSidebarOpen={isRightSidebarOpen}
        onToggleRightSidebar={toggleRightSidebar}
        onOpenAuthModal={() => setIsAuthModalOpen(true)}
        onOpenAdminDashboard={() => setIsAdminOpen(true)}
      />

      {/* Guest Mode Public Privacy Notice Banner */}
      {!user && showGuestBanner && (
        <div
          data-testid="guest-privacy-banner"
          style={{
            backgroundColor: 'var(--bg-card)',
            borderBottom: '1px solid var(--border-main)',
            padding: '7px 16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '12.5px',
            color: 'var(--text-main)',
            zIndex: 10,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Globe size={15} color="var(--border-accent)" />
            <span>
              <strong style={{ color: 'var(--border-accent)' }}>Guest Mode — Public Workspace:</strong> You are working in the public workspace. Any files or notebooks you create are visible to other users.
            </span>
            <button
              onClick={() => setIsAuthModalOpen(true)}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--border-accent)',
                textDecoration: 'underline',
                cursor: 'pointer',
                fontSize: '12.5px',
                fontWeight: 600,
                padding: '0 4px',
              }}
            >
              Sign in for your private workspace
            </button>
          </div>
          <button
            onClick={dismissGuestBanner}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
              fontSize: '14px',
              padding: '2px 6px',
              lineHeight: 1,
            }}
            title="Dismiss notice"
          >
            ✕
          </button>
        </div>
      )}

      {/* 3-Panel Resizable Workspace */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden', position: 'relative' }}>
        {/* Left Sidebar (Files) */}
        {isLeftSidebarOpen && (
          <Sidebar
            onOpenFile={handleOpenFile}
            onOpenNotebookFile={handleOpenNotebookFile}
            onCreateNewNotebook={handleCreateNewNotebook}
            activeFilePath={activeFilePath || undefined}
            width={leftSidebarWidth}
          />
        )}

        {/* Left Resizer Divider */}
        {isLeftSidebarOpen && (
          <div
            data-testid="left-resizer"
            onMouseDown={handleMouseDownLeft}
            style={{
              width: '5px',
              cursor: 'col-resize',
              backgroundColor: isDraggingLeft ? 'var(--border-accent)' : 'var(--border-main)',
              borderLeft: '1px solid var(--border-main)',
              borderRight: '1px solid var(--border-secondary)',
              transition: isDraggingLeft ? 'none' : 'background-color 0.15s ease',
              zIndex: 20,
              flexShrink: 0,
              userSelect: 'none',
            }}
            title="Drag to resize Left Sidebar"
          />
        )}

        {/* Center Workspace (Jupyter Notebook Editor) - 100% remaining horizontal space */}
        {notebook && (
          <div
            style={{
              flex: 1,
              minWidth: 0,
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
            }}
          >
            <NotebookEditor
              cells={notebook.cells}
              onUpdateCellSource={handleUpdateCellSource}
              onRunCell={handleRunCell}
              onAddCell={handleAddCell}
              onDeleteCell={handleDeleteCell}
              onMoveCell={handleMoveCell}
              onDuplicateCell={handleDuplicateCell}
              onClearCellOutput={handleClearCellOutput}
              onClearAllOutputs={handleClearAllOutputs}
              onRunCurrentCell={handleRunCurrentCell}
              onRunAndAdvance={handleRunAndAdvance}
              onRunAndInsertBelow={handleRunAndInsertBelow}
              activeCellId={activeCellId}
              onSelectCell={setActiveCellId}
              sessionId={notebook ? `session-${notebook.id}` : undefined}
              onUpdateCellMetadata={handleUpdateCellMetadata}
            />
          </div>
        )}

        {/* Right Resizer Divider */}
        {isRightSidebarOpen && (
          <div
            data-testid="right-resizer"
            onMouseDown={handleMouseDownRight}
            style={{
              width: '5px',
              cursor: 'col-resize',
              backgroundColor: isDraggingRight ? 'var(--border-accent)' : 'var(--border-main)',
              borderLeft: '1px solid var(--border-secondary)',
              borderRight: '1px solid var(--border-main)',
              transition: isDraggingRight ? 'none' : 'background-color 0.15s ease',
              zIndex: 20,
              flexShrink: 0,
              userSelect: 'none',
            }}
            title="Drag to resize Right Sidebar"
          />
        )}

        {/* Right Sidebar (File Preview & Code Editor / Tools) */}
        {isRightSidebarOpen && (
          <div
            style={{
              width: `${rightSidebarWidth}px`,
              flexShrink: 0,
              height: '100%',
              display: 'flex',
              overflow: 'hidden',
            }}
          >
            {rightSidebarTab === 'editor' && openFiles.length > 0 ? (
              <FileEditorPanel
                openFiles={openFiles}
                activeFilePath={activeFilePath}
                isOpen={isRightSidebarOpen}
                onClose={() => setIsRightSidebarOpen(false)}
                onSelectTab={handleSelectTab}
                onCloseTab={handleCloseTab}
                onSave={handleSaveOpenFile}
                onContentChange={handleContentChange}
                onOpenAsNotebook={handleOpenNotebookFile}
                width={rightSidebarWidth}
              />
            ) : (
              <RightPanel
                onInsertCodeSnippet={handleInsertCodeSnippet}
                width={rightSidebarWidth}
              />
            )}
          </div>
        )}
      </div>

      {/* Non-intrusive Authentication Modal Dialog */}
      {isAuthModalOpen && (
        <div
          data-testid="auth-modal"
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
            if (e.target === e.currentTarget) setIsAuthModalOpen(false);
          }}
        >
          <div
            style={{
              width: '400px',
              padding: '30px',
              backgroundColor: 'var(--bg-modal)',
              borderRadius: '12px',
              border: '1px solid var(--border-secondary)',
              boxShadow: '0 25px 50px rgba(0, 0, 0, 0.4)',
              position: 'relative',
            }}
          >
            <button
              onClick={() => setIsAuthModalOpen(false)}
              style={{
                position: 'absolute',
                top: '16px',
                right: '16px',
                backgroundColor: 'transparent',
                border: 'none',
                color: 'var(--text-secondary)',
                cursor: 'pointer',
                padding: '4px',
              }}
              title="Close"
            >
              <X size={18} />
            </button>

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
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
                <Lock size={16} color="#ffffff" />
              </div>
              <h2 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--text-main)', margin: 0 }}>
                {isRegisterMode ? 'Create Private Workspace' : 'Sign In to Workspace'}
              </h2>
            </div>

            <p style={{ fontSize: '12.5px', color: 'var(--text-secondary)', marginBottom: '20px' }}>
              {isRegisterMode
                ? 'Get your dedicated, completely private environment with isolated files.'
                : 'Access your private workspace and secure notebooks.'}
            </p>

            {authError && (
              <div
                style={{
                  padding: '8px 12px',
                  backgroundColor: '#450a0a',
                  border: '1px solid #ef4444',
                  borderRadius: '6px',
                  color: '#fca5a5',
                  fontSize: '12px',
                  marginBottom: '16px',
                }}
              >
                {authError}
              </div>
            )}

            <form onSubmit={handleAuthSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {isRegisterMode && (
                <div>
                  <label style={{ fontSize: '12px', color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>
                    Full Name
                  </label>
                  <input
                    type="text"
                    required
                    value={authName}
                    onChange={(e) => setAuthName(e.target.value)}
                    placeholder="e.g. Alex Johnson"
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      backgroundColor: 'var(--bg-input)',
                      border: '1px solid var(--border-secondary)',
                      borderRadius: '6px',
                      color: 'var(--text-main)',
                      outline: 'none',
                      fontSize: '13px',
                      boxSizing: 'border-box',
                    }}
                  />
                </div>
              )}
              <div>
                <label style={{ fontSize: '12px', color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>
                  Email Address
                </label>
                <input
                  type="email"
                  required
                  value={authEmail}
                  onChange={(e) => setAuthEmail(e.target.value)}
                  placeholder="user@example.com"
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    backgroundColor: 'var(--bg-input)',
                    border: '1px solid var(--border-secondary)',
                    borderRadius: '6px',
                    color: 'var(--text-main)',
                    outline: 'none',
                    fontSize: '13px',
                    boxSizing: 'border-box',
                  }}
                />
              </div>
              <div>
                <label style={{ fontSize: '12px', color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>
                  Password
                </label>
                <input
                  type="password"
                  required
                  value={authPassword}
                  onChange={(e) => setAuthPassword(e.target.value)}
                  placeholder="••••••••"
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    backgroundColor: 'var(--bg-input)',
                    border: '1px solid var(--border-secondary)',
                    borderRadius: '6px',
                    color: 'var(--text-main)',
                    outline: 'none',
                    fontSize: '13px',
                    boxSizing: 'border-box',
                  }}
                />
              </div>

              <button
                type="submit"
                style={{
                  marginTop: '8px',
                  padding: '10px 16px',
                  backgroundColor: '#2563eb',
                  border: 'none',
                  borderRadius: '6px',
                  color: '#ffffff',
                  fontWeight: 600,
                  fontSize: '13px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px',
                }}
              >
                <LogIn size={15} />
                {isRegisterMode ? 'Create Account & Switch' : 'Sign In'}
              </button>
            </form>

            <div style={{ marginTop: '16px', textAlign: 'center', fontSize: '12px', color: '#94a3b8' }}>
              {isRegisterMode ? (
                <span>
                  Already have an account?{' '}
                  <a
                    href="#"
                    onClick={(e) => {
                      e.preventDefault();
                      setIsRegisterMode(false);
                      setAuthError('');
                    }}
                    style={{ color: '#3b82f6', textDecoration: 'none' }}
                  >
                    Sign In
                  </a>
                </span>
              ) : (
                <span>
                  New to Cloud Studio?{' '}
                  <a
                    href="#"
                    onClick={(e) => {
                      e.preventDefault();
                      setIsRegisterMode(true);
                      setAuthError('');
                    }}
                    style={{ color: '#3b82f6', textDecoration: 'none' }}
                  >
                    Create Account
                  </a>
                </span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Super Admin Dashboard Modal */}
      <ErrorBoundary fallbackTitle="Admin Console Encountered an Issue" onClose={() => setIsAdminOpen(false)}>
        <AdminDashboard
          isOpen={isAdminOpen}
          onClose={() => setIsAdminOpen(false)}
          currentUserEmail={user?.email}
        />
      </ErrorBoundary>
    </div>
  );
};
