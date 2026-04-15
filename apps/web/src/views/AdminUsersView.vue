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
  SsoBindingItem,
  SsoConflictItem,
  SsoManualBindingPayload,
  SsoUnboundUserItem,
  UserCreatePayload,
  UserRole,
  UserUpdatePayload,
} from "../types";

type StatusFilter = "ALL" | "ACTIVE" | "INACTIVE";
type GrantStatusFilter = "ALL" | "ACTIVE" | "INACTIVE" | "EFFECTIVE";
type SsoConflictStatusFilter = "PENDING" | "RESOLVED" | "ALL";

const auth = useAuthStore();
const route = useRoute();
const activeTab = ref<"users" | "grants" | "sso" | "security" | "ldap" | "logs" | "recycle">("users");
const isMobileWorkflow = computed(() => isMobileAppPath(route.path));

const loading = ref(false);
const createLoading = ref(false);
const editLoading = ref(false);
const deleteLoadingUserId = ref<number | null>(null);
const deleteLoadingGrantId = ref<number | null>(null);
const rows = ref<ManagedUser[]>([]);
const allUserOptions = ref<ManagedUser[]>([]);
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
const showAdvancedLogFilters = ref(false);
const logFilters = reactive({
  keyword: "",
  action: "",
  entity_type: "",
  audit_scope: "",
  limit: 200,
});

const recycleLoading = ref(false);
const recycleRestoreLoadingKey = ref<string | null>(null);
const recycleBulkRestoring = ref(false);
const deletedRows = ref<DeletedRecordItem[]>([]);
const recycleSelectedRows = ref<DeletedRecordItem[]>([]);
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

const ssoBindingLoading = ref(false);
const ssoConflictLoading = ref(false);
const ssoUnboundLoading = ref(false);
const ssoDeleteLoadingId = ref<number | null>(null);
const ssoManualBindingLoading = ref(false);
const ssoResolveLoadingId = ref<number | null>(null);
const showSsoManualDialog = ref(false);
const showSsoResolveDialog = ref(false);
const ssoBindings = ref<SsoBindingItem[]>([]);
const ssoConflicts = ref<SsoConflictItem[]>([]);
const ssoUnboundUsers = ref<SsoUnboundUserItem[]>([]);
const ssoConflictOrigin = ref<SsoConflictItem | null>(null);
const ssoFilters = reactive({
  bindingKeyword: "",
  conflictKeyword: "",
  conflictStatus: "PENDING" as SsoConflictStatusFilter,
  includeInactiveUsers: false,
});
const ssoManualForm = reactive({
  user_id: null as number | null,
  issuer: "",
  subject: "",
  preferred_username: "",
  email: "",
  email_verified: false,
  display_name: "",
  raw_claims_json: "",
});
const ssoResolveForm = reactive({
  conflict_id: null as number | null,
  user_id: null as number | null,
});

const canManageAdminUsers = computed(() => auth.user?.role === "ADMIN");
const editingSelf = computed(() => editForm.id === auth.user?.id);
const managerOptions = computed(() =>
  rows.value.filter((item) => item.role === "MANAGER" && item.is_active),
);
const bindableUserOptions = computed(() => allUserOptions.value.filter((item) => item.is_active));
const ssoPendingConflictCount = computed(() => ssoConflicts.value.filter((item) => item.status === "PENDING").length);
const ssoResolvedConflictCount = computed(() => ssoConflicts.value.filter((item) => item.status === "RESOLVED").length);
const ssoResolveCandidateOptions = computed(() => {
  if (!ssoConflictOrigin.value?.candidate_user_ids.length) {
    return bindableUserOptions.value;
  }
  const candidateSet = new Set(ssoConflictOrigin.value.candidate_user_ids);
  const preferred = bindableUserOptions.value.filter((item) => candidateSet.has(item.id));
  return preferred.length ? preferred : bindableUserOptions.value;
});
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
  { key: "sso", label: "SSO" },
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
  { label: "用户账号", value: "USER" },
  { label: "线索", value: "LEAD" },
  { label: "客户", value: "CUSTOMER" },
  { label: "收费单", value: "BILLING" },
  { label: "待办", value: "TODO" },
  { label: "数据授权", value: "DATA_ACCESS_GRANT" },
  { label: "挂靠地址", value: "ADDRESS_RESOURCE" },
  { label: "已服务公司", value: "ADDRESS_RESOURCE_COMPANY" },
  { label: "常用资料", value: "COMMON_LIBRARY" },
] as const;

const recycleQuickFilters = computed(() => {
  const counts = deletedRows.value.reduce<Record<string, number>>((acc, item) => {
    acc[item.entity_type] = (acc[item.entity_type] || 0) + 1;
    return acc;
  }, {});
  return [
    { label: "全部", value: "", count: deletedRows.value.length },
    ...deletedEntityOptions
      .filter((item) => item.value)
      .map((item) => ({
        label: item.label,
        value: item.value,
        count: counts[item.value] || 0,
      })),
  ];
});

const activeAdvancedLogFilterCount = computed(() => {
  let count = 0;
  if (logFilters.action.trim()) count += 1;
  if (logFilters.entity_type.trim()) count += 1;
  if (logFilters.audit_scope) count += 1;
  if (logFilters.limit !== 200) count += 1;
  return count;
});

function resolveTab(tab: unknown): "users" | "grants" | "sso" | "security" | "ldap" | "logs" | "recycle" {
  if (tab === "grants") return "grants";
  if (tab === "sso") return "sso";
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
  if (source === "SSO") return "SSO";
  return "本地";
}

