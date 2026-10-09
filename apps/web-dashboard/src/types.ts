export type CellType = 'code' | 'markdown';

export interface KernelOutput {
  output_type: 'stream' | 'display_data' | 'execute_result' | 'error';
  name?: 'stdout' | 'stderr';
  text?: string;
  data?: Record<string, any>;
  metadata?: Record<string, any>;
  execution_count?: number;
  ename?: string;
  evalue?: string;
  traceback?: string[];
}

export interface NotebookCell {
  id: string;
  cell_type: CellType;
  source: string;
  execution_count?: number | null;
  outputs: KernelOutput[];
  is_running?: boolean;
  metadata?: Record<string, any>;
}

export interface NotebookDocument {
  id: string;
  title: string;
  kernel_name: string;
  cells: NotebookCell[];
  updated_at?: string;
}

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  role: 'student' | 'instructor' | 'org_admin' | 'platform_admin' | 'admin' | 'super_admin';
  can_manage_packages?: boolean;
  theme_preference?: 'system' | 'dark' | 'light';
}

export interface AdminStats {
  total_users: number;
  active_users?: number;
  total_notebooks: number;
  total_projects: number;
  active_kernels: number;
  system_memory: {
    total_gb: number;
    available_gb: number;
    used_gb: number;
    percent: number;
  };
  disk_usage: {
    total_gb: number;
    free_gb: number;
    used_gb: number;
    percent: number;
  };
}

export interface AdminPackageItem {
  name: string;
  version: string;
  summary: string;
  is_protected: boolean;
}

export interface AdminRuntimeItem {
  session_id: string;
  user_id: string;
  user_email: string;
  is_running: boolean;
  pid: number | null;
  memory_mb: number;
  cpu_percent: number;
  execution_count: number;
  workspace_dir: string;
  idle_seconds: number;
}

export interface AdminWorkspaceItem {
  id: string;
  type: 'public' | 'user';
  name: string;
  path: string;
  item_count: number;
  total_size_mb: number;
  files: Array<{
    name: string;
    path: string;
    is_dir: boolean;
    size: number;
    modified_at: number;
  }>;
}

export interface AdminAuditItem {
  id: string;
  user_id: string;
  action: string;
  resource_type: string;
  resource_id: string | null;
  timestamp: string;
  details: Record<string, any>;
}

export interface FileItem {
  name: string;
  path: string;
  is_dir: boolean;
  size: number;
  modified_at: number;
}

export type KernelStatus = 'disconnected' | 'connecting' | 'idle' | 'busy' | 'restarting';


