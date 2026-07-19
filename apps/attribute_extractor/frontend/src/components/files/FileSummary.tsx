import type { Task } from '../../types/api';
import { extractReport } from '../../utils/validation';

export function FileSummary({ task }: { task: Task }) {
  const items = [
    task.registry_file_name ? 'реестр' : null,
    extractReport(task)?.packages?.length ? 'PDF-файлы' : null,
    task.has_ground_truth ? 'эталонные данные' : null,
  ].filter(Boolean);
  return <span className="file-summary">{items.length ? items.join(', ') : 'ничего не загружено'}</span>;
}
