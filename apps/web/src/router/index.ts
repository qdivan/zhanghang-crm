import { createRouter, createWebHistory } from "vue-router";

import { useAuthStore } from "../stores/auth";
import AddressResourceView from "../views/AddressResourceView.vue";
import AdminUsersView from "../views/AdminUsersView.vue";
import AppLayout from "../layouts/AppLayout.vue";
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
    return "/dashboard";
  }
  if (to.path.startsWith("/receipt-reconciliation") && !canAccessReceiptReconciliation(auth.user)) {
    return "/dashboard";
  }
  const roleLimit = to.meta.roles as UserRole[] | undefined;
  if (roleLimit && (!auth.user || !roleLimit.includes(auth.user.role))) {
    return "/dashboard";
  }
  return true;
});

export default router;
