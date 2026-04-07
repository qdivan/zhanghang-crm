export type UserRole = "OWNER" | "ADMIN" | "MANAGER" | "ACCOUNTANT";

export interface UserInfo {
  id: number;
  username: string;
  auth_source: "LOCAL" | "LDAP" | string;
  ldap_dn: string;
  role: UserRole;
  granted_read_modules: DataAccessModule[];
  manager_user_id: number | null;
  manager_username: string;
  is_active: boolean;
  created_at: string;
  last_login_at: string | null;
}

export interface ManagedUser extends UserInfo {}

export interface UserCreatePayload {
  username: string;
  password: string;
  role: UserRole;
  manager_user_id?: number | null;
  is_active: boolean;
}

export interface UserUpdatePayload {
  username?: string;
  password?: string;
  role?: UserRole;
  manager_user_id?: number | null;
  is_active?: boolean;
}

export interface LdapSettings {
  id: number;
  enabled: boolean;
  server_url: string;
  bind_dn: string;
  has_bind_password: boolean;
  base_dn: string;
  user_base_dn: string;
  user_filter: string;
  username_attr: string;
  display_name_attr: string;
  default_role: UserRole;
  created_at: string;
  updated_at: string;
}

export interface LdapSettingsUpdatePayload {
  enabled?: boolean;
  server_url?: string;
  bind_dn?: string;
  bind_password?: string;
  base_dn?: string;
  user_base_dn?: string;
  user_filter?: string;
  username_attr?: string;
  display_name_attr?: string;
  default_role?: UserRole;
}

export interface LdapSyncResult {
  total_found: number;
  created_count: number;
  updated_count: number;
  skipped_count: number;
  message: string;
}

export interface SecuritySettings {
  id: number;
  local_ip_lock_enabled: boolean;
  local_ip_lock_window_minutes: number;
  local_ip_lock_max_attempts: number;
  created_at: string;
  updated_at: string;
}

export interface SecuritySettingsUpdatePayload {
  local_ip_lock_enabled?: boolean;
  local_ip_lock_window_minutes?: number;
  local_ip_lock_max_attempts?: number;
}

export interface OperationLogItem {
  id: number;
  actor_id: number | null;
  actor_username: string;
  action: string;
  entity_type: string;
  entity_id: string;
  detail: string;
  created_at: string;
}

export interface DeletedRecordItem {
  entity_type: string;
  entity_id: number;
  display_name: string;
  detail: string;
  deleted_at: string;
  deleted_by_user_id: number | null;
  deleted_by_username: string;
}

export interface DeletedRecordRestoreResult {
  entity_type: string;
  entity_id: number;
  display_name: string;
  restored_at: string;
}

export type DataAccessModule = "CUSTOMER" | "BILLING";

export interface DataAccessGrantItem {
  id: number;
  grantee_user_id: number;
  grantee_username: string;
  module: DataAccessModule;
  is_active: boolean;
  is_effective: boolean;
  starts_at: string | null;
  ends_at: string | null;
  reason: string;
  granted_by_user_id: number | null;
  granted_by_username: string;
  created_at: string;
  updated_at: string;
}

export interface DataAccessGrantCreatePayload {
  grantee_user_id: number;
  module: DataAccessModule;
  starts_at?: string;
  ends_at?: string;
  reason?: string;
  is_active?: boolean;
}

export interface DataAccessGrantUpdatePayload {
  starts_at?: string;
  ends_at?: string;
  reason?: string;
  is_active?: boolean;
}

export type LeadStatus = "NEW" | "FOLLOWING" | "CONVERTED" | "LOST";
export type LeadTemplateType = "FOLLOWUP" | "CONVERSION" | "REDEVELOP";

export interface LeadItem {
  id: number;
  template_type: LeadTemplateType;
  name: string;
  grade: string;
  contact_name: string;
  phone: string;
  region: string;
  country: string;
  source: string;
  contact_wechat: string;
  fax: string;
  other_contact: string;
  contact_start_date: string | null;
  service_start_text: string;
  company_nature: string;
  service_mode: string;
  main_business: string;
  intro: string;
  fee_standard: string;
  first_billing_period: string;
  reserve_2: string;
  reserve_3: string;
  reserve_4: string;
  related_customer_id: number | null;
  customer_id: number | null;
  status: LeadStatus;
  next_reminder_at: string | null;
  last_followup_date: string | null;
  reminder_value: string;
  last_feedback: string;
  notes: string;
  owner_id: number;
  created_at: string;
  updated_at: string;
}