function actionLabel(action: string): string {
  const map: Record<string, string> = {
    LOGIN: "登录",
    USER_CREATED: "创建用户",
    USER_UPDATED: "更新用户",
    USER_DELETED: "删除用户",
    USER_RESTORED: "恢复用户",
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
    DATA_ACCESS_GRANT_RESTORED: "数据授权恢复",
    SSO_LOGIN: "SSO 登录",
    SSO_BINDING_CREATED: "SSO 绑定创建",
    SSO_BINDING_REMOVED: "SSO 绑定移除",
    SSO_CONFLICT_RESOLVED: "SSO 冲突处理",
    TODO_CREATED: "待办创建",
    TODO_UPDATED: "待办更新",
    TODO_DELETED: "待办删除",
    TODO_RESTORED: "待办恢复",
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
    "确认名称不匹配": "确认名称不匹配",
    "老板不能管理管理员账号": "老板不能管理管理员账号",
    "Owner cannot manage admin users": "老板不能管理管理员账号",
    "直属经理不存在或已停用": "直属经理不存在或已停用",
    "直属经理必须是部门经理": "直属经理必须是部门经理",
    "该部门经理仍有关联下属，不能直接改成其他角色": "该部门经理仍有关联下属，不能直接改成其他角色",
    "该部门经理仍有关联下属，不能直接停用": "该部门经理仍有关联下属，不能直接停用",
    "直属经理不能设置为自己": "直属经理不能设置为自己",
    "用户不存在": "用户不存在",
    "User not found": "用户不存在",
    "该用户名已在回收站，可先恢复": "该用户名已在回收站，可先恢复",
    "请先恢复被授权账号": "请先恢复被授权账号",
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

async function fetchAllUserOptions() {
  try {
    const resp = await apiClient.get<ManagedUser[]>("/users", {
      params: {
        include_inactive: true,
      },
    });
    allUserOptions.value = resp.data;
  } catch (error) {
    ElMessage.error("加载账号选项失败");
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
    await Promise.all([fetchUsers(), fetchAllUserOptions(), fetchLogs()]);
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
    await Promise.all([fetchUsers(), fetchAllUserOptions(), fetchLogs()]);
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
  const expectedName = row.username;
  try {
    const result = (await ElMessageBox.prompt(
      `请输入“${expectedName}”确认删除这个账号。删除后会先进入回收站，且仅无关联业务数据的账号可删除。`,
      "删除用户",
      {
        type: "warning",
        confirmButtonText: "确认删除",
        cancelButtonText: "取消",
        inputPlaceholder: expectedName,
        customClass: "app-prompt-box",
      },
    )) as { value: string };
    if ((result.value || "").trim() !== expectedName) {
      ElMessage.warning("输入名称不一致，已取消删除");
      return;
    }
  } catch {
    return;
  }

  deleteLoadingUserId.value = row.id;
  try {
    await apiClient.delete(`/users/${row.id}`, {
      params: { confirm_name: expectedName },
    });
    ElMessage.success("账号已移入回收站");
    await Promise.all([fetchUsers(), fetchAllUserOptions(), fetchDeletedRecords(), fetchLogs()]);
  } catch (error: any) {
    ElMessage.error(resolveErrorMessage(error, "删除失败"));
  } finally {
    deleteLoadingUserId.value = null;
  }
}

function getGrantDeleteConfirmName(row: DataAccessGrantItem) {
  return `${row.grantee_username} · ${moduleLabel(row.module)}`;
}

async function removeGrant(row: DataAccessGrantItem) {
  const expectedName = getGrantDeleteConfirmName(row);
  try {
    const result = (await ElMessageBox.prompt(
      `请输入“${expectedName}”确认删除这条临时授权。删除后会先进入回收站。`,
      "删除数据授权",
      {
        type: "warning",
        confirmButtonText: "确认删除",
        cancelButtonText: "取消",
        inputPlaceholder: expectedName,
        customClass: "app-prompt-box",
      },
    )) as { value: string };
    if ((result.value || "").trim() !== expectedName) {
      ElMessage.warning("输入名称不一致，已取消删除");
      return;
    }
  } catch {
    return;
  }

  deleteLoadingGrantId.value = row.id;
  try {
    await apiClient.delete(`/admin/data-access-grants/${row.id}`, {
      params: { confirm_name: expectedName },
    });
    ElMessage.success("数据授权已移入回收站");
    await Promise.all([fetchDataAccessGrants(), fetchDeletedRecords(), fetchLogs()]);
  } catch (error: any) {
    ElMessage.error(resolveErrorMessage(error, "删除授权失败"));
  } finally {
    deleteLoadingGrantId.value = null;
  }
}

function resetSsoManualForm() {
  ssoManualForm.user_id = null;
  ssoManualForm.issuer = "";
  ssoManualForm.subject = "";
  ssoManualForm.preferred_username = "";
  ssoManualForm.email = "";
  ssoManualForm.email_verified = false;
  ssoManualForm.display_name = "";
  ssoManualForm.raw_claims_json = "";
}

async function fetchSsoBindings() {
  ssoBindingLoading.value = true;
  try {
    const resp = await apiClient.get<SsoBindingItem[]>("/admin/sso/bindings", {
      params: {
        keyword: ssoFilters.bindingKeyword || undefined,
      },
    });
    ssoBindings.value = resp.data;
  } catch (error) {
    ElMessage.error("加载身份绑定列表失败");
  } finally {
    ssoBindingLoading.value = false;
  }
}

async function fetchSsoUnboundUsers() {
  ssoUnboundLoading.value = true;
  try {
    const resp = await apiClient.get<SsoUnboundUserItem[]>("/admin/sso/unbound-users", {
      params: {
        keyword: ssoFilters.bindingKeyword || undefined,
        include_inactive: ssoFilters.includeInactiveUsers,
      },
    });
    ssoUnboundUsers.value = resp.data;
  } catch (error) {
    ElMessage.error("加载未绑定用户失败");
  } finally {
    ssoUnboundLoading.value = false;
  }
}

async function fetchSsoConflicts() {
  ssoConflictLoading.value = true;
  try {
    const resp = await apiClient.get<SsoConflictItem[]>("/admin/sso/conflicts", {
      params: {
        status_filter: ssoFilters.conflictStatus,
        keyword: ssoFilters.conflictKeyword || undefined,
      },
    });
    ssoConflicts.value = resp.data;
  } catch (error) {
    ElMessage.error("加载待处理冲突失败");
  } finally {
    ssoConflictLoading.value = false;
  }
}

async function fetchSsoWorkspace() {
  await Promise.all([fetchSsoBindings(), fetchSsoUnboundUsers(), fetchSsoConflicts()]);
}

function openSsoManualBindingDialog(row?: SsoUnboundUserItem) {
  resetSsoManualForm();
  if (row) {
    ssoManualForm.user_id = row.id;
    ssoManualForm.email = row.email || "";
    ssoManualForm.display_name = row.display_name || row.username;
    ssoManualForm.preferred_username = row.username;
  }
  showSsoManualDialog.value = true;
}

async function submitSsoManualBinding() {
  if (!ssoManualForm.user_id) {
    ElMessage.warning("请选择要绑定的本地用户");
    return;
  }
  if (!ssoManualForm.issuer.trim() || !ssoManualForm.subject.trim()) {
    ElMessage.warning("Issuer 和 Subject 都必须填写");
    return;
  }
  const payload: SsoManualBindingPayload = {
    user_id: ssoManualForm.user_id,
    issuer: ssoManualForm.issuer.trim(),
    subject: ssoManualForm.subject.trim(),
    preferred_username: ssoManualForm.preferred_username.trim(),
    email: ssoManualForm.email.trim(),
    email_verified: ssoManualForm.email_verified,
    display_name: ssoManualForm.display_name.trim(),
    raw_claims_json: ssoManualForm.raw_claims_json.trim(),
  };
  ssoManualBindingLoading.value = true;
  try {
    await apiClient.post("/admin/sso/bindings/manual", payload);
    ElMessage.success("SSO 绑定已创建");
    showSsoManualDialog.value = false;
    await Promise.all([fetchSsoWorkspace(), fetchUsers(), fetchAllUserOptions(), fetchLogs()]);
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "创建 SSO 绑定失败");
  } finally {
    ssoManualBindingLoading.value = false;
  }
}

function openResolveSsoConflictDialog(conflict: SsoConflictItem) {
  ssoConflictOrigin.value = conflict;
  ssoResolveForm.conflict_id = conflict.id;
  ssoResolveForm.user_id = conflict.candidate_user_ids[0] ?? null;
  showSsoResolveDialog.value = true;
}

async function submitResolveSsoConflict() {
  if (!ssoResolveForm.conflict_id || !ssoResolveForm.user_id) {
    ElMessage.warning("请先选择要绑定的本地用户");
    return;
  }
  ssoResolveLoadingId.value = ssoResolveForm.conflict_id;
  try {
    await apiClient.post(`/admin/sso/conflicts/${ssoResolveForm.conflict_id}/resolve`, {
      user_id: ssoResolveForm.user_id,
    });
    ElMessage.success("冲突已处理并完成绑定");
    showSsoResolveDialog.value = false;
    await Promise.all([fetchSsoWorkspace(), fetchUsers(), fetchAllUserOptions(), fetchLogs()]);
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "处理绑定冲突失败");
  } finally {
    ssoResolveLoadingId.value = null;
  }
}

async function removeSsoBinding(row: SsoBindingItem) {
  try {
    await ElMessageBox.confirm(
      `确认解绑 ${row.username} 的企业单点登录吗？解绑后不会删除本地业务用户。`,
      "解除 SSO 绑定",
      {
        type: "warning",
        confirmButtonText: "确认解绑",
        cancelButtonText: "取消",
      },
    );
  } catch {
    return;
  }
  ssoDeleteLoadingId.value = row.id;
  try {
    await apiClient.delete(`/admin/sso/bindings/${row.id}`);
    ElMessage.success("SSO 绑定已解除");
    await Promise.all([fetchSsoWorkspace(), fetchUsers(), fetchAllUserOptions(), fetchLogs()]);
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "解除绑定失败");
  } finally {
    ssoDeleteLoadingId.value = null;
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

function resetAdvancedLogFilters() {
  logFilters.action = "";
  logFilters.entity_type = "";
  logFilters.audit_scope = "";
  logFilters.limit = 200;
  fetchLogs();
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
    await Promise.all([fetchUsers(), fetchDataAccessGrants(), fetchDeletedRecords(), fetchLogs()]);
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "恢复失败");
  } finally {
    recycleRestoreLoadingKey.value = null;
  }
}

