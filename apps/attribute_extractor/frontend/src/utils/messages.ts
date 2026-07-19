import { API_ERROR_LABEL, STEP_LABEL, TECHNICAL_MESSAGE_LABELS } from './constants';

export function hasCyrillic(value: string): boolean {
  return /[А-Яа-яЁё]/.test(value);
}

export function isTechnicalMessage(value: string): boolean {
  return /[A-Za-z]{3}/.test(value) && !hasCyrillic(value);
}

export function userMessageFromText(message: string | null | undefined, fallback: string): string {
  const trimmed = message?.trim();
  if (!trimmed) return fallback;
  const translated = TECHNICAL_MESSAGE_LABELS.find(([pattern]) => pattern.test(trimmed));
  if (translated) return translated[1];
  return isTechnicalMessage(trimmed) ? fallback : trimmed;
}

export function processingMessage(message: string | null | undefined, step: string | null | undefined): string {
  const trimmed = message?.trim();
  if (!trimmed) return step ? (STEP_LABEL[step] || 'Обработка идет в фоновом режиме') : 'Обработка идет в фоновом режиме';

  const preparingPackage = trimmed.match(/^Preparing\s+(.+)$/i);
  if (preparingPackage) return `Подготовка пакета ${preparingPackage[1]}`;

  const packageStep = trimmed.match(/^(.+?):\s*(OCR|postprocess|chunking|indexing chunks|search|rerank grouping|extraction)(?:\s+(.+))?$/i);
  if (packageStep) {
    const [, tzId, rawAction, fileName] = packageStep;
    const action = rawAction.toLowerCase();
    if (action === 'ocr') return fileName ? `Чтение PDF-файла ${fileName} для пакета ${tzId}` : `Чтение PDF-файлов для пакета ${tzId}`;
    if (action === 'postprocess') return fileName ? `Подготовка текста файла ${fileName} для пакета ${tzId}` : `Подготовка текста для пакета ${tzId}`;
    if (action === 'chunking') return fileName ? `Разделение файла ${fileName} на фрагменты для пакета ${tzId}` : `Разделение текста на фрагменты для пакета ${tzId}`;
    if (action === 'indexing chunks') return `Подготовка поиска для пакета ${tzId}`;
    if (action === 'search') return `Поиск нужных фрагментов для пакета ${tzId}`;
    if (action === 'rerank grouping') return `Сбор и группировка фрагментов для пакета ${tzId}`;
    if (action === 'extraction') return `Извлечение атрибутов для пакета ${tzId}`;
  }

  return userMessageFromText(trimmed, step ? (STEP_LABEL[step] || 'Обработка идет в фоновом режиме') : 'Обработка идет в фоновом режиме');
}

export function describeApiError(error: import('../api/client').ApiError): string {
  const message = API_ERROR_LABEL[error.code] || userMessageFromText(error.message, 'Не удалось выполнить действие');
  const first = error.details[0];
  const detailed = first && typeof first.value === 'string' ? first.value : null;
  return detailed && !isTechnicalMessage(detailed) ? `${message}: ${detailed}` : message;
}
