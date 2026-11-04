import { NotebookDocument, UserProfile, FileItem } from '../types';
import { guestStore } from './guestStore';

const API_BASE = '/api/v1';
// Guest tokens are issued and signed by the server: gst_<random>.<signature>
const SIGNED_GUEST_TOKEN = /^gst_[A-Za-z0-9_-]+\.[0-9a-f]{32}$/;
// Files up to this size are copied into the browser's guest workspace store
const MIRROR_MAX_BYTES = 1024 * 1024;
// How many folder levels below the listed one the browser copy follows
const MIRROR_MAX_DEPTH = 3;

export class ApiClient {
  private token: string | null = null;
  private guestToken: string | null = null;
  private guestSessionPromise: Promise<void> | null = null;
  private mirroring = false;

  constructor() {
    this.token = localStorage.getItem('pcs_token');
    // Tokens the browser made up itself (older versions) are not accepted any more
    const gst = localStorage.getItem('pcs_guest_token');
    this.guestToken = gst && SIGNED_GUEST_TOKEN.test(gst) ? gst : null;
  }

  isGuest(): boolean {
    return !this.token;
  }

  /** Makes sure this browser has a server-issued guest token (one request, however many callers). */
  async ensureGuestSession(): Promise<void> {
    if (this.token || this.guestToken) return;
    if (!this.guestSessionPromise) {
      this.guestSessionPromise = (async () => {
        const res = await fetch(`${API_BASE}/auth/guest-session`, { method: 'POST' });
        if (!res.ok) throw new Error('Could not start a guest session. Please reload the page.');
        const data = await res.json();
        this.guestToken = data.guest_token;
        localStorage.setItem('pcs_guest_token', data.guest_token);
      })().finally(() => {
        this.guestSessionPromise = null;
      });
    }
    return this.guestSessionPromise;
  }

  setToken(token: string) {
    this.token = token;
    localStorage.setItem('pcs_token', token);
  }

  getToken(): string | null {
    return this.token;
  }

  getGuestToken(): string {
    return this.guestToken || '';
  }

  clearToken() {
    this.token = null;
    localStorage.removeItem('pcs_token');
  }

  private async request<T>(endpoint: string, options: RequestInit = {}, retried = false): Promise<T> {
    if (!this.token && !endpoint.startsWith('/auth/')) await this.ensureGuestSession();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    } else if (this.guestToken) {
      headers['X-Guest-Token'] = this.guestToken;
    }