function handleRecycleSelectionChange(rows: DeletedRecordItem[]) {
  recycleSelectedRows.value = rows;
}

async function restoreSelectedDeletedRecords() {
  if (!recycleSelectedRows.value.length) {
    ElMessage.warning("请先勾选要恢复的记录");
    return;
  }
  try {
    await ElMessageBox.confirm(
      `确认批量恢复已勾选的 ${recycleSelectedRows.value.length} 条记录吗？`,
      "批量恢复确认",
      {
        type: "warning",
        confirmButtonText: "确认恢复",
        cancelButtonText: "取消",
      },
    );
  } catch {
    return;
  }

  recycleBulkRestoring.value = true;
  const rows = [...recycleSelectedRows.value];
  const results = await Promise.allSettled(
    rows.map((row) =>
      apiClient.post<DeletedRecordRestoreResult>(
        `/admin/deleted-records/${row.entity_type}/${row.entity_id}/restore`,
        {},
      ),
    ),
  );
  const successCount = results.filter((item) => item.status === "fulfilled").length;
  const failedCount = results.length - successCount;
  recycleSelectedRows.value = [];
  try {
    await Promise.all([fetchUsers(), fetchDataAccessGrants(), fetchDeletedRecords(), fetchLogs()]);
    if (successCount && !failedCount) {
      ElMessage.success(`已恢复 ${successCount} 条记录`);
    } else if (successCount) {
      ElMessage.warning(`已恢复 ${successCount} 条，另有 ${failedCount} 条恢复失败`);
    } else {
      ElMessage.error("批量恢复失败");
    }
  } finally {
    recycleBulkRestoring.value = false;
  }
}

