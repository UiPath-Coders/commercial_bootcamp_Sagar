import { useCallback, useEffect, useRef, useState } from 'react';
import { Entities } from '@uipath/uipath-typescript/entities';
import { useAuth } from '@/auth/AuthProvider';
import { UIPATH_CONFIG, folderScope, isEntityIdConfigured } from '@/config/uipath';
import { DECISION_WRITE_FIELDS, UI_DEPENDENT_FIELDS, type FieldName } from './invoiceFields';
import { toAppError, type AppError } from './errors';

/**
 * Live schema of AP_Invoice_<user_name>, discovered through `entities.getById`
 * (scope: DataFabric.Schema.Read). The UI uses it to tell "field not in
 * schema" apart from "no data yet": the data-integrity banner, the per-card
 * KPI empty states and the decision buttons all key off this.
 */
export interface SchemaState {
  status: 'idle' | 'loading' | 'ready' | 'error';
  entityName: string;
  /** Exact, case-sensitive field system names present on the entity. */
  fieldNames: Set<string>;
  /** UI-dependent fields (InvoiceLifecycleState, AgentRecommendation, ReviewedBy) absent from the schema. */
  missingUiFields: FieldName[];
  /** True when every field the approve / reject write touches exists. */
  canWriteDecision: boolean;
  error: AppError | null;
  reload: () => void;
}

export function useInvoiceSchema(): SchemaState {
  const { sdk, isAuthenticated } = useAuth();
  const [status, setStatus] = useState<SchemaState['status']>('idle');
  const [entityName, setEntityName] = useState('');
  const [fieldNames, setFieldNames] = useState<Set<string>>(new Set());
  const [error, setError] = useState<AppError | null>(null);
  const inFlight = useRef(false);

  const load = useCallback(async () => {
    if (!isAuthenticated || !isEntityIdConfigured() || inFlight.current) return;
    inFlight.current = true;
    setStatus('loading');
    setError(null);
    try {
      const entities = new Entities(sdk);
      const entity = await entities.getById(UIPATH_CONFIG.invoiceEntityId, folderScope);
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

  const has = (f: FieldName) => status !== 'ready' || fieldNames.has(f);
  const missingUiFields = status === 'ready' ? UI_DEPENDENT_FIELDS.filter((f) => !fieldNames.has(f)) : [];
  const canWriteDecision = DECISION_WRITE_FIELDS.every(has) && status === 'ready';

  return { status, entityName, fieldNames, missingUiFields, canWriteDecision, error, reload: load };
}

/** True when the schema is known and the field is absent; false while loading or when present. */
export function fieldMissing(schema: SchemaState, field: FieldName): boolean {
  return schema.status === 'ready' && !schema.fieldNames.has(field);
}
