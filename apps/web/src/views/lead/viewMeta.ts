import type { LeadItem, LeadStatus, LeadTemplateType } from "../../types";
import { toEpochMillis } from "../../utils/time";

export const statusOptions: Array<{ label: string; value: LeadStatus }> = [
  { label: "新线索", value: "NEW" },
  { label: "跟进中", value: "FOLLOWING" },
  { label: "已转化", value: "CONVERTED" },
  { label: "已丢失", value: "LOST" },
];

export const templateOptions: Array<{ label: string; value: LeadTemplateType }> = [
  { label: "客户跟进模板", value: "FOLLOWUP" },
  { label: "转化模板", value: "CONVERSION" },
  { label: "老客二开模板", value: "REDEVELOP" },
];

const statusLabelMap: Record<LeadStatus, string> = {
  NEW: "新线索",
  FOLLOWING: "跟进中",
  CONVERTED: "已转化",
  LOST: "已丢失",
};

const leadStatusOrder: Record<LeadStatus, number> = {
  FOLLOWING: 0,
  NEW: 1,
  LOST: 2,
  CONVERTED: 3,
};

export const leadGuideStatusItems = [
  { label: "NEW（新线索）", value: "刚录入，尚未有效跟进。" },
  { label: "FOLLOWING（跟进中）", value: "已有跟进记录，正在推进。" },
  { label: "CONVERTED（已转化）", value: "已转客户，进入客户列表与收费流程。" },
  { label: "LOST（已丢失）", value: "当前阶段暂停推进，后续可重新激活。" },
];

export const leadGuideStepItems = [
  { label: "1. 新增线索", value: "录入开发信息，初始状态 NEW。" },
  { label: "2. 跟进", value: "点击“跟进”记录反馈和下次提醒，进入 FOLLOWING。" },
  { label: "3. 转化", value: "点击“转化”，补充客户档案信息并分配会计。" },
  { label: "4. 客户档案", value: "转化后点“客户档案”进入客户模块页面。" },
];

export const leadGuideTemplateItems = [
  { label: "客户跟进模板（FOLLOWUP）", value: "适合常规跟进字段：服务方式、收费标准、国家/类型等。" },
  { label: "转化模板（CONVERSION）", value: "适合转化导向字段：地区、联络时间、备用字段等。" },
  { label: "老客二开模板（REDEVELOP）", value: "用于老客户二次开发，成交后复用原客户档案并直接录入新增费用。" },
  { label: "页面顶部“模板筛选”", value: "仅用于过滤列表显示，不会修改线索本身的数据。" },
];

export function buildLeadDialogSheetHint(templateType: LeadTemplateType): string {
  return templateType === "FOLLOWUP"
    ? "当前按《客户跟进表 > 客户总览》录入，字段更偏客户维护。"
    : "当前按《转化2026 > 客户总览》录入，字段更偏客户开发。";
}

export function statusTagType(status: LeadStatus): string {
  if (status === "CONVERTED") return "success";
  if (status === "FOLLOWING") return "warning";
  if (status === "LOST") return "info";
  return "primary";
}

export function getStatusLabel(status: LeadStatus): string {
  return statusLabelMap[status] ?? status;
}

export function getTemplateLabel(templateType: LeadTemplateType): string {
  if (templateType === "FOLLOWUP") return "客户跟进";
  if (templateType === "REDEVELOP") return "老客二开";
  return "转化";
}

export function getLeadAreaText(lead: LeadItem): string {
  return lead.region || lead.country || "-";
}

export function getLeadStartText(lead: LeadItem): string {
  return lead.contact_start_date || lead.service_start_text || "-";
}

export function getLeadContactText(lead: LeadItem): string {
  return lead.contact_wechat ? `${lead.contact_name} / ${lead.contact_wechat}` : lead.contact_name;
}

export function sortLeadRows(items: LeadItem[]): LeadItem[] {
  return [...items].sort((a, b) => {
    const statusDiff = (leadStatusOrder[a.status] ?? 9) - (leadStatusOrder[b.status] ?? 9);
    if (statusDiff !== 0) {
      return statusDiff;
    }
    const aReminder = toEpochMillis(a.next_reminder_at);
    const bReminder = toEpochMillis(b.next_reminder_at);
    if (!Number.isNaN(aReminder) && !Number.isNaN(bReminder) && aReminder !== bReminder) {
      return aReminder - bReminder;
    }
    if (!Number.isNaN(aReminder) && Number.isNaN(bReminder)) {
      return -1;
    }
    if (Number.isNaN(aReminder) && !Number.isNaN(bReminder)) {
      return 1;
    }
    const aUpdated = toEpochMillis(a.updated_at);
    const bUpdated = toEpochMillis(b.updated_at);
    if (!Number.isNaN(aUpdated) && !Number.isNaN(bUpdated) && aUpdated !== bUpdated) {
      return bUpdated - aUpdated;
    }
    return b.id - a.id;
  });
}
