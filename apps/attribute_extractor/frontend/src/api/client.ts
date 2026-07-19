import type {
  ApiErrorBody,
  ObjectType,
  DocumentFile,
  ProcessRestartMode,
  Task,
  TaskCreate,
  TaskListResponse,
  TaskStatus,
  TaskUpdate,
  ValidationReport,
} from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

export class ApiError extends Error {
  status: number;
  code: string;
  details: Array<Record<string, unknown>>;

  constructor(status: number, code: string, message: string, details: Array<Record<string, unknown>> = []) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);
  if (!response.ok) {
    let body: ApiErrorBody = {};
    try {
      body = await response.json();
    } catch {
      body = {};
    }
    const structured = body.error;
    const fallback = typeof body.detail === 'string' ? body.detail : response.statusText;
    throw new ApiError(
      response.status,
      structured?.code || 'api_error',
      structured?.message || fallback,
      structured?.details || [],
    );
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

async function requestBlob(path: string, init?: RequestInit): Promise<{ blob: Blob; filename: string | null }> {
  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, cache: init?.cache ?? 'no-store' });
  if (!response.ok) {
    let body: ApiErrorBody = {};
    try {
      body = await response.json();
    } catch {
      body = {};
    }
    const structured = body.error;
    const fallback = typeof body.detail === 'string' ? body.detail : response.statusText;
    throw new ApiError(
      response.status,
      structured?.code || 'api_error',
      structured?.message || fallback,
      structured?.details || [],
    );
  }
  return {
    blob: await response.blob(),
    filename: filenameFromDisposition(response.headers.get('content-disposition')),
  };
}

function jsonRequest<T>(path: string, method: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

function uploadFile(path: string, file: File, extraForm?: Record<string, string>): Promise<Task> {
  const form = new FormData();
  form.append('file', file);
  if (extraForm) {
    Object.entries(extraForm).forEach(([key, value]) => form.append(key, value));
  }
  return request<Task>(path, { method: 'POST', body: form });
}

function filenameFromDisposition(value: string | null): string | null {
  if (!value) return null;
  const utf8Match = value.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) return decodeURIComponent(utf8Match[1]);
  const asciiMatch = value.match(/filename="?([^";]+)"?/i);
  return asciiMatch?.[1] || null;
}

export const api = {
  baseUrl: API_BASE_URL,

  listObjectTypes(): Promise<ObjectType[]> {
    return request<ObjectType[]>('/object-types');
  },

  listTasks(params: {
    limit?: number;
    offset?: number;
    status?: TaskStatus | 'all';
    search?: string;
    object_type?: string;
  } = {}): Promise<TaskListResponse> {
    const query = new URLSearchParams();
    query.set('limit', String(params.limit ?? 50));
    query.set('offset', String(params.offset ?? 0));
    if (params.status && params.status !== 'all') query.set('status', params.status);
    if (params.search) query.set('search', params.search);
    if (params.object_type) query.set('object_type', params.object_type);
    return request<TaskListResponse>(`/tasks?${query.toString()}`);
  },

  createTask(payload: TaskCreate): Promise<Task> {
    return jsonRequest<Task>('/tasks', 'POST', payload);
  },

  getTask(taskId: string): Promise<Task> {
    return request<Task>(`/tasks/${taskId}`);
  },

  updateTask(taskId: string, payload: TaskUpdate): Promise<Task> {
    return jsonRequest<Task>(`/tasks/${taskId}`, 'PATCH', payload);
  },

  deleteTask(taskId: string): Promise<void> {
    return request<void>(`/tasks/${taskId}`, { method: 'DELETE' });
  },

  uploadRegistry(taskId: string, file: File): Promise<Task> {
    return uploadFile(`/tasks/${taskId}/registry`, file);
  },

  uploadDocument(taskId: string, file: File, overwrite = false): Promise<Task> {
    return uploadFile(`/tasks/${taskId}/documents`, file, { overwrite: overwrite ? 'true' : 'false' });
  },

  listDocuments(taskId: string): Promise<DocumentFile[]> {
    return request<DocumentFile[]>(`/tasks/${taskId}/documents`);
  },

  deleteDocument(taskId: string, fileName: string): Promise<Task> {
    return request<Task>(`/tasks/${taskId}/documents/${encodeURIComponent(fileName)}`, { method: 'DELETE' });
  },

  uploadGroundTruth(taskId: string, file: File): Promise<Task> {
    return uploadFile(`/tasks/${taskId}/ground-truth`, file);
  },

  deleteGroundTruth(taskId: string): Promise<Task> {
    return request<Task>(`/tasks/${taskId}/ground-truth`, { method: 'DELETE' });
  },

  validateTask(taskId: string): Promise<ValidationReport> {
    return request<ValidationReport>(`/tasks/${taskId}/validate`, { method: 'POST' });
  },

  processTask(taskId: string, mode: ProcessRestartMode = 'from_start'): Promise<Task> {
    return jsonRequest<Task>(`/tasks/${taskId}/process`, 'POST', { mode });
  },

  resultUrl(taskId: string): string {
    return `${API_BASE_URL}/tasks/${taskId}/result`;
  },

  downloadResult(taskId: string): Promise<{ blob: Blob; filename: string | null }> {
    return requestBlob(`/tasks/${taskId}/result`);
  },

  downloadRegistry(taskId: string): Promise<{ blob: Blob; filename: string | null }> {
    return requestBlob(`/tasks/${taskId}/registry`);
  },

  downloadDocument(taskId: string, fileName: string): Promise<{ blob: Blob; filename: string | null }> {
    return requestBlob(`/tasks/${taskId}/documents/${encodeURIComponent(fileName)}`);
  },

  downloadGroundTruth(taskId: string): Promise<{ blob: Blob; filename: string | null }> {
    return requestBlob(`/tasks/${taskId}/ground-truth`);
  },

  registryTemplateUrl(): string {
    return `${API_BASE_URL}/registry-template`;
  },
};
