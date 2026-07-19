import type { ValidationReport } from '../../types/api';
import { listSupplementFiles } from '../../utils/validation';
import { Panel } from '../ui/Panel';

export function ValidationPanel({ report }: { report: ValidationReport | null }) {
  if (!report) {
    return (
      <Panel title="Проверка комплекта">
        <div className="muted-box">Результат проверки появится после проверки комплекта.</div>
      </Panel>
    );
  }

  return (
    <Panel title="Проверка комплекта">
      <div className={report.is_valid ? 'success-box' : 'warning-box'}>
        {report.is_valid ? `Проверка пройдена. Пакетов: ${report.packages.length}` : `Найдены ошибки: ${report.issues.length}`}
      </div>
      {report.packages.some((item) => item.recpart_source === 'synthetic') && (
        <div className="warning-box">
          В загруженном реестре не было RECPart, поэтому система создала их автоматически. Для сопоставления с эталонными данными используйте значения из колонки RECPart ниже.
        </div>
      )}
      {report.issues.length > 0 && (
        <div className="issue-list">
          {report.issues.map((issue, index) => (
            <div className="issue" key={`${issue.code}-${index}`}>
              <div className="issue__title">{issue.message}</div>
              <div className="issue__meta">
                {issue.tz_id && <span>Пакет: {issue.tz_id}</span>}
                {issue.file_name && <span>Файл: {issue.file_name}</span>}
                <span>{issue.code}</span>
              </div>
            </div>
          ))}
        </div>
      )}
      {report.packages.length > 0 && (
        <div className="package-list">
          <div className="package-table__header" aria-hidden="true">
            <span>Основной файл</span>
            <span>Файлы-дополнения</span>
            <span>RECPart</span>
            <span>ТЗ</span>
          </div>
          {report.packages.slice(0, 8).map((item) => {
            const supplementFiles = listSupplementFiles(item);
            return (
              <div className="package-row" key={item.package_id || item.tz_id}>
                <div className="package-cell">
                  <div className="package-cell__label">Основной файл</div>
                  {item.main_file_name}
                </div>
                <div className="package-cell">
                  <div className="package-cell__label">Файлы-дополнения</div>
                  {supplementFiles.length > 0 ? (
                    <div className="package-file-list">
                      {supplementFiles.map((fileName, index) => (
                        <div className="package-file-list__item" key={`${item.tz_id}-${fileName}-${index}`}>
                          {fileName}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <span className="package-empty">Нет</span>
                  )}
                </div>
                <div className="package-cell">
                  <div className="package-cell__label">RECPart</div>
                  {item.recpart || 'не задан'}
                </div>
                <div className="package-cell">
                  <div className="package-cell__label">ТЗ</div>
                  {item.tz_id}
                </div>
              </div>
            );
          })}
          {report.packages.length > 8 && <div className="package-more">и еще {report.packages.length - 8}</div>}
        </div>
      )}
    </Panel>
  );
}
