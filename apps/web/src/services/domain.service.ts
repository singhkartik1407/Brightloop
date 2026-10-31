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
// NORMALIZATION HELPERS
// ==========================================
function normalizeCustomer(c: any): CustomerRecord {
  return {
    id: c.id,
    displayName: c.displayName || c.display_name || "",
    companyName: c.companyName || c.company_name || null,
    billingEmail: c.billingEmail || c.billing_email || "",
    phone: c.phone || null,
    billingState: c.billingState || c.billing_state || null,
    status: c.is_active === false || c.status === "INACTIVE" ? "INACTIVE" : "ACTIVE",
    createdAt: c.createdAt || c.created_at || new Date().toISOString(),
  };
}

function normalizeProduct(p: any): ProductRecord {
  const notes = p.notes || "";
  const sku = notes.startsWith("SKU: ") ? notes.replace("SKU: ", "") : `SKU-${String(p.id).slice(0, 8).toUpperCase()}`;
  return {
    id: p.id,
    name: p.name,
    sku,
    basePrice: p.salesPrice ?? p.sales_price ?? "0.00",
    currency: p.currency || APP_CONFIG.DEFAULT_CURRENCY,
    isActive: p.isActive ?? p.is_active ?? true,
    createdAt: p.createdAt ?? p.created_at ?? new Date().toISOString(),
  };
}

function normalizePlan(p: any): PlanItem {
  return {
    id: p.id,
    name: p.name,
    price: p.price ?? "0.00",
    currency: p.currency || APP_CONFIG.DEFAULT_CURRENCY,
    billingInterval: p.billingInterval || p.billing_interval || "MONTHLY",
    intervalCount: p.intervalCount || p.interval_count || 1,
    isActive: p.isActive ?? p.is_active ?? true,
    activeSubscribers: p.activeSubscribers ?? p.active_subscribers ?? 0,
  };
}

function normalizeTaxRule(t: any): TaxRuleRecord {
  return {
    id: t.id,
    name: t.name,
    code: t.code,
    taxType: t.taxType || t.tax_type,
    ratePercentage: String(t.ratePercent ?? t.rate_percent ?? t.ratePercentage ?? "0.00"),
    jurisdiction: t.jurisdiction || "National",
    isInclusive: t.isInclusive ?? t.is_inclusive ?? false,
    isActive: t.isActive ?? t.is_active ?? true,
    createdAt: t.createdAt ?? t.created_at ?? new Date().toISOString(),
  };
}

function normalizeDiscount(d: any): DiscountRecord {
  return {
    id: d.id,
    name: d.name,
    code: d.code || "",
    discountType: d.discountType || d.discount_type || "PERCENTAGE",
    value: String(d.value ?? "0.00"),
    maxUsage: d.maxUses ?? d.max_uses ?? d.maxUsage ?? null,
    isActive: d.isActive ?? d.is_active ?? true,
    createdAt: d.createdAt ?? d.created_at ?? new Date().toISOString(),
  };
}

function normalizeQuotation(q: any): QuotationRecord {
  const item = q?.quotation ? q.quotation : q;
  const subId = item?.subscriptionId || item?.subscription_id || q?.subscriptionId || q?.subscription_id || null;
  return {
    id: item.id,
    quotationNumber: item.quotationNumber || item.number || `QUO-${String(item.id).slice(0, 8)}`,
    customerId: item.customerId || item.customer_id,
    customerName: item.customerName || item.customer_name || "Customer",
    planId: item.planId || item.plan_id,
    planName: item.planName || item.plan_name || "Selected Plan",
    status: item.status,
    subtotal: item.subtotal ?? "0.00",
    taxAmount: item.taxAmount ?? item.taxTotal ?? item.tax_total ?? "0.00",
    discountAmount: item.discountAmount ?? item.discountTotal ?? item.discount_total ?? "0.00",
    totalAmount: item.totalAmount ?? item.total ?? "0.00",
    currency: item.currency || APP_CONFIG.DEFAULT_CURRENCY,
    subscriptionId: subId,
    createdAt: item.createdAt ?? item.created_at ?? new Date().toISOString(),
  };
}

