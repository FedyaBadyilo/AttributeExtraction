import type { Task } from '../../types/api';
import { Button } from '../ui/Button';
import { Panel } from '../ui/Panel';

export function ResultPanel({
  task,
  exporting,
  onDownload,
}: {
  task: Task;
  exporting: boolean;
  onDownload: () => void;
}) {
  return (
    <Panel title="Выгрузка результатов">
      {task.status !== 'done' ? (
        <div className="warning-box">Результаты появятся после успешной обработки задачи.</div>
      ) : (
        <div className="export-box">
          <div>
            <div className="export-title">Итоговый Excel-отчет</div>
            <div className="export-subtitle">
              {task.has_ground_truth
                ? 'При первом скачивании отчет будет сформирован с метками и метриками по эталонным данным. Это может занять несколько минут.'
                : 'При первом скачивании отчет будет сформирован с результатами обработки, уверенностью и текстом исходных фрагментов.'}
            </div>
            {exporting && (
              <div className="export-progress" role="status">
                <span className="spinner" aria-hidden="true" />
                <span>{task.has_ground_truth ? 'Подготавливаем отчет и считаем метки...' : 'Подготавливаем отчет...'}</span>
              </div>
            )}
          </div>
          <Button onClick={onDownload} disabled={exporting}>
            {exporting ? 'Готовится...' : 'Скачать отчет'}
          </Button>
        </div>
      )}
    </Panel>
  );
}
