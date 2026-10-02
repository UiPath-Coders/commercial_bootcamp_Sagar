import { isAuthenticationError, isAuthorizationError, isNotFoundError, isUiPathError } from '@uipath/uipath-typescript/core';

export type ErrorKind = 'auth' | 'forbidden' | 'not-found' | 'service';

export interface AppError {
  kind: ErrorKind;
  message: string;
  /** HTTP status when the SDK exposes one. */
  status?: number;
}

/**
 * Normalise SDK / network errors into the states the UI renders:
 *  - auth       : 401 / expired session -> "sign in again"
 *  - forbidden  : 403 -> OAuth scope or entity permission
 *  - not-found  : 404 -> wrong entity id (or a folder key on a tenant entity)
 *  - service    : anything else -> retry
 */
export function toAppError(err: unknown, fallback = 'Something went wrong.'): AppError {
  if (isAuthenticationError(err)) {
    return { kind: 'auth', message: err.message || 'Your UiPath session has expired. Sign in again.', status: err.statusCode };
  }
  if (isAuthorizationError(err)) {
    return {
      kind: 'forbidden',
      message: `${err.message || 'Access denied.'} Check that the OAuth client grants DataFabric.Schema.Read, DataFabric.Data.Read and DataFabric.Data.Write, and that your user can read and update the entity.`,
      status: err.statusCode,
    };
  }
  if (isNotFoundError(err)) {
    return {
      kind: 'not-found',
      message: `${err.message || 'Not found.'} Check invoiceEntityId in src/config/uipath.ts (uip df entities list) and make sure no folder key is passed for a tenant-scoped entity.`,
      status: err.statusCode,
    };
  }
  if (isUiPathError(err)) {
    const status = err.statusCode;
    if (status === 401) return { kind: 'auth', message: err.message || 'Session expired.', status };
    if (status === 403) return { kind: 'forbidden', message: err.message || 'Access denied.', status };
    if (status === 404) return { kind: 'not-found', message: err.message || 'Not found.', status };
    return { kind: 'service', message: err.message || fallback, status };
  }
  if (err instanceof Error) return { kind: 'service', message: err.message || fallback };
  return { kind: 'service', message: fallback };
}
