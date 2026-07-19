import { useRef } from 'react';

export function MultiFileDrop({
  label,
  hint,
  accept,
  disabled,
  onFiles,
}: {
  label: string;
  hint: string;
  accept: string;
  disabled?: boolean;
  onFiles: (files: FileList) => void;
}) {
  const ref = useRef<HTMLInputElement | null>(null);

  return (
    <div className={`file-drop ${disabled ? 'file-drop--inactive' : ''}`} onClick={() => !disabled && ref.current?.click()}>
      <div className="file-drop__icon">↑</div>
      <div className="file-drop__body">
        <div className="file-drop__title">{label}</div>
        <div className="file-drop__hint">{`${hint}. Нажмите для выбора файлов.`}</div>
      </div>
      <input
        ref={ref}
        hidden
        multiple
        type="file"
        accept={accept}
        onChange={(event) => {
          const files = event.currentTarget.files;
          if (files && files.length > 0) onFiles(files);
          event.currentTarget.value = '';
        }}
      />
    </div>
  );
}
