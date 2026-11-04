import React, { useState, useEffect, useRef } from 'react';
import { Navbar } from './components/Navbar';
import { Sidebar } from './components/Sidebar';
import { NotebookEditor } from './components/NotebookEditor';
import { FileEditorPanel, OpenFileInfo } from './components/FileEditorPanel';
import { AdminDashboard } from './components/AdminDashboard';
import { ErrorBoundary } from './components/ErrorBoundary';
import { Modal, ModalHeader, ModalBody } from './components/Modal';
import { RightPanel } from './components/RightPanel';
import { NotebooksModal } from './components/NotebooksModal';
import { SecretsModal } from './components/SecretsModal';
import { NotebookDocument, NotebookCell, KernelStatus, KernelOutput, UserProfile, FileItem, PendingInput } from './types';
import { api } from './services/api';
import { guestStore } from './services/guestStore';
import { KernelWebSocketClient } from './services/websocket';
import { Globe, X, Lock, LogIn, RotateCcw, CheckCircle, AlertCircle } from 'lucide-react';

// After Stop, the server interrupts, then stops the cell's child processes ~3 s later (plus up to
// ~4 s for them to exit). If a cell is still running after this, interrupting has failed.
const STOP_RECOVERY_DELAY_MS = 8000;

// A print loop can stream thousands of chunks; keep at most this much text per stream output
const MAX_STREAM_CHARS = 200_000;
const TRUNCATION_NOTICE = '[... earlier output truncated ...]\n';

// Appends a streamed output to a cell, merging consecutive stdout/stderr chunks into one output
// (as Jupyter does) so runaway printing cannot create thousands of output elements.
// Same rules as apply_output() in services/runtime_management/kernel_session.py
function appendOutput(outputs: KernelOutput[], output: KernelOutput): KernelOutput[] {
  if (output.output_type === 'clear_output') {
    if (!output.wait) return [];
    // clear_output(wait=True): a marker; the outputs are cleared when the next one arrives
    const pending = outputs[outputs.length - 1]?.output_type === 'clear_output';
    return pending ? outputs : [...outputs, output];
  }
  if (outputs[outputs.length - 1]?.output_type === 'clear_output') outputs = [];
  if (output.output_type === 'update_display_data') {
    return outputs.map((o) =>
      o.display_id === output.display_id && (o.output_type === 'display_data' || o.output_type === 'execute_result')
        ? { ...o, data: output.data, metadata: output.metadata }
        : o
    );
  }
  const last = outputs[outputs.length - 1];
  if (output.output_type !== 'stream' || !last || last.output_type !== 'stream' || last.name !== output.name) {
    return [...outputs, output];
  }
  const asText = (t: string | string[] | undefined) => (Array.isArray(t) ? t.join('') : t ?? '');
  let text = asText(last.text) + asText(output.text);
  if (text.length > MAX_STREAM_CHARS) {
    text = TRUNCATION_NOTICE + text.slice(text.length - MAX_STREAM_CHARS);
  }
  return [...outputs.slice(0, -1), { ...last, text }];
}

// Layout breakpoints (px): drawers below COMPACT, a full-screen file editor below PHONE
const COMPACT_MAX_WIDTH = 1024;
const PHONE_MAX_WIDTH = 768;