function normalizeSubscription(sub: any): SubscriptionItem {
  return {
    id: sub.id,
    subscriptionNumber: sub.subscriptionNumber || sub.number || `SUB-${String(sub.id).slice(0, 8)}`,
    customerId: sub.customerId || sub.customer_id,
    customerName: sub.customerName || sub.customer_name || "Customer",
    planId: sub.planId || sub.plan_id,
    planName: sub.planName || sub.plan_name || "Plan",
    quotationId: sub.quotationId || sub.quotation_id || null,
    status: sub.status,
    currency: sub.currency || APP_CONFIG.DEFAULT_CURRENCY,
    price: sub.price ?? sub.recurringSubtotal ?? sub.recurring_subtotal ?? "0.00",
    billingInterval: sub.billingInterval || sub.billing_interval || "MONTHLY",
    currentPeriodStart: sub.currentPeriodStart || sub.current_period_start || "",
    currentPeriodEnd: sub.currentPeriodEnd || sub.current_period_end || "",
    nextBillingDate: sub.nextBillingDate || sub.next_billing_date || "",
    cancelAtPeriodEnd: sub.cancelAtPeriodEnd ?? sub.cancel_at_period_end ?? false,
    createdAt: sub.createdAt || sub.created_at || new Date().toISOString(),
  };
}

function normalizeInvoice(inv: any): InvoiceRecord {
  return {
    id: inv.id,
    invoiceNumber: inv.invoiceNumber || inv.number || `INV-${String(inv.id).slice(0, 8)}`,
    customerId: inv.customerId || inv.customer_id,
    customerName: inv.customerName || inv.customer_name || "Customer",
    subscriptionId: inv.subscriptionId || inv.subscription_id || null,
    totalAmount: inv.totalAmount ?? inv.total ?? "0.00",
    amountDue: inv.amountDue ?? inv.amount_due ?? "0.00",
    currency: inv.currency || APP_CONFIG.DEFAULT_CURRENCY,
    status: inv.status,
    dueDate: inv.dueDate || inv.due_date || "",
    createdAt: inv.createdAt || inv.created_at || inv.issueDate || inv.issue_date || new Date().toISOString(),
  };
}

function normalizePayment(pay: any): PaymentRecord {
  return {
    id: pay.id,
    paymentNumber: pay.paymentNumber || pay.number || pay.reference || `PAY-${String(pay.id).slice(0, 8)}`,
    invoiceId: pay.invoiceId || pay.invoice_id,
    amount: pay.amount ?? "0.00",
    currency: pay.currency || APP_CONFIG.DEFAULT_CURRENCY,
    method: pay.method,
    status: pay.status,
    reference: pay.reference || null,
    createdAt: pay.createdAt || pay.created_at || new Date().toISOString(),
  };
}

function normalizeNotification(n: any): NotificationItem {
  return {
    id: n.id,
    type: n.type || n.notificationType || n.notification_type || "OTHER",
    title: n.title,
    message: n.message,
    isRead: n.isRead ?? n.is_read ?? false,
    resourceType: n.relatedEntityType || n.related_entity_type || null,
    resourceId: n.relatedEntityId || n.related_entity_id || null,
    createdAt: n.createdAt || n.created_at || new Date().toISOString(),
  };
}

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

  const data = await apiRequest<PaginatedResponse<any> | any[]>(`/customers?${query.toString()}`);
  const items = Array.isArray(data) ? data : data.items || [];
  return items.map(normalizeCustomer);
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
    display_name: payload.displayName.trim(),
    billing_email: payload.billingEmail.trim(),
    company_name: payload.companyName ? payload.companyName.trim() : null,
    phone: payload.phone ? payload.phone.trim() : null,
  };

  const res = await apiRequest<any>("/customers", {
    method: "POST",
    body: JSON.stringify(body),
  });
  return normalizeCustomer(res);
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

  const data = await apiRequest<PaginatedResponse<any> | any[]>("/products?page=1&pageSize=50");
  const items = Array.isArray(data) ? data : data.items || [];
  return items.map(normalizeProduct);
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

  const cleanPrice = String(payload.basePrice).replace(/[^0-9.]/g, "") || "0.00";
  const body = {
    name: payload.name.trim(),
    type: "SERVICE",
    salesPrice: cleanPrice,
    costPrice: "0.00",
    currency: (payload.currency || APP_CONFIG.DEFAULT_CURRENCY).toUpperCase(),
    notes: payload.sku ? `SKU: ${payload.sku.trim()}` : null,
  };

  const res = await apiRequest<any>("/products", {
    method: "POST",
    body: JSON.stringify(body),
  });
  return normalizeProduct(res);
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

  const data = await apiRequest<PaginatedResponse<any> | any[]>("/plans?page=1&pageSize=50");
  const items = Array.isArray(data) ? data : data.items || [];
  return items.map(normalizePlan);
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
    minQuantity: 1,
  };

  const res = await apiRequest<any>("/plans", {
    method: "POST",
    body: JSON.stringify(body),
  });
  return normalizePlan(res);
}

