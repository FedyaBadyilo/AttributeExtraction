import type { TaskStatus } from '../../types/api';
import { STATUS_LABEL } from '../../utils/constants';

export function StatusBadge({ status }: { status: TaskStatus }) {
  return <span className={`status status--${status}`}>{STATUS_LABEL[status]}</span>;
}