export const App: React.FC = () => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [isNotebooksModalOpen, setIsNotebooksModalOpen] = useState(false);
  const [isSecretsModalOpen, setIsSecretsModalOpen] = useState(false);
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
  // Latest notebook for listeners and timers that outlive a render
  const notebookRef = useRef<NotebookDocument | null>(null);
  notebookRef.current = notebook;
  const [activeCellId, setActiveCellId] = useState<string | null>(null);
  const [kernelStatus, setKernelStatus] = useState<KernelStatus>('disconnected');
  const [isRestartingKernel, setIsRestartingKernel] = useState(false);
  const [kernelToast, setKernelToast] = useState<{ text: string; type: 'info' | 'success' | 'error' } | null>(null);
  const [pendingInput, setPendingInput] = useState<PendingInput | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  // False in private windows or when site storage is blocked: no browser copy of the guest workspace
  const [guestStorageAvailable, setGuestStorageAvailable] = useState(true);
  const autoSaveTimerRef = useRef<NodeJS.Timeout | null>(null);
  const isDirtyRef = useRef(false);

  // Layout mode. Below COMPACT_MAX_WIDTH the side panels open as overlay drawers instead of squeezing
  // the notebook; below PHONE_MAX_WIDTH the file editor takes the whole workspace (one editor at a time).
  const [viewportWidth, setViewportWidth] = useState<number>(() =>
    typeof window !== 'undefined' ? window.innerWidth : 1280
  );
  const isCompact = viewportWidth < COMPACT_MAX_WIDTH;
  const isPhone = viewportWidth < PHONE_MAX_WIDTH;

  useEffect(() => {
    // Only the width matters: mobile browsers also fire resize when the on-screen keyboard opens,
    // which must not close the editor the user is typing in
    const handleResize = () => setViewportWidth(window.innerWidth);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Sidebar Layout State (Right sidebar COLLAPSED by default; drawers start closed on small screens)
  const [isLeftSidebarOpen, setIsLeftSidebarOpen] = useState<boolean>(() => {
    if (typeof window !== 'undefined' && window.innerWidth < COMPACT_MAX_WIDTH) return false;
    return localStorage.getItem('pcs_left_sidebar') !== 'false';
  });
  const [isRightSidebarOpen, setIsRightSidebarOpen] = useState<boolean>(false);

  // Crossing into drawer mode closes the drawers so the notebook is visible; crossing back restores
  // the docked sidebar the user chose on desktop
  const wasCompactRef = useRef(isCompact);
  useEffect(() => {
    if (isCompact === wasCompactRef.current) return;
    wasCompactRef.current = isCompact;
    if (isCompact) {
      setIsLeftSidebarOpen(false);
      setIsRightSidebarOpen(false);
    } else {
      setIsLeftSidebarOpen(localStorage.getItem('pcs_left_sidebar') !== 'false');
    }
  }, [isCompact]);

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
  // Cells whose execution was sent over the WebSocket and has not replied yet
  const wsRunningCellsRef = useRef<Set<string>>(new Set());
  // Offered after Stop when code keeps running (interrupt could not stop it)
  const [showRecoveryPrompt, setShowRecoveryPrompt] = useState(false);
  const recoveryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

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
      // The drawer's open state is transient; only the docked sidebar's preference is remembered
      if (!isCompact) localStorage.setItem('pcs_left_sidebar', String(next));
      return next;
    });
  };
  const toggleLeftSidebarRef = useRef(toggleLeftSidebar);
  toggleLeftSidebarRef.current = toggleLeftSidebar;

  const toggleRightSidebar = () => {
    setIsRightSidebarOpen((prev) => !prev);
  };

  useEffect(() => {
    if (!isCompact || !(isLeftSidebarOpen || (isRightSidebarOpen && !isPhone))) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Escape' || e.defaultPrevented) return;
      if (document.querySelector('.pcs-modal-backdrop, .tb-menu')) return;
      if (isLeftSidebarOpen) setIsLeftSidebarOpen(false);
      else setIsRightSidebarOpen(false);
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [isCompact, isPhone, isLeftSidebarOpen, isRightSidebarOpen]);

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
      // Zero Login Wall: this browser's private guest workspace (resumed with its existing token)
      await startGuestWorkspace();
      await loadOrCreateInitialNotebook();
    };
    initAuth();
  }, []);

  // Guest workspace: make sure of the session, restore the browser copy into a workspace the server
  // has just recreated, and note whether this browser can keep a copy at all
  const startGuestWorkspace = async () => {
    try {
      await api.initGuestSession();
      setGuestStorageAvailable(await guestStore.isAvailable());
      const restored = await api.restoreGuestWorkspace();
      if (restored > 0) {
        setKernelToast({ text: `Your guest workspace was restored from this browser (${restored} items).`, type: 'success' });
        setTimeout(() => setKernelToast(null), 6000);
        window.dispatchEvent(new CustomEvent('pcs-refresh-files'));
      }
    } catch (e) {
      console.warn('Guest workspace start error:', e);
    }
  };

  const loadOrCreateInitialNotebook = async (preferredId?: string) => {
    try {
      const nbs = await api.listNotebooks();
      const targetId = preferredId || localStorage.getItem('pcs_active_notebook_id');
      const match = nbs.find((n) => n.id === targetId);

      if (match) {
        const loaded = await api.getNotebook(match.id);
        setNotebook(loaded);
        localStorage.setItem('pcs_active_notebook_id', loaded.id);
        if (loaded.cells.length > 0) setActiveCellId(loaded.cells[0].id);
      } else if (nbs.length > 0) {
        const loaded = await api.getNotebook(nbs[0].id);
        setNotebook(loaded);
        localStorage.setItem('pcs_active_notebook_id', loaded.id);
        if (loaded.cells.length > 0) setActiveCellId(loaded.cells[0].id);
      } else {
        const created = await api.createNotebook('Welcome to Python Cloud Studio');
        setNotebook(created);
        localStorage.setItem('pcs_active_notebook_id', created.id);
        if (created.cells.length > 0) setActiveCellId(created.cells[0].id);
      }
    } catch (err) {
      console.error('Failed to initialize notebook:', err);
    }
  };

  const handleSelectNotebook = async (id: string) => {
    try {
      const loaded = await api.getNotebook(id);
      setNotebook(loaded);
      localStorage.setItem('pcs_active_notebook_id', loaded.id);
      if (loaded.cells.length > 0) setActiveCellId(loaded.cells[0].id);
    } catch (err) {
      console.error('Failed to switch notebook:', err);
    }
  };

  const getKernelSessionId = (nbId: string): string => {
    // Never put the guest token (a secret) in the session id: it travels in the WebSocket URL.
    // The server separates kernels by owner, so guest sessions only need the notebook id.
    const scope = user?.id ? `usr_${user.id}` : 'guest';
    return `session-${scope}-${nbId}`;
  };

  // Connect WebSocket when notebook is ready (works for both guests and authenticated users)
  useEffect(() => {
    if (!notebook) return;

    const token = api.getToken() || api.getGuestToken();
    const sessionId = getKernelSessionId(notebook.id);
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
                return { ...c, outputs: appendOutput(c.outputs, output) };
              }
              return c;
            }),
          };
        });
      },
      // onStatus
      (status) => {
        setKernelStatus(status);
        if (status === 'disconnected') {
          setPendingInput(null);
          // Results of cells sent over the dropped socket will never arrive; stop their spinners
          const lostCellIds = new Set(wsRunningCellsRef.current);
          wsRunningCellsRef.current.clear();
          if (lostCellIds.size > 0) {
            setNotebook((prev) => {
              if (!prev) return prev;
              return {
                ...prev,
                cells: prev.cells.map((c) =>
                  lostCellIds.has(c.id) && c.is_running
                    ? {
                        ...c,
                        is_running: false,
                        outputs: [
                          ...c.outputs,
                          {
                            output_type: 'error',
                            ename: 'ConnectionLost',
                            evalue:
                              'The connection to the Python kernel was lost while this cell was running. Reconnecting automatically; run the cell again once the kernel is idle.',
                            traceback: [],
                          },
                        ],
                      }
                    : c
                ),
              };
            });
          }
        }
      },
      // onComplete
      (cellId, reply) => {
        wsRunningCellsRef.current.delete(cellId);
        window.dispatchEvent(new CustomEvent('pcs-refresh-diagnostics'));
        setPendingInput((prev) => (prev && prev.cellId === cellId ? null : prev));
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
      },
      // onInputRequest: the running cell called input() / getpass()
      (cellId, prompt, password) => {
        setPendingInput({ cellId, prompt, password });
      },
      // onServerError: e.g. kernel quota or server capacity reached
      (message) => {
        setKernelToast({ text: message, type: 'error' });
        setTimeout(() => setKernelToast(null), 6000);
      }
    );

    wsClient.connect();
    wsClientRef.current = wsClient;

    return () => {
      wsClient.disconnect();
    };
  }, [notebook?.id, user?.id]);

  // Keep open editor tabs pointing at files that were moved or renamed in the File Explorer
  useEffect(() => {
    const remap = (path: string, oldPath: string, newPath: string) =>
      path === oldPath || path.startsWith(`${oldPath}/`) ? newPath + path.substring(oldPath.length) : path;
    const handleMoved = (e: Event) => {
      const { oldPath, newPath } = (e as CustomEvent<{ oldPath: string; newPath: string }>).detail;
      setOpenFiles((prev) =>
        prev.map((f) => {
          const path = remap(f.path, oldPath, newPath);
          return path === f.path ? f : { ...f, path, name: path.split('/').pop() || f.name };
        })
      );
      setActiveFilePath((prev) => (prev ? remap(prev, oldPath, newPath) : prev));
    };
    window.addEventListener('pcs-file-moved', handleMoved);
    return () => window.removeEventListener('pcs-file-moved', handleMoved);
  }, []);

  // Open file in right sidebar (called on double-click from File Explorer)
  const handleOpenFile = async (fileItem: FileItem) => {
    if (isCompact) setIsLeftSidebarOpen(false);
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
    if (isCompact) {
      setIsLeftSidebarOpen(false);
      if (isPhone) setIsRightSidebarOpen(false);
    }
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
    setNotebook((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        cells: prev.cells.map((c) => (c.id === cellId ? { ...c, source: newSource } : c)),
      };
    });
  };

  const handleRunCell = async (cellId: string, sourceOverride?: string) => {
    if (!notebook) return;
    const targetCell = notebook.cells.find((c) => c.id === cellId);
    if (!targetCell || targetCell.cell_type !== 'code') return;
    // One execution per cell at a time: a second run would interleave both runs' outputs
    if (targetCell.is_running || wsRunningCellsRef.current.has(cellId)) return;

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

    const wsClient = wsClientRef.current;
    // The socket may be reconnecting after a network blip; give it a moment before using REST
    if (wsClient && !wsClient.isOpen()) {
      await wsClient.waitUntilOpen(5000);
    }
    if (wsClient && wsClient.isOpen()) {
      try {
        wsClient.execute(cellId, codeToExecute);
        wsRunningCellsRef.current.add(cellId);
        return;
      } catch (err) {
        console.warn('WebSocket execution failed, using REST fallback:', err);
      }
    }

    // Direct REST execution fallback
    api
      .runCode(getKernelSessionId(notebook.id), codeToExecute)
      .then((res) => {
        window.dispatchEvent(new CustomEvent('pcs-refresh-diagnostics'));
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

  // Run the code cells before / from a cell, in notebook order (queued on the kernel like Run All)
  const handleRunCellsAbove = (cellId: string) => {
    if (!notebook) return;
    const idx = notebook.cells.findIndex((c) => c.id === cellId);
    notebook.cells.slice(0, Math.max(0, idx)).filter((c) => c.cell_type === 'code').forEach((c) => handleRunCell(c.id));
  };
  const handleRunCellsBelow = (cellId: string) => {
    if (!notebook) return;
    const idx = notebook.cells.findIndex((c) => c.id === cellId);
    if (idx < 0) return;
    notebook.cells.slice(idx).filter((c) => c.cell_type === 'code').forEach((c) => handleRunCell(c.id));
  };

  // Command mode M / Y: a code cell becomes Markdown (its outputs go) or back to code
  const handleChangeCellType = (cellId: string, cellType: 'code' | 'markdown') => {
    setNotebook((prev) =>
      prev
        ? {
            ...prev,
            cells: prev.cells.map((c) =>
              c.id === cellId && c.cell_type !== cellType && !c.is_running
                ? { ...c, cell_type: cellType, outputs: cellType === 'markdown' ? [] : c.outputs, execution_count: cellType === 'markdown' ? null : c.execution_count }
                : c
            ),
          }
        : prev
    );
  };

  const handleRestartKernel = async () => {
    if (!notebook) return;
    setIsRestartingKernel(true);
    setShowRecoveryPrompt(false);
    setPendingInput(null);
    setKernelStatus('restarting');
    setKernelToast({ text: 'Restarting Python kernel... all variables will be cleared.', type: 'info' });
    // Cells running now belong to the old kernel; cells started after this click run on the new one
    const runningAtRestart = new Set(notebook.cells.filter((c) => c.is_running).map((c) => c.id));

    try {
      const wsClient = wsClientRef.current;
      if (wsClient && wsClient.isOpen()) {
        // A single restart over the socket: the server first drops queued cells (they reply
        // "abort"), so nothing queued before the restart runs on the fresh kernel
        await wsClient.restart();
      } else {
        await api.controlKernel(getKernelSessionId(notebook.id), 'restart');
      }
      // Cells that were running on the old kernel are finished, even if their reply was lost
      runningAtRestart.forEach((id) => wsRunningCellsRef.current.delete(id));
      setNotebook((prev) =>
        prev
          ? {
              ...prev,
              cells: prev.cells.map((c) => (runningAtRestart.has(c.id) && c.is_running ? { ...c, is_running: false } : c)),
            }
          : prev
      );
      setKernelStatus('idle');
      setKernelToast({ text: 'Python kernel restarted successfully. Variables reset.', type: 'success' });
      window.dispatchEvent(new CustomEvent('pcs-refresh-diagnostics'));
    } catch (err: any) {
      console.warn('Kernel restart failed:', err);
      setKernelStatus(wsClientRef.current?.isOpen() ? 'idle' : 'disconnected');
      setKernelToast({ text: `Kernel restart failed: ${err.message || 'Unknown error'}`, type: 'error' });
    } finally {
      setIsRestartingKernel(false);
      setTimeout(() => setKernelToast(null), 3500);
    }
  };

  // Answer a pending input() prompt; echo prompt + answer into the cell output like Jupyter does
  const handleSubmitInput = (value: string) => {
    if (!pendingInput || !wsClientRef.current) return;
    const { cellId, prompt, password } = pendingInput;
    try {
      wsClientRef.current.sendInput(value);
    } catch (err) {
      console.warn('Failed to send input to kernel:', err);
      return;
    }
    setPendingInput(null);
    setNotebook((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        cells: prev.cells.map((c) =>
          c.id === cellId
            ? {
                ...c,
                outputs: [
                  ...c.outputs,
                  { output_type: 'stream', name: 'stdout', text: `${prompt}${password ? '' : value}\n` },
                ],
              }
            : c
        ),
      };
    });
  };

  // Stop: interrupt the running cell on the real kernel. The server stops processes the cell started
  // if the interrupt alone does not end it; if code is still running afterwards (e.g. blocked in
  // native code), offer a kernel restart instead of leaving the user stuck.
  const handleInterruptKernel = async () => {
    if (!notebook) return;
    const wsClient = wsClientRef.current;
    try {
      if (wsClient && wsClient.isOpen()) {
        wsClient.interrupt();
      } else {
        await api.controlKernel(getKernelSessionId(notebook.id), 'interrupt');
      }
    } catch (err: any) {
      setKernelToast({ text: `Could not stop execution: ${err.message || 'Unknown error'}`, type: 'error' });
      setTimeout(() => setKernelToast(null), 5000);
    }
    if (recoveryTimerRef.current) clearTimeout(recoveryTimerRef.current);
    recoveryTimerRef.current = setTimeout(() => {
      if (notebookRef.current?.cells.some((c) => c.is_running)) setShowRecoveryPrompt(true);
    }, STOP_RECOVERY_DELAY_MS);
  };
  const handleInterruptRef = useRef(handleInterruptKernel);
  handleInterruptRef.current = handleInterruptKernel;

  // Ctrl+C stops a running notebook, like a terminal, unless there is text selected to copy.
  // Cmd+C on macOS is always copy.
  useEffect(() => {
    const handleCtrlC = (e: KeyboardEvent) => {
      if (!e.ctrlKey || e.metaKey || e.altKey || e.shiftKey) return;
      if (e.key.toLowerCase() !== 'c' && e.code !== 'KeyC') return;
      if (!notebookRef.current?.cells.some((c) => c.is_running)) return;
      const active = document.activeElement as HTMLInputElement | HTMLTextAreaElement | null;
      const fieldSelection =
        !!active && typeof active.selectionStart === 'number' && active.selectionStart !== active.selectionEnd;
      const pageSelection = (window.getSelection()?.toString() ?? '').length > 0;
      if (fieldSelection || pageSelection) return;
      e.preventDefault();
      handleInterruptRef.current();
    };
    window.addEventListener('keydown', handleCtrlC);
    return () => window.removeEventListener('keydown', handleCtrlC);
  }, []);

  // Hide the recovery prompt once nothing is running any more
  useEffect(() => {
    if (showRecoveryPrompt && !notebook?.cells.some((c) => c.is_running)) setShowRecoveryPrompt(false);
  }, [notebook, showRecoveryPrompt]);

  const handleSaveNotebook = async () => {
    if (!notebook) return;
    if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current);
    setIsSaving(true);
    try {
      await api.saveNotebook(notebook);
    } catch (err) {
      console.error('Failed to save notebook:', err);
    } finally {
      setTimeout(() => setIsSaving(false), 500);
    }
  };
  const handleSaveNotebookRef = useRef(handleSaveNotebook);
  handleSaveNotebookRef.current = handleSaveNotebook;

  // App-wide shortcuts: Ctrl/Cmd+S saves the notebook (the file editor panel handles it itself
  // while focused) instead of the browser's "Save page"; Ctrl/Cmd+B shows or hides the Files sidebar
  useEffect(() => {
    const handleAppShortcuts = (e: KeyboardEvent) => {
      if (!(e.ctrlKey || e.metaKey) || e.altKey || e.shiftKey) return;
      const key = e.key.toLowerCase();
      if (key === 's' || e.code === 'KeyS') {
        e.preventDefault();
        const inFileEditor = !!(document.activeElement as HTMLElement | null)?.closest(
          '[data-testid="right-file-editor-panel"]'
        );
        if (!inFileEditor) handleSaveNotebookRef.current();
      } else if (key === 'b' || e.code === 'KeyB') {
        e.preventDefault();
        toggleLeftSidebarRef.current();
      }
    };
    window.addEventListener('keydown', handleAppShortcuts);
    return () => window.removeEventListener('keydown', handleAppShortcuts);
  }, []);

  // Debounced auto-save effect (2.5 seconds)
  useEffect(() => {
    if (!notebook) return;
    if (!isDirtyRef.current) {
      isDirtyRef.current = true;
      return;
    }

    if (autoSaveTimerRef.current) {
      clearTimeout(autoSaveTimerRef.current);
    }
    // While cells run, outputs stream in: save once they finish rather than after every chunk
    if (notebook.cells.some((c) => c.is_running)) return;

    autoSaveTimerRef.current = setTimeout(async () => {
      try {
        setIsSaving(true);
        await api.saveNotebook(notebook);
      } catch (err) {
        console.warn('Auto-save error:', err);
      } finally {
        setTimeout(() => setIsSaving(false), 500);
      }
    }, 2500);

    return () => {
      if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current);
    };
  }, [notebook]);

  const handleAddCell = (index: number, cellType: 'code' | 'markdown') => {
    if (!notebook) return;
    const newCell: NotebookCell = {
      id: `cell-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
      cell_type: cellType,
      source: '',
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
    setOpenFiles([]);
    setActiveFilePath(null);
    setIsRightSidebarOpen(false);
    localStorage.removeItem('pcs_active_notebook_id');
    await startGuestWorkspace();
    await loadOrCreateInitialNotebook();
    window.dispatchEvent(new CustomEvent('pcs-refresh-files'));
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
      setOpenFiles([]);
      setActiveFilePath(null);
      setIsRightSidebarOpen(false);
      localStorage.removeItem('pcs_active_notebook_id');
      // Load user's private notebooks
      await loadOrCreateInitialNotebook();
      window.dispatchEvent(new CustomEvent('pcs-refresh-files'));
    } catch (err: any) {
      setAuthError(err.message || 'Authentication failed');
    }
  };

  const leftDrawerWidth = Math.min(320, viewportWidth - 48);
  const rightPanelWidth = isPhone ? viewportWidth : isCompact ? Math.min(560, viewportWidth - 48) : rightSidebarWidth;

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
        isExecuting={!!notebook?.cells.some((c) => c.is_running)}
        onClearAllOutputs={handleClearAllOutputs}
        onSave={handleSaveNotebook}
        onLogout={handleLogout}
        isLeftSidebarOpen={isLeftSidebarOpen}
        onToggleLeftSidebar={toggleLeftSidebar}
        isRightSidebarOpen={isRightSidebarOpen}
        onToggleRightSidebar={toggleRightSidebar}
        onOpenAuthModal={() => setIsAuthModalOpen(true)}
        onOpenAdminDashboard={() => setIsAdminOpen(true)}
        onOpenNotebooks={() => setIsNotebooksModalOpen(true)}
        onOpenSecrets={() => setIsSecretsModalOpen(true)}
        isRestarting={isRestartingKernel}
      />

      {/* Kernel Toast Notification Banner */}
      {showRecoveryPrompt && (
        <div
          data-testid="kernel-recovery-prompt"
          role="alert"
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '12px',
            flexWrap: 'wrap',
            padding: '8px 16px',
            backgroundColor: 'rgba(245, 158, 11, 0.15)',
            borderBottom: '1px solid #f59e0b',
            color: 'var(--text-main)',
            fontSize: '12.5px',
            zIndex: 40,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertCircle size={14} color="#f59e0b" />
            <span>
              <strong>Python is not responding to Stop</strong> (it may be blocked inside native code). Restarting the
              kernel stops it, but clears all variables and imports.
            </span>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              data-testid="recovery-restart-btn"
              onClick={handleRestartKernel}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                backgroundColor: '#f59e0b',
                color: '#1f2937',
                border: 'none',
                padding: '5px 11px',
                borderRadius: '6px',
                fontSize: '12px',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              <RotateCcw size={13} /> Restart kernel
            </button>
            <button
              onClick={() => setShowRecoveryPrompt(false)}
              style={{
                backgroundColor: 'var(--btn-secondary-bg)',
                color: 'var(--btn-secondary-text)',
                border: '1px solid var(--btn-secondary-border)',
                padding: '5px 11px',
                borderRadius: '6px',
                fontSize: '12px',
                cursor: 'pointer',
              }}
            >
              Keep waiting
            </button>
          </div>
        </div>
      )}

      {kernelToast && (
        <div
          data-testid="kernel-toast-banner"
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '7px 16px',
            backgroundColor:
              kernelToast.type === 'error'
                ? 'rgba(239, 68, 68, 0.15)'
                : kernelToast.type === 'success'
                ? 'rgba(16, 185, 129, 0.15)'
                : 'rgba(59, 130, 246, 0.15)',
            borderBottom: `1px solid ${
              kernelToast.type === 'error'
                ? '#ef4444'
                : kernelToast.type === 'success'
                ? '#10b981'
                : '#3b82f6'
            }`,
            color: 'var(--text-main)',
            fontSize: '12.5px',
            zIndex: 40,
            transition: 'all 0.2s ease',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {kernelToast.type === 'info' && (
              <RotateCcw size={14} color="#3b82f6" className="animate-spin" />
            )}
            {kernelToast.type === 'success' && <CheckCircle size={14} color="#10b981" />}
            {kernelToast.type === 'error' && <AlertCircle size={14} color="#ef4444" />}
            <span style={{ fontWeight: 500 }}>{kernelToast.text}</span>
          </div>
          <button
            onClick={() => setKernelToast(null)}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
              padding: '2px',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* Guest Mode notice: private workspace kept in this browser */}
      {!user && showGuestBanner && (
        <div
          data-testid="guest-privacy-banner"
          className="guest-banner"
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
              <strong style={{ color: 'var(--border-accent)' }}>Guest Mode — Private Workspace:</strong>
              <span className="guest-banner-detail">
                {guestStorageAvailable
                  ? ' Your files and notebooks are private and saved in this browser. Sign in to use them on other devices.'
                  : ' Your files and notebooks are private. This browser cannot keep a copy (private window or storage blocked), so unused guest work is removed from the server after 14 days.'}
              </span>
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
              Sign in<span className="guest-banner-detail"> for your private workspace</span>
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
      {/* Panels inside take height: 100% of this row, which already excludes the navbar and any
          banners above it; minHeight: 0 lets the row shrink below its content in the column */}
      <div
        data-testid="workspace-row"
        data-layout={isPhone ? 'phone' : isCompact ? 'tablet' : 'desktop'}
        style={{ flex: 1, minHeight: 0, display: 'flex', overflow: 'hidden', position: 'relative', zIndex: 1, isolation: 'isolate' }}
      >
        {/* Drawer backdrop. It lives in the same stacking context as the drawers (this row isolates
            its children), so it sits between the notebook and the drawer instead of above both. */}
        {isCompact && (isLeftSidebarOpen || (isRightSidebarOpen && !isPhone)) && (
          <div
            data-testid={isLeftSidebarOpen ? 'mobile-left-backdrop' : 'mobile-right-backdrop'}
            className="pcs-drawer-backdrop"
            onClick={() => (isLeftSidebarOpen ? setIsLeftSidebarOpen(false) : setIsRightSidebarOpen(false))}
            style={{ zIndex: isLeftSidebarOpen ? 47 : 43 }}
          />
        )}

        {/* Left Sidebar (Files): docked on desktop, an overlay drawer on smaller screens */}
        {isLeftSidebarOpen && (
          <div
            data-testid={isCompact ? 'left-drawer' : undefined}
            className={isCompact ? 'pcs-drawer pcs-drawer--left' : undefined}
            style={isCompact ? { width: `${leftDrawerWidth}px` } : { height: '100%' }}
          >
            <Sidebar
              key={user ? `user-${user.id}` : 'guest-public'}
              user={user}
              onOpenFile={handleOpenFile}
              onOpenNotebookFile={handleOpenNotebookFile}
              onCreateNewNotebook={handleCreateNewNotebook}
              activeFilePath={activeFilePath || undefined}
              width={isCompact ? leftDrawerWidth : leftSidebarWidth}
            />
          </div>
        )}

        {/* Left Resizer Divider (Hidden on Mobile) */}
        {!isCompact && isLeftSidebarOpen && (
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
              onRunCellsAbove={handleRunCellsAbove}
              onRunCellsBelow={handleRunCellsBelow}
              onChangeCellType={handleChangeCellType}
              activeCellId={activeCellId}
              onSelectCell={setActiveCellId}
              sessionId={notebook ? getKernelSessionId(notebook.id) : undefined}
              onUpdateCellMetadata={handleUpdateCellMetadata}
              onInterrupt={handleInterruptKernel}
              pendingInput={pendingInput}
              onSubmitInput={handleSubmitInput}
            />
          </div>
        )}

        {/* Right Resizer Divider (Hidden on Mobile) */}
        {!isCompact && isRightSidebarOpen && (
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
            data-testid={isCompact ? 'right-drawer' : undefined}
            className={isPhone ? 'pcs-drawer pcs-drawer--full' : isCompact ? 'pcs-drawer pcs-drawer--right' : undefined}
            style={isCompact ? { width: isPhone ? undefined : `${rightPanelWidth}px` } : {
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
                width={rightPanelWidth}
                layout={isPhone ? 'fullscreen' : isCompact ? 'drawer' : 'docked'}
              />
            ) : (
              <RightPanel
                onInsertCodeSnippet={handleInsertCodeSnippet}
                width={rightPanelWidth}
              />
            )}
          </div>
        )}
      </div>

      {/* Non-intrusive Authentication Modal Dialog */}
      {isAuthModalOpen && (
        <Modal
          onClose={() => setIsAuthModalOpen(false)}
          label={isRegisterMode ? 'Create private workspace' : 'Sign in to workspace'}
          size="sm"
          testId="auth-modal"
        >
          <ModalHeader
            icon={<Lock size={16} />}
            iconBackground="var(--accent-strong)"
            title={isRegisterMode ? 'Create Private Workspace' : 'Sign In to Workspace'}
            subtitle={
              isRegisterMode
                ? 'Get your dedicated, completely private environment with isolated files.'
                : 'Access your private workspace and secure notebooks.'
            }
            onClose={() => setIsAuthModalOpen(false)}
          />
          <ModalBody>
            {authError && (
              <div
                role="alert"
                style={{
                  padding: '8px 12px',
                  backgroundColor: 'var(--status-danger-bg)',
                  border: '1px solid var(--status-danger-border)',
                  borderRadius: '6px',
                  color: 'var(--status-danger-text)',
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
                  <label htmlFor="auth-name" style={{ fontSize: '12px', color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>
                    Full Name
                  </label>
                  <input
                    id="auth-name"
                    type="text"
                    required
                    className="pcs-input"
                    value={authName}
                    onChange={(e) => setAuthName(e.target.value)}
                    placeholder="e.g. Alex Johnson"
                  />
                </div>
              )}
              <div>
                <label htmlFor="auth-email" style={{ fontSize: '12px', color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>
                  Email Address
                </label>
                <input
                  id="auth-email"
                  type="email"
                  required
                  autoFocus
                  className="pcs-input"
                  value={authEmail}
                  onChange={(e) => setAuthEmail(e.target.value)}
                  placeholder="user@example.com"
                />
              </div>
              <div>
                <label htmlFor="auth-password" style={{ fontSize: '12px', color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>
                  Password
                </label>
                <input
                  id="auth-password"
                  type="password"
                  required
                  className="pcs-input"
                  value={authPassword}
                  onChange={(e) => setAuthPassword(e.target.value)}
                  placeholder="••••••••"
                />
              </div>

              <button type="submit" className="pcs-btn pcs-btn--primary" style={{ marginTop: '8px', minHeight: '38px', fontSize: '13px' }}>
                <LogIn size={15} />
                {isRegisterMode ? 'Create Account & Switch' : 'Sign In'}
              </button>
            </form>

            <div style={{ marginTop: '16px', textAlign: 'center', fontSize: '12px', color: 'var(--text-secondary)' }}>
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
                    style={{ color: 'var(--accent)', textDecoration: 'none', fontWeight: 600 }}
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
                    style={{ color: 'var(--accent)', textDecoration: 'none', fontWeight: 600 }}
                  >
                    Create Account
                  </a>
                </span>
              )}
            </div>
          </ModalBody>
        </Modal>
      )}

      {/* Super Admin Dashboard Modal */}
      <ErrorBoundary fallbackTitle="Admin Console Encountered an Issue" onClose={() => setIsAdminOpen(false)}>
        <AdminDashboard
          isOpen={isAdminOpen}
          onClose={() => setIsAdminOpen(false)}
          currentUserEmail={user?.email}
        />
      </ErrorBoundary>

      {/* Persistent Notebooks Manager Modal */}
      <NotebooksModal
        isOpen={isNotebooksModalOpen}
        onClose={() => setIsNotebooksModalOpen(false)}
        currentNotebookId={notebook?.id}
        onSelectNotebook={handleSelectNotebook}
        onCreateNewNotebook={handleCreateNewNotebook}
        currentNotebookDoc={notebook}
      />

      {/* Secure Environment Variables & AI Secrets Modal */}
      <SecretsModal
        isOpen={isSecretsModalOpen}
        onClose={() => setIsSecretsModalOpen(false)}
      />
    </div>
  );
};
