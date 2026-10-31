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
  PaymentRecord,
  RecordPaymentPayload,
  DashboardMetrics,
  PaginatedResponse,
} from "@/types/domain.types";

// ==========================================
// CUSTOMERS
// ==========================================
export async function fetchCustomers(search = ""): Promise<CustomerRecord[]> {
  if (USE_MOCK) {
    return [
      { id: "cust-01", displayName: "Sarah Jenkins", companyName: "Acme Cloud Corp", billingEmail: "sarah@acme.com", status: "ACTIVE", createdAt: "2026-10-12" },
      { id: "cust-02", displayName: "Marcus Vance", companyName: "Apex Design Labs", billingEmail: "marcus@apex.io", status: "ACTIVE", createdAt: "2026-10-18" },
    ];
  }

  const query = new URLSearchParams({ page: "1", pageSize: "50" });
  if (search.trim()) query.set("search", search.trim());
  const data = await apiRequest<PaginatedResponse<CustomerRecord> | CustomerRecord[]>(`/customers?${query.toString()}`);
  return Array.isArray(data) ? data : data.items || [];
}

export async function createCustomer(payload: CreateCustomerPayload): Promise<CustomerRecord> {
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

// ==========================================
// PLANS
// ==========================================
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
  const cleanPrice = String(payload.price).replace(/[^0-9.]/g, "");
  const body = {
    name: payload.name.trim(),
    description: payload.description || `Tier for ${payload.name.trim()}`,
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

// ==========================================
// SUBSCRIPTIONS
// ==========================================
export async function fetchSubscriptions(): Promise<SubscriptionItem[]> {
  if (USE_MOCK) {
    return [
      { id: "sub-01", subscriptionNumber: "SUB-2026-0001", customerId: "cust-01", customerName: "Acme Cloud Corp", planId: "plan-02", planName: "Enterprise Pro", status: "ACTIVE", price: "2499.00", currency: "INR", billingInterval: "MONTHLY", currentPeriodEnd: "2026-11-15" },
    ];
  }

  const data = await apiRequest<PaginatedResponse<SubscriptionItem> | SubscriptionItem[]>("/subscriptions?page=1&pageSize=50");
  return Array.isArray(data) ? data : data.items || [];
}

export async function createSubscription(payload: CreateSubscriptionPayload): Promise<SubscriptionItem> {
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

// ==========================================
// LIVE INVOICES (Real FastAPI Backend)
// ==========================================
export async function fetchInvoices(): Promise<InvoiceRecord[]> {
  if (USE_MOCK) {
    return [
      { id: "inv-01", invoiceNumber: "INV-2026-0001", customerId: "cust-01", customerName: "Acme Cloud Corp", status: "CONFIRMED", currency: "INR", subtotal: "2499.00", taxTotal: "449.82", total: "2948.82", amountPaid: "0.00", amountDue: "2948.82", issueDate: "2026-10-15", dueDate: "2026-11-01" },
      { id: "inv-02", invoiceNumber: "INV-2026-0002", customerId: "cust-02", customerName: "Apex Design Labs", status: "PAID", currency: "INR", subtotal: "499.00", taxTotal: "89.82", total: "588.82", amountPaid: "588.82", amountDue: "0.00", issueDate: "2026-10-22", dueDate: "2026-11-05" },
    ];
  }

  const data = await apiRequest<PaginatedResponse<InvoiceRecord> | InvoiceRecord[]>("/invoices?page=1&pageSize=50");
  return Array.isArray(data) ? data : data.items || [];
}

export async function confirmInvoice(id: string): Promise<InvoiceRecord> {
  return apiRequest<InvoiceRecord>(`/invoices/${id}/confirm`, { method: "POST" });
}

export async function cancelInvoice(id: string): Promise<InvoiceRecord> {
  return apiRequest<InvoiceRecord>(`/invoices/${id}/cancel`, { method: "POST" });
}

export async function sendInvoice(id: string): Promise<{ status: string; message: string }> {
  return apiRequest<{ status: string; message: string }>(`/invoices/${id}/send`, { method: "POST" });
}

export async function downloadInvoicePdf(id: string, invoiceNumber: string): Promise<void> {
  const token = localStorage.getItem("brightloop_access_token");
  const baseUrl = APP_CONFIG.API_BASE_URL.replace(/\/+$/, "");
  const response = await fetch(`${baseUrl}/invoices/${id}/pdf`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  if (!response.ok) {
    throw new Error(`Failed to download PDF (${response.status})`);
  }

  const blob = await response.blob();
  const downloadUrl = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = downloadUrl;
  a.download = `${invoiceNumber}.pdf`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(downloadUrl);
}

// ==========================================
// LIVE PAYMENTS (Real FastAPI Backend)
// ==========================================
export async function fetchPayments(): Promise<PaymentRecord[]> {
  if (USE_MOCK) return [];
  const data = await apiRequest<PaginatedResponse<PaymentRecord> | PaymentRecord[]>("/payments?page=1&pageSize=50");
  return Array.isArray(data) ? data : data.items || [];
}

export async function recordPayment(payload: RecordPaymentPayload): Promise<PaymentRecord> {
  return apiRequest<PaymentRecord>("/payments", {
    method: "POST",
    body: JSON.stringify({
      invoiceId: payload.invoiceId,
      amount: String(payload.amount).replace(/[^0-9.]/g, ""),
      currency: (payload.currency || APP_CONFIG.DEFAULT_CURRENCY).toUpperCase(),
      method: payload.method,
      reference: payload.reference || null,
      notes: payload.notes || null,
    }),
  });
}

// ==========================================
// ANALYTICS & DASHBOARD KPIS
// ==========================================
export async function fetchDashboardAnalytics(currency = "INR"): Promise<DashboardMetrics> {
  if (USE_MOCK) {
    return {
      activeSubscriptions: 4,
      collectedRevenue: "42890.00",
      outstandingBalance: "3537.64",
      overdueInvoiceCount: 1,
      mrr: "42890.00",
      arr: "514680.00",
      totalInvoiceCount: 8,
    };
  }

  return apiRequest<DashboardMetrics>(`/analytics/dashboard?currency=${currency}`);
}
