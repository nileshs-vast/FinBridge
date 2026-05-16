export interface User {
  id: string
  email: string
  role: 'platform_admin' | 'firm_admin' | 'accountant' | 'company_user'
  firm_id: string | null
  company_id: string | null
  created_at: string
}

export interface LoginResponse {
  access_token: string
  user: User
}

export interface FirmOut {
  id: string
  name: string
  created_at: string
}

export interface CompanyOut {
  id: string
  firm_id: string
  name: string
  business_type: string
  created_at: string
}

export interface PaymentHeadOut {
  id: string
  company_id: string
  name: string
  parent_head_id: string | null
  created_at: string
  children: PaymentHeadOut[]
}

export interface UserOut {
  id: string
  email: string
  role: string
  firm_id: string | null
  company_id: string | null
  created_at: string
}

export interface AttachmentOut {
  id: string
  original_name: string
  mime_type: string
  size_bytes: number
  created_at: string
}

export type TransactionStatus = 'draft_ai' | 'pending_review' | 'needs_info' | 'accepted' | 'rejected'
export type TransactionType = 'invoice' | 'payment' | 'salary_register' | 'bank_statement'
export type TransactionDirection = 'purchase' | 'sales' | 'payment_in' | 'payment_out'

export interface TransactionOut {
  id: string
  company_id: string
  transaction_type: TransactionType
  direction: TransactionDirection | null
  vendor: string | null
  invoice_no: string | null
  transaction_date: string | null
  amount: string | null
  currency: string
  payment_head_id: string | null
  status: TransactionStatus
  raw_extraction: Record<string, unknown> | null
  notes: string | null
  rejection_reason: string | null
  info_request_reason: string | null
  possible_duplicate_of: string | null
  uploaded_by: string
  reviewed_by: string | null
  created_at: string
  reviewed_at: string | null
  attachments: AttachmentOut[]
}

export interface LineItem {
  description: string
  quantity: number | null
  unit_price: number | null
  amount: number
  hsn_sac: string | null
}

export interface ExtractedInvoice {
  vendor: string | null
  vendor_address: string | null
  vendor_gstin: string | null
  customer_gstin: string | null
  place_of_supply: string | null
  invoice_no: string | null
  invoice_date: string | null
  due_date: string | null
  currency: string
  subtotal: number | null
  tax_amount: number | null
  cgst: number | null
  sgst: number | null
  igst: number | null
  reverse_charge: boolean
  total: number | null
  line_items: LineItem[]
  suggested_direction: 'purchase' | 'sales' | null
  confidence: Record<string, number>
  notes: string | null
}

export interface TransactionUploadResponse {
  transaction: TransactionOut
  extracted: ExtractedInvoice
}

export interface ReportOut {
  id: string
  company_id: string
  title: string
  original_name: string
  mime_type: string
  uploaded_by: string
  created_at: string
}

export interface StatusCount {
  status: string
  count: number
}

export interface ExpenseHeadStat {
  payment_head_id: string
  name: string
  total_amount: string
}

export interface DashboardSummary {
  counts_by_status: StatusCount[]
  top_expense_heads: ExpenseHeadStat[]
  recent_transactions: TransactionOut[]
}
