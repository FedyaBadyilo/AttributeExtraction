export type TaskStatus = 'draft' | 'ready' | 'processing' | 'done' | 'error';
export type ProcessRestartMode = 'from_start' | 'from_failed_tz';

export interface ObjectType {
  code: string;
  title: string;
  dataset_dirname: string;
}

export interface Task {
  id: string;
  name: string;
  object_type: string;
  status: TaskStatus;
  created_at: string;
  updated_at: string;
  registry_file_name: string | null;
  documents_archive_name: string | null;
  ground_truth_file_name: string | null;
  has_ground_truth: boolean;
  result_file_name: string | null;
  last_validation: string | null;
  progress_step: string | null;
  progress_message: string | null;
  progress_tz_id: string | null;
  progress_tz_index: number | null;
  progress_tz_total: number | null;
  progress_execution_variant: string | null;
  failed_tz_id: string | null;
  failed_tz_index: number | null;
  failed_execution_variant: string | null;
  error_message: string | null;
}

export interface DocumentFile {
  file_name: string;
  size_bytes: number;
  uploaded_at: string;
}

export interface TaskListResponse {
  items: Task[];
  total: number;
  limit: number;
  offset: number;
}

export interface TaskCreate {
  name: string;
  object_type: string;
}

export interface TaskUpdate {
  name?: string;
  object_type?: string;
}

export interface ProcessTaskRequest {
  mode?: ProcessRestartMode;
}

export interface TzPackage {
  package_id: string | null;
  tz_id: string;
  main_file_name: string;
  supplements_by_index: Record<string, string>;
  recpart: string | null;
  recpart_source: 'file' | 'synthetic';
  execution_variant: string | null;
}

export interface ValidationIssue {
  code: string;
  message: string;
  field: string | null;
  tz_id: string | null;
  file_name: string | null;
  details: Record<string, unknown>;
}

export interface ValidationReport {
  is_valid: boolean;
  issues: ValidationIssue[];
  packages: TzPackage[];
}

export interface ApiErrorBody {
  error?: {
    code: string;
    message: string;
    details?: Array<Record<string, unknown>>;
  };
  detail?: unknown;
}
