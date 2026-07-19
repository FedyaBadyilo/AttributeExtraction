import { useRef } from 'react';

export function FileDrop({
  label,
  hint,
  accept,
  fileName,
  disabled,
  loading,
  loadingTitle,
  loadingHint,
  onFile,
  onClear,
  onDownload,
}: {
  label: string;
  hint: string;
  accept: string;
  fileName?: string | null;
  disabled?: boolean;
  loading?: boolean;
  loadingTitle?: string;
  loadingHint?: string;
  onFile: (file: File) => void;
  onClear?: () => void;
  onDownload?: () => void;
}) {
  const ref = useRef<HTMLInputElement | null>(null);
  const showReady = Boolean(fileName) && !loading;
  const uploadDisabled = Boolean(disabled);
  const locked = uploadDisabled && showReady;
  const inactive = uploadDisabled && !showReady && !loading;

  return (
    <div
      className={`file-drop ${showReady ? 'file-drop--ready' : ''} ${loading ? 'file-drop--loading' : ''} ${locked ? 'file-drop--locked' : ''} ${inactive ? 'file-drop--inactive' : ''}`}
      onClick={() => !uploadDisabled && !loading && ref.current?.click()}
      aria-busy={loading || undefined}
    >
      <div className="file-drop__icon" aria-hidden="true">
        {loading ? <span className="spinner" /> : showReady ? '✓' : '↑'}
      </div>
      <div className="file-drop__body">
        <div className="file-drop__title">{loading ? loadingTitle || label : fileName || label}</div>
        <div className="file-drop__hint">
          {loading ? loadingHint || 'Проверяем файл на сервере...' : fileName ? hint : `${hint}. Нажмите для выбора файла.`}
        </div>
      </div>
      {onDownload && showReady && (
        <button
          className="file-drop__download"
          type="button"
          onClick={(event) => {
            event.stopPropagation();
            onDownload();
          }}
        >
          Скачать
        </button>
      )}
      {onClear && !loading && (
        <button
          className="file-drop__clear"
          type="button"
          onClick={(event) => {
            event.stopPropagation();
            onClear();
          }}
        >
          Удалить
        </button>
      )}
      <input
        ref={ref}
        hidden
        type="file"
        accept={accept}
        onChange={(event) => {
          const file = event.currentTarget.files?.[0];
          if (file) onFile(file);
          event.currentTarget.value = '';
        }}
      />
    </div>
  );
}
