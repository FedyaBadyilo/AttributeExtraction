import type { ObjectType } from '../../types/api';
import { Button } from '../ui/Button';
import { FormRow } from '../ui/FormRow';
import { Panel } from '../ui/Panel';

export function TaskMetadataPanel({
  objectTypes,
  name,
  objectType,
  metadataLocked,
  saving,
  onNameChange,
  onObjectTypeChange,
  onSave,
}: {
  objectTypes: ObjectType[];
  name: string;
  objectType: string;
  metadataLocked: boolean;
  saving: boolean;
  onNameChange: (value: string) => void;
  onObjectTypeChange: (value: string) => void;
  onSave: () => void;
}) {
  return (
    <Panel title="Параметры задачи">
      <FormRow label="Название задачи">
        <input className="text-input" value={name} disabled={metadataLocked} onChange={(event) => onNameChange(event.target.value)} />
      </FormRow>
      <FormRow label="Тип объекта">
        <select className="select-input" value={objectType} disabled={metadataLocked || objectTypes.length === 0} onChange={(event) => onObjectTypeChange(event.target.value)}>
          {objectTypes.length === 0 && <option value="">Типы объектов не загружены</option>}
          {objectType && !objectTypes.some((item) => item.code === objectType) && (
            <option value={objectType}>{objectType}</option>
          )}
          {objectTypes.map((item) => (
            <option key={item.code} value={item.code}>{item.title}</option>
          ))}
        </select>
      </FormRow>
      <Button onClick={onSave} disabled={metadataLocked || saving || !name.trim() || !objectType}>Сохранить</Button>
    </Panel>
  );
}
