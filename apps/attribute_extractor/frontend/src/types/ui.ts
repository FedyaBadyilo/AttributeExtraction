export type View = 'tasks' | 'detail';
export type Tab = 'main' | 'processing' | 'export';
export type ToastState = { message: string; type: 'info' | 'success' | 'error' | 'warning' } | null;
export type StartupErrorKind = 'backend_unavailable' | 'integration_error';
export type StartupErrorState = {
  kind: StartupErrorKind;
  message: string;
  technical: string;
};
