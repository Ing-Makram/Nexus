export type InvoiceStatus = 'draft' | 'sent' | 'paid' | 'overdue' | 'void'

export const INVOICE_STATUSES: InvoiceStatus[] = ['draft', 'sent', 'paid', 'overdue', 'void']

export interface Invoice {
  id: number
  organization: number
  customer: number
  order: number | null
  invoice_number: string
  status: InvoiceStatus
  issue_date: string
  due_date: string | null
  total_amount: string
  notes: string
  created_by: string | null
  created_at: string
  updated_at: string
}

/** Editable invoice fields sent to the API. */
export interface InvoiceInput {
  customer: number
  order: number | null
  /** Blank means "let the backend assign the next INV-NNNN". */
  invoice_number?: string
  status?: InvoiceStatus
  issue_date: string
  due_date: string | null
  total_amount: string
  notes?: string
}
