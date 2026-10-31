import { apiRequest, getAccessToken } from "./api";
import { USE_MOCK, APP_CONFIG } from "./mock.config";
import type {
  CustomerRecord,
  CreateCustomerPayload,
  ProductRecord,
  CreateProductPayload,
  PlanItem,
  CreatePlanPayload,
  TaxRuleRecord,
  CreateTaxRulePayload,
  DiscountRecord,
  CreateDiscountPayload,
  QuotationRecord,
  CreateQuotationPayload,
  SubscriptionItem,
  CreateSubscriptionPayload,
  InvoiceRecord,
  PaymentRecord,
  RecordPaymentPayload,
  NotificationItem,
  AnalyticsDashboard,
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

// ==========================================
// PRODUCTS
// ==========================================
export async function fetchProducts(): Promise<ProductRecord[]> {
  if (USE_MOCK) {
    return [
      { id: "prod-01", name: "Cloud Compute Node", sku: "SKU-NODE-01", basePrice: "199.00", currency: "INR", isActive: true, createdAt: "2026-10-01" },
    ];
  }

  const data = await apiRequest<PaginatedResponse<ProductRecord> | ProductRecord[]>("/products?page=1&pageSize=50");
  return Array.isArray(data) ? data : data.items || [];
}

export async function createProduct(payload: CreateProductPayload): Promise<ProductRecord> {
  if (USE_MOCK) {
    return {
      id: `prod-${Date.now()}`,
      name: payload.name,
      sku: payload.sku,
      basePrice: payload.basePrice,
      currency: payload.currency,
      isActive: true,
      createdAt: new Date().toISOString(),
    };
  }

  const body = {
    name: payload.name.trim(),
    description: payload.description || `Catalog product ${payload.name.trim()}`,
    sku: payload.sku.trim(),
    basePrice: String(payload.basePrice).replace(/[^0-9.]/g, ""),
    currency: payload.currency.toUpperCase(),
  };

  return apiRequest<ProductRecord>("/products", {
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

// ==========================================
// TAX RULES & DISCOUNT RULES (ALIGNED)
// ==========================================
export async function fetchTaxRules(): Promise<TaxRuleRecord[]> {
  if (USE_MOCK) {
    return [
      { id: "tax-01", name: "GST Standard", code: "GST-18", taxType: "IGST", ratePercentage: "18.00", isInclusive: false, isActive: true, createdAt: "2026-10-01" },
    ];
  }

  const data = await apiRequest<PaginatedResponse<TaxRuleRecord> | TaxRuleRecord[]>("/tax-rules?page=1&pageSize=50");
  return Array.isArray(data) ? data : data.items || [];
}

export async function createTaxRule(payload: CreateTaxRulePayload): Promise<TaxRuleRecord> {
  const body = {
    name: payload.name.trim(),
    code: payload.code.trim().toUpperCase(),
    taxType: payload.taxType,
    ratePercentage: String(payload.ratePercentage).replace(/[^0-9.]/g, ""),
    jurisdiction: payload.jurisdiction || "National",
    isInclusive: payload.isInclusive,
  };

  return apiRequest<TaxRuleRecord>("/tax-rules", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function fetchDiscounts(): Promise<DiscountRecord[]> {
  if (USE_MOCK) {
    return [
      { id: "disc-01", name: "Early Bird", code: "EARLY10", discountType: "PERCENTAGE", value: "10.00", maxUsage: 100, isActive: true, createdAt: "2026-10-01" },
    ];
  }

  // Aligned: backend FastAPI endpoint is /discount-rules
  const data = await apiRequest<PaginatedResponse<DiscountRecord> | DiscountRecord[]>("/discount-rules?page=1&pageSize=50");
  return Array.isArray(data) ? data : data.items || [];
}

export async function createDiscount(payload: CreateDiscountPayload): Promise<DiscountRecord> {
  const body = {
    name: payload.name.trim(),
    code: payload.code.trim().toUpperCase(),
    discountType: payload.discountType,
    value: String(payload.value).replace(/[^0-9.]/g, ""),
    maxUsage: payload.maxUsage || null,
  };

  // Aligned: backend FastAPI endpoint is /discount-rules
  return apiRequest<DiscountRecord>("/discount-rules", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// ==========================================
// QUOTATIONS & ACCEPTANCE
// ==========================================
export async function fetchQuotations(): Promise<QuotationRecord[]> {
  if (USE_MOCK) {
    return [
      { id: "quote-01", quotationNumber: "QUO-2026-0001", customerId: "cust-01", customerName: "Acme Cloud Corp", planId: "plan-02", planName: "Enterprise Pro", status: "DRAFT", subtotal: "2499.00", taxAmount: "449.82", discountAmount: "0.00", totalAmount: "2948.82", currency: "INR", createdAt: "2026-10-15" },
    ];
  }

  const data = await apiRequest<PaginatedResponse<QuotationRecord> | QuotationRecord[]>("/quotations?page=1&pageSize=50");
  return Array.isArray(data) ? data : data.items || [];
}

export async function createQuotation(payload: CreateQuotationPayload): Promise<QuotationRecord> {
  const body = {
    customerId: payload.customerId,
    planId: payload.planId,
    currency: payload.currency.toUpperCase(),
    lines: payload.lines.map((l) => ({
      productId: l.productId,
      quantity: Number(l.quantity) || 1,
      unitPrice: String(l.unitPrice).replace(/[^0-9.]/g, ""),
    })),
    taxRuleIds: payload.taxRuleIds || [],
    discountCode: payload.discountCode ? payload.discountCode.trim().toUpperCase() : null,
  };

  return apiRequest<QuotationRecord>("/quotations", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function acceptQuotation(quotationId: string): Promise<{ quotation: QuotationRecord; subscriptionId: string }> {
  return apiRequest<{ quotation: QuotationRecord; subscriptionId: string }>(`/quotations/${quotationId}/accept`, {
    method: "POST",
  });
}

// ==========================================
// SUBSCRIPTIONS (EXACT FASTAPI SCHEMA)
// ==========================================
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
    startDate: payload.startDate || new Date().toISOString().split("T")[0],
    lines: payload.lines.map((l) => ({
      productId: l.productId,
      quantity: Number(l.quantity) || 1,
    })),
  };

  return apiRequest<SubscriptionItem>("/subscriptions", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// ==========================================
// INVOICES
// ==========================================
export async function fetchInvoices(): Promise<InvoiceRecord[]> {
  if (USE_MOCK) {
    return [
      { id: "inv-01", invoiceNumber: "INV-2026-0001", customerId: "cust-01", customerName: "Acme Cloud Corp", totalAmount: "2499.00", amountDue: "0.00", currency: "INR", status: "PAID", dueDate: "2026-11-15", createdAt: "2026-10-15" },
      { id: "inv-02", invoiceNumber: "INV-2026-0002", customerId: "cust-02", customerName: "Apex Design Labs", totalAmount: "499.00", amountDue: "499.00", currency: "INR", status: "CONFIRMED", dueDate: "2026-11-20", createdAt: "2026-10-20" },
    ];
  }

  const data = await apiRequest<PaginatedResponse<InvoiceRecord> | InvoiceRecord[]>("/invoices?page=1&pageSize=50");
  return Array.isArray(data) ? data : data.items || [];
}

export async function confirmInvoice(invoiceId: string): Promise<InvoiceRecord> {
  return apiRequest<InvoiceRecord>(`/invoices/${invoiceId}/confirm`, { method: "POST" });
}

export async function cancelInvoice(invoiceId: string): Promise<InvoiceRecord> {
  return apiRequest<InvoiceRecord>(`/invoices/${invoiceId}/cancel`, { method: "POST" });
}

export async function sendInvoice(invoiceId: string): Promise<{ status: string; message: string }> {
  return apiRequest<{ status: string; message: string }>(`/invoices/${invoiceId}/send`, { method: "POST" });
}

export async function downloadInvoicePdf(invoiceId: string, invoiceNumber = "invoice"): Promise<void> {
  const token = getAccessToken();
  const cleanBase = APP_CONFIG.API_BASE_URL.replace(/\/+$/, "");
  const response = await fetch(`${cleanBase}/invoices/${invoiceId}/pdf`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  if (!response.ok) {
    throw new Error(`Failed to download PDF (HTTP ${response.status})`);
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
// PAYMENTS
// ==========================================
export async function fetchPayments(): Promise<PaymentRecord[]> {
  if (USE_MOCK) {
    return [
      { id: "pay-01", paymentNumber: "PAY-2026-0001", invoiceId: "inv-01", amount: "2499.00", currency: "INR", method: "UPI", status: "SUCCEEDED", createdAt: "2026-10-16" },
    ];
  }

  const data = await apiRequest<PaginatedResponse<PaymentRecord> | PaymentRecord[]>("/payments?page=1&pageSize=50");
  return Array.isArray(data) ? data : data.items || [];
}

export async function recordPayment(payload: RecordPaymentPayload): Promise<PaymentRecord> {
  const body = {
    invoiceId: payload.invoiceId,
    amount: String(payload.amount).replace(/[^0-9.]/g, ""),
    currency: payload.currency.toUpperCase(),
    method: payload.method,
    reference: payload.reference || null,
  };

  return apiRequest<PaymentRecord>("/payments", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// ==========================================
// NOTIFICATIONS
// ==========================================
export async function fetchNotifications(): Promise<NotificationItem[]> {
  if (USE_MOCK) {
    return [
      { id: "notif-01", type: "INVOICE_ISSUED", title: "Invoice Issued", message: "Invoice INV-2026-0002 has been generated.", isRead: false, createdAt: new Date().toISOString() },
    ];
  }

  const data = await apiRequest<PaginatedResponse<NotificationItem> | NotificationItem[]>("/notifications?page=1&pageSize=20");
  return Array.isArray(data) ? data : data.items || [];
}

export async function markNotificationRead(id: string): Promise<void> {
  if (USE_MOCK) return;
  await apiRequest(`/notifications/${id}/read`, { method: "POST" });
}

export async function markAllNotificationsRead(): Promise<void> {
  if (USE_MOCK) return;
  await apiRequest("/notifications/read-all", { method: "POST" });
}

// ==========================================
// ANALYTICS (ALIGNED)
// ==========================================
export async function fetchAnalyticsDashboard(currency = "INR"): Promise<AnalyticsDashboard> {
  if (USE_MOCK) {
    return {
      currency,
      activeSubscriptions: 4,
      collectedRevenue: "42890.00",
      outstandingBalance: "1280.00",
      overdueInvoiceCount: 1,
      mrr: "3574.00",
      arr: "42888.00",
      totalInvoices: 12,
      upcomingRenewalsCount: 2,
    };
  }

  // Aligned: backend FastAPI endpoint is /analytics/summary
  return apiRequest<AnalyticsDashboard>(`/analytics/summary?currency=${encodeURIComponent(currency)}`);
}
