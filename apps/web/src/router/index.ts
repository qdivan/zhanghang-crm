import { createRouter, createWebHistory } from "vue-router";

import { useAuthStore } from "../stores/auth";
import AddressResourceView from "../views/AddressResourceView.vue";
import AdminUsersView from "../views/AdminUsersView.vue";
import AppLayout from "../layouts/AppLayout.vue";
import MobileLayout from "../layouts/MobileLayout.vue";
import BillingView from "../views/BillingView.vue";
import CommonLibraryView from "../views/CommonLibraryView.vue";
import CostView from "../views/CostView.vue";
import CustomerDetailView from "../views/CustomerDetailView.vue";
import CustomersView from "../views/CustomersView.vue";
import DashboardView from "../views/DashboardView.vue";
import LeadDetailView from "../views/LeadDetailView.vue";
import LeadView from "../views/LeadView.vue";
import LoginView from "../views/LoginView.vue";
import PublicLibraryView from "../views/PublicLibraryView.vue";
import ReceiptReconciliationView from "../views/ReceiptReconciliationView.vue";
import { getDefaultProtectedPath, isHandsetViewport, isMobileAppPath, mapPathToMobile } from "../mobile/config";
import MobileMoreView from "../views/mobile/MobileMoreView.vue";
import MobileTodoView from "../views/mobile/MobileTodoView.vue";
import type { UserRole } from "../types";

