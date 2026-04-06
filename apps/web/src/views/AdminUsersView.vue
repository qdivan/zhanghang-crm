<script setup lang="ts">
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute } from "vue-router";

import { apiClient } from "../api/client";
import { isMobileAppPath } from "../mobile/config";
import { useAuthStore } from "../stores/auth";
import { formatDateTimeInBrowserTimeZone } from "../utils/time";
import type {
  DataAccessGrantCreatePayload,
  DataAccessGrantItem,
  DataAccessGrantUpdatePayload,
  DataAccessModule,
  DeletedRecordItem,
  DeletedRecordRestoreResult,
  LdapSettings,
  LdapSettingsUpdatePayload,
  LdapSyncResult,
  ManagedUser,
  OperationLogItem,
  SecuritySettings,
  SecuritySettingsUpdatePayload,
  UserCreatePayload,
  UserRole,
  UserUpdatePayload,
} from "../types";

type StatusFilter = "ALL" | "ACTIVE" | "INACTIVE";
type GrantStatusFilter = "ALL" | "ACTIVE" | "INACTIVE" | "EFFECTIVE";

const auth = useAuthStore();
const route = useRoute();
const activeTab = ref<"users" | "grants" | "security" | "ldap" | "logs" | "recycle">("users");
const isMobileWorkflow = computed(() => isMobileAppPath(route.path));

const loading = ref(false);
const createLoading = ref(false);
const editLoading = ref(false);
const deleteLoadingUserId = ref<number | null>(null);
const rows = ref<ManagedUser[]>([]);
const showCreateDialog = ref(false);
const showEditDialog = ref(false);
const editingOrigin = ref<ManagedUser | null>(null);

const filters = reactive({
  keyword: "",
  role: "",
  status: "ALL" as StatusFilter,
});

const createForm = reactive({
  username: "",
  password: "",
  confirm_password: "",
  role: "ACCOUNTANT" as UserRole,
  manager_user_id: null as number | null,
  is_active: true,
});

const editForm = reactive({
  id: null as number | null,
  username: "",
  role: "ACCOUNTANT" as UserRole,
  manager_user_id: null as number | null,
  is_active: true,
  password: "",
});

const ldapLoading = ref(false);
const ldapSaving = ref(false);
const ldapSyncing = ref(false);
const hasBindPassword = ref(false);
const ldapForm = reactive({
  enabled: false,
  server_url: "",
  bind_dn: "",
  bind_password: "",
  base_dn: "",
  user_base_dn: "",
  user_filter: "(uid=*)",
  username_attr: "uid",
  display_name_attr: "cn",
  default_role: "ACCOUNTANT" as UserRole,
});

const securityLoading = ref(false);
const securitySaving = ref(false);
const securityForm = reactive({
  local_ip_lock_enabled: true,
  local_ip_lock_window_minutes: 5,
  local_ip_lock_max_attempts: 20,
});

const logLoading = ref(false);
const logRows = ref<OperationLogItem[]>([]);
const logFilters = reactive({
  keyword: "",
  action: "",
  entity_type: "",
  audit_scope: "",
  limit: 200,
});

const recycleLoading = ref(false);
const recycleRestoreLoadingKey = ref<string | null>(null);
const deletedRows = ref<DeletedRecordItem[]>([]);
const recycleFilters = reactive({
  keyword: "",
  entity_type: "",
  limit: 200,
});

const grantLoading = ref(false);
const grantCreateLoading = ref(false);
const grantToggleLoadingId = ref<number | null>(null);
const showGrantDialog = ref(false);
const grantRows = ref<DataAccessGrantItem[]>([]);
const grantUserOptions = ref<ManagedUser[]>([]);
const grantFilters = reactive({
  keyword: "",
  module: "",
  status: "ALL" as GrantStatusFilter,
});
const grantForm = reactive({
  grantee_user_id: null as number | null,
  module: "CUSTOMER" as DataAccessModule,
  starts_at: "" as string,
  ends_at: "" as string,
  reason: "",
  is_active: true,
});

const canManageAdminUsers = computed(() => auth.user?.role === "ADMIN");
const editingSelf = computed(() => editForm.id === auth.user?.id);
const managerOptions = computed(() =>
  rows.value.filter((item) => item.role === "MANAGER" && item.is_active),
);
const createNeedsManager = computed(() => createForm.role === "ACCOUNTANT");
const editNeedsManager = computed(() => editForm.role === "ACCOUNTANT");

const roleOptions = computed(() =>
  canManageAdminUsers.value
    ? [
        { label: "老板", value: "OWNER" as UserRole },
        { label: "管理员", value: "ADMIN" as UserRole },
        { label: "部门经理", value: "MANAGER" as UserRole },
        { label: "会计", value: "ACCOUNTANT" as UserRole },
      ]
    : [
        { label: "老板", value: "OWNER" as UserRole },
        { label: "部门经理", value: "MANAGER" as UserRole },
        { label: "会计", value: "ACCOUNTANT" as UserRole },
      ],
);

const visibleRows = computed(() => {
  if (filters.status === "ALL") return rows.value;
  if (filters.status === "ACTIVE") return rows.value.filter((item) => item.is_active);
  return rows.value.filter((item) => !item.is_active);
});

const grantModuleOptions: Array<{ label: string; value: DataAccessModule }> = [
  { label: "客户列表", value: "CUSTOMER" },
  { label: "收费明细", value: "BILLING" },
];

const filteredGrantRows = computed(() => {
  if (grantFilters.status === "ALL") return grantRows.value;
  if (grantFilters.status === "ACTIVE") return grantRows.value.filter((item) => item.is_active);
  if (grantFilters.status === "INACTIVE") return grantRows.value.filter((item) => !item.is_active);
  return grantRows.value.filter((item) => item.is_effective);
});

const panelScopeText = computed(() =>
  canManageAdminUsers.value
    ? "管理员可管理全部本地用户（含管理员），并给会计指定部门经理"
    : "老板可管理除管理员以外的用户，并给会计指定部门经理",
);
const mobileTabItems = [
  { key: "users", label: "用户" },
  { key: "grants", label: "授权" },
  { key: "security", label: "安全" },
  { key: "ldap", label: "LDAP" },
  { key: "logs", label: "日志" },
  { key: "recycle", label: "回收站" },
] as const;
const mobileUserStats = computed(() => [
  { label: "全部", value: rows.value.length },
  { label: "启用", value: rows.value.filter((item) => item.is_active).length },
  { label: "停用", value: rows.value.filter((item) => !item.is_active).length },
]);
const mobileGrantStats = computed(() => [
  { label: "全部", value: grantRows.value.length },
  { label: "生效中", value: grantRows.value.filter((item) => item.is_effective).length },
  { label: "停用", value: grantRows.value.filter((item) => !item.is_active).length },
]);
const deletedEntityOptions = [
  { label: "全部类型", value: "" },
  { label: "线索", value: "LEAD" },
  { label: "客户", value: "CUSTOMER" },
  { label: "收费单", value: "BILLING" },
  { label: "待办", value: "TODO" },
  { label: "挂靠地址", value: "ADDRESS_RESOURCE" },
  { label: "已服务公司", value: "ADDRESS_RESOURCE_COMPANY" },
  { label: "常用资料", value: "COMMON_LIBRARY" },
] as const;

function resolveTab(tab: unknown): "users" | "grants" | "security" | "ldap" | "logs" | "recycle" {
  if (tab === "grants") return "grants";
  if (tab === "security") return "security";
  if (tab === "ldap") return "ldap";
  if (tab === "logs") return "logs";
  if (tab === "recycle") return "recycle";
  return "users";
}

function roleLabel(role: UserRole): string {
  if (role === "OWNER") return "老板";
  if (role === "ADMIN") return "管理员";
  if (role === "MANAGER") return "部门经理";
  return "会计";
}

function roleTagType(role: UserRole): "danger" | "warning" | "primary" | "success" {
  if (role === "OWNER") return "danger";
  if (role === "ADMIN") return "warning";
  if (role === "MANAGER") return "primary";
  return "success";
}

function authSourceLabel(source: string): string {
  if (source === "LDAP") return "LDAP";
  return "本地";
}