function applyRecycleQuickFilter(value: string) {
  recycleFilters.entity_type = value;
  recycleSelectedRows.value = [];
  fetchDeletedRecords();
}

function recycleRowKey(row: DeletedRecordItem) {
  return `${row.entity_type}:${row.entity_id}`;
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
    fetchAllUserOptions(),
    fetchGrantUsers(),
    fetchDataAccessGrants(),
    fetchSsoWorkspace(),
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
                <el-button
                  class="mobile-row-secondary-button"
                  size="small"
                  plain
                  type="danger"
                  :loading="deleteLoadingGrantId === row.id"
                  @click="removeGrant(row)"
                >
                  删除
                </el-button>
              </div>
            </article>
          </div>
        </section>
      </template>

      <template v-else-if="activeTab === 'sso'">
        <section class="mobile-shell-panel">
          <div class="mobile-toolbar">
            <div class="mobile-toolbar-main">
              <div class="admin-mobile-section-title">SSO / 身份绑定</div>
              <div class="admin-mobile-section-copy">迁移期在这里看已绑定账号、待处理冲突和还没绑定的本地用户。</div>
            </div>
            <div class="mobile-toolbar-actions">
              <el-tag class="mobile-count-tag" size="small" effect="plain">{{ ssoBindings.length }} 已绑定</el-tag>
              <el-button class="mobile-row-primary-button" type="primary" @click="openSsoManualBindingDialog()">
                手动绑定
              </el-button>
            </div>
          </div>
          <div class="mobile-chip-row admin-mobile-stat-row">
            <span class="mobile-chip">待处理 {{ ssoPendingConflictCount }}</span>
            <span class="mobile-chip">已解决 {{ ssoResolvedConflictCount }}</span>
            <span class="mobile-chip">未绑定 {{ ssoUnboundUsers.length }}</span>
          </div>
          <div class="admin-mobile-filter-grid">
            <el-input
              v-model="ssoFilters.bindingKeyword"
              placeholder="账号 / 邮箱 / subject"
              clearable
              @keyup.enter="fetchSsoWorkspace"
            />
            <el-select v-model="ssoFilters.conflictStatus" placeholder="冲突状态">
              <el-option label="待处理" value="PENDING" />
              <el-option label="已处理" value="RESOLVED" />
              <el-option label="全部" value="ALL" />
            </el-select>
          </div>
          <div class="admin-mobile-filter-actions">
            <el-button class="mobile-row-secondary-button" plain @click="fetchSsoWorkspace">查询</el-button>
          </div>
        </section>

        <section class="mobile-shell-panel">
          <div class="admin-mobile-section-title">待处理冲突</div>
          <div class="admin-mobile-section-copy">出现邮箱或用户名冲突时，需要管理员确认绑到哪一个本地业务账号。</div>
          <div v-if="ssoConflictLoading && !ssoConflicts.length" class="mobile-empty-block">
            <div class="mobile-empty-kicker">SSO 冲突</div>
            <div class="mobile-empty-title">正在加载待处理项</div>
            <div class="mobile-empty-copy">冲突账号会在这里集中显示。</div>
          </div>
          <div v-else-if="!ssoConflicts.length" class="mobile-empty-block">
            <div class="mobile-empty-kicker">SSO 冲突</div>
            <div class="mobile-empty-title">当前没有需要人工处理的冲突</div>
            <div class="mobile-empty-copy">后续有新的绑定冲突时会出现在这里。</div>
          </div>
          <div v-else class="mobile-record-list">
            <article v-for="row in ssoConflicts" :key="row.id" class="mobile-record-card admin-mobile-card">
              <div class="mobile-record-head">
                <div class="mobile-record-main">
                  <div class="mobile-record-title">{{ row.display_name || row.preferred_username || row.email || row.subject }}</div>
                  <div class="mobile-record-subtitle">{{ row.reason }} · {{ row.status === "PENDING" ? "待处理" : "已处理" }}</div>
                </div>
                <el-tag class="mobile-status-tag" size="small" effect="plain" :type="row.status === 'PENDING' ? 'warning' : 'success'">
                  {{ row.status === "PENDING" ? "待处理" : "已处理" }}
                </el-tag>
              </div>
              <div class="mobile-record-note">候选账号：{{ row.candidate_usernames.join("、") || "暂无候选账号" }}</div>
              <div class="mobile-action-main" v-if="row.status === 'PENDING'">
                <el-button class="mobile-row-primary-button" size="small" type="primary" @click="openResolveSsoConflictDialog(row)">
                  处理冲突
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
              <div class="admin-mobile-section-copy">已删除的账号、授权和业务数据都会先留在这里，确认后可以恢复。</div>
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
            <div class="mobile-empty-copy">用户、授权、线索、客户、收费单和资料删除后都会先留在这里。</div>
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
              <el-table-column label="操作" width="150">
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
          <el-card shadow="never" class="admin-panel-card">
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

          <el-card shadow="never" class="admin-panel-card">
            <template #header>
              <div class="head head-rich">
                <div>
                  <div class="section-title">临时只读授权</div>
                  <div class="section-copy">把重点信息压缩在一屏内，方便快速停用、恢复或删除授权。</div>
                </div>
                <div class="head-actions">
                  <el-tag type="warning" effect="plain">{{ filteredGrantRows.length }} 条</el-tag>
                  <el-button type="primary" @click="openGrantDialog">新增授权</el-button>
                </div>
              </div>
            </template>
            <el-table v-loading="grantLoading" :data="filteredGrantRows" stripe border size="small" class="admin-grant-table">
              <el-table-column prop="grantee_username" label="被授权会计" min-width="150" fixed="left" />
              <el-table-column label="模块" width="110">
                <template #default="{ row }">{{ moduleLabel(row.module) }}</template>
              </el-table-column>
              <el-table-column label="授权状态" width="150">
                <template #default="{ row }">
                  <div class="grant-status-stack">
                    <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
                      {{ row.is_active ? "启用" : "停用" }}
                    </el-tag>
                    <el-tag :type="row.is_effective ? 'success' : 'warning'" size="small" effect="plain">
                      {{ row.is_effective ? "当前生效" : "当前未生效" }}
                    </el-tag>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="有效期" min-width="230" class-name="mobile-hide" label-class-name="mobile-hide">
                <template #default="{ row }">
                  <div class="grant-period-cell">
                    <div>起：{{ formatDateTimeInBrowserTimeZone(row.starts_at) }}</div>
                    <div>止：{{ formatDateTimeInBrowserTimeZone(row.ends_at) }}</div>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="授权说明" min-width="280" show-overflow-tooltip>
                <template #default="{ row }">
                  <div class="grant-reason-cell">
                    <div class="grant-reason-main">{{ row.reason || "未填写原因" }}</div>
                    <div class="grant-reason-meta">
                      授权人：{{ row.granted_by_username || "-" }} · 创建于 {{ formatDateTimeInBrowserTimeZone(row.created_at) }}
                    </div>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="150" fixed="right">
                <template #default="{ row }">
                  <div class="admin-row-actions">
                    <el-button
                      link
                      :type="row.is_active ? 'danger' : 'primary'"
                      :loading="grantToggleLoadingId === row.id"
                      @click="toggleGrantActive(row, !row.is_active)"
                    >
                      {{ row.is_active ? "停用" : "启用" }}
                    </el-button>
                    <el-button
                      link
                      type="danger"
                      :loading="deleteLoadingGrantId === row.id"
                      @click="removeGrant(row)"
                    >
                      删除
                    </el-button>
                  </div>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-space>
      </el-tab-pane>

      <el-tab-pane label="SSO / 身份绑定" name="sso">
      <el-space direction="vertical" fill :size="12">
          <el-card shadow="never" class="admin-panel-card">
            <div class="head head-rich">
              <div>
                <div class="section-title">企业单点登录绑定管理</div>
                <div class="section-copy">这里不执行正式历史迁移，只负责确认系统已经具备绑定、冲突处理和新用户投影落地能力。</div>
              </div>
              <div class="head-actions">
                <el-tag type="success" effect="plain">{{ ssoBindings.length }} 已绑定</el-tag>
                <el-tag type="warning" effect="plain">{{ ssoPendingConflictCount }} 待处理</el-tag>
                <el-button type="primary" @click="openSsoManualBindingDialog()">手动绑定</el-button>
              </div>
            </div>
            <el-alert
              title="迁移期建议先处理待绑定冲突，再补未绑定本地用户。若绑定错误，可先解绑，再重新绑定。"
              type="info"
              :closable="false"
              class="admin-inline-note"
            />
            <el-form inline @submit.prevent="fetchSsoWorkspace" class="admin-filter-form">
              <el-form-item label="账号检索">
                <el-input
                  v-model="ssoFilters.bindingKeyword"
                  placeholder="账号 / 邮箱 / subject"
                  clearable
                  @keyup.enter="fetchSsoWorkspace"
                />
              </el-form-item>
              <el-form-item label="冲突状态">
                <el-select v-model="ssoFilters.conflictStatus" placeholder="待处理">
                  <el-option label="待处理" value="PENDING" />
                  <el-option label="已处理" value="RESOLVED" />
                  <el-option label="全部" value="ALL" />
                </el-select>
              </el-form-item>
              <el-form-item>
                <el-checkbox v-model="ssoFilters.includeInactiveUsers">包含停用本地用户</el-checkbox>
              </el-form-item>
              <el-form-item>
                <el-button @click="fetchSsoWorkspace">查询</el-button>
              </el-form-item>
            </el-form>
          </el-card>

          <el-row :gutter="12" class="sso-grid">
            <el-col :xs="24" :xl="13">
              <el-card shadow="never" class="admin-panel-card">
                <template #header>
                  <div class="head head-rich">
                    <div>
                      <div class="section-title">已绑定账号</div>
                      <div class="section-copy">一旦绑定成功，后续主要依赖 issuer + subject 识别，不再长期依赖用户名。</div>
                    </div>
                    <div class="head-actions">
                      <el-tag type="success" effect="plain">{{ ssoBindings.length }} 条</el-tag>
                    </div>
                  </div>
                </template>
                <el-table
                  v-loading="ssoBindingLoading"
                  :data="ssoBindings"
                  stripe
                  border
                  size="small"
                  class="admin-sso-table"
                >
                  <el-table-column prop="username" label="本地账号" min-width="150" />
                  <el-table-column label="展示信息" min-width="220">
                    <template #default="{ row }">
                      <div class="sso-cell-stack">
                        <div class="sso-cell-main">{{ row.display_name || row.preferred_username || row.username }}</div>
                        <div class="sso-cell-meta">{{ row.email || "未同步邮箱" }}</div>
                      </div>
                    </template>
                  </el-table-column>
                  <el-table-column label="外部身份" min-width="260" show-overflow-tooltip>
                    <template #default="{ row }">
                      <div class="sso-cell-stack">
                        <div class="sso-cell-main">{{ row.preferred_username || row.subject }}</div>
                        <div class="sso-cell-meta">{{ row.subject }}</div>
                      </div>
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
                  <el-table-column label="状态" width="120">
                    <template #default="{ row }">
                      <el-tag size="small" :type="row.external_managed ? 'success' : 'info'">
                        {{ row.external_managed ? "外部托管" : "普通投影" }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column label="操作" width="96" fixed="right">
                    <template #default="{ row }">
                      <el-button
                        link
                        type="danger"
                        :loading="ssoDeleteLoadingId === row.id"
                        @click="removeSsoBinding(row)"
                      >
                        解绑
                      </el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </el-card>
            </el-col>

            <el-col :xs="24" :xl="11">
              <el-card shadow="never" class="admin-panel-card">
                <template #header>
                  <div class="head head-rich">
                    <div>
                      <div class="section-title">待处理冲突</div>
                      <div class="section-copy">邮箱或用户名无法唯一命中时，会先落到这里，避免自动绑错本地业务账号。</div>
                    </div>
                    <div class="head-actions">
                      <el-tag type="warning" effect="plain">{{ ssoPendingConflictCount }} 待处理</el-tag>
                      <el-tag type="info" effect="plain">{{ ssoResolvedConflictCount }} 已处理</el-tag>
                    </div>
                  </div>
                </template>
                <el-table
                  v-loading="ssoConflictLoading"
                  :data="ssoConflicts"
                  stripe
                  border
                  size="small"
                  class="admin-sso-table"
                >
                  <el-table-column label="企业账号" min-width="180">
                    <template #default="{ row }">
                      <div class="sso-cell-stack">
                        <div class="sso-cell-main">{{ row.display_name || row.preferred_username || row.email || row.subject }}</div>
                        <div class="sso-cell-meta">{{ row.email || row.preferred_username || row.subject }}</div>
                      </div>
                    </template>
                  </el-table-column>
                  <el-table-column label="冲突原因" min-width="180" show-overflow-tooltip>
                    <template #default="{ row }">
                      <div class="sso-cell-stack">
                        <div class="sso-cell-main">{{ row.reason }}</div>
                        <div class="sso-cell-meta">候选：{{ row.candidate_usernames.join("、") || "暂无候选账号" }}</div>
                      </div>
                    </template>
                  </el-table-column>
                  <el-table-column label="状态" width="110">
                    <template #default="{ row }">
                      <el-tag size="small" :type="row.status === 'PENDING' ? 'warning' : 'success'">
                        {{ row.status === "PENDING" ? "待处理" : "已处理" }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column label="操作" width="110" fixed="right">
                    <template #default="{ row }">
                      <el-button
                        v-if="row.status === 'PENDING'"
                        link
                        type="primary"
                        :loading="ssoResolveLoadingId === row.id"
                        @click="openResolveSsoConflictDialog(row)"
                      >
                        处理
                      </el-button>
                      <span v-else class="sso-resolved-text">已处理</span>
                    </template>
                  </el-table-column>
                </el-table>
              </el-card>
            </el-col>
          </el-row>

          <el-card shadow="never" class="admin-panel-card">
            <template #header>
              <div class="head head-rich">
                <div>
                  <div class="section-title">未绑定本地用户</div>
                  <div class="section-copy">这些账号已经在 CRM 里可用，但还没绑定到 Keycloak。历史迁移阶段可以按需手动补绑。</div>
                </div>
                <div class="head-actions">
                  <el-tag type="info" effect="plain">{{ ssoUnboundUsers.length }} 条</el-tag>
                </div>
              </div>
            </template>
            <el-table
              v-loading="ssoUnboundLoading"
              :data="ssoUnboundUsers"
              stripe
              border
              size="small"
              class="admin-sso-table"
            >
              <el-table-column prop="username" label="本地账号" min-width="150" />
              <el-table-column label="显示信息" min-width="220">
                <template #default="{ row }">
                  <div class="sso-cell-stack">
                    <div class="sso-cell-main">{{ row.display_name || row.username }}</div>
                    <div class="sso-cell-meta">{{ row.email || "未填写邮箱" }}</div>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="来源 / 角色" width="160">
                <template #default="{ row }">
                  <div class="sso-cell-stack">
                    <div class="sso-cell-main">{{ authSourceLabel(row.auth_source) }}</div>
                    <div class="sso-cell-meta">{{ roleLabel(row.role) }}</div>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="创建时间" min-width="170" class-name="mobile-hide" label-class-name="mobile-hide">
                <template #default="{ row }">{{ formatDateTimeInBrowserTimeZone(row.created_at) }}</template>
              </el-table-column>
              <el-table-column label="操作" width="110" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" @click="openSsoManualBindingDialog(row)">手动绑定</el-button>
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
              title="当前锁定仅作用于本地账号登录，不影响老板账号在局域网内测试。"
              type="info"
              :closable="false"
            />
            <el-space style="margin-top: 12px">
              <el-button type="primary" :loading="securitySaving" @click="saveSecuritySettings">保存设置</el-button>
              <el-tag type="warning" effect="plain">
                当前规则：{{ securityForm.local_ip_lock_window_minutes }} 分钟 / {{ securityForm.local_ip_lock_max_attempts }} 次
              </el-tag>
            </el-space>
          </el-form>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="LDAP 设置" name="ldap">
        <el-card v-loading="ldapLoading" shadow="never" class="ldap-settings-card">
          <div class="ldap-settings-shell">
            <div class="ldap-settings-summary">
              <div>
                <div class="section-title">LDAP 同步设置</div>
                <div class="section-copy">长表单继续保留，但操作区固定在底部，滚动到任何位置都能直接保存或同步。</div>
              </div>
              <el-tag type="info" effect="plain">{{ hasBindPassword ? "已保存绑定密码" : "未保存绑定密码" }}</el-tag>
            </div>
            <el-form label-position="top" class="ldap-settings-form">
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
            </el-form>
            <div class="ldap-settings-footer">
              <div class="ldap-settings-footer-copy">
                保存不会覆盖已存在的绑定密码，只有重新填写密码时才会更新。
              </div>
              <div class="ldap-settings-footer-actions">
                <el-button type="primary" :loading="ldapSaving" @click="saveLdapSettings">保存设置</el-button>
                <el-button :loading="ldapSyncing" @click="syncLdapUsers">立即同步 LDAP 账号</el-button>
              </div>
            </div>
          </div>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="操作日志" name="logs">
        <el-space direction="vertical" fill :size="12">
          <el-card shadow="never" class="admin-panel-card">
            <div class="log-filter-shell">
              <div class="log-filter-primary">
                <div class="log-filter-copy">
                  <div class="section-title">操作日志筛选</div>
                  <div class="section-copy">先用关键词快速定位，再按动作、对象类型和审计范围细筛。</div>
                </div>
                <el-form inline @submit.prevent="fetchLogs" class="admin-filter-form log-filter-primary-form">
                  <el-form-item label="关键词">
                    <el-input
                      v-model="logFilters.keyword"
                      placeholder="操作描述 / 对象 / 用户"
                      clearable
                      @keyup.enter="fetchLogs"
                    />
                  </el-form-item>
                  <el-form-item>
                    <el-button type="primary" @click="fetchLogs">查询</el-button>
                  </el-form-item>
                  <el-form-item>
                    <el-button text @click="showAdvancedLogFilters = !showAdvancedLogFilters">
                      {{ showAdvancedLogFilters ? "收起高级筛选" : "高级筛选" }}
                      <el-tag
                        v-if="activeAdvancedLogFilterCount"
                        size="small"
                        effect="plain"
                        class="log-advanced-count"
                      >
                        {{ activeAdvancedLogFilterCount }}
                      </el-tag>
                    </el-button>
                  </el-form-item>
                </el-form>
              </div>
              <el-collapse-transition>
                <div v-show="showAdvancedLogFilters" class="log-filter-advanced">
                  <div class="log-filter-advanced-head">
                    <div class="log-filter-advanced-title">高级筛选</div>
                    <el-button text @click="resetAdvancedLogFilters">清空细筛</el-button>
                  </div>
                  <el-form inline @submit.prevent="fetchLogs" class="admin-filter-form log-filter-advanced-form">
                    <el-form-item label="动作">
                      <el-input v-model="logFilters.action" placeholder="如 USER_UPDATED" clearable />
                    </el-form-item>
                    <el-form-item label="对象类型">
                      <el-input v-model="logFilters.entity_type" placeholder="如 USER / LDAP" clearable />
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
                  </el-form>
                </div>
              </el-collapse-transition>
            </div>
          </el-card>

          <el-card shadow="never" class="admin-panel-card">
            <template #header>
              <div class="head head-rich">
                <div>
                  <div class="section-title">操作日志</div>
                  <div class="section-copy">集中看账号、授权、删除恢复这些关键动作，判断是谁在什么时间做了什么。</div>
                </div>
                <div class="head-actions">
                  <el-tag type="info" effect="plain">{{ logRows.length }} 条</el-tag>
                </div>
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
          <el-card shadow="never" class="admin-panel-card">
            <div class="recycle-filter-strip">
              <div class="recycle-filter-strip-label">快捷筛选</div>
              <div class="recycle-filter-chips">
                <el-button
                  v-for="item in recycleQuickFilters"
                  :key="item.value || 'all'"
                  size="small"
                  :type="recycleFilters.entity_type === item.value ? 'primary' : 'default'"
                  :plain="recycleFilters.entity_type !== item.value"
                  class="recycle-filter-chip"
                  @click="applyRecycleQuickFilter(item.value)"
                >
                  {{ item.label }}
                  <span class="recycle-filter-chip-count">{{ item.count }}</span>
                </el-button>
              </div>
            </div>
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

          <el-card shadow="never" class="admin-panel-card">
            <template #header>
              <div class="head head-rich">
                <div>
                  <div class="section-title">回收站</div>
                  <div class="section-copy">先按类型快速缩小范围，再批量恢复，能少很多来回点开的操作。</div>
                </div>
                <div class="head-actions">
                  <el-tag type="warning" effect="plain">{{ deletedRows.length }} 条</el-tag>
                  <el-button
                    type="primary"
                    plain
                    :disabled="!recycleSelectedRows.length"
                    :loading="recycleBulkRestoring"
                    @click="restoreSelectedDeletedRecords"
                  >
                    批量恢复
                  </el-button>
                </div>
              </div>
            </template>
            <el-table
              v-loading="recycleLoading"
              :data="deletedRows"
              stripe
              border
              size="small"
              :row-key="recycleRowKey"
              class="recycle-table"
              @selection-change="handleRecycleSelectionChange"
            >
              <el-table-column type="selection" width="48" reserve-selection />
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
              <el-table-column label="操作" width="108" fixed="right">
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
    <el-form label-position="top" class="admin-dialog-form">
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
    <el-form label-position="top" class="admin-dialog-form">
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
    <el-form label-position="top" class="admin-dialog-form">
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

  <el-dialog v-model="showSsoManualDialog" title="手动创建 SSO 绑定" width="620px">
    <el-form label-position="top" class="admin-dialog-form">
      <el-form-item label="本地业务用户">
        <el-select v-model="ssoManualForm.user_id" filterable placeholder="请选择本地账号">
          <el-option
            v-for="item in bindableUserOptions"
            :key="item.id"
            :label="`${item.username}${item.display_name ? ` · ${item.display_name}` : ''}`"
            :value="item.id"
          />
        </el-select>
      </el-form-item>
      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="身份中心 Issuer">
            <el-input v-model="ssoManualForm.issuer" placeholder="如 https://sso.example.com/realms/company" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="外部 Subject">
            <el-input v-model="ssoManualForm.subject" placeholder="Keycloak 返回的 subject" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="外部用户名">
            <el-input v-model="ssoManualForm.preferred_username" placeholder="如 crm-test" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="邮箱">
            <el-input v-model="ssoManualForm.email" placeholder="如 crm-test@ivanshang.com" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="显示名">
            <el-input v-model="ssoManualForm.display_name" placeholder="如 CRM 测试账号" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="邮箱已验证">
            <el-switch v-model="ssoManualForm.email_verified" active-text="是" inactive-text="否" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="原始 claims（可留空）">
        <el-input
          v-model="ssoManualForm.raw_claims_json"
          type="textarea"
          :rows="4"
          placeholder='如 {"groups":["crm-accountant"]}'
        />
      </el-form-item>
      <el-alert
        title="这一步只是在 CRM 里建立身份绑定，不执行正式历史迁移。"
        type="info"
        :closable="false"
      />
    </el-form>
    <template #footer>
      <el-button @click="showSsoManualDialog = false">取消</el-button>
      <el-button type="primary" :loading="ssoManualBindingLoading" @click="submitSsoManualBinding">创建绑定</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="showSsoResolveDialog" title="处理 SSO 绑定冲突" width="560px">
    <el-form label-position="top" class="admin-dialog-form">
      <el-alert
        v-if="ssoConflictOrigin"
        :title="ssoConflictOrigin.reason"
        type="warning"
        :closable="false"
      />
      <el-form-item label="企业账号">
        <el-input
          :model-value="ssoConflictOrigin ? `${ssoConflictOrigin.display_name || ssoConflictOrigin.preferred_username || '-'} · ${ssoConflictOrigin.email || ssoConflictOrigin.subject}` : ''"
          readonly
        />
      </el-form-item>
      <el-form-item label="绑定到本地业务用户">
        <el-select v-model="ssoResolveForm.user_id" filterable placeholder="请选择本地账号">
          <el-option
            v-for="item in ssoResolveCandidateOptions"
            :key="item.id"
            :label="`${item.username}${item.display_name ? ` · ${item.display_name}` : ''}`"
            :value="item.id"
          />
        </el-select>
      </el-form-item>
      <div v-if="ssoConflictOrigin" class="sso-dialog-helper">
        候选账号：{{ ssoConflictOrigin.candidate_usernames.join("、") || "暂无候选账号，允许手动指定" }}
      </div>
    </el-form>
    <template #footer>
      <el-button @click="showSsoResolveDialog = false">取消</el-button>
      <el-button type="primary" :loading="ssoResolveLoadingId === ssoResolveForm.conflict_id" @click="submitResolveSsoConflict">
        确认绑定
      </el-button>
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
  grid-template-columns: repeat(auto-fit, minmax(72px, 1fr));
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

.head-rich {
  align-items: flex-start;
  gap: 16px;
}

.head-actions,
.admin-row-actions,
.ldap-settings-footer-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.section-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--app-text-primary);
}

.section-copy {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--app-text-muted);
}

