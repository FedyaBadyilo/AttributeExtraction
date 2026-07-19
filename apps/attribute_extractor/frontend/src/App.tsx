import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ApiError, api } from './api/client';
import type { ObjectType, Task, TaskStatus } from './types/api';
import type { StartupErrorKind, StartupErrorState, ToastState, View } from './types/ui';
import { INITIAL_LOAD_MAX_ATTEMPTS, INITIAL_LOAD_RETRY_DELAY_MS } from './utils/constants';
import { describeApiError, userMessageFromText } from './utils/messages';
import { Sidebar } from './components/layout/Sidebar';
import { StartupErrorScreen } from './components/layout/StartupErrorScreen';
import { CreateTaskModal } from './components/tasks/CreateTaskModal';
import { TaskList } from './components/tasks/TaskList';
import { TaskDetailPage } from './components/task-detail/TaskDetailPage';
import { Toast } from './components/ui/Toast';

export function App() {
  const [view, setView] = useState<View>('tasks');
  const [objectTypes, setObjectTypes] = useState<ObjectType[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<TaskStatus | 'all'>('all');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<ToastState>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [startupError, setStartupError] = useState<StartupErrorState | null>(null);
  const didInitialLoad = useRef(false);

  const showToast = useCallback((message: string, type: NonNullable<ToastState>['type'] = 'info') => {
    setToast({ message, type });
  }, []);

  const describeError = useCallback((error: unknown) => {
    if (error instanceof ApiError) return describeApiError(error);
    if (error instanceof Error) return userMessageFromText(error.message, 'Не удалось выполнить действие');
    return 'Неизвестная ошибка';
  }, []);

  const classifyStartupError = useCallback((error: unknown): StartupErrorState => {
    if (error instanceof ApiError) {
      const kind: StartupErrorKind = error.status >= 500 ? 'backend_unavailable' : 'integration_error';
      return {
        kind,
        message: kind === 'backend_unavailable'
          ? 'Сервис временно недоступен.'
          : 'Не удалось загрузить данные при запуске.',
        technical: userMessageFromText(error.message, 'Попробуйте обновить страницу чуть позже.'),
      };
    }
    const technical = error instanceof Error
      ? userMessageFromText(error.message, 'Попробуйте обновить страницу чуть позже.')
      : userMessageFromText(String(error), 'Попробуйте обновить страницу чуть позже.');
    return {
      kind: 'backend_unavailable',
      message: 'Не удалось подключиться к сервису.',
      technical,
    };
  }, []);

  const refreshTasks = useCallback(async () => {
    const response = await api.listTasks({
      limit: 100,
      search: search.trim() || undefined,
      status: statusFilter,
    });
    setTasks(response.items);
  }, [search, statusFilter]);

  const refreshSelectedTask = useCallback(async (taskId: string) => {
    const task = await api.getTask(taskId);
    setSelectedTask(task);
    setTasks((current) => current.map((item) => (item.id === task.id ? task : item)));
  }, []);

  useEffect(() => {
    let ignore = false;
    const wait = (ms: number) => new Promise((resolve) => window.setTimeout(resolve, ms));

    async function loadInitial() {
      setLoading(true);
      setStartupError(null);
      let lastError: unknown = null;

      for (let attempt = 1; attempt <= INITIAL_LOAD_MAX_ATTEMPTS; attempt += 1) {
        try {
          const [types, taskResponse] = await Promise.all([
            api.listObjectTypes(),
            api.listTasks({ limit: 100 }),
          ]);
          if (!ignore) {
            setObjectTypes(types);
            setTasks(taskResponse.items);
            didInitialLoad.current = true;
            setStartupError(null);
            setLoading(false);
          }
          return;
        } catch (error) {
          lastError = error;
          if (ignore) return;
          if (attempt < INITIAL_LOAD_MAX_ATTEMPTS) {
            await wait(INITIAL_LOAD_RETRY_DELAY_MS);
          }
        }
      }

      if (!ignore && lastError) {
        const startupState = classifyStartupError(lastError);
        setStartupError(startupState);
        showToast(startupState.message, 'error');
      }
      if (!ignore) setLoading(false);
    }
    void loadInitial();
    return () => {
      ignore = true;
    };
  }, [classifyStartupError, showToast]);

  useEffect(() => {
    if (!didInitialLoad.current) return undefined;
    const timeout = window.setTimeout(() => {
      void refreshTasks().catch((error) => showToast(describeError(error), 'error'));
    }, 250);
    return () => window.clearTimeout(timeout);
  }, [refreshTasks, describeError, showToast]);

  useEffect(() => {
    if (!selectedTaskId) return undefined;
    const selected = tasks.find((task) => task.id === selectedTaskId);
    if (selected) setSelectedTask(selected);
    return undefined;
  }, [tasks, selectedTaskId]);

  useEffect(() => {
    const hasProcessing = tasks.some((task) => task.status === 'processing') || selectedTask?.status === 'processing';
    if (!hasProcessing) return undefined;
    const interval = window.setInterval(() => {
      void refreshTasks().catch(() => undefined);
      if (selectedTaskId) {
        void refreshSelectedTask(selectedTaskId).catch(() => undefined);
      }
    }, 3000);
    return () => window.clearInterval(interval);
  }, [tasks, selectedTask, selectedTaskId, refreshTasks, refreshSelectedTask]);

  const statusCounts = useMemo(() => {
    const counts: Record<string, number> = { all: tasks.length };
    for (const task of tasks) {
      counts[task.status] = (counts[task.status] || 0) + 1;
    }
    return counts;
  }, [tasks]);

  const openTask = async (taskId: string) => {
    setSelectedTaskId(taskId);
    setView('detail');
    try {
      await refreshSelectedTask(taskId);
    } catch (error) {
      showToast(describeError(error), 'error');
    }
  };

  const handleCreateTask = async (payload: { name: string; object_type: string }) => {
    setBusy(true);
    try {
      const task = await api.createTask(payload);
      setTasks((current) => [task, ...current]);
      setCreateOpen(false);
      await openTask(task.id);
      showToast('Задача создана', 'success');
    } catch (error) {
      showToast(describeError(error), 'error');
    } finally {
      setBusy(false);
    }
  };

  const handleDeleteTask = async (task: Task) => {
    if (!window.confirm(`Удалить задачу «${task.name}»?`)) return;
    setBusy(true);
    try {
      await api.deleteTask(task.id);
      setTasks((current) => current.filter((item) => item.id !== task.id));
      setSelectedTask(null);
      setSelectedTaskId(null);
      setView('tasks');
      showToast('Задача удалена', 'info');
    } catch (error) {
      showToast(describeError(error), 'error');
    } finally {
      setBusy(false);
    }
  };

  const updateSelectedTask = (task: Task) => {
    setSelectedTask(task);
    setTasks((current) => current.map((item) => (item.id === task.id ? task : item)));
  };

  return (
    <div className="app-shell">
      <Sidebar />
      <main className="app-main">
        {loading && (
          <section className="page">
            <header className="page-header">
              <div>
                <h1>Загрузка</h1>
                <p>Загружаем список задач и типы объектов.</p>
              </div>
            </header>
          </section>
        )}
        {!loading && startupError && <StartupErrorScreen error={startupError} />}
        {!loading && !startupError && view === 'tasks' && (
          <TaskList
            tasks={tasks}
            objectTypes={objectTypes}
            loading={loading}
            search={search}
            statusFilter={statusFilter}
            statusCounts={statusCounts}
            onSearch={setSearch}
            onStatusFilter={setStatusFilter}
            onOpenTask={openTask}
            onCreate={() => setCreateOpen(true)}
          />
        )}
        {!loading && !startupError && view === 'detail' && selectedTask && (
          <TaskDetailPage
            task={selectedTask}
            objectTypes={objectTypes}
            busy={busy}
            onBack={() => setView('tasks')}
            onTaskChange={updateSelectedTask}
            onDelete={handleDeleteTask}
            onRefresh={() => refreshSelectedTask(selectedTask.id)}
            onToast={showToast}
            describeError={describeError}
          />
        )}
      </main>

      {createOpen && (
        <CreateTaskModal
          objectTypes={objectTypes}
          busy={busy}
          onClose={() => setCreateOpen(false)}
          onCreate={handleCreateTask}
        />
      )}

      {toast && <Toast toast={toast} onClose={() => setToast(null)} />}
    </div>
  );
}
