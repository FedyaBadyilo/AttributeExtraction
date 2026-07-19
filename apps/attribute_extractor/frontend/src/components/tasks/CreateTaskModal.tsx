import { useState } from 'react';
import type { ObjectType } from '../../types/api';
import { Button } from '../ui/Button';
import { FormRow } from '../ui/FormRow';

export function CreateTaskModal({
  objectTypes,
  busy,
  onClose,
  onCreate,
}: {
  objectTypes: ObjectType[];
  busy: boolean;
  onClose: () => void;
  onCreate: (payload: { name: string; object_type: string }) => void;
}) {
  const [name, setName] = useState('');
  const [objectType, setObjectType] = useState('');

  return (
    <div className="modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-header">
          <h2>Создать задачу</h2>
          <button type="button" onClick={onClose}>×</button>
        </div>
        <div className="modal-body">
          <FormRow label="Название задачи">
            <input className="text-input" value={name} onChange={(event) => setName(event.target.value)} autoFocus />
          </FormRow>
          <FormRow label="Тип объекта">
            <select className="select-input" value={objectType} disabled={objectTypes.length === 0} onChange={(event) => setObjectType(event.target.value)}>
              <option value="" disabled>{objectTypes.length === 0 ? 'Типы объектов не загружены' : 'Выберите тип объекта'}</option>
              {objectTypes.map((item) => (
                <option key={item.code} value={item.code}>{item.title}</option>
              ))}
            </select>
          </FormRow>
        </div>
        <div className="modal-footer">
          <Button variant="secondary" onClick={onClose}>Отмена</Button>
          <Button onClick={() => onCreate({ name: name.trim(), object_type: objectType })} disabled={busy || !name.trim() || !objectType}>
            Создать
          </Button>
        </div>
      </div>
    </div>
  );
}
