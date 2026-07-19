import { useCallback } from 'react';
import type { ObjectType, Task, TaskStatus } from '../../types/api';
import { STATUS_FILTERS } from '../../utils/constants';
import { formatDate } from '../../utils/format';
import { FileSummary } from '../files/FileSummary';
import { Button } from '../ui/Button';
import { StatusBadge } from '../ui/StatusBadge';

export function TaskList({
  tasks,
  objectTypes,
  loading,
  search,
  statusFilter,
  statusCounts,
  onSearch,
  onStatusFilter,
  onOpenTask,
  onCreate,
}: {
  tasks: Task[];
  objectTypes: ObjectType[];
  loading: boolean;
  search: string;
  statusFilter: TaskStatus | 'all';
  statusCounts: Record<string, number>;
  onSearch: (value: string) => void;
  onStatusFilter: (value: TaskStatus | 'all') => void;
  onOpenTask: (taskId: string) => void;
  onCreate: () => void;
}) {
  const objectLabel = useCallback(
    (code: string) => objectTypes.find((item) => item.code === code)?.title || code,
    [objectTypes],
  );

  return (
    <section className="page page--tasks">
      <header className="page-header">
        <div>
          <h1>Задачи</h1>
          <p>Работа с задачами, загрузка файлов и запуск обработки.</p>
        </div>
        <Button onClick={onCreate}>Создать задачу</Button>
      </header>

      <div className="toolbar">
        <input className="search-input" value={search} onChange={(event) => onSearch(event.target.value)} placeholder="Поиск по названию" />
        <div className="segmented">
          {STATUS_FILTERS.map((filter) => (
            <button
              key={filter.id}
              type="button"
              className={statusFilter === filter.id ? 'active' : ''}
              onClick={() => onStatusFilter(filter.id)}
            >
              {filter.label}
              {statusCounts[filter.id] ? ` (${statusCounts[filter.id]})` : ''}
            </button>
          ))}
        </div>
      </div>

      <div className="table-wrap">
        <table className="tasks-table">
          <thead>
            <tr>
              <th>Название задачи</th>
              <th>Тип объекта</th>
              <th>Статус</th>
              <th>Файлы</th>
              <th>Дата создания</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={6} className="empty-cell">Загрузка задач...</td>
              </tr>
            )}
            {!loading && tasks.length === 0 && (
              <tr>
                <td colSpan={6} className="empty-cell">Задачи не найдены</td>
              </tr>
            )}
            {!loading &&
              tasks.map((task) => (
                <tr key={task.id} onClick={() => onOpenTask(task.id)}>
                  <td>
                    <div className="task-name">{task.name}</div>
                    {task.has_ground_truth && <div className="task-subline">Эталонные данные загружены</div>}
                  </td>
                  <td>{objectLabel(task.object_type)}</td>
                  <td><StatusBadge status={task.status} /></td>
                  <td>
                    <FileSummary task={task} />
                  </td>
                  <td>{formatDate(task.created_at)}</td>
                  <td className="cell-actions">
                    <Button variant="ghost" onClick={() => onOpenTask(task.id)}>Открыть</Button>
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
