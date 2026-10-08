import { useCallback, useEffect, useRef, useState } from 'react';
import { Entities } from '@uipath/uipath-typescript/entities';
import { useAuth } from '@/hooks/useAuth';
import { APP_CONFIG } from '@/config/app';
import { DECISION_WRITE_FIELDS, UI_DEPENDENT_FIELDS, type FieldName } from './fields';
import { toAppError, type AppError } from './errors';

/**
 * Live schema of AP_Invoice_Sagar (entities.getByName, scope DataFabric.Schema.Read).
 * Lets the UI tell "field not in schema" apart from "no data yet".
 */
export interface SchemaState {
  status: 'idle' | 'loading' | 'ready' | 'error';
  entityName: string;
  fieldNames: Set<string>;
  /** UI-dependent fields absent from the schema (drives the data-integrity banner). */
  missingUiFields: FieldName[];
  /** True when every field the approve / reject write touches exists. */
  canWriteDecision: boolean;
  error: AppError | null;
  reload: () => void;
}

export function useSchema(): SchemaState {
  const { sdk, isAuthenticated } = useAuth();
  const [status, setStatus] = useState<SchemaState['status']>('idle');
  const [entityName, setEntityName] = useState<string>(APP_CONFIG.invoiceEntityName);
  const [fieldNames, setFieldNames] = useState<Set<string>>(new Set());
  const [error, setError] = useState<AppError | null>(null);
  const inFlight = useRef(false);

  const load = useCallback(async () => {
    if (!isAuthenticated || inFlight.current) return;
    inFlight.current = true;
    setStatus('loading');
    setError(null);
    try {
      const entity = await new Entities(sdk).getByName(APP_CONFIG.invoiceEntityName);
      setEntityName(entity.name);
      setFieldNames(new Set(entity.fields.map((f) => f.name)));
      setStatus('ready');
    } catch (err) {
      setError(toAppError(err, 'Unable to read the entity schema.'));
      setStatus('error');
    } finally {
      inFlight.current = false;
    }
  }, [sdk, isAuthenticated]);

  useEffect(() => {
    load();
  }, [load]);

  const ready = status === 'ready';
  const missingUiFields = ready ? UI_DEPENDENT_FIELDS.filter((f) => !fieldNames.has(f)) : [];
  const canWriteDecision = ready && DECISION_WRITE_FIELDS.every((f) => fieldNames.has(f));

  return { status, entityName, fieldNames, missingUiFields, canWriteDecision, error, reload: load };
}

/** True only when the schema is known and the field is absent. */
export function fieldMissing(schema: SchemaState, field: string): boolean {
  return schema.status === 'ready' && !schema.fieldNames.has(field);
}