export interface CustomerListItem {
  id: number;
  customer_code_seq: number | null;
  customer_code_suffix: string;
  customer_code: string;
  name: string;
  contact_name: string;
  phone: string;
  status: string;
  assigned_accountant_id: number;
  accountant_username: string;
  source_customer_id: number | null;
  source_lead_id: number;
  source_template_type: LeadTemplateType;
  source_grade: string;
  source_country: string;
  source_service_start_text: string;
  source_area_display: string;
  source_service_start_display: string;
  source_company_nature: string;
  source_service_mode: string;
  source_contact_wechat: string;
  source_other_contact: string;
  source_main_business: string;
  source_intro: string;
  source_fee_standard: string;
  source_first_billing_period: string;
  source_last_followup_date: string | null;
  source_reminder_value: string;
  created_at: string;
}

export interface CustomerDetail {
  id: number;
  customer_code_seq: number | null;
  customer_code_suffix: string;
  customer_code: string;
  name: string;
  contact_name: string;
  phone: string;
  status: string;
  assigned_accountant_id: number;
  accountant_username: string;
  source_customer_id: number | null;
  source_lead_id: number;
  created_at: string;
  lead: LeadItem;
  followups: Array<{
    id: number;
    lead_id: number;
    followup_at: string;
    feedback: string;
    next_reminder_at: string | null;
    notes: string;
    created_by: number;
    created_by_username: string;
    created_at: string;
  }>;
  timeline: CustomerTimelineEntry[];
}

export type CustomerTimelineSourceType =
  | "LEAD_CREATED"
  | "LEAD_FOLLOWUP"
  | "CONVERTED"
  | "BILLING_RECORD"
  | "BILLING_ACTIVITY"
  | "EXECUTION_LOG"
  | "CUSTOMER_EVENT";

export interface CustomerTimelineEntry {
  occurred_at: string;
  source_type: CustomerTimelineSourceType | string;
  source_id: number | null;
  title: string;
  content: string;
  note: string;
  amount: number | null;
  status: string;
  reminder_at: string | null;
  completed_at: string | null;
  result: string;
  actor_username: string;
  extra: string;
}

export interface CustomerTimelineEventCreatePayload {
  occurred_at: string;
  event_type: string;
  status: string;
  reminder_at: string | null;
  completed_at: string | null;
  content: string;
  note: string;
  result: string;
  amount: number | null;
}

export interface CustomerTimelineEventUpdatePayload {
  occurred_at?: string;
  event_type?: string;
  status?: string;
  reminder_at?: string | null;
  completed_at: string | null;
  content?: string;
  note?: string;
  result?: string;
  amount?: number | null;
}