function actionLabel(action: string): string {
  const map: Record<string, string> = {
    LOGIN: "登录",
    USER_CREATED: "创建用户",
    USER_UPDATED: "更新用户",
    USER_DELETED: "删除用户",
    SECURITY_SETTINGS_UPDATED: "安全设置更新",
    LOGIN_FAILED: "登录失败",
    LOGIN_IP_BLOCKED: "IP锁定拦截",
    LDAP_SETTINGS_UPDATED: "LDAP设置更新",
    LDAP_SYNC: "LDAP同步",
    LEAD_CREATED: "线索创建",
    LEAD_FOLLOWUP_CREATED: "线索跟进",
    LEAD_CONVERTED: "线索转化",
    LEAD_UNCONVERTED: "撤销转化",
    LEAD_DELETED: "线索删除",
    LEAD_RESTORED: "线索恢复",
    BILLING_RECORD_CREATED: "收费记录创建",
    BILLING_RECORD_UPDATED: "收费记录更新",
    BILLING_RECORD_RENEWED: "收费记录续费",
    BILLING_RECORD_TERMINATED: "收费记录终止",
    BILLING_RECORD_DELETED: "收费记录删除",
    BILLING_RECORD_RESTORED: "收费记录恢复",
    BILLING_ACTIVITY_CREATED: "收费明细日志创建",
    BILLING_PAYMENT_CREATED: "统一收款分摊",
    CUSTOMER_UPDATED: "客户档案更新",
    CUSTOMER_DELETED: "客户删除",
    CUSTOMER_RESTORED: "客户恢复",
    CUSTOMER_TIMELINE_EVENT_CREATED: "客户事项创建",
    CUSTOMER_TIMELINE_EVENT_UPDATED: "客户事项更新",
    CUSTOMER_TIMELINE_TEMPLATE_APPLIED: "客户模板套用",
    ADDRESS_RESOURCE_CREATED: "地址资源创建",
    ADDRESS_RESOURCE_UPDATED: "地址资源更新",
    ADDRESS_RESOURCE_DELETED: "地址资源删除",
    ADDRESS_RESOURCE_RESTORED: "地址资源恢复",
    ADDRESS_RESOURCE_COMPANY_CREATED: "已服务公司创建",
    ADDRESS_RESOURCE_COMPANY_DELETED: "已服务公司删除",
    ADDRESS_RESOURCE_COMPANY_RESTORED: "已服务公司恢复",
    COMMON_LIBRARY_ITEM_CREATED: "常用资料创建",
    COMMON_LIBRARY_ITEM_UPDATED: "常用资料更新",
    COMMON_LIBRARY_ITEM_DELETED: "常用资料删除",
    COMMON_LIBRARY_ITEM_RESTORED: "常用资料恢复",
    DATA_ACCESS_GRANT_CREATED: "数据授权创建",
    DATA_ACCESS_GRANT_UPDATED: "数据授权更新",
    DATA_ACCESS_GRANT_REVOKED: "数据授权停用",
    DATA_ACCESS_GRANT_REACTIVATED: "数据授权启用",
    DATA_ACCESS_GRANT_DELETED: "数据授权删除",
    TODO_CREATED: "待办创建",
    TODO_UPDATED: "待办更新",
    TODO_DELETED: "待办删除",
    TODO_MY_DAY_BULK_ADD: "待办批量加入今日",
    TODO_MY_DAY_CLEARED: "待办今日清空",
  };
  return map[action] || action;
}

function entityTypeLabel(value: string): string {
  const found = deletedEntityOptions.find((item) => item.value === value);
  return found?.label ?? (value || "-");
}

function moduleLabel(module: DataAccessModule): string {
  if (module === "CUSTOMER") return "客户列表";
  return "收费明细";
}

function resolveErrorMessage(error: any, fallback: string): string {
  const detail = error?.response?.data?.detail;
  if (!detail || typeof detail !== "string") {
    return fallback;
  }
  const map: Record<string, string> = {
    "用户名已存在": "用户名已存在",
    "Username already exists": "用户名已存在",
    "用户名不能为空": "用户名不能为空",
    "Username cannot be empty": "用户名不能为空",
    "不能停用当前登录账号": "不能停用当前登录账号",
    "Cannot deactivate yourself": "不能停用当前登录账号",
    "不能删除当前登录账号": "不能删除当前登录账号",
    "Cannot delete yourself": "不能删除当前登录账号",
    "老板不能管理管理员账号": "老板不能管理管理员账号",
    "Owner cannot manage admin users": "老板不能管理管理员账号",
    "直属经理不存在或已停用": "直属经理不存在或已停用",
    "直属经理必须是部门经理": "直属经理必须是部门经理",
    "该部门经理仍有关联下属，不能直接改成其他角色": "该部门经理仍有关联下属，不能直接改成其他角色",
    "该部门经理仍有关联下属，不能直接停用": "该部门经理仍有关联下属，不能直接停用",
    "直属经理不能设置为自己": "直属经理不能设置为自己",
    "用户不存在": "用户不存在",
    "User not found": "用户不存在",
    "LDAP账号请在LDAP中停用或删除": "LDAP账号请在LDAP中停用或删除",
  };
  return map[detail] ?? detail;
}

function resetCreateForm() {
  createForm.username = "";
  createForm.password = "";
  createForm.confirm_password = "";
  createForm.role = "ACCOUNTANT";
  createForm.manager_user_id = null;
  createForm.is_active = true;
}

async function fetchUsers() {
  loading.value = true;
  try {
    const resp = await apiClient.get<ManagedUser[]>("/users", {
      params: {
        keyword: filters.keyword || undefined,
        role: filters.role || undefined,
        include_inactive: true,
      },
    });
    rows.value = resp.data;
  } catch (error) {
    ElMessage.error("加载用户列表失败");
  } finally {
    loading.value = false;
  }
}

function openCreateDialog() {
  resetCreateForm();
  showCreateDialog.value = true;
}

async function submitCreate() {
  const username = createForm.username.trim();
  if (!username) {
    ElMessage.warning("用户名不能为空");
    return;
  }
  if (createForm.password.length < 6) {
    ElMessage.warning("密码至少 6 位");
    return;
  }
  if (createForm.password !== createForm.confirm_password) {
    ElMessage.warning("两次输入的密码不一致");
    return;
  }

  const payload: UserCreatePayload = {
    username,
    password: createForm.password,
    role: createForm.role,
    manager_user_id: createNeedsManager.value ? createForm.manager_user_id : null,
    is_active: createForm.is_active,
  };

  createLoading.value = true;
  try {
    await apiClient.post("/users", payload);
    ElMessage.success("用户已创建");
    showCreateDialog.value = false;
    await Promise.all([fetchUsers(), fetchLogs()]);
  } catch (error: any) {
    ElMessage.error(resolveErrorMessage(error, "创建失败"));
  } finally {
    createLoading.value = false;
  }
}

function openEditDialog(row: ManagedUser) {
  editingOrigin.value = row;
  editForm.id = row.id;
  editForm.username = row.username;
  editForm.role = row.role;
  editForm.manager_user_id = row.manager_user_id;
  editForm.is_active = row.is_active;
  editForm.password = "";
  showEditDialog.value = true;
}

async function submitEdit() {
  if (!editForm.id || !editingOrigin.value) return;
  const username = editForm.username.trim();
  if (!username) {
    ElMessage.warning("用户名不能为空");
    return;
  }
  if (editForm.password && editForm.password.length < 6) {
    ElMessage.warning("新密码至少 6 位");
    return;
  }

  const payload: UserUpdatePayload = {};
  if (username !== editingOrigin.value.username) {
    payload.username = username;
  }
  if (!editingSelf.value && editForm.role !== editingOrigin.value.role) {
    payload.role = editForm.role;
  }
  if (
    !editingSelf.value &&
    editForm.manager_user_id !== editingOrigin.value.manager_user_id
  ) {
    payload.manager_user_id = editNeedsManager.value ? editForm.manager_user_id : null;
  } else if (!editingSelf.value && !editNeedsManager.value && editingOrigin.value.manager_user_id !== null) {
    payload.manager_user_id = null;
  }
  if (!editingSelf.value && editForm.is_active !== editingOrigin.value.is_active) {
    payload.is_active = editForm.is_active;
  }
  if (editForm.password.trim()) {
    payload.password = editForm.password.trim();
  }

  if (Object.keys(payload).length === 0) {
    ElMessage.info("没有变更内容");
    return;
  }

  editLoading.value = true;
  try {
    await apiClient.patch(`/users/${editForm.id}`, payload);
    ElMessage.success("用户已更新");
    showEditDialog.value = false;
    await Promise.all([fetchUsers(), fetchLogs()]);
  } catch (error: any) {
    ElMessage.error(resolveErrorMessage(error, "更新失败"));
  } finally {
    editLoading.value = false;
  }
}

async function removeUser(row: ManagedUser) {
  if (row.id === auth.user?.id) {
    ElMessage.warning("不能删除当前登录账号");
    return;
  }
  try {
    await ElMessageBox.confirm(
      `确认删除账号「${row.username}」吗？删除后无法登录，且仅无关联业务数据的账号可删除。`,
      "删除确认",
      {
        type: "warning",
        confirmButtonText: "确认删除",
        cancelButtonText: "取消",
      },
    );
  } catch {
    return;
  }

  deleteLoadingUserId.value = row.id;
  try {
    await apiClient.delete(`/users/${row.id}`);
    ElMessage.success("账号已删除");
    await Promise.all([fetchUsers(), fetchLogs()]);
  } catch (error: any) {
    ElMessage.error(resolveErrorMessage(error, "删除失败"));
  } finally {
    deleteLoadingUserId.value = null;
  }
}

