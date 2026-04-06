import type { LeadTemplateType } from "../../types";
import { todayInBrowserTimeZone } from "../../utils/time";
import { buildNextReminderDate, getDefaultReminderValueForGrade } from "./viewMeta";

export type LeadCreateForm = {
  template_type: LeadTemplateType;
  name: string;
  related_customer_id: number | null;
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
  reminder_value: string;
  next_reminder_at: string | null;
  notes: string;
};

export type LeadFollowupForm = {
  lead_id: number | null;
  followup_at: string;
  grade: string;
  reminder_value: string;
  feedback: string;
  notes: string;
  next_reminder_at: string | null;
};

export type LeadRedevelopForm = {
  customer_id: number | null;
  source: string;
  notes: string;
  next_reminder_at: string | null;
};

export type LeadConvertForm = {
  lead_id: number | null;
  accountant_id: number | null;
  customer_name: string;
  customer_contact_name: string;
  customer_phone: string;
  conversion_mode: "NEW_CUSTOMER_LINKED" | "REUSE_CUSTOMER";
};

export type LeadFilters = {
  keyword: string;
  status: string;
  template_type: string;
};

export function createLeadFilters(): LeadFilters {
  return {
    keyword: "",
    status: "",
    template_type: "",
  };
}

export function createLeadForm(): LeadCreateForm {
  const today = todayInBrowserTimeZone();
  const defaultGrade = "意向中";
  const defaultReminderValue = getDefaultReminderValueForGrade(defaultGrade);
  return {
    template_type: "CONVERSION",
    name: "",
    related_customer_id: null,
    grade: defaultGrade,
    contact_name: "",
    phone: "",
    region: "",
    country: "",
    source: "Sally直播",
    contact_wechat: "",
    fax: "",
    other_contact: "",
    contact_start_date: today,
    service_start_text: "",
    company_nature: "",
    service_mode: "",
    main_business: "",
    intro: "",
    fee_standard: "",
    first_billing_period: "",
    reserve_2: "",
    reserve_3: "",
    reserve_4: "",
    reminder_value: defaultReminderValue,
    next_reminder_at: buildNextReminderDate(today, defaultReminderValue),
    notes: "",
  };
}

export function createLeadFollowupForm(today: string): LeadFollowupForm {
  return {
    lead_id: null,
    followup_at: today,
    grade: "",
    reminder_value: "",
    feedback: "",
    notes: "",
    next_reminder_at: null,
  };
}

export function createLeadRedevelopForm(): LeadRedevelopForm {
  return {
    customer_id: null,
    source: "老客户二次开发",
    notes: "",
    next_reminder_at: null,
  };
}

export function createLeadConvertForm(): LeadConvertForm {
  return {
    lead_id: null,
    accountant_id: null,
    customer_name: "",
    customer_contact_name: "",
    customer_phone: "",
    conversion_mode: "NEW_CUSTOMER_LINKED",
  };
}
