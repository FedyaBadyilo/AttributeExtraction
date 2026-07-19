import { api } from '../../api/client';
import type { DocumentFile, Task, ValidationReport } from '../../types/api';
import { FileDrop } from '../files/FileDrop';
import { MultiFileDrop } from '../files/MultiFileDrop';
import { Button } from '../ui/Button';
import { Panel } from '../ui/Panel';

type UploadActivity = null | { kind: 'registry' | 'groundTruth' | 'validate'; fileName?: string };

export function UploadPanel({
  task,
  documents,
  validationReport,
  sourceLocked,
  groundTruthLocked,
  saving,
  uploadActivity,
  hasSyntheticRecparts,
  onUploadRegistry,
  onUploadDocuments,
  onDeleteDocument,
  onValidate,
  onUploadGroundTruth,
  onDeleteGroundTruth,
  onDownloadRegistry,
  onDownloadDocument,
  onDownloadGroundTruth,
}: {
  task: Task;
  documents: DocumentFile[];
  validationReport: ValidationReport | null;
  sourceLocked: boolean;
  groundTruthLocked: boolean;
  saving: boolean;
  uploadActivity: UploadActivity;
  hasSyntheticRecparts: boolean;
  onUploadRegistry: (file: File) => void;
  onUploadDocuments: (files: FileList) => void;
  onDeleteDocument: (fileName: string) => void;
  onValidate: () => void;
  onUploadGroundTruth: (file: File) => void;
  onDeleteGroundTruth: () => void;
  onDownloadRegistry: () => void;
  onDownloadDocument: (fileName: string) => void;
  onDownloadGroundTruth: () => void;
}) {
  return (
    <>
      <Panel title="Исходный комплект">
        <div className="template-link-row">
          <span>Шаблон реестра</span>
          <a className="button button--secondary" href={api.registryTemplateUrl()} download>
            Скачать шаблон
          </a>
        </div>
        <FileDrop
          label="Реестр в Excel"
          hint="Загрузите Excel-файл по шаблону реестра. RECPart можно оставить пустым, тогда он появится в проверке комплекта"
          accept=".xls,.xlsx"
          fileName={task.registry_file_name}
          disabled={sourceLocked || saving}
          loading={uploadActivity?.kind === 'registry'}
          loadingTitle={uploadActivity?.fileName || 'Загружаем реестр...'}
          loadingHint="Файл отправляется на сервер"
          onFile={onUploadRegistry}
          onDownload={task.registry_file_name ? onDownloadRegistry : undefined}
        />
        <MultiFileDrop
          label="PDF-файлы"
          hint="Можно выбрать несколько PDF. Имена файлов должны совпадать с реестром"
          accept=".pdf"
          disabled={sourceLocked || saving}
          onFiles={onUploadDocuments}
        />
        {documents.length > 0 ? (
          <div className="document-list">
            {documents.map((doc) => (
              <div className="file-card file-card--ready" key={doc.file_name}>
                <div>
                  <span>{doc.file_name}</span>
                  <div className="task-subline">{Math.round(doc.size_bytes / 1024)} KB</div>
                </div>
                <div className="file-card__actions">
                  <button
                    type="button"
                    className="file-action file-action--download"
                    onClick={() => onDownloadDocument(doc.file_name)}
                  >
                    Скачать
                  </button>
                  {!sourceLocked && (
                    <button type="button" className="file-action file-action--danger" onClick={() => onDeleteDocument(doc.file_name)}>
                      Удалить
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="source-note">Пока нет загруженных PDF-файлов.</div>
        )}
        <Button onClick={onValidate} disabled={sourceLocked || saving || !task.registry_file_name || documents.length === 0}>
          {uploadActivity?.kind === 'validate' ? 'Проверяем комплект...' : 'Проверить комплект'}
        </Button>
        {uploadActivity?.kind === 'validate' && (
          <div className="file-drop-progress" role="status">
            <span className="spinner" aria-hidden="true" />
            <span>Проверяем реестр, PDF и соответствие имён файлов. Это может занять до минуты.</span>
          </div>
        )}
      </Panel>

      <Panel title="Эталонные данные">
        {task.has_ground_truth && task.ground_truth_file_name && (
          <div className="file-card file-card--ready">
            <div>
              <span>{task.ground_truth_file_name}</span>
              <div className="task-subline">Эталонные данные загружены и проверены</div>
            </div>
            <div className="file-card__actions">
              <button
                type="button"
                className="file-action file-action--download"
                onClick={onDownloadGroundTruth}
              >
                Скачать
              </button>
              {!groundTruthLocked && (
                <button type="button" className="file-action file-action--danger" onClick={onDeleteGroundTruth}>
                  Удалить
                </button>
              )}
            </div>
          </div>
        )}
        <FileDrop
          label={task.has_ground_truth ? 'Заменить эталонные данные' : 'Загрузить эталонные данные'}
          hint="Excel-файл с эталонными значениями"
          accept=".xls,.xlsx"
          fileName={uploadActivity?.kind === 'groundTruth' ? uploadActivity.fileName : task.ground_truth_file_name}
          disabled={groundTruthLocked || saving || !validationReport?.is_valid}
          loading={uploadActivity?.kind === 'groundTruth'}
          loadingTitle={uploadActivity?.fileName || 'Проверяем эталонные данные...'}
          loadingHint="Сверяем RECPart, атрибуты и выравнивание листов. Обычно 10–30 секунд."
          onFile={onUploadGroundTruth}
        />
        {!validationReport?.is_valid && (
          <div className="source-note">
            Сначала проверьте комплект. После изменения реестра, PDF-файлов или типа объекта эталонные данные нужно загрузить заново.
          </div>
        )}
        {validationReport?.is_valid && (
          <div className="source-note">
            Эталонные данные проверяются автоматически при загрузке. Если файл отображается выше, проверка уже пройдена.
            После изменения реестра или PDF-файлов эталонные данные нужно загрузить заново.
          </div>
        )}
        {hasSyntheticRecparts && (
          <div className="warning-box">
            В реестре есть RECPart, заполненные автоматически. Используйте значения из проверки комплекта при подготовке эталонных данных, чтобы сопоставление прошло по тем же пакетам.
          </div>
        )}
      </Panel>
    </>
  );
}
