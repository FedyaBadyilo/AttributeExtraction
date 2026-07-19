import type { ValidationReport } from '../../types/api';
import { formatIssueDetail } from '../../utils/format';
import { Button } from '../ui/Button';

export function ValidationIssuesModal({
  title,
  report,
  onClose,
}: {
  title: string;
  report: ValidationReport;
  onClose: () => void;
}) {
  return (
    <div className="modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <div className="modal modal--wide">
        <div className="modal-header">
          <h2>{title}</h2>
          <button type="button" onClick={onClose}>×</button>
        </div>
        <div className="modal-body">
          <div className={report.is_valid ? 'success-box' : 'warning-box'}>
            {report.is_valid ? 'Эталонные данные соответствуют текущему комплекту.' : `Найдены ошибки: ${report.issues.length}`}
          </div>
          {report.issues.length > 0 && (
            <div className="issue-list issue-list--modal">
              {report.issues.map((issue, index) => (
                <div className="issue" key={`${issue.code}-${index}`}>
                  <div className="issue__title">{issue.message}</div>
                  <div className="issue__meta">
                    {issue.field && <span>Поле: {issue.field}</span>}
                    {issue.tz_id && <span>Пакет: {issue.tz_id}</span>}
                    {issue.file_name && <span>Файл: {issue.file_name}</span>}
                    <span>{issue.code}</span>
                  </div>
                  {Object.keys(issue.details || {}).length > 0 && (
                    <div className="issue__details">
                      {Object.entries(issue.details).map(([key, value]) => (
                        <div className="issue__detail-row" key={key}>
                          <span>{key}</span>
                          <code>{formatIssueDetail(value)}</code>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="modal-footer">
          <Button onClick={onClose}>Закрыть</Button>
        </div>
      </div>
    </div>
  );
}
