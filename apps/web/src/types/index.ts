export type UserRole = "OWNER" | "ADMIN" | "ACCOUNTANT";

export interface UserInfo {
  id: number;
  username: string;
  auth_source: "LOCAL" | "LDAP" | string;
  ldap_dn: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  last_login_at: string | null;
}

export interface ManagedUser extends UserInfo {}

export interface UserCreatePayload {
  username: string;
  password: string;
  role: UserRole;
  is_active: boolean;
}

export interface UserUpdatePayload {
  username?: string;
  password?: string;
  role?: UserRole;
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

export type LeadStatus = "NEW" | "FOLLOWING" | "CONVERTED" | "LOST";
export type LeadTemplateType = "FOLLOWUP" | "CONVERSION";

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
  name: string;
  contact_name: string;
  phone: string;
  status: string;
  assigned_accountant_id: number;
  accountant_username: string;
  source_lead_id: number;
  source_template_type: LeadTemplateType;
  source_grade: string;
  source_last_followup_date: string | null;
  source_reminder_value: string;
  created_at: string;
}

export interface CustomerDetail {
  id: number;
  name: string;
  contact_name: string;
  phone: string;
  status: string;
  assigned_accountant_id: number;
  accountant_username: string;
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
    created_at: string;
  }>;
}

export interface AddressResource {
  id: number;
  category: string;
  contact_info: string;
  description: string;
  next_action: string;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: "bearer";
}

export interface BillingRecord {
  id: number;
  serial_no: number;
  customer_id: number | null;
  customer_name: string;
  accountant_username: string;
  total_fee: number;
  monthly_fee: number;
  billing_cycle_text: string;
  due_month: string;
  payment_method: string;
  status: "CLEARED" | "FULL_ARREARS" | "PARTIAL";
  received_amount: number;
  outstanding_amount: number;
  note: string;
  extra_note: string;
  color_tag: string;
  created_at: string;
  updated_at: string;
}

export interface BillingActivity {
  id: number;
  billing_record_id: number;
  activity_type: "REMINDER" | "PAYMENT";
  occurred_at: string;
  actor_id: number;
  amount: number;
  payment_nature: "" | "MONTHLY" | "YEARLY" | "ONE_OFF";
  is_prepay: boolean;
  is_settlement: boolean;
  content: string;
  next_followup_at: string | null;
  note: string;
  created_at: string;
}
