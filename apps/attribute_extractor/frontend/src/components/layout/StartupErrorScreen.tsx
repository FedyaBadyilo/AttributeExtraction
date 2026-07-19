import type { StartupErrorState } from '../../types/ui';

export function StartupErrorScreen({ error }: { error: StartupErrorState }) {
  const title = error.kind === 'backend_unavailable' ? 'Сервис временно недоступен' : 'Не удалось загрузить данные';
  return (
    <section className="page">
      <header className="page-header">
        <div>
          <h1>{title}</h1>
          <p>{error.message}</p>
        </div>
      </header>
      <div className="warning-box">
        Стартовая загрузка не выполнена. Обновите страницу после восстановления сервиса.
      </div>
      <div className="muted-box">{error.technical}</div>
    </section>
  );
}