    let res: Response;
    try {
      res = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers,
      });
    } catch (err: any) {
      if (err?.name === 'AbortError') throw err;
      throw new Error('Network error: the server could not be reached. Check your connection and try again.');
    }

    if (!res.ok) {
      // Proxies (nginx, Cloudflare) answer with HTML error pages, and HTTP/2 has no statusText
      const errorData = await res.json().catch(() => ({ detail: '' }));
      // The guest token is no longer valid (e.g. the server's key changed): get a new one, retry once
      if (res.status === 401 && !this.token && !retried && errorData.detail === 'guest_session_required') {
        this.guestToken = null;
        localStorage.removeItem('pcs_guest_token');
        await this.ensureGuestSession();
        return this.request<T>(endpoint, options, true);
      }
      let msg = 'Request failed';
      if (typeof errorData.detail === 'string' && !errorData.detail) {
        msg =
          res.status === 502 || res.status === 503 || res.status === 504 || res.status >= 520
            ? `Server unavailable (HTTP ${res.status}). The execution service may be restarting or overloaded; please retry shortly.`
            : `Request failed with status ${res.status}${res.statusText ? ` ${res.statusText}` : ''}`;
      } else if (typeof errorData.detail === 'string') {
        msg = errorData.detail;
      } else if (Array.isArray(errorData.detail)) {
        msg = errorData.detail.map((e: any) => e.msg || JSON.stringify(e)).join(', ');
      } else if (errorData.detail) {
        msg = JSON.stringify(errorData.detail);
      } else {
        msg = `Request failed with status ${res.status}`;
      }
      throw new Error(msg);
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

  /** Starts (or resumes) this browser's private guest workspace. Keeps an existing valid token. */
  async initGuestSession(): Promise<{ guest_token: string; workspace_type: string }> {
    await this.ensureGuestSession();
    return { guest_token: this.getGuestToken(), workspace_type: 'private' };
  }

  // --- Guest workspace: browser copy (IndexedDB) ---------------------------------------------------

  /** After a guest change on the server, keep the browser copy in step (best effort). */
  private async mirror(fn: () => Promise<void>): Promise<void> {
    if (!this.isGuest()) return;
    try {
      await fn();
    } catch {
      /* the server copy stays authoritative; the browser copy is a convenience */
    }
  }

  /**
   * Restores the browser copy into a guest workspace the server has just (re)created, e.g. after it
   * removed a long-unused workspace. Returns how many items were restored.
   */
  async restoreGuestWorkspace(): Promise<number> {
    if (!this.isGuest()) return 0;
    const info = await this.request<{ kind: string; restore_pending: boolean }>('/files/workspace-info');
    if (info.kind !== 'guest' || !info.restore_pending) return 0;
    const { entries, notebooks } = await guestStore.snapshot();
    let restored = 0;
    const depth = (p: string) => p.split('/').length;
    for (const folder of entries.filter((e) => e.kind === 'folder').sort((a, b) => depth(a.path) - depth(b.path))) {
      try {
        await this.request('/files/folder', { method: 'POST', body: JSON.stringify({ path: folder.path }) });
        restored++;
      } catch { /* keep going */ }
    }
    for (const file of entries.filter((e) => e.kind === 'file')) {
      try {
        if (typeof file.content === 'string') {
          await this.request('/files/write', { method: 'POST', body: JSON.stringify({ path: file.path, content: file.content }) });
        } else if (file.content instanceof Blob) {
          const slash = file.path.lastIndexOf('/');
          const name = file.path.slice(slash + 1);
          await this.uploadFile(new File([file.content], name), slash >= 0 ? file.path.slice(0, slash) : '');
        }
        restored++;
      } catch { /* keep going */ }
    }
    for (const nb of notebooks) {
      try {
        await this.request(`/notebooks/${encodeURIComponent(nb.id)}`, { method: 'PUT', body: JSON.stringify({ title: nb.title, content: nb.content }) });
        restored++;
      } catch { /* keep going */ }
    }
    await this.request('/files/workspace-info/restored', { method: 'POST' });
    return restored;
  }

  /** Copies files that changed on the server (e.g. written by Python code) into the browser copy. */
  private async mirrorListing(items: FileItem[], depth: number): Promise<void> {
    for (const item of items) {
      if (item.name.startsWith('.')) continue;
      if (item.is_dir) {
        await guestStore.putFolder(item.path);
        // Subfolders too (files Python code wrote there), a few levels deep
        if (depth < MIRROR_MAX_DEPTH) {
          const children = await this.request<FileItem[]>(`/files?directory=${encodeURIComponent(item.path)}`).catch(() => []);
          await this.mirrorListing(children, depth + 1);
        }
        continue;
      }
      if (item.size > MIRROR_MAX_BYTES) continue;
      const held = await guestStore.getEntry(item.path);
      if (held && (held.modifiedAt ?? 0) >= item.modified_at) continue;
      const res = await fetch(this.getDownloadUrl(item.path));
      if (!res.ok) continue;
      await guestStore.putFile(item.path, await res.blob(), item.modified_at);
    }
  }

  // Notebooks
  async createNotebook(title: string, kernelName = 'python3'): Promise<NotebookDocument> {
    const res = await this.request<any>('/notebooks', {
      method: 'POST',
      body: JSON.stringify({ title, kernel_name: kernelName }),
    });
    await this.mirror(() => guestStore.putNotebook({ id: res.id, title: res.title, kernel_name: res.kernel_name, content: res.content }));
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
    await this.mirror(() => guestStore.putNotebook({ id: notebook.id, title: notebook.title, kernel_name: notebook.kernel_name, content }));
  }

  async deleteNotebook(notebookId: string): Promise<void> {
    await this.request(`/notebooks/${notebookId}`, {
      method: 'DELETE',
    });
    await this.mirror(() => guestStore.deleteNotebook(notebookId));
  }

  // Files
  async listFiles(directory = ''): Promise<FileItem[]> {
    const items = await this.request<FileItem[]>(`/files?directory=${encodeURIComponent(directory)}`);
    if (this.isGuest() && !this.mirroring) {
      // One walk at a time: the explorer refreshes often
      this.mirroring = true;
      void this.mirror(() => this.mirrorListing(items, 0)).finally(() => { this.mirroring = false; });
    }
    return items;
  }

  async readFile(path: string): Promise<{ path: string; content: string }> {
    return this.request<{ path: string; content: string }>(`/files/read?path=${encodeURIComponent(path)}`);
  }

  async writeFile(path: string, content: string): Promise<{ status: string; path: string }> {
    const res = await this.request<{ status: string; path: string }>('/files/write', {
      method: 'POST',
      body: JSON.stringify({ path, content }),
    });
    await this.mirror(() => guestStore.putFile(path, content));
    return res;
  }

  async createFolder(path: string): Promise<{ status: string; path: string }> {
    const res = await this.request<{ status: string; path: string }>('/files/folder', {
      method: 'POST',
      body: JSON.stringify({ path }),
    });
    await this.mirror(() => guestStore.putFolder(path));
    return res;
  }

  async renameFile(oldPath: string, newPath: string): Promise<{ status: string; old_path: string; new_path: string }> {
    const res = await this.request<{ status: string; old_path: string; new_path: string }>('/files/rename', {
      method: 'POST',
      body: JSON.stringify({ old_path: oldPath, new_path: newPath }),
    });
    await this.mirror(() => guestStore.renamePath(oldPath, newPath));
    return res;
  }

  async deleteFile(path: string): Promise<{ status: string; deleted: string }> {
    const res = await this.request<{ status: string; deleted: string }>(`/files?path=${encodeURIComponent(path)}`, {
      method: 'DELETE',
    });
    await this.mirror(() => guestStore.deletePath(path));
    return res;
  }

  async uploadFile(file: File, directory = ''): Promise<{ status: string; filename: string; size: number }> {
    const formData = new FormData();
    formData.append('file', file);

    if (!this.token) await this.ensureGuestSession();
    const headers: Record<string, string> = {};
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    } else if (this.guestToken) {
      headers['X-Guest-Token'] = this.guestToken;
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
    const data = await res.json();
    await this.mirror(() => guestStore.putFile(directory ? `${directory}/${file.name}` : file.name, file));
    return data;
  }

  getDownloadUrl(path: string): string {
    const tokenParam = this.token
      ? `&token=${encodeURIComponent(this.token)}`
      : `&x_guest_token=${encodeURIComponent(this.getGuestToken())}`;
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

  // Theme Preference
  async updateThemePreference(theme: string): Promise<{ status: string; theme_preference: string }> {
    return this.request('/auth/theme', {
      method: 'PUT',
      body: JSON.stringify({ theme_preference: theme }),
    });
  }

  // Admin APIs
  async getAdminStats() {
    return this.request<any>('/admin/stats');
  }

  async getAdminUsers(page = 1, limit = 50, search = '') {
    const q = new URLSearchParams({ page: String(page), limit: String(limit), search });
    return this.request<any>(`/admin/users?${q.toString()}`);
  }

  async createAdminUser(data: any) {
    return this.request<any>('/admin/users', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateAdminUser(userId: string, data: any) {
    return this.request<any>(`/admin/users/${userId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async resetUserPassword(userId: string, newPassword: string) {
    return this.request<any>(`/admin/users/${userId}/reset-password`, {
      method: 'POST',
      body: JSON.stringify({ new_password: newPassword }),
    });
  }

  async deleteUser(userId: string) {
    return this.request<any>(`/admin/users/${userId}`, {
      method: 'DELETE',
    });
  }

  async getAdminPackages(search = '') {
    const q = search ? `?search=${encodeURIComponent(search)}` : '';
    return this.request<any>(`/admin/packages${q}`);
  }

  async installPackage(packageName: string) {
    return this.request<any>('/admin/packages/install', {
      method: 'POST',
      body: JSON.stringify({ package_name: packageName }),
    });
  }

  async uninstallPackage(packageName: string) {
    return this.request<any>('/admin/packages/uninstall', {
      method: 'POST',
      body: JSON.stringify({ package_name: packageName }),
    });
  }

  async getAdminRuntimes() {
    return this.request<any>('/admin/runtimes');
  }

  async clearRuntimes(sessionId?: string, clearAll = false) {
    return this.request<any>('/admin/runtimes/clear', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId, clear_all: clearAll }),
    });
  }

  async getAdminWorkspaces() {
    return this.request<any>('/admin/workspaces');
  }

  async deleteWorkspaceFile(targetPath: string) {
    return this.request<any>('/admin/workspaces/delete-file', {
      method: 'POST',
      body: JSON.stringify({ target_path: targetPath }),
    });
  }

  async getAdminAuditLogs(limit = 100) {
    return this.request<any>(`/admin/audit-logs?limit=${limit}`);
  }

  async updateAdminProfile(data: any) {
    return this.request<any>('/admin/profile', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  // Workspace Environment & Secrets (.env)
  async getWorkspaceEnv(): Promise<{ env: Record<string, string>; has_env_file: boolean }> {
    return this.request<{ env: Record<string, string>; has_env_file: boolean }>('/files/env');
  }

  async saveWorkspaceEnv(env: Record<string, string>): Promise<{ status: string; keys: string[] }> {
    return this.request<{ status: string; keys: string[] }>('/files/env', {
      method: 'PUT',
      body: JSON.stringify({ env }),
    });
  }

  // Admin Notebooks & Workspace Inspections
  async getAdminNotebooks(): Promise<any[]> {
    return this.request<any[]>('/admin/notebooks');
  }

  async deleteAdminNotebook(id: string): Promise<any> {
    return this.request<any>(`/admin/notebooks/${id}`, {
      method: 'DELETE',
    });
  }

  async getAdminUserFiles(userId: string): Promise<any[]> {
    return this.request<any[]>(`/admin/workspaces/${userId}/files`);
  }

  async getAdminIntegrations(): Promise<any> {
    return this.request<any>('/admin/settings/integrations');
  }

  async updateAdminIntegrations(integrations: any): Promise<any> {
    return this.request<any>('/admin/settings/integrations', {
      method: 'PUT',
      body: JSON.stringify({ integrations }),
    });
  }

  // Language Service / Autocomplete / Diagnostics
  async getCompletions(
    code: string,
    line: number,
    column: number,
    notebookContext: string[] = [],
    sessionId?: string,
    signal?: AbortSignal
  ) {
    return this.request<{
      completions: Array<{ label: string; type: string; detail?: string; documentation?: string; insert_text?: string }>;
      signatures: any[];
      /** "column": DataFrame column keys replacing `prefix` (typed after `quote`) */
      context?: string | null;
      prefix?: string | null;
      quote?: string | null;
      /** Why runtime suggestions are missing or possibly out of date */
      notice?: string | null;
    }>('/editor/complete', {
      method: 'POST',
      body: JSON.stringify({ code, line, column, notebook_context: notebookContext, session_id: sessionId }),
      signal,
    });
  }

  // Structured documentation for a dotted name (suggestion details panel)
  async inspectExpression(expression: string, code: string, line: number, column: number, notebookContext: string[] = [], sessionId?: string, signal?: AbortSignal) {
    return this.request<{ doc: any | null; reason?: string }>('/editor/inspect', {
      method: 'POST',
      body: JSON.stringify({ expression, code, line, column, notebook_context: notebookContext, session_id: sessionId }),
      signal,
    });
  }

  async getSignatures(code: string, line: number, column: number, notebookContext: string[] = []) {
    return this.request<{ signatures: Array<{ name: string; signature: string; params: string[]; docstring?: string; index: number }> }>('/editor/signatures', {
      method: 'POST',
      body: JSON.stringify({ code, line, column, notebook_context: notebookContext }),
    });
  }

  async getDiagnostics(code: string, notebookContext: string[] = [], sessionId?: string, signal?: AbortSignal) {
    return this.request<{ diagnostics: Array<{ from_line: number; from_col: number; to_line: number; to_col: number; message: string; severity: string }> }>('/editor/diagnostics', {
      method: 'POST',
      body: JSON.stringify({ code, notebook_context: notebookContext, session_id: sessionId }),
      signal,
    });
  }
}

export const api = new ApiClient();

