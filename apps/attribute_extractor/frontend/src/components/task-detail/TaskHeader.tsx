import type { ProcessRestartMode, Task } from '../../types/api';
import { formatDate } from '../../utils/format';
import { Button } from '../ui/Button';
import { StatusBadge } from '../ui/StatusBadge';

export function TaskHeader({
  task,
  objectLabel,
  busy,
  running,
  canProcess,
  resumeDisabledReason,
  onBack,
  onProcess,
  onRefresh,
  onDelete,
}: {
  task: Task;
  objectLabel: string;
  busy: boolean;
  running: boolean;
  canProcess: boolean;
  resumeDisabledReason: string | null;
  onBack: () => void;
  onProcess: (mode: ProcessRestartMode) => void;
  onRefresh: () => void;
  onDelete: (task: Task) => void;
}) {
  return (
    <header className="detail-header">
      <div className="breadcrumbs">
        <button type="button" onClick={onBack}>Задачи</button>
        <span>/</span>
        <span>{task.name}</span>
      </div>
      <div className="detail-heading">
        <div>
          <h1>{task.name}</h1>
          <div className="detail-meta">
            <StatusBadge status={task.status} />
            <span>{objectLabel}</span>
            <span>Создана: {formatDate(task.created_at)}</span>
          </div>
        </div>
        <div className="detail-actions">
          {canProcess && task.status === 'error' && (
            <div className="restart-actions">
              <Button onClick={() => onProcess('from_start')} disabled={busy || running}>Запустить заново</Button>
              {!resumeDisabledReason && task.failed_tz_id && (
                <Button variant="secondary" onClick={() => onProcess('from_failed_tz')} disabled={busy || running}>
                  Продолжить с места ошибки
                </Button>
              )}
            </div>
          )}
          {canProcess && task.status !== 'error' && (
            <Button onClick={() => onProcess('from_start')} disabled={busy || running}>
              {task.status === 'done' ? 'Запустить заново' : 'Запустить обработку'}
            </Button>
          )}
          <Button variant="secondary" onClick={onRefresh}>Обновить</Button>
          <Button variant="danger" onClick={() => onDelete(task)}>Удалить</Button>
        </div>
      </div>
    </header>
  );
}
