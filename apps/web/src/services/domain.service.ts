import { apiRequest } from "./api";
import { USE_MOCK, APP_CONFIG } from "./mock.config";
import type {
  CustomerRecord,
  CreateCustomerPayload,
  PlanItem,
  CreatePlanPayload,
  SubscriptionItem,
  CreateSubscriptionPayload,
  InvoiceRecord,
  PaginatedResponse,
} from "@/types/domain.types";

export async function fetchCustomers(search = ""): Promise<CustomerRecord[]> {
  if (USE_MOCK) {
    return [
      { id: "cust-01", displayName: "Sarah Jenkins", companyName: "Acme Cloud Corp", billingEmail: "sarah@acme.com", status: "ACTIVE", createdAt: "2026-10-12" },
      { id: "cust-02", displayName: "Marcus Vance", companyName: "Apex Design Labs", billingEmail: "marcus@apex.io", status: "ACTIVE", createdAt: "2026-10-18" },
    ];
  }

  const query = new URLSearchParams({
    page: "1",
    pageSize: "50",
  });
  if (search.trim()) query.set("search", search.trim());

  const data = await apiRequest<PaginatedResponse<CustomerRecord> | CustomerRecord[]>(`/customers?${query.toString()}`);
  return Array.isArray(data) ? data : data.items || [];
}

export async function createCustomer(payload: CreateCustomerPayload): Promise<CustomerRecord> {
  if (USE_MOCK) {
    return {
      id: `cust-${Date.now()}`,
      displayName: payload.displayName,
      companyName: payload.companyName || null,
      billingEmail: payload.billingEmail,
      status: "ACTIVE",
      createdAt: new Date().toISOString(),
    };
  }

  const body = {
    displayName: payload.displayName.trim(),
    billingEmail: payload.billingEmail.trim(),
    companyName: payload.companyName ? payload.companyName.trim() : null,
    phone: payload.phone ? payload.phone.trim() : null,
  };

  return apiRequest<CustomerRecord>("/customers", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function fetchPlans(): Promise<PlanItem[]> {
  if (USE_MOCK) {
    return [
      { id: "plan-01", name: "Starter Growth", price: "499.00", currency: "INR", billingInterval: "MONTHLY", intervalCount: 1, isActive: true, activeSubscribers: 142 },
      { id: "plan-02", name: "Enterprise Pro", price: "2499.00", currency: "INR", billingInterval: "MONTHLY", intervalCount: 1, isActive: true, activeSubscribers: 38 },
    ];
  }

  const data = await apiRequest<PaginatedResponse<PlanItem> | PlanItem[]>("/plans?page=1&pageSize=50");
  return Array.isArray(data) ? data : data.items || [];
}

export async function createPlan(payload: CreatePlanPayload): Promise<PlanItem> {
  if (USE_MOCK) {
    return {
      id: `plan-${Date.now()}`,
      name: payload.name,
      price: payload.price,
      currency: payload.currency || APP_CONFIG.DEFAULT_CURRENCY,
      billingInterval: payload.billingInterval,
      intervalCount: payload.intervalCount || 1,
      isActive: true,
      activeSubscribers: 0,
    };
  }

  const cleanPrice = String(payload.price).replace(/[^0-9.]/g, "");
  const body = {
    name: payload.name.trim(),
    description: payload.description || `Billing tier for ${payload.name.trim()}`,
    price: cleanPrice,
    currency: (payload.currency || APP_CONFIG.DEFAULT_CURRENCY).toUpperCase(),
    billingInterval: payload.billingInterval,
    intervalCount: Number(payload.intervalCount) || 1,
  };

  return apiRequest<PlanItem>("/plans", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function fetchSubscriptions(): Promise<SubscriptionItem[]> {
  if (USE_MOCK) {
    return [
      { id: "sub-01", customerId: "cust-01", customerName: "Acme Cloud Corp", planId: "plan-02", planName: "Enterprise Pro", status: "ACTIVE", price: "2499.00", currency: "INR", billingInterval: "MONTHLY", currentPeriodEnd: "2026-11-15" },
      { id: "sub-02", customerId: "cust-02", customerName: "Apex Design Labs", planId: "plan-01", planName: "Starter Growth", status: "TRIAL", price: "499.00", currency: "INR", billingInterval: "MONTHLY", currentPeriodEnd: "2026-11-22" },
    ];
  }

  const data = await apiRequest<PaginatedResponse<SubscriptionItem> | SubscriptionItem[]>("/subscriptions?page=1&pageSize=50");
  return Array.isArray(data) ? data : data.items || [];
}

export async function createSubscription(payload: CreateSubscriptionPayload): Promise<SubscriptionItem> {
  if (USE_MOCK) {
    return {
      id: `sub-${Date.now()}`,
      customerId: payload.customerId,
      planId: payload.planId,
      status: "ACTIVE",
      price: "499.00",
      currency: "INR",
      billingInterval: "MONTHLY",
      createdAt: new Date().toISOString(),
    };
  }

  const body = {
    customerId: payload.customerId,
    planId: payload.planId,
    currency: payload.currency || APP_CONFIG.DEFAULT_CURRENCY,
    startDate: payload.startDate || new Date().toISOString().split("T")[0],
  };

  return apiRequest<SubscriptionItem>("/subscriptions", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getIsolatedInvoices(): InvoiceRecord[] {
  return [
    { id: "INV-2026-089", customer: "Acme Cloud Corp", amount: "2,499.00", currency: "INR", status: "PAID", due: "15 Oct 2026", isMock: true },
    { id: "INV-2026-090", customer: "Horizon Data Tech", amount: "780.50", currency: "INR", status: "PENDING", due: "01 Nov 2026", isMock: true },
    { id: "INV-2026-091", customer: "Apex Design Labs", amount: "499.00", currency: "INR", status: "PAID", due: "22 Oct 2026", isMock: true },
    { id: "INV-2026-092", customer: "Nova Dynamics", amount: "2,040.50", currency: "INR", status: "PENDING", due: "10 Nov 2026", isMock: true },
  ];
}
