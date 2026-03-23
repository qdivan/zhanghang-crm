import { apiClient } from "../../api/client";

export type LeadCustomerSearchItem = {
  id: number;
  name: string;
  contact_name: string;
  phone: string;
  assigned_accountant_id: number;
  accountant_username: string;
};

function normalizeCustomerName(value: string) {
  return value.trim().replace(/\s+/g, " ").toLowerCase();
}

export async function searchLeadCustomers(keyword: string): Promise<LeadCustomerSearchItem[]> {
  const q = keyword.trim();
  if (!q) {
    return [];
  }

  const resp = await apiClient.get<LeadCustomerSearchItem[]>("/customers", {
    params: { keyword: q },
  });
  return resp.data.slice(0, 20);
}

export async function findExactLeadCustomer(name: string): Promise<LeadCustomerSearchItem | null> {
  const normalized = normalizeCustomerName(name);
  if (!normalized) {
    return null;
  }

  const items = await searchLeadCustomers(name);
  return items.find((item) => normalizeCustomerName(item.name) === normalized) ?? null;
}
