import { useEffect, useState } from 'react';
import { ApiError, api } from '../../api/client';
import type { DocumentFile, ObjectType, ProcessRestartMode, Task, ValidationReport } from '../../types/api';
import type { Tab, ToastState } from '../../types/ui';
import { API_ERROR_LABEL } from '../../utils/constants';
import { userMessageFromText } from '../../utils/messages';
import { extractReport, validationReportFromApiError } from '../../utils/validation';
import { ProgressPanel } from './ProgressPanel';
import { ResultPanel } from './ResultPanel';
import { TaskHeader } from './TaskHeader';
import { TaskMetadataPanel } from './TaskMetadataPanel';
import { UploadPanel } from './UploadPanel';
import { ValidationIssuesModal } from './ValidationIssuesModal';
import { ValidationPanel } from './ValidationPanel';

export function TaskDetailPage({
  task,
  objectTypes,
  busy,
  onBack,
  onTaskChange,
  onDelete,
  onRefresh,
  onToast,
  describeError,
}: {
  task: Task;
  objectTypes: ObjectType[];
  busy: boolean;
  onBack: () => void;
  onTaskChange: (task: Task) => void;
  onDelete: (task: Task) => void;
  onRefresh: () => Promise<void>;
  onToast: (message: string, type?: NonNullable<ToastState>['type']) => void;
  describeError: (error: unknown) => string;
}) {
  const [tab, setTab] = useState<Tab>('main');
  const [name, setName] = useState(task.name);
  const [objectType, setObjectType] = useState(task.object_type);
  const [saving, setSaving] = useState(false);
  const [uploadActivity, setUploadActivity] = useState<
    null | { kind: 'registry' | 'groundTruth' | 'validate'; fileName?: string }
  >(null);
  const [running, setRunning] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [resumeDisabledReason, setResumeDisabledReason] = useState<string | null>(null);
  const [validationReport, setValidationReport] = useState<ValidationReport | null>(() => extractReport(task));
  const [groundTruthReport, setGroundTruthReport] = useState<ValidationReport | null>(null);
  const [groundTruthModalOpen, setGroundTruthModalOpen] = useState(false);
  const [documents, setDocuments] = useState<DocumentFile[]>([]);

  useEffect(() => {
    setName(task.name);
    setObjectType(task.object_type);
  }, [task.id]);

  useEffect(() => {
    setValidationReport(extractReport(task));
    setResumeDisabledReason(null);
    setGroundTruthReport(null);
    setGroundTruthModalOpen(false);
    setUploadActivity(null);
  }, [task]);

  useEffect(() => {
    let cancelled = false;
    api.listDocuments(task.id)
      .then((items) => {
        if (!cancelled) setDocuments(items);
      })
      .catch(() => {
        if (!cancelled) setDocuments([]);
      });
    return () => {
      cancelled = true;
    };
  }, [task.id, task.updated_at]);

  const metadataLocked = task.status === 'processing';
  const sourceLocked = metadataLocked || task.status === 'done';
  const groundTruthLocked = task.status === 'processing';
  const canProcess = task.status === 'ready' || task.status === 'done' || task.status === 'error';
  const objectLabel = objectTypes.find((item) => item.code === task.object_type)?.title || task.object_type;
  const hasSyntheticRecparts = Boolean(validationReport?.packages.some((item) => item.recpart_source === 'synthetic'));

  const saveMetadata = async () => {
    setSaving(true);
    try {
      const updated = await api.updateTask(task.id, {
        name: name.trim(),
        object_type: objectType,
      });
      onTaskChange(updated);
      setName(updated.name);
      setObjectType(updated.object_type);
      onToast('Изменения сохранены', 'success');
    } catch (error) {
      onToast(describeError(error), 'error');
    } finally {
      setSaving(false);
    }
  };

  const upload = async (kind: 'registry' | 'groundTruth', file: File) => {
    setSaving(true);
    setUploadActivity({ kind, fileName: file.name });
    try {
      const hadGroundTruthBefore = task.has_ground_truth;
      let updated: Task;
      if (kind === 'registry') updated = await api.uploadRegistry(task.id, file);
      else updated = await api.uploadGroundTruth(task.id, file);
      if (kind === 'groundTruth') {
        setGroundTruthReport(null);
        setGroundTruthModalOpen(false);
      }
      onTaskChange(updated);
      if (kind === 'groundTruth') {
        onToast('Эталонные данные загружены и проверены', 'success');
      } else {
        onToast(kind === 'registry' ? 'Реестр загружен' : 'PDF-файлы загружены', 'success');
        if (hadGroundTruthBefore && !updated.has_ground_truth) {
          onToast('Исходный комплект изменен: эталонные данные сброшены, загрузите их заново', 'warning');
        }
      }
    } catch (error) {
      const report = kind === 'groundTruth' ? validationReportFromApiError(error) : null;
      if (report) {
        setGroundTruthReport(report);
        setGroundTruthModalOpen(true);
      }
      onToast(describeError(error), 'error');
    } finally {
      setSaving(false);
      setUploadActivity(null);
    }
  };

  const uploadDocuments = async (files: FileList) => {
    const fileList = Array.from(files);
    if (fileList.length === 0) return;
    setSaving(true);
    try {
      const byName = new Set(documents.map((item) => item.file_name));
      let lastTask = task;
      for (const file of fileList) {
        let overwrite = false;
        if (byName.has(file.name)) {
          overwrite = window.confirm(`Файл ${file.name} уже есть. Заменить его?`);
          if (!overwrite) continue;
        }
        try {
          lastTask = await api.uploadDocument(task.id, file, overwrite);
          byName.add(file.name);
        } catch (error) {
          if (error instanceof ApiError && error.code === 'document_already_exists') {
            const confirmOverwrite = window.confirm(`Файл ${file.name} уже есть. Заменить его?`);
            if (!confirmOverwrite) continue;
            lastTask = await api.uploadDocument(task.id, file, true);
            byName.add(file.name);
          } else {
            throw error;
          }
        }
      }
      onTaskChange(lastTask);
      setDocuments(await api.listDocuments(task.id));
      onToast('PDF-файлы обновлены', 'success');
    } catch (error) {
      onToast(describeError(error), 'error');
    } finally {
      setSaving(false);
    }
  };

  const deleteDocument = async (fileName: string) => {
    if (!window.confirm(`Удалить PDF-файл ${fileName}?`)) return;
    setSaving(true);
    try {
      const updated = await api.deleteDocument(task.id, fileName);
      onTaskChange(updated);
      setDocuments(await api.listDocuments(task.id));
      onToast('PDF-файл удален', 'info');
    } catch (error) {
      onToast(describeError(error), 'error');
    } finally {
      setSaving(false);
    }
  };

  const deleteGroundTruth = async () => {
    if (!window.confirm('Удалить эталонные данные?')) return;
    setSaving(true);
    try {
      const updated = await api.deleteGroundTruth(task.id);
      onTaskChange(updated);
      onToast('Эталонные данные удалены', 'info');
    } catch (error) {
      onToast(describeError(error), 'error');
    } finally {
      setSaving(false);
    }
  };

  const validate = async () => {
    setSaving(true);
    setUploadActivity({ kind: 'validate' });
    try {
      const report = await api.validateTask(task.id);
      setValidationReport(report);
      await onRefresh();
      onToast(report.is_valid ? 'Комплект проверен и готов к обработке' : 'В комплекте есть ошибки', report.is_valid ? 'success' : 'warning');
    } catch (error) {
      onToast(describeError(error), 'error');
    } finally {
      setSaving(false);
      setUploadActivity(null);
    }
  };

  const process = async (mode: ProcessRestartMode = 'from_start') => {
    if (task.status === 'done' && !window.confirm('Запустить обработку заново? Текущий результат будет заменен.')) return;
    if (task.status === 'error') {
      const message = mode === 'from_failed_tz'
        ? 'Продолжить обработку с места ошибки?'
        : 'Запустить обработку с начала?';
      if (!window.confirm(message)) return;
    }
    setRunning(true);
    try {
      const updated = await api.processTask(task.id, mode);
      onTaskChange(updated);
      setTab('processing');
      onToast('Обработка началась', 'success');
    } catch (error) {
      if (mode === 'from_failed_tz' && error instanceof ApiError) {
        setResumeDisabledReason(API_ERROR_LABEL[error.code] || userMessageFromText(error.message, 'Продолжить с места ошибки сейчас нельзя'));
      }
      const report = error instanceof ApiError && error.code.startsWith('ground_truth')
        ? validationReportFromApiError(error)
        : null;
      if (report) {
        setGroundTruthReport(report);
        setGroundTruthModalOpen(true);
      }
      onToast(describeError(error), 'error');
    } finally {
      setRunning(false);
    }
  };

  const downloadBlob = (blob: Blob, filename: string) => {
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  };

  const downloadSourceFile = async (
    kind: 'registry' | 'document' | 'groundTruth',
    fallbackName: string,
    fileName?: string,
  ) => {
    try {
      const { blob, filename } =
        kind === 'registry'
          ? await api.downloadRegistry(task.id)
          : kind === 'groundTruth'
            ? await api.downloadGroundTruth(task.id)
            : await api.downloadDocument(task.id, fileName || fallbackName);
      downloadBlob(blob, filename || fallbackName);
    } catch (error) {
      onToast(describeError(error), 'error');
    }
  };

  const downloadResult = async () => {
    setExporting(true);
    try {
      onToast(task.has_ground_truth
        ? 'Подготавливаем отчет и считаем метрики по эталонным данным'
        : 'Подготавливаем отчет с результатами обработки',
      'info');
      const { blob, filename } = await api.downloadResult(task.id);
      downloadBlob(blob, filename || task.result_file_name || 'result.xlsx');
      const mode = filename?.includes('_отчет_с_метриками') ? 'with_gt' : 'predictions';
      onToast(
        mode === 'with_gt'
          ? 'Отчет сформирован с эталонными данными'
          : 'Отчет сформирован без эталонных данных',
        mode === 'with_gt' ? 'success' : 'warning',
      );
    } catch (error) {
      onToast(describeError(error), 'error');
    } finally {
      setExporting(false);
    }
  };

  return (
    <section className="page page--detail">
      <TaskHeader
        task={task}
        objectLabel={objectLabel}
        busy={busy}
        running={running}
        canProcess={canProcess}
        resumeDisabledReason={resumeDisabledReason}
        onBack={onBack}
        onProcess={process}
        onRefresh={() => { void onRefresh(); }}
        onDelete={onDelete}
      />

      <div className="tabs">
        {[
          ['main', 'Основное'],
          ['processing', 'Обработка'],
          ['export', 'Результаты'],
        ].map(([id, label]) => (
          <button key={id} type="button" className={tab === id ? 'active' : ''} onClick={() => setTab(id as Tab)}>
            {label}
          </button>
        ))}
      </div>

      <div className="detail-content">
        {tab === 'main' && (
          <div className="content-grid">
            <TaskMetadataPanel
              objectTypes={objectTypes}
              name={name}
              objectType={objectType}
              metadataLocked={metadataLocked}
              saving={saving}
              onNameChange={setName}
              onObjectTypeChange={setObjectType}
              onSave={saveMetadata}
            />

            <UploadPanel
              task={task}
              documents={documents}
              validationReport={validationReport}
              sourceLocked={sourceLocked}
              groundTruthLocked={groundTruthLocked}
              saving={saving}
              uploadActivity={uploadActivity}
              hasSyntheticRecparts={hasSyntheticRecparts}
              onUploadRegistry={(file) => { void upload('registry', file); }}
              onUploadDocuments={(files) => { void uploadDocuments(files); }}
              onDeleteDocument={(fileName) => { void deleteDocument(fileName); }}
              onValidate={() => { void validate(); }}
              onUploadGroundTruth={(file) => { void upload('groundTruth', file); }}
              onDeleteGroundTruth={() => { void deleteGroundTruth(); }}
              onDownloadRegistry={() => { void downloadSourceFile('registry', task.registry_file_name || 'registry.xlsx'); }}
              onDownloadDocument={(fileName) => { void downloadSourceFile('document', fileName, fileName); }}
              onDownloadGroundTruth={() => { void downloadSourceFile('groundTruth', task.ground_truth_file_name || 'ground_truth.xlsx'); }}
            />

            <ValidationPanel report={validationReport} />
          </div>
        )}

        {tab === 'processing' && <ProgressPanel task={task} />}

        {tab === 'export' && (
          <ResultPanel
            task={task}
            exporting={exporting}
            onDownload={() => { void downloadResult(); }}
          />
        )}
      </div>
      {groundTruthModalOpen && groundTruthReport && (
        <ValidationIssuesModal
          title="Проверка эталонных данных"
          report={groundTruthReport}
          onClose={() => setGroundTruthModalOpen(false)}
        />
      )}
    </section>
  );
}