// ==========================================
// TAX RULES & DISCOUNTS
// ==========================================
export async function fetchTaxRules(): Promise<TaxRuleRecord[]> {
  if (USE_MOCK) {
    return [
      { id: "tax-01", name: "GST Standard", code: "GST-18", taxType: "IGST", ratePercentage: "18.00", isInclusive: false, isActive: true, createdAt: "2026-10-01" },
    ];
  }

  const data = await apiRequest<PaginatedResponse<any> | any[]>("/tax-rules?page=1&pageSize=50");
  const items = Array.isArray(data) ? data : data.items || [];
  return items.map(normalizeTaxRule);
}

export async function createTaxRule(payload: CreateTaxRulePayload): Promise<TaxRuleRecord> {
  const body = {
    name: payload.name.trim(),
    code: payload.code.trim().toUpperCase(),
    taxType: payload.taxType,
    ratePercent: String(payload.ratePercentage).replace(/[^0-9.]/g, ""),
    jurisdiction: payload.jurisdiction || "National",
    isInclusive: Boolean(payload.isInclusive),
  };

  const res = await apiRequest<any>("/tax-rules", {
    method: "POST",
    body: JSON.stringify(body),
  });
  return normalizeTaxRule(res);
}

export async function fetchDiscounts(): Promise<DiscountRecord[]> {
  if (USE_MOCK) {
    return [
      { id: "disc-01", name: "Early Bird", code: "EARLY10", discountType: "PERCENTAGE", value: "10.00", maxUsage: 100, isActive: true, createdAt: "2026-10-01" },
    ];
  }

  const data = await apiRequest<PaginatedResponse<any> | any[]>("/discount-rules?page=1&pageSize=50");
  const items = Array.isArray(data) ? data : data.items || [];
  return items.map(normalizeDiscount);
}

export async function createDiscount(payload: CreateDiscountPayload): Promise<DiscountRecord> {
  const now = new Date();
  const nextYear = new Date(now.getTime() + 365 * 24 * 3600 * 1000);
  const body: Record<string, any> = {
    name: payload.name.trim(),
    code: payload.code.trim().toUpperCase(),
    discountType: payload.discountType,
    value: String(payload.value).replace(/[^0-9.]/g, ""),
    scope: "SUBSCRIPTION",
    startsAt: now.toISOString(),
    endsAt: nextYear.toISOString(),
    isActive: true,
  };
  if (payload.maxUsage) {
    body.maxUses = Number(payload.maxUsage);
  }

  const res = await apiRequest<any>("/discount-rules", {
    method: "POST",
    body: JSON.stringify(body),
  });
  return normalizeDiscount(res);
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

  const data = await apiRequest<PaginatedResponse<any> | any[]>("/quotations?page=1&pageSize=50");
  const items = Array.isArray(data) ? data : data.items || [];
  return items.map(normalizeQuotation);
}

export async function createQuotation(payload: CreateQuotationPayload): Promise<QuotationRecord> {
  const today = new Date().toISOString().split("T")[0];
  const body = {
    customerId: payload.customerId,
    planId: payload.planId,
    startDate: today,
    lines: payload.lines.map((l) => ({
      productId: l.productId,
      quantity: Number(l.quantity) || 1,
      selectedVariantIds: [],
      taxRuleIds: payload.taxRuleIds && payload.taxRuleIds.length > 0 ? payload.taxRuleIds : undefined,
    })),
    discountCode: payload.discountCode ? payload.discountCode.trim().toUpperCase() : null,
  };

  const res = await apiRequest<any>("/quotations", {
    method: "POST",
    body: JSON.stringify(body),
  });
  return normalizeQuotation(res);
}

export async function acceptQuotation(quotationId: string): Promise<{ quotation: QuotationRecord; subscriptionId: string }> {
  const res = await apiRequest<any>(`/quotations/${quotationId}/accept`, {
    method: "POST",
  });
  const quoteData = res?.quotation ? res.quotation : res;
  const subId = res?.subscriptionId || res?.subscription_id || quoteData?.subscriptionId || quoteData?.subscription_id || "";
  const normalized = normalizeQuotation(quoteData);
  if (subId && !normalized.subscriptionId) {
    normalized.subscriptionId = subId;
  }
  return {
    ...normalized,
    subscriptionId: subId || normalized.subscriptionId || "",
    quotation: normalized,
  };
}

