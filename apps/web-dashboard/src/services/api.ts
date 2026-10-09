import { NotebookDocument, UserProfile, FileItem } from '../types';

const API_BASE = '/api/v1';

export class ApiClient {
  private token: string | null = null;

  constructor() {
    this.token = localStorage.getItem('pcs_token');
  }

  setToken(token: string) {
    this.token = token;
    localStorage.setItem('pcs_token', token);
  }

  getToken(): string | null {
    return this.token;
  }

  clearToken() {
    this.token = null;
    localStorage.removeItem('pcs_token');
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const res = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(errorData.detail || `Request failed with status ${res.status}`);
    }

    if (res.status === 204) {
      return {} as T;
    }

    return res.json();
  }

  // Auth
  async login(email: string, password: string) {
    const data = await this.request<{ access_token: string; role: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    this.setToken(data.access_token);
    return data;
  }

  async register(email: string, password: string, fullName: string, role = 'student') {
    const data = await this.request<{ access_token: string; role: string }>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, full_name: fullName, role }),
    });
    this.setToken(data.access_token);
    return data;
  }

  async getMe(): Promise<UserProfile> {
    return this.request<UserProfile>('/auth/me');
  }

  // Notebooks
  async createNotebook(title: string, kernelName = 'python3'): Promise<NotebookDocument> {
    const res = await this.request<any>('/notebooks', {
      method: 'POST',
      body: JSON.stringify({ title, kernel_name: kernelName }),
    });
    return {
      id: res.id,
      title: res.title,
      kernel_name: res.kernel_name,
      cells: (res.content?.cells || []).map((c: any, idx: number) => ({
        id: `cell-${idx}-${Date.now()}`,
        cell_type: c.cell_type || 'code',
        source: Array.isArray(c.source) ? c.source.join('') : c.source || '',
        outputs: c.outputs || [],
        execution_count: c.execution_count ?? null,
      })),
      updated_at: res.updated_at,
    };
  }

  async listNotebooks(): Promise<Array<{ id: string; title: string; updated_at: string }>> {
    return this.request<any[]>('/notebooks');
  }

  async getNotebook(notebookId: string): Promise<NotebookDocument> {
    const res = await this.request<any>(`/notebooks/${notebookId}`);
    return {
      id: res.id,
      title: res.title,
      kernel_name: res.kernel_name,
      cells: (res.content?.cells || []).map((c: any, idx: number) => ({
        id: `cell-${idx}-${Date.now()}`,
        cell_type: c.cell_type || 'code',
        source: Array.isArray(c.source) ? c.source.join('') : c.source || '',
        outputs: c.outputs || [],
        execution_count: c.execution_count ?? null,
      })),
      updated_at: res.updated_at,
    };
  }

  async saveNotebook(notebook: NotebookDocument): Promise<void> {
    const content = {
      nbformat: 4,
      nbformat_minor: 5,
      metadata: {
        kernelspec: {
          display_name: 'Python 3',
          language: 'python',
          name: notebook.kernel_name,
        },
      },
      cells: notebook.cells.map(c => ({
        cell_type: c.cell_type,
        metadata: {},
        source: c.source,
        outputs: c.outputs,
        execution_count: c.execution_count,
      })),
    };

    await this.request(`/notebooks/${notebook.id}`, {
      method: 'PUT',
      body: JSON.stringify({
        title: notebook.title,
        content,
      }),
    });
  }

  async deleteNotebook(notebookId: string): Promise<void> {
    await this.request(`/notebooks/${notebookId}`, {
      method: 'DELETE',
    });
  }

  // Files
  async listFiles(directory = ''): Promise<FileItem[]> {
    return this.request<FileItem[]>(`/files?directory=${encodeURIComponent(directory)}`);
  }

  async readFile(path: string): Promise<{ path: string; content: string }> {
    return this.request<{ path: string; content: string }>(`/files/read?path=${encodeURIComponent(path)}`);
  }

  async writeFile(path: string, content: string): Promise<{ status: string; path: string }> {
    return this.request<{ status: string; path: string }>('/files/write', {
      method: 'POST',
      body: JSON.stringify({ path, content }),
    });
  }

  async createFolder(path: string): Promise<{ status: string; path: string }> {
    return this.request<{ status: string; path: string }>('/files/folder', {
      method: 'POST',
      body: JSON.stringify({ path }),
    });
  }

  async renameFile(oldPath: string, newPath: string): Promise<{ status: string; old_path: string; new_path: string }> {
    return this.request<{ status: string; old_path: string; new_path: string }>('/files/rename', {
      method: 'POST',
      body: JSON.stringify({ old_path: oldPath, new_path: newPath }),
    });
  }

  async deleteFile(path: string): Promise<{ status: string; deleted: string }> {
    return this.request<{ status: string; deleted: string }>(`/files?path=${encodeURIComponent(path)}`, {
      method: 'DELETE',
    });
  }

  async uploadFile(file: File, directory = ''): Promise<{ status: string; filename: string; size: number }> {
    const formData = new FormData();
    formData.append('file', file);

    const headers: Record<string, string> = {};
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const res = await fetch(`/api/v1/files/upload?directory=${encodeURIComponent(directory)}`, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(err.detail || 'Upload failed');
    }
    return res.json();
  }

  getDownloadUrl(path: string): string {
    const tokenParam = this.token ? `&token=${encodeURIComponent(this.token)}` : '';
    return `/api/v1/files/download?path=${encodeURIComponent(path)}${tokenParam}`;
  }

  // Execution REST fallback
  async runCode(sessionId: string, code: string) {
    return this.request<any>('/execution/run', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId, code }),
    });
  }

  async controlKernel(sessionId: string, action: 'restart' | 'interrupt' | 'shutdown') {
    return this.request<any>('/execution/control', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId, action }),
    });
  }
}

export const api = new ApiClient();

