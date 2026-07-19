import { ApiError } from '../api/client';
import type { Task, TzPackage, ValidationIssue, ValidationReport } from '../types/api';
import { userMessageFromText } from './messages';

export function extractReport(task: Task | null): ValidationReport | null {
  if (!task?.last_validation) return null;
  try {
    return JSON.parse(task.last_validation) as ValidationReport;
  } catch {
    return null;
  }
}

export function issueFromRecord(value: Record<string, unknown>): ValidationIssue {
  return {
    code: typeof value.code === 'string' ? value.code : 'validation_error',
    message: typeof value.message === 'string' ? value.message : 'Ошибка валидации',
    field: typeof value.field === 'string' ? value.field : null,
    tz_id: typeof value.tz_id === 'string' ? value.tz_id : null,
    file_name: typeof value.file_name === 'string' ? value.file_name : null,
    details: value.details && typeof value.details === 'object' && !Array.isArray(value.details)
      ? (value.details as Record<string, unknown>)
      : {},
  };
}

export function validationReportFromApiError(error: unknown): ValidationReport | null {
  if (!(error instanceof ApiError)) return null;
  if (error.details.length === 0) {
    return {
      is_valid: false,
      issues: [{
        code: error.code || 'validation_error',
        message: userMessageFromText(error.message, 'Ошибка валидации'),
        field: 'Эталонные данные',
        tz_id: null,
        file_name: null,
        details: {},
      }],
      packages: [],
    };
  }
  return {
    is_valid: false,
    issues: error.details.map((raw) => {
      const issue = issueFromRecord(raw);
      return {
        ...issue,
        code: issue.code || error.code || 'validation_error',
        message: userMessageFromText(issue.message || error.message, 'Ошибка валидации'),
      };
    }),
    packages: [],
  };
}

export function listSupplementFiles(item: TzPackage): string[] {
  return Object.entries(item.supplements_by_index)
    .sort(([left], [right]) => Number(left) - Number(right))
    .map(([, fileName]) => fileName)
    .filter((fileName): fileName is string => Boolean(fileName));
}
