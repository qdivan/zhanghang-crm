export type BillingFilters = {
  keyword: string;
  customer_id: number | null;
  accountant_id: number | null;
  billing_month: string;
  receipt_account: string;
  contact_name: string;
  payment_method: string;
  status: string;
};

export type BillingActivityForm = {
  activity_type: "REMINDER" | "PAYMENT";
  occurred_at: string;
  amount: number;
  payment_nature: "" | "MONTHLY" | "YEARLY" | "ONE_OFF";
  receipt_account: string;
  is_prepay: boolean;
  is_settlement: boolean;
  content: string;
  next_followup_at: string | null;
  note: string;
};

export type BillingAssignmentForm = {
  assignee_user_id: number | null;
  assignment_role: "REGISTRATION" | "DELIVERY" | "OTHER";
  note: string;
};

export type BillingExecutionForm = {
  occurred_at: string;
  progress_type: "UPDATE" | "MILESTONE" | "BLOCKER" | "DONE";
  content: string;
  next_action: string;
  due_date: string | null;
  note: string;
};

export type BillingSplitPaymentForm = {
  customer_id: number | null;
  occurred_at: string;
  amount: number;
  strategy: "DUE_DATE_ASC" | "SERIAL_ASC" | "AMOUNT_DESC";
  receipt_account: string;
  is_prepay: boolean;
  note: string;
};

export type BillingSplitAllocationRow = {
  billing_record_id: number;
  serial_no: number;
  summary: string;
  due_month: string;
  outstanding_amount: number;
  allocated_amount: number;
};

export type BillingTerminateForm = {
  terminated_at: string;
  reduced_fee: number;
  reason: string;
};

export function createBillingFilters(): BillingFilters {
  return {
    keyword: "",
    customer_id: null,
    accountant_id: null,
    billing_month: "",
    receipt_account: "",
    contact_name: "",
    payment_method: "",
    status: "",
  };
}

export function createBillingAssignmentForm(): BillingAssignmentForm {
  return {
    assignee_user_id: null,
    assignment_role: "DELIVERY",
    note: "",
  };
}

export function createBillingExecutionForm(today: string): BillingExecutionForm {
  return {
    occurred_at: today,
    progress_type: "UPDATE",
    content: "",
    next_action: "",
    due_date: null,
    note: "",
  };
}

export function createBillingActivityForm(today: string): BillingActivityForm {
  return {
    activity_type: "REMINDER",
    occurred_at: today,
    amount: 0,
    payment_nature: "",
    receipt_account: "未指定",
    is_prepay: false,
    is_settlement: false,
    content: "",
    next_followup_at: null,
    note: "",
  };
}

export function createBillingSplitPaymentForm(today: string): BillingSplitPaymentForm {
  return {
    customer_id: null,
    occurred_at: today,
    amount: 0,
    strategy: "DUE_DATE_ASC",
    receipt_account: "未指定",
    is_prepay: false,
    note: "",
  };
}

export function createBillingTerminateForm(today: string): BillingTerminateForm {
  return {
    terminated_at: today,
    reduced_fee: 0,
    reason: "",
  };
}