// ==========================================
// SUBSCRIPTIONS (HTTP 422 RESOLVED)
// ==========================================
export async function fetchSubscriptions(): Promise<SubscriptionItem[]> {
  if (USE_MOCK) {
    return [
      { id: "sub-01", customerId: "cust-01", customerName: "Acme Cloud Corp", planId: "plan-02", planName: "Enterprise Pro", status: "ACTIVE", price: "2499.00", currency: "INR", billingInterval: "MONTHLY", currentPeriodEnd: "2026-11-15" },
      { id: "sub-02", customerId: "cust-02", customerName: "Apex Design Labs", planId: "plan-01", planName: "Starter Growth", status: "TRIAL", price: "499.00", currency: "INR", billingInterval: "MONTHLY", currentPeriodEnd: "2026-11-22" },
    ];
  }

  const data = await apiRequest<PaginatedResponse<any> | any[]>("/subscriptions?page=1&pageSize=50");
  const items = Array.isArray(data) ? data : data.items || [];
  return items.map(normalizeSubscription);
}

export async function createSubscription(payload: CreateSubscriptionPayload): Promise<SubscriptionItem> {
  if (USE_MOCK) {
    return {
      id: `sub-${Date.now()}`,
      customerId: payload.customerId,
      planId: payload.planId,
      status: "ACTIVE",
      price: payload.lines[0]?.unitPrice || "499.00",
      currency: "INR",
      billingInterval: "MONTHLY",
      createdAt: new Date().toISOString(),
    };
  }

  // Exact FastAPI SubscriptionCreateRequest schema:
  // - Top-level currency removed
  // - Mandatory lines array passed
  const body = {
    customerId: payload.customerId,
    planId: payload.planId,
    startDate: payload.startDate || new Date().toISOString().split("T")[0],
    lines: payload.lines.map((l) => ({
      planId: l.planId || payload.planId,
      productId: l.productId || null,
      variantId: l.variantId || null,
      quantity: Number(l.quantity) || 1,
      unitPrice: String(l.unitPrice).replace(/[^0-9.]/g, ""),
    })),
  };

  const res = await apiRequest<any>("/subscriptions", {
    method: "POST",
    body: JSON.stringify(body),
  });
  return normalizeSubscription(res);
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

  const data = await apiRequest<PaginatedResponse<any> | any[]>("/invoices?page=1&pageSize=50");
  const items = Array.isArray(data) ? data : data.items || [];
  return items.map(normalizeInvoice);
}

export async function confirmInvoice(invoiceId: string): Promise<InvoiceRecord> {
  const res = await apiRequest<any>(`/invoices/${invoiceId}/confirm`, { method: "POST" });
  return normalizeInvoice(res);
}

export async function cancelInvoice(invoiceId: string): Promise<InvoiceRecord> {
  const res = await apiRequest<any>(`/invoices/${invoiceId}/cancel`, { method: "POST" });
  return normalizeInvoice(res);
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

  const data = await apiRequest<PaginatedResponse<any> | any[]>("/payments?page=1&pageSize=50");
  const items = Array.isArray(data) ? data : data.items || [];
  return items.map(normalizePayment);
}

export async function recordPayment(payload: RecordPaymentPayload): Promise<PaymentRecord> {
  const body = {
    invoiceId: payload.invoiceId,
    amount: String(payload.amount).replace(/[^0-9.]/g, ""),
    currency: payload.currency.toUpperCase(),
    method: payload.method,
    paidAt: new Date().toISOString(),
    reference: payload.reference || null,
  };

  const res = await apiRequest<any>("/payments", {
    method: "POST",
    body: JSON.stringify(body),
  });
  return normalizePayment(res);
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

  const data = await apiRequest<PaginatedResponse<any> | any[]>("/notifications?page=1&pageSize=20");
  const items = Array.isArray(data) ? data : data.items || [];
  return items.map(normalizeNotification);
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
// ANALYTICS
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

  const data = await apiRequest<any>(`/analytics/summary?currency=${encodeURIComponent(currency)}`);
  return {
    currency: data.currency || currency,
    activeSubscriptions: data.activeSubscriptions ?? data.active_subscriptions ?? 0,
    collectedRevenue: data.revenueReceived ?? data.revenue_received ?? data.collectedRevenue ?? "0.00",
    outstandingBalance: data.outstandingAmount ?? data.outstanding_amount ?? data.outstandingBalance ?? "0.00",
    overdueInvoiceCount: data.overdueInvoiceCount ?? data.overdue_invoice_count ?? 0,
    mrr: data.mrr ?? "0.00",
    arr: data.arr ?? "0.00",
    totalInvoices: data.totalInvoices ?? data.total_invoices ?? 0,
    upcomingRenewalsCount: data.upcomingRenewals ?? data.upcoming_renewals ?? 0,
  };
}
