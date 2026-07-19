import type { Task } from '../../types/api';
import { PROCESSING_STEPS, STEP_LABEL } from '../../utils/constants';
import { formatPackageLabel } from '../../utils/format';
import { processingMessage, userMessageFromText } from '../../utils/messages';
import { Panel } from '../ui/Panel';

export function ProgressPanel({ task }: { task: Task }) {
  const activeIndex = task.progress_step ? PROCESSING_STEPS.indexOf(task.progress_step) : -1;
  const hasTzProgress = Boolean(task.progress_tz_total && task.progress_tz_total > 0);
  const tzTotal = task.progress_tz_total || 0;
  const currentTzIndex = task.progress_tz_index || 0;
  const completedTzCount = task.status === 'done' || task.progress_step === 'export'
    ? tzTotal
    : Math.max(0, currentTzIndex - 1);
  const tzProgressPercent = hasTzProgress
    ? Math.min(100, Math.round((completedTzCount / tzTotal) * 100))
    : 0;
  const currentTzLabel = task.progress_tz_id && currentTzIndex && tzTotal
    ? `Обработка пакета ${formatPackageLabel(task.progress_tz_id, task.progress_execution_variant)}: ${currentTzIndex}/${tzTotal}`
    : null;
  const currentMessage = processingMessage(task.progress_message, task.progress_step);
  const errorMessage = userMessageFromText(task.error_message, 'Обработка остановлена из-за ошибки');

  return (
    <Panel title="Ход обработки">
      <div className="processing-summary">
        {task.status === 'processing' && currentMessage}
        {task.status === 'done' && 'Обработка завершена'}
        {task.status === 'error' && errorMessage}
        {(task.status === 'draft' || task.status === 'ready') && 'Когда все файлы будут загружены и проверены, можно запускать обработку.'}
      </div>
      {hasTzProgress && (
        <div className="tz-progress" aria-label="Прогресс обработки пакетов">
          <div className="tz-progress__header">
            <span>
              {task.status === 'processing' && currentTzLabel
                ? currentTzLabel
                : `Обработано пакетов: ${completedTzCount}/${tzTotal}`}
            </span>
            <span>{tzProgressPercent}%</span>
          </div>
          <div className="tz-progress__bar">
            <div className="tz-progress__fill" style={{ width: `${tzProgressPercent}%` }} />
          </div>
        </div>
      )}
      {task.status === 'error' && task.failed_tz_id && (
        <div className="warning-box">
          Пакет {formatPackageLabel(task.failed_tz_id, task.failed_execution_variant)} завершился с ошибкой{task.failed_tz_index && task.progress_tz_total ? `: ${task.failed_tz_index}/${task.progress_tz_total}` : ''}
        </div>
      )}
      <div className="steps">
        {PROCESSING_STEPS.map((step, index) => {
          const done = task.status === 'done' || (task.status === 'processing' && activeIndex > index);
          const active = task.status === 'processing' && activeIndex === index;
          return (
            <div className={`step ${done ? 'step--done' : ''} ${active ? 'step--active' : ''}`} key={step}>
              <div className="step__marker">{done ? '✓' : index + 1}</div>
              <div>
                <div className="step__title">{STEP_LABEL[step] || step}</div>
                {active && <div className="step__message">{currentMessage}</div>}
              </div>
            </div>
          );
        })}
      </div>
    </Panel>
  );
}