async function fetchLdapSettings() {
  ldapLoading.value = true;
  try {
    const resp = await apiClient.get<LdapSettings>("/admin/ldap/settings");
    const data = resp.data;
    ldapForm.enabled = data.enabled;
    ldapForm.server_url = data.server_url;
    ldapForm.bind_dn = data.bind_dn;
    ldapForm.bind_password = "";
    ldapForm.base_dn = data.base_dn;
    ldapForm.user_base_dn = data.user_base_dn;
    ldapForm.user_filter = data.user_filter;
    ldapForm.username_attr = data.username_attr;
    ldapForm.display_name_attr = data.display_name_attr;
    ldapForm.default_role = data.default_role;
    hasBindPassword.value = data.has_bind_password;
  } catch (error) {
    ElMessage.error("加载 LDAP 设置失败");
  } finally {
    ldapLoading.value = false;
  }
}

async function fetchSecuritySettings() {
  securityLoading.value = true;
  try {
    const resp = await apiClient.get<SecuritySettings>("/admin/security-settings");
    const data = resp.data;
    securityForm.local_ip_lock_enabled = data.local_ip_lock_enabled;
    securityForm.local_ip_lock_window_minutes = data.local_ip_lock_window_minutes;
    securityForm.local_ip_lock_max_attempts = data.local_ip_lock_max_attempts;
  } catch (error) {
    ElMessage.error("加载安全设置失败");
  } finally {
    securityLoading.value = false;
  }
}

async function saveSecuritySettings() {
  if (securityForm.local_ip_lock_window_minutes < 1 || securityForm.local_ip_lock_max_attempts < 1) {
    ElMessage.warning("锁定时长和失败次数都必须大于 0");
    return;
  }

  const payload: SecuritySettingsUpdatePayload = {
    local_ip_lock_enabled: securityForm.local_ip_lock_enabled,
    local_ip_lock_window_minutes: Number(securityForm.local_ip_lock_window_minutes),
    local_ip_lock_max_attempts: Number(securityForm.local_ip_lock_max_attempts),
  };

  securitySaving.value = true;
  try {
    await apiClient.put("/admin/security-settings", payload);
    ElMessage.success("安全设置已保存");
    await Promise.all([fetchSecuritySettings(), fetchLogs()]);
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "保存安全设置失败");
  } finally {
    securitySaving.value = false;
  }
}

async function saveLdapSettings() {
  const payload: LdapSettingsUpdatePayload = {
    enabled: ldapForm.enabled,
    server_url: ldapForm.server_url.trim(),
    bind_dn: ldapForm.bind_dn.trim(),
    base_dn: ldapForm.base_dn.trim(),
    user_base_dn: ldapForm.user_base_dn.trim(),
    user_filter: ldapForm.user_filter.trim(),
    username_attr: ldapForm.username_attr.trim(),
    display_name_attr: ldapForm.display_name_attr.trim(),
    default_role: ldapForm.default_role,
  };
  if (ldapForm.bind_password.trim()) {
    payload.bind_password = ldapForm.bind_password.trim();
  }

  ldapSaving.value = true;
  try {
    await apiClient.put("/admin/ldap/settings", payload);
    ElMessage.success("LDAP 设置已保存");
    ldapForm.bind_password = "";
    await Promise.all([fetchLdapSettings(), fetchLogs()]);
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "保存 LDAP 设置失败");
  } finally {
    ldapSaving.value = false;
  }
}

async function syncLdapUsers() {
  ldapSyncing.value = true;
  try {
    const resp = await apiClient.post<LdapSyncResult>("/admin/ldap/sync", {});
    const result = resp.data;
    ElMessage.success(
      `LDAP 同步完成：发现 ${result.total_found}，新建 ${result.created_count}，更新 ${result.updated_count}，跳过 ${result.skipped_count}`,
    );
    await Promise.all([fetchUsers(), fetchLogs()]);
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "LDAP 同步失败");
  } finally {
    ldapSyncing.value = false;
  }
}

async function fetchLogs() {
  logLoading.value = true;
  try {
    const resp = await apiClient.get<OperationLogItem[]>("/admin/operation-logs", {
      params: {
        keyword: logFilters.keyword || undefined,
        action: logFilters.action || undefined,
        entity_type: logFilters.entity_type || undefined,
        audit_scope: logFilters.audit_scope || undefined,
        limit: logFilters.limit,
      },
    });
    logRows.value = resp.data;
  } catch (error) {
    ElMessage.error("加载操作日志失败");
  } finally {
    logLoading.value = false;
  }
}

async function fetchDeletedRecords() {
  recycleLoading.value = true;
  try {
    const resp = await apiClient.get<DeletedRecordItem[]>("/admin/deleted-records", {
      params: {
        keyword: recycleFilters.keyword || undefined,
        entity_type: recycleFilters.entity_type || undefined,
        limit: recycleFilters.limit,
      },
    });
    deletedRows.value = resp.data;
  } catch (error) {
    ElMessage.error("加载回收站失败");
  } finally {
    recycleLoading.value = false;
  }
}

async function restoreDeletedRecord(row: DeletedRecordItem) {
  const restoreKey = `${row.entity_type}:${row.entity_id}`;
  try {
    await ElMessageBox.confirm(
      `确认恢复「${row.display_name}」吗？恢复后会重新出现在业务页面里。`,
      "恢复确认",
      {
        type: "warning",
        confirmButtonText: "确认恢复",
        cancelButtonText: "取消",
      },
    );
  } catch {
    return;
  }

  recycleRestoreLoadingKey.value = restoreKey;
  try {
    const resp = await apiClient.post<DeletedRecordRestoreResult>(
      `/admin/deleted-records/${row.entity_type}/${row.entity_id}/restore`,
      {},
    );
    ElMessage.success(`已恢复：${resp.data.display_name}`);
    await Promise.all([fetchDeletedRecords(), fetchLogs()]);
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "恢复失败");
  } finally {
    recycleRestoreLoadingKey.value = null;
  }
}

function resetGrantForm() {
  grantForm.grantee_user_id = null;
  grantForm.module = "CUSTOMER";
  grantForm.starts_at = "";
  grantForm.ends_at = "";
  grantForm.reason = "";
  grantForm.is_active = true;
}

async function fetchGrantUsers() {
  try {
    const resp = await apiClient.get<ManagedUser[]>("/users", {
      params: {
        role: "ACCOUNTANT",
        include_inactive: true,
      },
    });
    grantUserOptions.value = resp.data;
  } catch (error) {
    ElMessage.error("加载可授权会计失败");
  }
}

async function fetchDataAccessGrants() {
  grantLoading.value = true;
  try {
    const resp = await apiClient.get<DataAccessGrantItem[]>("/admin/data-access-grants", {
      params: {
        keyword: grantFilters.keyword || undefined,
        module: grantFilters.module || undefined,
        include_inactive: true,
      },
    });
    grantRows.value = resp.data;
  } catch (error) {
    ElMessage.error("加载数据授权失败");
  } finally {
    grantLoading.value = false;
  }
}

function openGrantDialog() {
  resetGrantForm();
  showGrantDialog.value = true;
}

async function submitGrantCreate() {
  if (!grantForm.grantee_user_id) {
    ElMessage.warning("请选择被授权会计");
    return;
  }
  if (grantForm.starts_at && grantForm.ends_at && grantForm.ends_at <= grantForm.starts_at) {
    ElMessage.warning("失效时间必须晚于生效时间");
    return;
  }

  const payload: DataAccessGrantCreatePayload = {
    grantee_user_id: grantForm.grantee_user_id,
    module: grantForm.module,
    reason: grantForm.reason.trim() || undefined,
    is_active: grantForm.is_active,
  };
  if (grantForm.starts_at) payload.starts_at = grantForm.starts_at;
  if (grantForm.ends_at) payload.ends_at = grantForm.ends_at;

  grantCreateLoading.value = true;
  try {
    await apiClient.post("/admin/data-access-grants", payload);
    ElMessage.success("临时只读授权已创建");
    showGrantDialog.value = false;
    await Promise.all([fetchDataAccessGrants(), fetchLogs()]);
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "创建数据授权失败");
  } finally {
    grantCreateLoading.value = false;
  }
}

