import { isEvaluationRow } from '@/data/invoice';

/**
 * Lab 5 evaluation rows (InvoiceNumber TRAIN-*) share vendors with real
 * invoices. A small neutral tag keeps a reviewer from deciding the wrong one.
 */
export function EvaluationTag({ invoiceNumber }: { invoiceNumber: string | null | undefined }) {
  if (!isEvaluationRow(invoiceNumber)) return null;
  return (
    <span className="pill pill-eval" title="Lab 5 evaluation row, not a vendor invoice">
      Evaluation data
    </span>
  );
}
