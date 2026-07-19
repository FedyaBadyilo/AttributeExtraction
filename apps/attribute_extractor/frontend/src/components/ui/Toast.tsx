import { useEffect } from 'react';
import type { ToastState } from '../../types/ui';

export function Toast({ toast, onClose }: { toast: NonNullable<ToastState>; onClose: () => void }) {
  useEffect(() => {
    const timeout = window.setTimeout(onClose, 3500);
    return () => window.clearTimeout(timeout);
  }, [onClose]);

  return (
    <div className={`toast toast--${toast.type}`}>
      <span>{toast.message}</span>
      <button type="button" onClick={onClose}>×</button>
    </div>
  );
}
