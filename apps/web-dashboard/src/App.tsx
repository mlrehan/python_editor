import React, { useState, useEffect, useRef } from 'react';
import { Navbar } from './components/Navbar';
import { Sidebar } from './components/Sidebar';
import { NotebookEditor } from './components/NotebookEditor';
import { RightPanel } from './components/RightPanel';
import { NotebookDocument, NotebookCell, KernelStatus, UserProfile } from './types';
import { api } from './services/api';
import { KernelWebSocketClient } from './services/websocket';

export const App: React.FC = () => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [authEmail, setAuthEmail] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [authName, setAuthName] = useState('');
  const [isRegisterMode, setIsRegisterMode] = useState(false);
  const [authError, setAuthError] = useState('');

  const [notebook, setNotebook] = useState<NotebookDocument | null>(null);
  const [activeCellId, setActiveCellId] = useState<string | null>(null);
  const [kernelStatus, setKernelStatus] = useState<KernelStatus>('disconnected');
  const [isSaving, setIsSaving] = useState(false);

  const wsClientRef = useRef<KernelWebSocketClient | null>(null);

  // Initialize or check auth on mount
  useEffect(() => {
    const initAuth = async () => {
      const token = api.getToken();
      if (token) {
        try {
          const profile = await api.getMe();
          setUser(profile);
          loadOrCreateInitialNotebook();
          return;
        } catch {
          api.clearToken();
        }
      }
      // Auto-register developer session for immediate out-of-the-box usage
      try {
        const devEmail = `developer_${Date.now()}@cloudstudio.internal`;
        await api.register(devEmail, 'DevPassword123!', 'Lead Developer', 'instructor');
        const profile = await api.getMe();
        setUser(profile);
        loadOrCreateInitialNotebook();
      } catch (e) {
        console.warn('Auto registration failed, manual login required:', e);
      }
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

  // Connect WebSocket when notebook & user are ready
  useEffect(() => {
    if (!notebook || !user) return;

    const token = api.getToken();
    if (!token) return;

    const sessionId = `session-${notebook.id}`;
    const wsClient = new KernelWebSocketClient(
      sessionId,
      token,
      // onOutput
      (cellId, output) => {
        setNotebook(prev => {
          if (!prev) return prev;
          return {
            ...prev,
            cells: prev.cells.map(c => {
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
        setNotebook(prev => {
          if (!prev) return prev;
          return {
            ...prev,
            cells: prev.cells.map(c => {
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

  const handleUpdateTitle = (newTitle: string) => {
    if (!notebook) return;
    setNotebook({ ...notebook, title: newTitle });
  };

  const handleUpdateCellSource = (cellId: string, newSource: string) => {
    if (!notebook) return;
    setNotebook({
      ...notebook,
      cells: notebook.cells.map(c => (c.id === cellId ? { ...c, source: newSource } : c)),
    });
  };

  const handleRunCell = (cellId: string) => {
    if (!notebook || !wsClientRef.current) return;
    const targetCell = notebook.cells.find(c => c.id === cellId);
    if (!targetCell || targetCell.cell_type !== 'code') return;

    // Reset cell output and mark running
    setNotebook(prev => {
      if (!prev) return prev;
      return {
        ...prev,
        cells: prev.cells.map(c => (c.id === cellId ? { ...c, outputs: [], is_running: true } : c)),
      };
    });

    try {
      wsClientRef.current.execute(cellId, targetCell.source);
    } catch {
      // Fallback to REST execution if websocket disconnected
      api.runCode(`session-${notebook.id}`, targetCell.source).then((res) => {
        setNotebook(prev => {
          if (!prev) return prev;
          return {
            ...prev,
            cells: prev.cells.map(c =>
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
      });
    }
  };

  const handleRunAll = () => {
    if (!notebook) return;
    const codeCells = notebook.cells.filter(c => c.cell_type === 'code');
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

  const handleSave = async () => {
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
    const updated = notebook.cells.filter(c => c.id !== cellId);
    setNotebook({ ...notebook, cells: updated });
  };

  const handleMoveCell = (cellId: string, direction: 'up' | 'down') => {
    if (!notebook) return;
    const idx = notebook.cells.findIndex(c => c.id === cellId);
    if (idx < 0) return;
    if (direction === 'up' && idx === 0) return;
    if (direction === 'down' && idx === notebook.cells.length - 1) return;

    const targetIdx = direction === 'up' ? idx - 1 : idx + 1;
    const updated = [...notebook.cells];
    const [moved] = updated.splice(idx, 1);
    updated.splice(targetIdx, 0, moved);
    setNotebook({ ...notebook, cells: updated });
  };

  const handleInsertCodeSnippet = (code: string) => {
    if (!notebook) return;
    handleAddCell(notebook.cells.length, 'code');
    setTimeout(() => {
      setNotebook(prev => {
        if (!prev) return prev;
        const last = prev.cells[prev.cells.length - 1];
        return {
          ...prev,
          cells: prev.cells.map(c => (c.id === last.id ? { ...c, source: code } : c)),
        };
      });
    }, 50);
  };

  const handleLogout = () => {
    api.clearToken();
    setUser(null);
    setNotebook(null);
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
      loadOrCreateInitialNotebook();
    } catch (err: any) {
      setAuthError(err.message || 'Authentication failed');
    }
  };

  if (!user) {
    return (
      <div style={{
        height: '100vh',
        width: '100vw',
        backgroundColor: '#090d16',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}>
        <div style={{
          width: '380px',
          padding: '32px',
          backgroundColor: '#0f172a',
          borderRadius: '12px',
          border: '1px solid #1e293b',
          boxShadow: '0 20px 40px rgba(0,0,0,0.5)'
        }}>
          <h2 style={{ fontSize: '20px', fontWeight: 700, color: '#f8fafc', marginBottom: '8px' }}>
            Enterprise Python Cloud Studio
          </h2>
          <p style={{ fontSize: '13px', color: '#94a3b8', marginBottom: '24px' }}>
            {isRegisterMode ? 'Create your platform account' : 'Sign in to access your workspaces'}
          </p>

          {authError && (
            <div style={{ padding: '8px 12px', backgroundColor: '#450a0a', border: '1px solid #ef4444', borderRadius: '6px', color: '#fca5a5', fontSize: '12px', marginBottom: '16px' }}>
              {authError}
            </div>
          )}

          <form onSubmit={handleAuthSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {isRegisterMode && (
              <div>
                <label style={{ fontSize: '12px', color: '#cbd5e1', display: 'block', marginBottom: '4px' }}>Full Name</label>
                <input
                  type="text"
                  required
                  value={authName}
                  onChange={(e) => setAuthName(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '6px', color: '#ffffff', outline: 'none' }}
                />
              </div>
            )}
            <div>
              <label style={{ fontSize: '12px', color: '#cbd5e1', display: 'block', marginBottom: '4px' }}>Email Address</label>
              <input
                type="email"
                required
                value={authEmail}
                onChange={(e) => setAuthEmail(e.target.value)}
                style={{ width: '100%', padding: '8px 12px', backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '6px', color: '#ffffff', outline: 'none' }}
              />
            </div>
            <div>
              <label style={{ fontSize: '12px', color: '#cbd5e1', display: 'block', marginBottom: '4px' }}>Password</label>
              <input
                type="password"
                required
                value={authPassword}
                onChange={(e) => setAuthPassword(e.target.value)}
                style={{ width: '100%', padding: '8px 12px', backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '6px', color: '#ffffff', outline: 'none' }}
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
                cursor: 'pointer'
              }}
            >
              {isRegisterMode ? 'Register Account' : 'Sign In'}
            </button>
          </form>

          <div style={{ marginTop: '16px', textAlign: 'center', fontSize: '12px', color: '#94a3b8' }}>
            {isRegisterMode ? (
              <span>Already have an account? <a href="#" onClick={() => setIsRegisterMode(false)} style={{ color: '#3b82f6', textDecoration: 'none' }}>Sign In</a></span>
            ) : (
              <span>New to Cloud Studio? <a href="#" onClick={() => setIsRegisterMode(true)} style={{ color: '#3b82f6', textDecoration: 'none' }}>Create Account</a></span>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ height: '100vh', width: '100vw', display: 'flex', flexDirection: 'column' }}>
      <Navbar
        title={notebook?.title || 'Untitled Notebook'}
        onTitleChange={handleUpdateTitle}
        kernelStatus={kernelStatus}
        isSaving={isSaving}
        user={user}
        onRunAll={handleRunAll}
        onRestartKernel={handleRestartKernel}
        onInterruptKernel={handleInterruptKernel}
        onSave={handleSave}
        onLogout={handleLogout}
      />

      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        <Sidebar
          currentNotebookId={notebook?.id || ''}
          onSelectNotebook={async (id) => {
            const loaded = await api.getNotebook(id);
            setNotebook(loaded);
            if (loaded.cells.length > 0) setActiveCellId(loaded.cells[0].id);
          }}
          onCreateNotebook={async () => {
            const created = await api.createNotebook('New Notebook');
            setNotebook(created);
            if (created.cells.length > 0) setActiveCellId(created.cells[0].id);
          }}
        />

        {notebook && (
          <NotebookEditor
            cells={notebook.cells}
            onUpdateCellSource={handleUpdateCellSource}
            onRunCell={handleRunCell}
            onAddCell={handleAddCell}
            onDeleteCell={handleDeleteCell}
            onMoveCell={handleMoveCell}
            activeCellId={activeCellId}
            onSelectCell={setActiveCellId}
          />
        )}

        <RightPanel onInsertCodeSnippet={handleInsertCodeSnippet} />
      </div>
    </div>
  );
};