async function toggleGrantActive(row: DataAccessGrantItem, isActive: boolean) {
  const payload: DataAccessGrantUpdatePayload = { is_active: isActive };
  grantToggleLoadingId.value = row.id;
  try {
    await apiClient.patch(`/admin/data-access-grants/${row.id}`, payload);
    ElMessage.success(isActive ? "授权已启用" : "授权已停用");
    await Promise.all([fetchDataAccessGrants(), fetchLogs()]);
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "更新授权状态失败");
  } finally {
    grantToggleLoadingId.value = null;
  }
}

onMounted(async () => {
  await Promise.all([
    fetchUsers(),
    fetchGrantUsers(),
    fetchDataAccessGrants(),
    fetchSecuritySettings(),
    fetchLdapSettings(),
    fetchLogs(),
    fetchDeletedRecords(),
  ]);
});

watch(
  () => route.query.tab,
  (value) => {
    activeTab.value = resolveTab(value);
  },
  { immediate: true },
);
</script>

<template>
  <template v-if="isMobileWorkflow">
    <section class="mobile-page admin-mobile-page">
      <section class="mobile-shell-panel">
        <div class="admin-mobile-hero">
          <div class="admin-mobile-title-block">
            <div class="admin-mobile-eyebrow">{{ canManageAdminUsers ? "管理员视图" : "老板视图" }}</div>
            <div class="admin-mobile-title">用户与权限</div>
            <div class="admin-mobile-copy">{{ panelScopeText }}</div>
          </div>
          <el-tag class="mobile-count-tag" size="small" effect="plain">{{ roleOptions.length }} 类角色</el-tag>
        </div>
        <div class="admin-mobile-tab-row">
          <button
            v-for="item in mobileTabItems"
            :key="item.key"
            type="button"
            class="admin-mobile-tab"
            :class="{ active: activeTab === item.key }"
            @click="activeTab = item.key"
          >
            {{ item.label }}
          </button>
        </div>
      </section>

      <template v-if="activeTab === 'users'">
        <section class="mobile-shell-panel">
          <div class="mobile-toolbar">
            <div class="mobile-toolbar-main">
              <div class="admin-mobile-section-title">用户管理</div>
              <div class="admin-mobile-section-copy">账号、角色和直属经理都在这里维护。</div>
            </div>
            <div class="mobile-toolbar-actions">
              <el-tag class="mobile-count-tag" size="small" effect="plain">{{ visibleRows.length }} 人</el-tag>
              <el-button class="mobile-row-primary-button" type="primary" @click="openCreateDialog">新增用户</el-button>
            </div>
          </div>
          <div class="admin-mobile-filter-grid">
            <el-input
              v-model="filters.keyword"
              placeholder="用户名 / 角色"
              clearable
              @keyup.enter="fetchUsers"
            />
            <el-select v-model="filters.role" placeholder="全部角色" clearable>
              <el-option v-for="item in roleOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
            <el-select v-model="filters.status" placeholder="全部状态">
              <el-option label="全部" value="ALL" />
              <el-option label="启用" value="ACTIVE" />
              <el-option label="停用" value="INACTIVE" />
            </el-select>
          </div>
          <div class="admin-mobile-filter-actions">
            <el-button class="mobile-row-secondary-button" plain @click="fetchUsers">查询</el-button>
          </div>
          <div class="mobile-chip-row admin-mobile-stat-row">
            <span v-for="item in mobileUserStats" :key="item.label" class="mobile-chip">{{ item.label }} {{ item.value }}</span>
          </div>
        </section>

        <section class="mobile-shell-panel">
          <div v-if="loading && !visibleRows.length" class="mobile-empty-block">
            <div class="mobile-empty-kicker">用户管理</div>
            <div class="mobile-empty-title">正在加载账号</div>
            <div class="mobile-empty-copy">用户、角色和直属经理会在这里显示。</div>
          </div>
          <div v-else-if="!visibleRows.length" class="mobile-empty-block">
            <div class="mobile-empty-kicker">用户管理</div>
            <div class="mobile-empty-title">没有符合条件的账号</div>
            <div class="mobile-empty-copy">换一个关键词或状态，再查一次。</div>
          </div>
          <div v-else class="mobile-record-list">
            <article v-for="row in visibleRows" :key="row.id" class="mobile-record-card admin-mobile-card">
              <div class="mobile-record-head">
                <div class="mobile-record-main">
                  <div class="mobile-record-title">{{ row.username }}</div>
                  <div class="mobile-record-subtitle">{{ roleLabel(row.role) }} · {{ authSourceLabel(row.auth_source) }}</div>
                </div>
                <el-tag class="mobile-status-tag" size="small" effect="plain" :type="row.is_active ? 'success' : 'info'">
                  {{ row.is_active ? "启用" : "停用" }}
                </el-tag>
              </div>
              <div class="mobile-record-metrics">
                <div class="mobile-metric">
                  <div class="mobile-metric-label">直属经理</div>
                  <div class="mobile-metric-value">{{ row.manager_username || "-" }}</div>
                </div>
                <div class="mobile-metric">
                  <div class="mobile-metric-label">最近登录</div>
                  <div class="mobile-metric-value">{{ formatDateTimeInBrowserTimeZone(row.last_login_at) }}</div>
                </div>
                <div class="mobile-metric">
                  <div class="mobile-metric-label">创建时间</div>
                  <div class="mobile-metric-value">{{ formatDateTimeInBrowserTimeZone(row.created_at) }}</div>
                </div>
                <div class="mobile-metric">
                  <div class="mobile-metric-label">账号来源</div>
                  <div class="mobile-metric-value">{{ authSourceLabel(row.auth_source) }}</div>
                </div>
              </div>
              <div class="mobile-action-main">
                <el-button class="mobile-row-primary-button" size="small" type="primary" @click="openEditDialog(row)">编辑</el-button>
                <el-button
                  class="mobile-row-secondary-button"
                  size="small"
                  plain
                  type="danger"
                  :disabled="row.id === auth.user?.id"
                  :loading="deleteLoadingUserId === row.id"
                  @click="removeUser(row)"
                >
                  删除
                </el-button>
              </div>
            </article>
          </div>
        </section>
      </template>

      <template v-else-if="activeTab === 'grants'">
        <section class="mobile-shell-panel">
          <div class="mobile-toolbar">
            <div class="mobile-toolbar-main">
              <div class="admin-mobile-section-title">数据授权</div>
              <div class="admin-mobile-section-copy">临时只读授权只放开查看，不放开写入。</div>
            </div>
            <div class="mobile-toolbar-actions">
              <el-tag class="mobile-count-tag" size="small" effect="plain">{{ filteredGrantRows.length }} 条</el-tag>
              <el-button class="mobile-row-primary-button" type="primary" @click="openGrantDialog">新增授权</el-button>
            </div>
          </div>
          <div class="admin-mobile-filter-grid">
            <el-input
              v-model="grantFilters.keyword"
              placeholder="会计 / 授权原因"
              clearable
              @keyup.enter="fetchDataAccessGrants"
            />
            <el-select v-model="grantFilters.module" placeholder="全部模块" clearable>
              <el-option v-for="item in grantModuleOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
            <el-select v-model="grantFilters.status" placeholder="全部状态">
              <el-option label="全部" value="ALL" />
              <el-option label="生效中" value="EFFECTIVE" />
              <el-option label="启用" value="ACTIVE" />
              <el-option label="停用" value="INACTIVE" />
            </el-select>
          </div>
          <div class="admin-mobile-filter-actions">
            <el-button class="mobile-row-secondary-button" plain @click="fetchDataAccessGrants">查询</el-button>
          </div>
          <div class="mobile-chip-row admin-mobile-stat-row">
            <span v-for="item in mobileGrantStats" :key="item.label" class="mobile-chip">{{ item.label }} {{ item.value }}</span>
          </div>
        </section>

        <section class="mobile-shell-panel">
          <div v-if="grantLoading && !filteredGrantRows.length" class="mobile-empty-block">
            <div class="mobile-empty-kicker">数据授权</div>
            <div class="mobile-empty-title">正在加载授权</div>
            <div class="mobile-empty-copy">会计、模块和生效状态会在这里显示。</div>
          </div>
          <div v-else-if="!filteredGrantRows.length" class="mobile-empty-block">
            <div class="mobile-empty-kicker">数据授权</div>
            <div class="mobile-empty-title">没有符合条件的授权</div>
            <div class="mobile-empty-copy">可以换一个筛选条件，或直接新增授权。</div>
          </div>
          <div v-else class="mobile-record-list">
            <article v-for="row in filteredGrantRows" :key="row.id" class="mobile-record-card admin-mobile-card">
              <div class="mobile-record-head">
                <div class="mobile-record-main">
                  <div class="mobile-record-title">{{ row.grantee_username }}</div>
                  <div class="mobile-record-subtitle">{{ moduleLabel(row.module) }} · {{ row.reason || "未填写授权原因" }}</div>
                </div>
                <div class="admin-mobile-badge-stack">
                  <el-tag class="mobile-status-tag" size="small" effect="plain" :type="row.is_effective ? 'success' : 'warning'">
                    {{ row.is_effective ? "生效中" : "未生效" }}
                  </el-tag>
                  <el-tag class="mobile-status-tag" size="small" effect="plain" :type="row.is_active ? 'success' : 'info'">
                    {{ row.is_active ? "启用" : "停用" }}
                  </el-tag>
                </div>
              </div>
              <div class="mobile-record-metrics">
                <div class="mobile-metric">
                  <div class="mobile-metric-label">生效时间</div>
                  <div class="mobile-metric-value">{{ formatDateTimeInBrowserTimeZone(row.starts_at) }}</div>
                </div>
                <div class="mobile-metric">
                  <div class="mobile-metric-label">失效时间</div>
                  <div class="mobile-metric-value">{{ formatDateTimeInBrowserTimeZone(row.ends_at) }}</div>
                </div>
                <div class="mobile-metric">
                  <div class="mobile-metric-label">授权人</div>
                  <div class="mobile-metric-value">{{ row.granted_by_username || "-" }}</div>
                </div>
                <div class="mobile-metric">
                  <div class="mobile-metric-label">创建时间</div>
                  <div class="mobile-metric-value">{{ formatDateTimeInBrowserTimeZone(row.created_at) }}</div>
                </div>
              </div>
              <div class="mobile-action-main">
                <el-button
                  class="mobile-row-secondary-button"
                  size="small"
                  plain
                  :type="row.is_active ? 'danger' : 'primary'"
                  :loading="grantToggleLoadingId === row.id"
                  @click="toggleGrantActive(row, !row.is_active)"
                >
                  {{ row.is_active ? "停用" : "启用" }}
                </el-button>
              </div>
            </article>
          </div>
        </section>
      </template>

      <template v-else-if="activeTab === 'security'">
        <section class="mobile-shell-panel" v-loading="securityLoading">
          <div class="admin-mobile-section-title">安全设置</div>
          <div class="admin-mobile-section-copy">本地账号 IP 锁定只作用于本地登录，不影响 LDAP。</div>
          <div class="mobile-chip-row admin-mobile-stat-row">
            <span class="mobile-chip">窗口 {{ securityForm.local_ip_lock_window_minutes }} 分钟</span>
            <span class="mobile-chip">阈值 {{ securityForm.local_ip_lock_max_attempts }} 次</span>
          </div>
          <el-form label-position="top" class="admin-mobile-form">
            <el-form-item label="启用本地账号 IP 锁定">
              <el-switch v-model="securityForm.local_ip_lock_enabled" active-text="启用" inactive-text="停用" />
            </el-form-item>
            <el-form-item label="统计窗口（分钟）">
              <el-input-number
                v-model="securityForm.local_ip_lock_window_minutes"
                :min="1"
                :max="1440"
                :controls="false"
                style="width: 100%"
              />
            </el-form-item>
            <el-form-item label="失败阈值（次）">
              <el-input-number
                v-model="securityForm.local_ip_lock_max_attempts"
                :min="1"
                :max="1000"
                :controls="false"
                style="width: 100%"
              />
            </el-form-item>
          </el-form>
          <div class="admin-mobile-note">默认规则是 5 分钟内同一 IP 连续输错 20 次后锁定。</div>
          <div class="admin-mobile-filter-actions">
            <el-button class="mobile-row-primary-button" type="primary" :loading="securitySaving" @click="saveSecuritySettings">保存安全设置</el-button>
          </div>
        </section>
      </template>

      <template v-else-if="activeTab === 'ldap'">
        <section class="mobile-shell-panel" v-loading="ldapLoading">
          <div class="admin-mobile-section-title">LDAP 设置</div>
          <div class="admin-mobile-section-copy">保存后可同步 LDAP 账号，默认角色按这里的配置落地。</div>
          <div class="mobile-chip-row admin-mobile-stat-row">
            <span class="mobile-chip">{{ hasBindPassword ? "已保存绑定密码" : "未保存绑定密码" }}</span>
          </div>
          <el-form label-position="top" class="admin-mobile-form">
            <el-form-item label="启用 LDAP">
              <el-switch v-model="ldapForm.enabled" active-text="启用" inactive-text="停用" />
            </el-form-item>
            <el-form-item label="默认角色">
              <el-select v-model="ldapForm.default_role">
                <el-option v-for="item in roleOptions" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
            </el-form-item>
            <el-form-item label="服务器地址">
              <el-input v-model="ldapForm.server_url" placeholder="如 ldaps://ldap.example.com:636" />
            </el-form-item>
            <el-form-item label="Base DN">
              <el-input v-model="ldapForm.base_dn" placeholder="如 dc=example,dc=com" />
            </el-form-item>
            <el-form-item label="Bind DN">
              <el-input v-model="ldapForm.bind_dn" placeholder="如 uid=admin,cn=users,dc=example,dc=com" />
            </el-form-item>
            <el-form-item label="Bind Password（留空不修改）">
              <el-input v-model="ldapForm.bind_password" type="password" show-password />
            </el-form-item>
            <el-form-item label="用户搜索基准 DN">
              <el-input v-model="ldapForm.user_base_dn" placeholder="如 cn=users,dc=example,dc=com" />
            </el-form-item>
            <el-form-item label="用户过滤器">
              <el-input v-model="ldapForm.user_filter" placeholder="如 (uid=*)" />
            </el-form-item>
            <el-form-item label="用户名属性">
              <el-input v-model="ldapForm.username_attr" placeholder="如 uid" />
            </el-form-item>
            <el-form-item label="显示名属性">
              <el-input v-model="ldapForm.display_name_attr" placeholder="如 cn" />
            </el-form-item>
          </el-form>
          <div class="mobile-action-main">
            <el-button class="mobile-row-primary-button" type="primary" :loading="ldapSaving" @click="saveLdapSettings">保存设置</el-button>
            <el-button class="mobile-row-secondary-button" plain :loading="ldapSyncing" @click="syncLdapUsers">立即同步</el-button>
          </div>
        </section>
      </template>

      <template v-else-if="activeTab === 'logs'">
        <section class="mobile-shell-panel">
          <div class="mobile-toolbar">
            <div class="mobile-toolbar-main">
              <div class="admin-mobile-section-title">操作日志</div>
              <div class="admin-mobile-section-copy">按关键词、动作、对象类型和删除/恢复范围筛后台审计。</div>
            </div>
            <div class="mobile-toolbar-actions">
              <el-tag class="mobile-count-tag" size="small" effect="plain">{{ logRows.length }} 条</el-tag>
            </div>
          </div>
          <div class="admin-mobile-filter-grid">
            <el-input v-model="logFilters.keyword" placeholder="操作描述 / 对象" clearable @keyup.enter="fetchLogs" />
            <el-input v-model="logFilters.action" placeholder="如 USER_UPDATED" clearable />
            <el-input v-model="logFilters.entity_type" placeholder="如 USER / LDAP" clearable />
            <el-select v-model="logFilters.audit_scope" placeholder="全部审计">
              <el-option label="全部审计" value="" />
              <el-option label="仅删除" value="DELETE" />
              <el-option label="仅恢复" value="RESTORE" />
            </el-select>
            <el-input-number v-model="logFilters.limit" :min="1" :max="500" :controls="false" />
          </div>
          <div class="admin-mobile-filter-actions">
            <el-button class="mobile-row-secondary-button" plain @click="fetchLogs">查询</el-button>
          </div>
        </section>

        <section class="mobile-shell-panel">
          <div v-if="logLoading && !logRows.length" class="mobile-empty-block">
            <div class="mobile-empty-kicker">操作日志</div>
            <div class="mobile-empty-title">正在加载日志</div>
            <div class="mobile-empty-copy">后台操作、对象和时间会在这里显示。</div>
          </div>
          <div v-else-if="!logRows.length" class="mobile-empty-block">
            <div class="mobile-empty-kicker">操作日志</div>
            <div class="mobile-empty-title">没有匹配的日志</div>
            <div class="mobile-empty-copy">换一个关键词或对象类型，再查一次。</div>
          </div>
          <div v-else class="mobile-record-list">
            <article v-for="row in logRows" :key="row.id" class="mobile-record-card admin-mobile-card">
              <div class="mobile-record-head">
                <div class="mobile-record-main">
                  <div class="mobile-record-title">{{ actionLabel(row.action) }}</div>
                  <div class="mobile-record-subtitle">{{ formatDateTimeInBrowserTimeZone(row.created_at) }}</div>
                </div>
                <el-tag class="mobile-status-tag" size="small" effect="plain">{{ row.entity_type || "-" }}</el-tag>
              </div>
              <div class="mobile-record-note">{{ row.detail || "-" }}</div>
              <div class="mobile-record-metrics">
                <div class="mobile-metric">
                  <div class="mobile-metric-label">操作人</div>
                  <div class="mobile-metric-value">{{ row.actor_username || "-" }}</div>
                </div>
                <div class="mobile-metric">
                  <div class="mobile-metric-label">对象ID</div>
                  <div class="mobile-metric-value">{{ row.entity_id || "-" }}</div>
                </div>
              </div>
            </article>
          </div>
        </section>
      </template>

      <template v-else>
        <section class="mobile-shell-panel">
          <div class="mobile-toolbar">
            <div class="mobile-toolbar-main">
              <div class="admin-mobile-section-title">回收站</div>
              <div class="admin-mobile-section-copy">已删除业务数据会先留在这里，确认后可以恢复。</div>
            </div>
            <div class="mobile-toolbar-actions">
              <el-tag class="mobile-count-tag" size="small" effect="plain">{{ deletedRows.length }} 条</el-tag>
            </div>
          </div>
          <div class="admin-mobile-filter-grid">
            <el-input v-model="recycleFilters.keyword" placeholder="名称 / 备注" clearable @keyup.enter="fetchDeletedRecords" />
            <el-select v-model="recycleFilters.entity_type" placeholder="全部类型">
              <el-option v-for="item in deletedEntityOptions" :key="item.value || 'all'" :label="item.label" :value="item.value" />
            </el-select>
            <el-input-number v-model="recycleFilters.limit" :min="1" :max="500" :controls="false" />
          </div>
          <div class="admin-mobile-filter-actions">
            <el-button class="mobile-row-secondary-button" plain @click="fetchDeletedRecords">查询</el-button>
          </div>
        </section>

        <section class="mobile-shell-panel">
          <div v-if="recycleLoading && !deletedRows.length" class="mobile-empty-block">
            <div class="mobile-empty-kicker">回收站</div>
            <div class="mobile-empty-title">正在加载已删除数据</div>
            <div class="mobile-empty-copy">线索、客户、收费单和资料删除后会先留在这里。</div>
          </div>
          <div v-else-if="!deletedRows.length" class="mobile-empty-block">
            <div class="mobile-empty-kicker">回收站</div>
            <div class="mobile-empty-title">当前没有可恢复的数据</div>
            <div class="mobile-empty-copy">如果刚删了记录，可以刷新查询看看。</div>
          </div>
          <div v-else class="mobile-record-list">
            <article v-for="row in deletedRows" :key="`${row.entity_type}-${row.entity_id}`" class="mobile-record-card admin-mobile-card">
              <div class="mobile-record-head">
                <div class="mobile-record-main">
                  <div class="mobile-record-title">{{ row.display_name }}</div>
                  <div class="mobile-record-subtitle">{{ entityTypeLabel(row.entity_type) }} · {{ formatDateTimeInBrowserTimeZone(row.deleted_at) }}</div>
                </div>
                <el-tag class="mobile-status-tag" size="small" effect="plain">{{ row.deleted_by_username || "-" }}</el-tag>
              </div>
              <div class="mobile-record-note">{{ row.detail || "-" }}</div>
              <div class="mobile-action-main">
                <el-button
                  class="mobile-row-secondary-button"
                  size="small"
                  plain
                  type="primary"
                  :loading="recycleRestoreLoadingKey === `${row.entity_type}:${row.entity_id}`"
                  @click="restoreDeletedRecord(row)"
                >
                  恢复
                </el-button>
              </div>
            </article>
          </div>
        </section>
      </template>
    </section>
  </template>

  <el-space v-else direction="vertical" fill :size="12">
    <el-alert :title="panelScopeText" type="info" :closable="false" />

    <el-tabs v-model="activeTab">
      <el-tab-pane label="用户管理" name="users">
        <el-space direction="vertical" fill :size="12">
          <el-card shadow="never">
            <el-form inline @submit.prevent="fetchUsers" class="admin-filter-form">
              <el-form-item label="关键词">
                <el-input
                  v-model="filters.keyword"
                  placeholder="用户名/角色"
                  clearable
                  @keyup.enter="fetchUsers"
                />
              </el-form-item>
              <el-form-item label="角色">
                <el-select v-model="filters.role" placeholder="全部" clearable>
                  <el-option v-for="item in roleOptions" :key="item.value" :label="item.label" :value="item.value" />
                </el-select>
              </el-form-item>
              <el-form-item label="状态">
                <el-select v-model="filters.status" placeholder="全部">
                  <el-option label="全部" value="ALL" />
                  <el-option label="启用" value="ACTIVE" />
                  <el-option label="停用" value="INACTIVE" />
                </el-select>
              </el-form-item>
              <el-form-item>
                <el-button @click="fetchUsers">查询</el-button>
                <el-button type="primary" @click="openCreateDialog">新增用户</el-button>
              </el-form-item>
            </el-form>
          </el-card>

          <el-card shadow="never">
            <template #header>
              <div class="head">
                <span>用户管理</span>
                <el-tag type="success" effect="plain">{{ visibleRows.length }} 人</el-tag>
              </div>
            </template>
            <el-table v-loading="loading" :data="visibleRows" stripe border>
              <el-table-column prop="id" label="ID" width="80" />
              <el-table-column prop="username" label="账号" min-width="160" />
              <el-table-column
                label="账号来源"
                width="100"
                class-name="mobile-hide"
                label-class-name="mobile-hide"
              >
                <template #default="{ row }">{{ authSourceLabel(row.auth_source) }}</template>
              </el-table-column>
              <el-table-column
                label="角色"
                width="120"
                class-name="mobile-hide"
                label-class-name="mobile-hide"
              >
                <template #default="{ row }">
                  <el-tag :type="roleTagType(row.role)" size="small">{{ roleLabel(row.role) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column
                label="直属经理"
                min-width="120"
                class-name="mobile-hide"
                label-class-name="mobile-hide"
              >
                <template #default="{ row }">{{ row.manager_username || "-" }}</template>
              </el-table-column>
              <el-table-column
                label="状态"
                width="100"
                class-name="mobile-hide"
                label-class-name="mobile-hide"
              >
                <template #default="{ row }">
                  <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
                    {{ row.is_active ? "启用" : "停用" }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column
                label="最近登录"
                min-width="170"
                class-name="mobile-hide"
                label-class-name="mobile-hide"
              >
                <template #default="{ row }">{{ formatDateTimeInBrowserTimeZone(row.last_login_at) }}</template>
              </el-table-column>
              <el-table-column
                label="创建时间"
                min-width="170"
                class-name="mobile-hide"
                label-class-name="mobile-hide"
              >
                <template #default="{ row }">{{ formatDateTimeInBrowserTimeZone(row.created_at) }}</template>
              </el-table-column>
              <el-table-column label="操作" width="120">
                <template #default="{ row }">
                  <el-button link type="primary" @click="openEditDialog(row)">编辑</el-button>
                  <el-button
                    link
                    type="danger"
                    :disabled="row.id === auth.user?.id"
                    :loading="deleteLoadingUserId === row.id"
                    @click="removeUser(row)"
                  >
                    删除
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-space>
      </el-tab-pane>

      <el-tab-pane label="数据授权" name="grants">
        <el-space direction="vertical" fill :size="12">
          <el-card shadow="never">
            <el-form inline @submit.prevent="fetchDataAccessGrants" class="admin-filter-form">
              <el-form-item label="关键词">
                <el-input
                  v-model="grantFilters.keyword"
                  placeholder="会计/授权原因"
                  clearable
                  @keyup.enter="fetchDataAccessGrants"
                />
              </el-form-item>
              <el-form-item label="模块">
                <el-select v-model="grantFilters.module" placeholder="全部" clearable>
                  <el-option
                    v-for="item in grantModuleOptions"
                    :key="item.value"
                    :label="item.label"
                    :value="item.value"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="状态">
                <el-select v-model="grantFilters.status" placeholder="全部">
                  <el-option label="全部" value="ALL" />
                  <el-option label="生效中" value="EFFECTIVE" />
                  <el-option label="启用" value="ACTIVE" />
                  <el-option label="停用" value="INACTIVE" />
                </el-select>
              </el-form-item>
              <el-form-item>
                <el-button @click="fetchDataAccessGrants">查询</el-button>
                <el-button type="primary" @click="openGrantDialog">新增授权</el-button>
              </el-form-item>
            </el-form>
          </el-card>

          <el-card shadow="never">
            <template #header>
              <div class="head">
                <span>临时只读授权</span>
                <el-tag type="warning" effect="plain">{{ filteredGrantRows.length }} 条</el-tag>
              </div>
            </template>
            <el-table v-loading="grantLoading" :data="filteredGrantRows" stripe border>
              <el-table-column prop="id" label="ID" width="80" />
              <el-table-column prop="grantee_username" label="被授权会计" width="130" />
              <el-table-column label="模块" width="110">
                <template #default="{ row }">{{ moduleLabel(row.module) }}</template>
              </el-table-column>
              <el-table-column label="状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
                    {{ row.is_active ? "启用" : "停用" }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="当前生效" width="100">
                <template #default="{ row }">
                  <el-tag :type="row.is_effective ? 'success' : 'warning'" size="small">
                    {{ row.is_effective ? "是" : "否" }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="生效时间" min-width="165" class-name="mobile-hide" label-class-name="mobile-hide">
                <template #default="{ row }">{{ formatDateTimeInBrowserTimeZone(row.starts_at) }}</template>
              </el-table-column>
              <el-table-column label="失效时间" min-width="165" class-name="mobile-hide" label-class-name="mobile-hide">
                <template #default="{ row }">{{ formatDateTimeInBrowserTimeZone(row.ends_at) }}</template>
              </el-table-column>
              <el-table-column
                prop="reason"
                label="授权原因"
                min-width="180"
                show-overflow-tooltip
                class-name="mobile-hide"
                label-class-name="mobile-hide"
              />
              <el-table-column
                prop="granted_by_username"
                label="授权人"
                width="110"
                class-name="mobile-hide"
                label-class-name="mobile-hide"
              />
              <el-table-column
                label="创建时间"
                min-width="165"
                class-name="mobile-hide"
                label-class-name="mobile-hide"
              >
                <template #default="{ row }">{{ formatDateTimeInBrowserTimeZone(row.created_at) }}</template>
              </el-table-column>
              <el-table-column label="操作" width="110">
                <template #default="{ row }">
                  <el-button
                    link
                    :type="row.is_active ? 'danger' : 'primary'"
                    :loading="grantToggleLoadingId === row.id"
                    @click="toggleGrantActive(row, !row.is_active)"
                  >
                    {{ row.is_active ? "停用" : "启用" }}
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-space>
      </el-tab-pane>

      <el-tab-pane label="安全设置" name="security">
        <el-card v-loading="securityLoading" shadow="never">
          <el-form label-position="top">
            <el-row :gutter="12">
              <el-col :xs="24" :md="8">
                <el-form-item label="启用本地账号 IP 锁定">
                  <el-switch v-model="securityForm.local_ip_lock_enabled" active-text="启用" inactive-text="停用" />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :md="8">
                <el-form-item label="统计窗口（分钟）">
                  <el-input-number
                    v-model="securityForm.local_ip_lock_window_minutes"
                    :min="1"
                    :max="1440"
                    :controls="false"
                    style="width: 100%"
                  />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :md="8">
                <el-form-item label="失败阈值（次）">
                  <el-input-number
                    v-model="securityForm.local_ip_lock_max_attempts"
                    :min="1"
                    :max="1000"
                    :controls="false"
                    style="width: 100%"
                  />
                </el-form-item>
              </el-col>
            </el-row>

            <el-alert
              title="仅作用于本地账号登录。默认规则是 5 分钟内同一 IP 连续输错 20 次后锁定该 IP。"
              type="info"
              :closable="false"
              style="margin-bottom: 12px"
            />

            <el-space wrap>
              <el-button type="primary" :loading="securitySaving" @click="saveSecuritySettings">保存安全设置</el-button>
              <el-tag type="warning" effect="plain">
                当前规则：{{ securityForm.local_ip_lock_window_minutes }} 分钟 / {{ securityForm.local_ip_lock_max_attempts }} 次
              </el-tag>
            </el-space>
          </el-form>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="LDAP 设置" name="ldap">
        <el-card v-loading="ldapLoading" shadow="never">
          <el-form label-position="top">
            <el-row :gutter="12">
              <el-col :xs="24" :md="8">
                <el-form-item label="启用 LDAP">
                  <el-switch v-model="ldapForm.enabled" active-text="启用" inactive-text="停用" />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :md="8">
                <el-form-item label="默认角色">
                  <el-select v-model="ldapForm.default_role">
                    <el-option v-for="item in roleOptions" :key="item.value" :label="item.label" :value="item.value" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :xs="24" :md="8">
                <el-form-item label="同步状态">
                  <el-tag type="info">{{ hasBindPassword ? "已保存绑定密码" : "未保存绑定密码" }}</el-tag>
                </el-form-item>
              </el-col>
            </el-row>

            <el-row :gutter="12">
              <el-col :xs="24" :md="12">
                <el-form-item label="服务器地址">
                  <el-input v-model="ldapForm.server_url" placeholder="如 ldap://192.168.1.10:389 或 ldaps://..." />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :md="12">
                <el-form-item label="Base DN">
                  <el-input v-model="ldapForm.base_dn" placeholder="如 dc=example,dc=com" />
                </el-form-item>
              </el-col>
            </el-row>

            <el-row :gutter="12">
              <el-col :xs="24" :md="12">
                <el-form-item label="Bind DN">
                  <el-input v-model="ldapForm.bind_dn" placeholder="如 uid=admin,cn=users,dc=example,dc=com" />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :md="12">
                <el-form-item label="Bind Password（留空不修改）">
                  <el-input v-model="ldapForm.bind_password" type="password" show-password />
                </el-form-item>
              </el-col>
            </el-row>

            <el-row :gutter="12">
              <el-col :xs="24" :md="12">
                <el-form-item label="用户搜索基准 DN">
                  <el-input v-model="ldapForm.user_base_dn" placeholder="如 cn=users,dc=example,dc=com" />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :md="12">
                <el-form-item label="用户过滤器">
                  <el-input v-model="ldapForm.user_filter" placeholder="如 (uid=*)" />
                </el-form-item>
              </el-col>
            </el-row>

            <el-row :gutter="12">
              <el-col :xs="24" :md="12">
                <el-form-item label="用户名属性">
                  <el-input v-model="ldapForm.username_attr" placeholder="如 uid" />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :md="12">
                <el-form-item label="显示名属性">
                  <el-input v-model="ldapForm.display_name_attr" placeholder="如 cn" />
                </el-form-item>
              </el-col>
            </el-row>

            <el-space>
              <el-button type="primary" :loading="ldapSaving" @click="saveLdapSettings">保存设置</el-button>
              <el-button :loading="ldapSyncing" @click="syncLdapUsers">立即同步 LDAP 账号</el-button>
            </el-space>
          </el-form>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="操作日志" name="logs">
        <el-space direction="vertical" fill :size="12">
          <el-card shadow="never">
            <el-form inline @submit.prevent="fetchLogs" class="admin-filter-form">
              <el-form-item label="关键词">
                <el-input
                  v-model="logFilters.keyword"
                  placeholder="操作描述/对象"
                  clearable
                  @keyup.enter="fetchLogs"
                />
              </el-form-item>
              <el-form-item label="动作">
                <el-input v-model="logFilters.action" placeholder="如 USER_UPDATED" clearable />
              </el-form-item>
              <el-form-item label="对象类型">
                <el-input v-model="logFilters.entity_type" placeholder="如 USER/LDAP" clearable />
              </el-form-item>
              <el-form-item label="审计范围">
                <el-select v-model="logFilters.audit_scope" placeholder="全部" clearable>
                  <el-option label="仅删除" value="DELETE" />
                  <el-option label="仅恢复" value="RESTORE" />
                </el-select>
              </el-form-item>
              <el-form-item label="条数">
                <el-input-number v-model="logFilters.limit" :min="1" :max="500" :controls="false" />
              </el-form-item>
              <el-form-item>
                <el-button @click="fetchLogs">查询</el-button>
              </el-form-item>
            </el-form>
          </el-card>

          <el-card shadow="never">
            <template #header>
              <div class="head">
                <span>操作日志</span>
                <el-tag type="info" effect="plain">{{ logRows.length }} 条</el-tag>
              </div>
            </template>
            <el-table v-loading="logLoading" :data="logRows" stripe border>
              <el-table-column
                prop="id"
                label="ID"
                width="80"
                class-name="mobile-hide"
                label-class-name="mobile-hide"
              />
              <el-table-column label="时间" min-width="160">
                <template #default="{ row }">{{ formatDateTimeInBrowserTimeZone(row.created_at) }}</template>
              </el-table-column>
              <el-table-column
                prop="actor_username"
                label="操作人"
                width="120"
                class-name="mobile-hide"
                label-class-name="mobile-hide"
              />
              <el-table-column
                label="动作"
                min-width="140"
                show-overflow-tooltip
                class-name="mobile-hide"
                label-class-name="mobile-hide"
              >
                <template #default="{ row }">{{ actionLabel(row.action) }}</template>
              </el-table-column>
              <el-table-column
                prop="entity_type"
                label="对象类型"
                width="120"
                class-name="mobile-hide"
                label-class-name="mobile-hide"
              />
              <el-table-column
                prop="entity_id"
                label="对象ID"
                width="110"
                class-name="mobile-hide"
                label-class-name="mobile-hide"
              />
              <el-table-column prop="detail" label="详情" min-width="180" show-overflow-tooltip />
            </el-table>
          </el-card>
        </el-space>
      </el-tab-pane>

      <el-tab-pane label="回收站" name="recycle">
        <el-space direction="vertical" fill :size="12">
          <el-card shadow="never">
            <el-form inline @submit.prevent="fetchDeletedRecords" class="admin-filter-form">
              <el-form-item label="关键词">
                <el-input
                  v-model="recycleFilters.keyword"
                  placeholder="名称/备注"
                  clearable
                  @keyup.enter="fetchDeletedRecords"
                />
              </el-form-item>
              <el-form-item label="类型">
                <el-select v-model="recycleFilters.entity_type" placeholder="全部类型">
                  <el-option v-for="item in deletedEntityOptions" :key="item.value || 'all'" :label="item.label" :value="item.value" />
                </el-select>
              </el-form-item>
              <el-form-item label="条数">
                <el-input-number v-model="recycleFilters.limit" :min="1" :max="500" :controls="false" />
              </el-form-item>
              <el-form-item>
                <el-button @click="fetchDeletedRecords">查询</el-button>
              </el-form-item>
            </el-form>
          </el-card>

          <el-card shadow="never">
            <template #header>
              <div class="head">
                <span>回收站</span>
                <el-tag type="warning" effect="plain">{{ deletedRows.length }} 条</el-tag>
              </div>
            </template>
            <el-table v-loading="recycleLoading" :data="deletedRows" stripe border>
              <el-table-column label="删除时间" min-width="160">
                <template #default="{ row }">{{ formatDateTimeInBrowserTimeZone(row.deleted_at) }}</template>
              </el-table-column>
              <el-table-column label="类型" width="150">
                <template #default="{ row }">{{ entityTypeLabel(row.entity_type) }}</template>
              </el-table-column>
              <el-table-column prop="display_name" label="名称" min-width="220" show-overflow-tooltip />
              <el-table-column
                prop="detail"
                label="说明"
                min-width="180"
                show-overflow-tooltip
                class-name="mobile-hide"
                label-class-name="mobile-hide"
              />
              <el-table-column
                prop="deleted_by_username"
                label="删除人"
                width="120"
                class-name="mobile-hide"
                label-class-name="mobile-hide"
              />
              <el-table-column label="操作" width="100">
                <template #default="{ row }">
                  <el-button
                    link
                    type="primary"
                    :loading="recycleRestoreLoadingKey === `${row.entity_type}:${row.entity_id}`"
                    @click="restoreDeletedRecord(row)"
                  >
                    恢复
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-space>
      </el-tab-pane>
    </el-tabs>
  </el-space>

  <el-dialog v-model="showCreateDialog" title="新增本地用户" width="520px">
    <el-form label-position="top">
      <el-form-item label="用户名">
        <el-input v-model="createForm.username" placeholder="如 accountant5" />
      </el-form-item>
      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="密码">
            <el-input v-model="createForm.password" type="password" show-password />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="确认密码">
            <el-input v-model="createForm.confirm_password" type="password" show-password />
          </el-form-item>
        </el-col>
      </el-row>
      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="角色">
            <el-select v-model="createForm.role">
              <el-option v-for="item in roleOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="状态">
            <el-switch v-model="createForm.is_active" active-text="启用" inactive-text="停用" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item v-if="createNeedsManager" label="直属经理">
        <el-select v-model="createForm.manager_user_id" clearable placeholder="可选，选择部门经理">
          <el-option
            v-for="item in managerOptions"
            :key="item.id"
            :label="item.username"
            :value="item.id"
          />
        </el-select>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="showCreateDialog = false">取消</el-button>
      <el-button type="primary" :loading="createLoading" @click="submitCreate">创建</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="showEditDialog" title="编辑用户" width="520px">
    <el-form label-position="top">
      <el-form-item label="用户名">
        <el-input v-model="editForm.username" />
      </el-form-item>
      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="角色">
            <el-select v-model="editForm.role" :disabled="editingSelf">
              <el-option v-for="item in roleOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="状态">
            <el-switch
              v-model="editForm.is_active"
              active-text="启用"
              inactive-text="停用"
              :disabled="editingSelf"
            />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item v-if="editNeedsManager" label="直属经理">
        <el-select v-model="editForm.manager_user_id" clearable placeholder="可选，选择部门经理" :disabled="editingSelf">
          <el-option
            v-for="item in managerOptions"
            :key="item.id"
            :label="item.username"
            :value="item.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="新密码（留空表示不修改）">
        <el-input v-model="editForm.password" type="password" show-password />
      </el-form-item>
      <el-alert v-if="editingSelf" title="当前登录账号不能改自身角色或停用自身账号" type="warning" :closable="false" />
    </el-form>
    <template #footer>
      <el-button @click="showEditDialog = false">取消</el-button>
      <el-button type="primary" :loading="editLoading" @click="submitEdit">保存</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="showGrantDialog" title="新增临时只读授权" width="560px">
    <el-form label-position="top">
      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="被授权会计">
            <el-select v-model="grantForm.grantee_user_id" placeholder="请选择会计">
              <el-option
                v-for="item in grantUserOptions"
                :key="item.id"
                :label="`${item.username}${item.is_active ? '' : '（停用）'}`"
                :value="item.id"
              />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="授权模块">
            <el-select v-model="grantForm.module">
              <el-option
                v-for="item in grantModuleOptions"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>

      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="生效时间（可留空=立即）">
            <el-date-picker
              v-model="grantForm.starts_at"
              type="datetime"
              value-format="YYYY-MM-DDTHH:mm:ss"
              format="YYYY-MM-DD HH:mm:ss"
              placeholder="立即生效"
              clearable
            />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="失效时间（可留空）">
            <el-date-picker
              v-model="grantForm.ends_at"
              type="datetime"
              value-format="YYYY-MM-DDTHH:mm:ss"
              format="YYYY-MM-DD HH:mm:ss"
              placeholder="不设置失效时间"
              clearable
            />
          </el-form-item>
        </el-col>
      </el-row>

      <el-form-item label="授权原因">
        <el-input v-model="grantForm.reason" type="textarea" :rows="3" placeholder="如：月底工资核算临时查看" />
      </el-form-item>

      <el-form-item label="启用状态">
        <el-switch v-model="grantForm.is_active" active-text="启用" inactive-text="停用" />
      </el-form-item>

      <el-alert
        title="此授权仅放开查看权限，不放开编辑/催收/收款写入权限。"
        type="info"
        :closable="false"
      />
    </el-form>
    <template #footer>
      <el-button @click="showGrantDialog = false">取消</el-button>
      <el-button type="primary" :loading="grantCreateLoading" @click="submitGrantCreate">创建授权</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.admin-mobile-page {
  gap: 12px;
}

.admin-mobile-hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.admin-mobile-title-block {
  min-width: 0;
  flex: 1;
}

.admin-mobile-eyebrow {
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--app-text-muted);
}

.admin-mobile-title,
.admin-mobile-section-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--app-text-primary);
}

.admin-mobile-copy,
.admin-mobile-section-copy,
.admin-mobile-note {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--app-text-muted);
}

.admin-mobile-tab-row {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 6px;
  margin-top: 14px;
}

.admin-mobile-tab {
  border: 1px solid var(--app-border-soft);
  background: var(--app-surface-muted);
  padding: 9px 8px;
  font-size: 12px;
  color: var(--app-text-muted);
}

.admin-mobile-tab.active {
  border-color: rgba(77, 128, 150, 0.26);
  background: rgba(77, 128, 150, 0.12);
  color: var(--app-accent-strong);
}

.admin-mobile-filter-grid {
  display: grid;
  gap: 8px;
  margin-top: 12px;
}

.admin-mobile-filter-actions,
.admin-mobile-stat-row {
  margin-top: 10px;
}

.admin-mobile-card {
  gap: 10px;
}

.admin-mobile-badge-stack {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
}

.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

@media (max-width: 768px) {
  .admin-mobile-hero {
    flex-direction: column;
  }

  .admin-mobile-tab-row {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .admin-filter-form {
    display: flex;
    flex-wrap: wrap;
  }
}

@media (max-width: 420px) {
  .admin-mobile-tab-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
