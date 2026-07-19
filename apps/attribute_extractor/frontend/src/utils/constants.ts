import type { TaskStatus } from '../types/api';

export const STATUS_LABEL: Record<TaskStatus, string> = {
  draft: 'Черновик',
  ready: 'Готова к обработке',
  processing: 'В обработке',
  done: 'Готово',
  error: 'С ошибкой',
};

export const STATUS_FILTERS: Array<{ id: TaskStatus | 'all'; label: string }> = [
  { id: 'all', label: 'Все' },
  { id: 'draft', label: 'Черновик' },
  { id: 'ready', label: 'Готовые к обработке' },
  { id: 'processing', label: 'В обработке' },
  { id: 'done', label: 'Готово' },
  { id: 'error', label: 'С ошибкой' },
];

export const STEP_LABEL: Record<string, string> = {
  validate_input: 'Проверка и подготовка файлов',
  ocr: 'Чтение PDF-файлов',
  postprocess: 'Подготовка текста',
  chunking: 'Разделение текста на фрагменты',
  indexing: 'Подготовка поиска',
  search: 'Поиск нужных фрагментов',
  rerank_grouping: 'Сбор и группировка фрагментов',
  extraction: 'Извлечение атрибутов',
  export: 'Формирование отчета',
  done: 'Завершено',
};

export const PROCESSING_STEPS = [
  'validate_input',
  'ocr',
  'postprocess',
  'chunking',
  'indexing',
  'search',
  'rerank_grouping',
  'extraction',
  'export',
  'done',
];

export const API_ERROR_LABEL: Record<string, string> = {
  task_already_processing: 'Задача уже обрабатывается',
  task_not_ready_for_processing: 'Задача пока не готова к обработке',
  task_validation_missing: 'Перед обработкой нужно проверить комплект файлов',
  task_validation_not_valid: 'Сначала исправьте ошибки в комплекте файлов',
  task_validation_corrupted: 'Отчет проверки поврежден. Запустите проверку комплекта заново',
  task_result_not_ready: 'Результат еще не готов',
  task_result_export_failed: 'Не удалось сформировать отчет',
  task_result_checkpoints_missing: 'Не найдены промежуточные результаты обработки',
  restart_from_failed_tz_unavailable: 'Продолжить с места ошибки можно только для задач с ошибкой',
  restart_failed_tz_missing: 'Не удалось определить место остановки. Запустите обработку с начала',
  restart_failed_tz_out_of_range: 'Место остановки не совпадает с текущим комплектом файлов',
  restart_inputs_changed_after_failure: 'После ошибки исходные файлы изменились. Запустите обработку с начала',
  restart_checkpoints_missing: 'Не найдены промежуточные результаты. Запустите обработку с начала',
  restart_checkpoints_corrupted: 'Промежуточные результаты повреждены. Запустите обработку с начала',
};

export const TECHNICAL_MESSAGE_LABELS: Array<[RegExp, string]> = [
  [/^Processing was interrupted by backend restart$/i, 'Обработка прервалась из-за перезапуска сервиса. Можно продолжить с места остановки или запустить заново.'],
  [/^Task validation report is not valid$/i, 'Сначала исправьте ошибки в комплекте файлов'],
  [/^Task validation report is corrupted$/i, 'Отчет проверки поврежден. Запустите проверку комплекта заново'],
  [/^Task must be validated before processing$/i, 'Перед обработкой нужно проверить комплект файлов'],
  [/^Task processing results are missing$/i, 'Не найдены промежуточные результаты обработки'],
  [/^Task result export failed$/i, 'Не удалось сформировать отчет'],
  [/^Task result is not ready$/i, 'Результат еще не готов'],
  [/^PDF files not found:/i, 'Не найдены PDF-файлы из комплекта. Проверьте загруженные документы'],
  [/^Failed to fetch$/i, 'Не удалось подключиться к сервису. Проверьте, что он запущен'],
  [/backend/i, 'Сервис обработки временно недоступен. Попробуйте еще раз чуть позже'],
];

export const INITIAL_LOAD_MAX_ATTEMPTS = 3;
export const INITIAL_LOAD_RETRY_DELAY_MS = 1200;