.admin-panel-card {
  border-color: var(--app-border-soft);
}

.admin-inline-note {
  margin-bottom: 12px;
}

.grant-status-stack,
.grant-period-cell,
.grant-reason-cell {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.grant-period-cell,
.grant-reason-meta,
.ldap-settings-footer-copy,
.recycle-filter-strip-label,
.recycle-filter-chip-count {
  font-size: 12px;
  line-height: 1.45;
  color: var(--app-text-muted);
}

.sso-cell-stack,
.sso-dialog-helper {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.sso-cell-main,
.sso-resolved-text {
  color: var(--app-text-primary);
}

.sso-cell-meta,
.sso-dialog-helper {
  font-size: 12px;
  line-height: 1.5;
  color: var(--app-text-muted);
}

.sso-grid :deep(.el-card__body) {
  min-width: 0;
}

.admin-sso-table :deep(.el-table__cell) {
  padding-top: 9px;
  padding-bottom: 9px;
}

.grant-reason-main {
  color: var(--app-text-primary);
  line-height: 1.5;
}

.admin-grant-table :deep(.el-table__cell),
.recycle-table :deep(.el-table__cell) {
  padding-top: 9px;
  padding-bottom: 9px;
}

.ldap-settings-card :deep(.el-card__body) {
  padding: 18px 20px 0;
}

.ldap-settings-shell {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.ldap-settings-summary {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.ldap-settings-form {
  min-width: 0;
}

.ldap-settings-footer {
  position: sticky;
  bottom: 0;
  z-index: 5;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 0 16px;
  margin-top: 4px;
  border-top: 1px solid var(--app-border-soft);
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(8px);
}

.recycle-filter-strip {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding-bottom: 14px;
  margin-bottom: 14px;
  border-bottom: 1px dashed var(--app-border-soft);
}

.recycle-filter-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.recycle-filter-chip {
  min-height: 32px;
}

.log-filter-shell {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.log-filter-primary {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.log-filter-copy {
  min-width: 0;
  max-width: 440px;
}

.log-filter-primary-form {
  justify-content: flex-end;
}

.log-filter-primary-form :deep(.el-form-item:first-child .el-input) {
  width: min(420px, 100%);
}

.log-advanced-count {
  margin-left: 8px;
}

.log-filter-advanced {
  padding: 14px 16px 6px;
  border: 1px solid var(--app-border-soft);
  border-radius: 16px;
  background: var(--app-surface-muted);
}

.log-filter-advanced-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.log-filter-advanced-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--app-text-primary);
}

.log-filter-advanced-form {
  margin-bottom: -8px;
}

.admin-filter-form :deep(.el-select),
.admin-filter-form :deep(.el-autocomplete),
.admin-filter-form :deep(.el-date-editor),
.admin-filter-form :deep(.el-input-number) {
  min-width: 220px;
}

.admin-dialog-form :deep(.el-select),
.admin-dialog-form :deep(.el-autocomplete),
.admin-dialog-form :deep(.el-date-editor),
.admin-dialog-form :deep(.el-input-number) {
  width: 100%;
}

@media (max-width: 768px) {
  .admin-mobile-hero {
    flex-direction: column;
  }

  .head-rich,
  .log-filter-primary,
  .ldap-settings-summary,
  .ldap-settings-footer,
  .recycle-filter-strip {
    flex-direction: column;
  }

  .head-actions,
  .ldap-settings-footer-actions,
  .log-filter-primary-form {
    width: 100%;
    justify-content: flex-start;
    flex-wrap: wrap;
  }

  .log-filter-copy {
    max-width: none;
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