export interface AddressResourceCompanyItem {
  id: number;
  address_resource_id: number;
  customer_id: number | null;
  customer_name: string;
  company_name: string;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface AddressResource {
  id: number;
  category: string;
  contact_info: string;
  served_companies: string;
  served_company_count: number;
  company_items: AddressResourceCompanyItem[];
  description: string;
  next_action: string;
  notes: string;
  created_at: string;
  updated_at: string;
}

export type CommonLibraryModuleType =
  | "TEMPLATE"
  | "DIRECTORY"
  | "EXTENSION_A"
  | "EXTENSION_B"
  | "EXTENSION_C";

export type CommonLibraryVisibility = "INTERNAL" | "PUBLIC";

export interface CommonLibraryItem {
  id: number;
  module_type: CommonLibraryModuleType;
  visibility: CommonLibraryVisibility;
  category: string;
  title: string;
  content: string;
  phone: string;
  address: string;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: "bearer";
  user?: UserInfo;
}

export interface BillingRecord {
  id: number;
  serial_no: number;
  customer_id: number | null;
  customer_name: string;
  charge_category: string;
  charge_mode: "PERIODIC" | "ONE_TIME";
  amount_basis: "MONTHLY" | "YEARLY" | "ONE_TIME" | "PERIOD_TOTAL";
  summary: string;
  customer_contact_name: string;
  accountant_username: string;
  total_fee: number;
  monthly_fee: number;
  billing_cycle_text: string;
  period_start_month: string;
  period_end_month: string;
  collection_start_date: string;
  due_month: string;
  payment_method: string;
  status: "CLEARED" | "FULL_ARREARS" | "PARTIAL";
  received_amount: number;
  outstanding_amount: number;
  receivable_period_text: string;
  latest_payment_at: string | null;
  latest_payment_amount: number;
  latest_receipt_account: string;
  note: string;
  extra_note: string;
  color_tag: string;
  created_at: string;
  updated_at: string;
}

export interface BillingCreatePayload {
  serial_no: number | null;
  customer_id: number | null;
  charge_category: string;
  charge_mode: "PERIODIC" | "ONE_TIME";
  amount_basis: "MONTHLY" | "YEARLY" | "ONE_TIME" | "PERIOD_TOTAL";
  summary: string;
  total_fee: number;
  monthly_fee: number;
  billing_cycle_text: string;
  period_start_month: string;
  period_end_month: string;
  collection_start_date: string;
  due_month: string;
  payment_method: string;
  status: "CLEARED" | "FULL_ARREARS" | "PARTIAL";
  received_amount: number;
  note: string;
  extra_note: string;
  color_tag: string;
}

export interface BillingActivity {
  id: number;
  billing_record_id: number;
  payment_id: number | null;
  activity_type: "REMINDER" | "PAYMENT";
  occurred_at: string;
  actor_id: number;
  actor_username: string;
  amount: number;
  payment_nature: "" | "MONTHLY" | "YEARLY" | "ONE_OFF";
  receipt_account: string;
  is_prepay: boolean;
  is_settlement: boolean;
  content: string;
  next_followup_at: string | null;
  note: string;
  created_at: string;
}

export type BillingAssignmentRole = "REGISTRATION" | "DELIVERY" | "OTHER";

export interface BillingAssignmentItem {
  id: number;
  billing_record_id: number;
  assignee_user_id: number;
  assignee_username: string;
  assignee_role: UserRole | string;
  assignment_role: BillingAssignmentRole;
  is_active: boolean;
  note: string;
  created_by_user_id: number | null;
  created_at: string;
  updated_at: string;
}

export type BillingExecutionProgressType = "UPDATE" | "MILESTONE" | "BLOCKER" | "DONE";

export interface BillingExecutionLogItem {
  id: number;
  billing_record_id: number;
  occurred_at: string;
  actor_id: number;
  actor_username: string;
  progress_type: BillingExecutionProgressType | string;
  content: string;
  next_action: string;
  due_date: string | null;
  note: string;
  created_at: string;
}

export type BillingPaymentStrategy = "DUE_DATE_ASC" | "SERIAL_ASC" | "AMOUNT_DESC";

export interface BillingPaymentSuggestedAllocation {
  billing_record_id: number;
  serial_no: number;
  summary: string;
  due_month: string;
  outstanding_amount: number;
  suggested_amount: number;
}

export interface BillingPaymentSuggestion {
  customer_id: number;
  amount: number;
  strategy: BillingPaymentStrategy | string;
  outstanding_total: number;
  suggested_total: number;
  remaining_amount: number;
  allocations: BillingPaymentSuggestedAllocation[];
}

export interface BillingPaymentAllocationItem {
  id: number;
  billing_record_id: number;
  allocated_amount: number;
}

export interface BillingPaymentItem {
  id: number;
  payment_no: string;
  customer_id: number;
  customer_name: string;
  customer_contact_name: string;
  accountant_username: string;
  occurred_at: string;
  amount: number;
  strategy: BillingPaymentStrategy | string;
  receipt_account: string;
  summary: string;
  is_prepay: boolean;
  allocated_amount: number;
  unallocated_amount: number;
  allocation_status: "UNALLOCATED" | "PARTIAL" | "ALLOCATED";
  note: string;
  created_by_user_id: number;
  created_at: string;
  allocations: BillingPaymentAllocationItem[];
}

export interface BillingLedgerEntryItem {
  occurred_at: string;
  summary: string;
  receivable_amount: number;
  received_amount: number;
  balance: number;
  source_type: "RECEIVABLE" | "PAYMENT" | string;
  billing_record_id: number | null;
  receipt_account: string;
}

export interface BillingLedgerMonthlySummaryItem {
  month: string;
  receivable_total: number;
  received_total: number;
  net_change: number;
  ending_balance: number;
}

export interface BillingLedgerData {
  customer_id: number;
  customer_name: string;
  date_from: string | null;
  date_to: string | null;
  opening_balance: number;
  receivable_total: number;
  received_total: number;
  balance: number;
  closing_balance: number;
  monthly_summaries: BillingLedgerMonthlySummaryItem[];
  entries: BillingLedgerEntryItem[];
}

export interface BillingCustomerSummaryItem {
  customer_id: number;
  customer_name: string;
  customer_contact_name: string;
  opening_arrears: number;
  period_receivable: number;
  period_received: number;
  ending_outstanding: number;
  overdue_count: number;
  latest_activity_at: string | null;
  latest_activity_content: string;
}

export interface BillingSummaryData {
  total_records: number;
  total_fee: number;
  total_monthly_fee: number;
  payment_method_distribution: Array<{ payment_method: string; count: number }>;
  status_distribution: Array<{ status: string; count: number }>;
  receipt_account_distribution: Array<{ receipt_account: string; payment_count: number; total_amount: number }>;
  summary_date_from: string | null;
  summary_date_to: string | null;
  customer_summaries: BillingCustomerSummaryItem[];
}

export interface BillingReceiptAccountSummaryItem {
  receipt_account: string;
  payment_count: number;
  total_received: number;
  last_received_at: string | null;
}

export interface BillingReceiptAccountEntryItem {
  occurred_at: string;
  receipt_account: string;
  customer_name: string;
  summary: string;
  amount: number;
  debit_amount: number;
  credit_amount: number;
  balance: number;
  actor_username: string;
  payment_id: number | null;
  billing_record_id: number | null;
}

export interface BillingReceiptAccountLedgerData {
  receipt_account: string | null;
  date_from: string | null;
  date_to: string | null;
  opening_debit: number;
  opening_credit: number;
  opening_balance: number;
  total_received: number;
  payment_count: number;
  account_summaries: BillingReceiptAccountSummaryItem[];
  entries: BillingReceiptAccountEntryItem[];
}

export interface CustomerDeleteBlockerItem {
  type: string;
  count: number;
  label: string;
  message: string;
  href: string;
  filters: Record<string, unknown>;
}

export interface CustomerSuggestItem {
  id: number;
  name: string;
  contact_name: string;
  phone: string;
  customer_code: string;
  label: string;
}

export interface CustomerMatterSummaryItem {
  customer_id: number;
  customer_name: string;
  customer_code: string;
  customer_contact_name: string;
  service_start_display: string;
  current_service_summary: string;
  open_item_count: number;
  latest_reminder_at: string | null;
  latest_progress: string;
}

export interface CustomerImportRowResultItem {
  row_number: number;
  company_name: string;
  action: string;
  message: string;
}

export interface CustomerImportResultItem {
  created_count: number;
  updated_count: number;
  skipped_count: number;
  error_count: number;
  rows: CustomerImportRowResultItem[];
}

export type TodoPriority = "HIGH" | "MEDIUM" | "LOW";
export type TodoStatus = "OPEN" | "DONE";

export interface TodoItem {
  id: number;
  title: string;
  description: string;
  priority: TodoPriority;
  due_date: string | null;
  my_day_date: string | null;
  is_in_today: boolean;
  status: TodoStatus;
  assignee_user_id: number;
  assignee_username: string;
  created_by_user_id: number;
  created_by_username: string;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface TodoCreatePayload {
  title: string;
  description?: string;
  priority?: TodoPriority;
  due_date?: string;
  assignee_user_id?: number;
  is_in_today?: boolean;
}

export interface SystemTodoItem {
  id: string;
  module: "LEAD" | "BILLING" | "CUSTOMER";
  priority: TodoPriority;
  title: string;
  description: string;
  due_date: string | null;
  action_path: string;
  action_label: string;
  assignee_user_id: number | null;
  assignee_username: string;
}

export interface DashboardSummary {
  month: string;
  lead_new_count: number;
  lead_following_count: number;
  customer_count: number;
  billing_record_count: number;
  outstanding_amount_total: number;
  manual_open_todo_count: number;
  system_todo_count: number;
}
