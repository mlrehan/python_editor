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
  role: 'student' | 'instructor' | 'org_admin' | 'platform_admin';
}

export interface FileItem {
  name: string;
  path: string;
  is_dir: boolean;
  size: number;
  modified_at: number;
}

export type KernelStatus = 'disconnected' | 'connecting' | 'idle' | 'busy' | 'restarting';