function canAccessReceiptReconciliation(user: { role: UserRole; granted_read_modules: string[] } | null) {
  if (!user) return false;
  return (
    user.role === "OWNER" ||
    user.role === "ADMIN" ||
    user.role === "MANAGER" ||
    user.granted_read_modules.includes("BILLING")
  );
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/login",
      name: "login",
      component: LoginView,
    },
    {
      path: "/library/public",
      name: "public-library",
      component: PublicLibraryView,
      meta: {
        public: true,
      },
    },
    {
      path: "/",
      component: AppLayout,
      children: [
        {
          path: "",
          redirect: "/dashboard",
        },
        {
          path: "dashboard",
          name: "dashboard",
          component: DashboardView,
        },
        {
          path: "leads",
          name: "leads",
          component: LeadView,
        },
        {
          path: "leads/:id",
          name: "lead-detail",
          component: LeadDetailView,
        },
        {
          path: "customers",
          name: "customers",
          component: CustomersView,
        },
        {
          path: "customers/:id",
          name: "customer-detail",
          component: CustomerDetailView,
        },
        {
          path: "billing",
          name: "billing",
          component: BillingView,
        },
        {
          path: "receipt-reconciliation",
          name: "receipt-reconciliation",
          component: ReceiptReconciliationView,
        },
        {
          path: "common-library",
          name: "common-library",
          component: CommonLibraryView,
        },
        {
          path: "address-resources",
          name: "address-resources",
          component: AddressResourceView,
        },
        {
          path: "costs",
          name: "costs",
          component: CostView,
          meta: {
            roles: ["OWNER"] as UserRole[],
          },
        },
        {
          path: "admin/users",
          name: "admin-users",
          component: AdminUsersView,
          meta: {
            roles: ["OWNER", "ADMIN"] as UserRole[],
          },
        },
      ],
    },
    {
      path: "/m",
      component: MobileLayout,
      children: [
        {
          path: "",
          redirect: "/m/todo",
        },
        {
          path: "todo",
          name: "mobile-todo",
          component: MobileTodoView,
          meta: {
            mobileTitle: "Todo",
            mobileSubtitle: "先处理今天任务，再切到业务模块。",
            mobileNavKey: "todo",
          },
        },
        {
          path: "leads",
          name: "mobile-leads",
          component: LeadView,
          meta: {
            mobileTitle: "客户开发",
            mobileSubtitle: "先扫读状态，再做跟进和转化。",
            mobileNavKey: "leads",
          },
        },
        {
          path: "leads/:id",
          name: "mobile-lead-detail",
          component: LeadDetailView,
          meta: {
            mobileTitle: "开发详情",
            mobileSubtitle: "补全线索上下文和跟进记录。",
            mobileBackTo: "/m/leads",
            mobileIconKey: "leads",
          },
        },
        {
          path: "customers",
          name: "mobile-customers",
          component: CustomersView,
          meta: {
            mobileTitle: "客户列表",
            mobileSubtitle: "查客户、补收费、继续维护。",
            mobileNavKey: "customers",
          },
        },
        {
          path: "customers/:id",
          name: "mobile-customer-detail",
          component: CustomerDetailView,
          meta: {
            mobileTitle: "客户档案",
            mobileSubtitle: "成单后信息、时间线和客户事项。",
            mobileBackTo: "/m/customers",
            mobileIconKey: "customers",
          },
        },
        {
          path: "billing",
          name: "mobile-billing",
          component: BillingView,
          meta: {
            mobileTitle: "收费明细",
            mobileSubtitle: "先看未收和到期，再处理催收与收款。",
            mobileNavKey: "billing",
          },
        },
        {
          path: "receipt-reconciliation",
          name: "mobile-receipt-reconciliation",
          component: ReceiptReconciliationView,
          meta: {
            mobileTitle: "到账核对",
            mobileSubtitle: "按入账账户核对收款流水。",
            mobileBackTo: "/m/more",
            mobileSectionKey: "receipt-reconciliation",
          },
        },
        {
          path: "common-library",
          name: "mobile-common-library",
          component: CommonLibraryView,
          meta: {
            mobileTitle: "常用资料",
            mobileSubtitle: "查看内部资料、模板和公开资料。",
            mobileBackTo: "/m/more",
            mobileSectionKey: "common-library",
          },
        },
        {
          path: "address-resources",
          name: "mobile-address-resources",
          component: AddressResourceView,
          meta: {
            mobileTitle: "挂靠地址",
            mobileSubtitle: "集中查看地址资源和联系人。",
            mobileBackTo: "/m/more",
            mobileSectionKey: "address-resources",
          },
        },
        {
          path: "costs",
          name: "mobile-costs",
          component: CostView,
          meta: {
            roles: ["OWNER"] as UserRole[],
            mobileTitle: "成本与老板视图",
            mobileSubtitle: "仅老板可见的成本和视图数据。",
            mobileBackTo: "/m/more",
            mobileSectionKey: "costs",
          },
        },
        {
          path: "admin/users",
          name: "mobile-admin-users",
          component: AdminUsersView,
          meta: {
            roles: ["OWNER", "ADMIN"] as UserRole[],
            mobileTitle: "管理员面板",
            mobileSubtitle: "用户、角色和数据授权配置。",
            mobileBackTo: "/m/more",
            mobileSectionKey: "admin-users",
          },
        },
        {
          path: "more",
          name: "mobile-more",
          component: MobileMoreView,
          meta: {
            mobileTitle: "更多",
            mobileSubtitle: "低频入口和账户操作统一收口。",
            mobileNavKey: "more",
          },
        },
      ],
    },
  ],
});

router.beforeEach(async (to) => {
  const auth = useAuthStore();
  const isPublicRoute = Boolean(to.meta.public);
  if (!auth.ready) {
    await auth.hydrate();
  }

  if (!isPublicRoute && to.path !== "/login" && !auth.isLoggedIn) {
    return "/login";
  }
  if (to.path === "/login" && auth.isLoggedIn) {
    return getDefaultProtectedPath();
  }
  if (
    (to.path.startsWith("/receipt-reconciliation") || to.path.startsWith("/m/receipt-reconciliation")) &&
    !canAccessReceiptReconciliation(auth.user)
  ) {
    return getDefaultProtectedPath();
  }
  const roleLimit = to.meta.roles as UserRole[] | undefined;
  if (roleLimit && (!auth.user || !roleLimit.includes(auth.user.role))) {
    return getDefaultProtectedPath();
  }
  if (auth.isLoggedIn && isHandsetViewport() && !isMobileAppPath(to.path)) {
    const mobileTarget = mapPathToMobile(to.fullPath);
    if (mobileTarget && mobileTarget !== to.fullPath) {
      return mobileTarget;
    }
  }
  return true;
});

export default router;
