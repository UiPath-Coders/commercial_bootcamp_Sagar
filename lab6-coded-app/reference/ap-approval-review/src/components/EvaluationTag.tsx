/**
 * Lab 5 evaluation rows (InvoiceNumber TRAIN-*) share vendors with real invoices
 * (TRAIN-VA-1006 and VA-INV-40592 are both Vertex Analytics; TRAIN-CL-1002 and
 * CLL-2026-3391 are both Contoso Logistics). A small neutral tag keeps a reviewer
 * from approving the evaluation row by mistake.
 */
export function isEvaluationRow(invoiceNumber: string | null | undefined): boolean {
  return (invoiceNumber ?? '').trim().toUpperCase().startsWith('TRAIN-');
}

export function EvaluationTag({ invoiceNumber }: { invoiceNumber: string | null | undefined }) {
  if (!isEvaluationRow(invoiceNumber)) return null;
  return (
    <span className="pill pill-eval" title="Lab 5 evaluation row, not a vendor invoice to decide">
      Evaluation data
    </span>
  );
}
