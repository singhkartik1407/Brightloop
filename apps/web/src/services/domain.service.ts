import { apiRequest, getAccessToken } from "./api";
import { APP_CONFIG } from "./mock.config";
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
// RESILIENT NORMALIZERS (snake_case -> camelCase)
// ==========================================
function normalizeCustomer(raw: any): CustomerRecord {
  return {
    id: raw.id,
    displayName: raw.display_name || raw.displayName || raw.name || "Customer",
    companyName: raw.company_name || raw.companyName || null,
    billingEmail: raw.billing_email || raw.billingEmail || raw.email || "",
    phone: raw.phone || null,
    billingState: raw.billing_state || raw.billingState || "Maharashtra",
    status: raw.status || "ACTIVE",
    createdAt: raw.created_at || raw.createdAt || new Date().toISOString(),
  };
}

function normalizeProduct(raw: any): ProductRecord {
  let sku = raw.sku || "";
  if (!sku && raw.notes && String(raw.notes).includes("SKU:")) {
    const match = String(raw.notes).match(/SKU:\s*([^\s;]+)/i);
    if (match) sku = match[1];
  }
  return {
    id: raw.id,
    name: raw.name || "Unnamed Product",
    description: raw.description || raw.notes || null,
    sku: sku || raw.code || "SKU-GEN",
    salesPrice: raw.sales_price !== undefined ? raw.sales_price : (raw.basePrice || "0.00"),
    currency: raw.currency || "INR",
    type: raw.type || "SERVICE",
    isActive: raw.is_active !== undefined ? raw.is_active : true,
    createdAt: raw.created_at || raw.createdAt || new Date().toISOString(),
  };
}

function normalizePlan(raw: any): PlanItem {
  return {
    id: raw.id,
    name: raw.name || "Plan",
    description: raw.description || null,
    price: raw.price !== undefined ? raw.price : "0.00",
    currency: raw.currency || "INR",
    billingInterval: raw.billing_interval || raw.billingInterval || raw.interval || "MONTHLY",
    intervalCount: raw.interval_count || raw.intervalCount || 1,
    trialDays: raw.trial_days || raw.trialDays || 0,
    isActive: raw.is_active !== undefined ? raw.is_active : true,
    activeSubscribers: raw.active_subscribers || raw.activeSubscribers || 0,
    createdAt: raw.created_at || raw.createdAt,
  };
}

function normalizeQuotation(raw: any): QuotationRecord {
  return {
    id: raw.id,
    quotationNumber: raw.quotation_number || raw.quotationNumber || `QUO-${raw.id.slice(0, 8)}`,
    customerId: raw.customer_id || raw.customerId,
    customerName: raw.customer_name || raw.customerName,
    planId: raw.plan_id || raw.planId,
    planName: raw.plan_name || raw.planName,
    status: raw.status || "DRAFT",
    subtotal: raw.subtotal !== undefined ? raw.subtotal : "0.00",
    taxAmount: raw.tax_amount !== undefined ? raw.tax_amount : (raw.taxAmount || "0.00"),
    discountAmount: raw.discount_amount !== undefined ? raw.discount_amount : (raw.discountAmount || "0.00"),
    totalAmount: raw.total_amount !== undefined ? raw.total_amount : (raw.totalAmount || "0.00"),
    currency: raw.currency || "INR",
    subscriptionId: raw.subscription_id || raw.subscriptionId || null,
    createdAt: raw.created_at || raw.createdAt || new Date().toISOString(),
  };
}

function normalizeInvoice(raw: any): InvoiceRecord {
  return {
    id: raw.id,
    invoiceNumber: raw.invoice_number || raw.invoiceNumber || `INV-${raw.id.slice(0, 8)}`,
    customerId: raw.customer_id || raw.customerId,
    customerName: raw.customer_name || raw.customerName,
    subscriptionId: raw.subscription_id || raw.subscriptionId || null,
    totalAmount: raw.total_amount !== undefined ? raw.total_amount : (raw.totalAmount || "0.00"),
    amountDue: raw.amount_due !== undefined ? raw.amount_due : (raw.amountDue || "0.00"),
    currency: raw.currency || "INR",
    status: raw.status || "DRAFT",
    dueDate: raw.due_date || raw.dueDate || "",
    createdAt: raw.created_at || raw.createdAt || new Date().toISOString(),
  };
}

function normalizePayment(raw: any): PaymentRecord {
  return {
    id: raw.id,
    paymentNumber: raw.payment_number || raw.paymentNumber || `PAY-${raw.id.slice(0, 8)}`,
    invoiceId: raw.invoice_id || raw.invoiceId,
    amount: raw.amount || "0.00",
    currency: raw.currency || "INR",
    method: raw.method || "UPI",
    status: raw.status || "SUCCEEDED",
    reference: raw.reference || null,
    createdAt: raw.created_at || raw.createdAt || new Date().toISOString(),
  };
}

// ==========================================
// CUSTOMERS
// ==========================================
export async function fetchCustomers(search = ""): Promise<CustomerRecord[]> {
  const query = new URLSearchParams({ page: "1", pageSize: "50" });
  if (search.trim()) query.set("search", search.trim());

  const data = await apiRequest<PaginatedResponse<any> | any[]>(`/customers?${query.toString()}`);
  const items = Array.isArray(data) ? data : data.items || [];
  return items.map(normalizeCustomer);
}

export async function createCustomer(payload: CreateCustomerPayload): Promise<CustomerRecord> {
  const body = {
    display_name: payload.displayName.trim(),
    billing_email: payload.billingEmail.trim(),
    company_name: payload.companyName ? payload.companyName.trim() : null,
    phone: payload.phone ? payload.phone.trim() : null,
    billing_state: payload.billingState || "Maharashtra",
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
  const data = await apiRequest<PaginatedResponse<any> | any[]>("/products?page=1&pageSize=50");
  const items = Array.isArray(data) ? data : data.items || [];
  return items.map(normalizeProduct);
}

export async function createProduct(payload: CreateProductPayload): Promise<ProductRecord> {
  const cleanPrice = String(payload.salesPrice).replace(/[^0-9.]/g, "");
  const body = {
    name: payload.name.trim(),
    type: payload.type || "SERVICE",
    sales_price: cleanPrice,
    cost_price: "0.00",
    currency: payload.currency.toUpperCase(),
    notes: `SKU: ${payload.sku.trim()}`,
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
  const data = await apiRequest<PaginatedResponse<any> | any[]>("/plans?page=1&pageSize=50");
  const items = Array.isArray(data) ? data : data.items || [];
  return items.map(normalizePlan);
}

export async function createPlan(payload: CreatePlanPayload): Promise<PlanItem> {
  const cleanPrice = String(payload.price).replace(/[^0-9.]/g, "");
  const body = {
    name: payload.name.trim(),
    description: payload.description || `Billing tier for ${payload.name.trim()}`,
    price: cleanPrice,
    currency: (payload.currency || APP_CONFIG.DEFAULT_CURRENCY).toUpperCase(),
    billing_interval: payload.billingInterval,
    interval_count: Number(payload.intervalCount) || 1,
  };

  const res = await apiRequest<any>("/plans", {
    method: "POST",
    body: JSON.stringify(body),
  });
  return normalizePlan(res);
}

// ==========================================
// TAX RULES & DISCOUNT RULES
// ==========================================
export async function fetchTaxRules(): Promise<TaxRuleRecord[]> {
  const data = await apiRequest<PaginatedResponse<TaxRuleRecord> | TaxRuleRecord[]>("/tax-rules?page=1&pageSize=50");
  return Array.isArray(data) ? data : data.items || [];
}

export async function createTaxRule(payload: CreateTaxRulePayload): Promise<TaxRuleRecord> {
  const body = {
    name: payload.name.trim(),
    code: payload.code.trim().toUpperCase(),
    tax_type: payload.taxType,
    rate_percentage: String(payload.ratePercentage).replace(/[^0-9.]/g, ""),
    jurisdiction: payload.jurisdiction || "National",
    is_inclusive: payload.isInclusive,
  };

  return apiRequest<TaxRuleRecord>("/tax-rules", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function fetchDiscounts(): Promise<DiscountRecord[]> {
  const data = await apiRequest<PaginatedResponse<DiscountRecord> | DiscountRecord[]>("/discount-rules?page=1&pageSize=50");
  return Array.isArray(data) ? data : data.items || [];
}

export async function createDiscount(payload: CreateDiscountPayload): Promise<DiscountRecord> {
  const body = {
    name: payload.name.trim(),
    code: payload.code.trim().toUpperCase(),
    discount_type: payload.discountType,
    value: String(payload.value).replace(/[^0-9.]/g, ""),
    max_usage: payload.maxUsage || null,
  };

  return apiRequest<DiscountRecord>("/discount-rules", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// ==========================================
// QUOTATIONS
// ==========================================
export async function fetchQuotations(): Promise<QuotationRecord[]> {
  const data = await apiRequest<PaginatedResponse<any> | any[]>("/quotations?page=1&pageSize=50");
  const items = Array.isArray(data) ? data : data.items || [];
  return items.map(normalizeQuotation);
}

export async function createQuotation(payload: CreateQuotationPayload): Promise<QuotationRecord> {
  const body = {
    customer_id: payload.customerId,
    plan_id: payload.planId,
    start_date: payload.startDate || new Date().toISOString().split("T")[0],
    lines: payload.lines.map((l) => ({
      product_id: l.productId,
      quantity: Number(l.quantity) || 1,
    })),
    discount_code: payload.discountCode ? payload.discountCode.trim().toUpperCase() : null,
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
  return {
    quotation: normalizeQuotation(res.quotation || res),
    subscriptionId: res.subscription_id || res.subscriptionId || "",
  };
}

// ==========================================
// SUBSCRIPTIONS
// ==========================================
export async function fetchSubscriptions(): Promise<SubscriptionItem[]> {
  const data = await apiRequest<PaginatedResponse<any> | any[]>("/subscriptions?page=1&pageSize=50");
  const items = Array.isArray(data) ? data : data.items || [];
  return items.map((raw) => ({
    id: raw.id,
    subscriptionNumber: raw.subscription_number || raw.subscriptionNumber || `SUB-${raw.id.slice(0, 8)}`,
    customerId: raw.customer_id || raw.customerId,
    customerName: raw.customer_name || raw.customerName,
    planId: raw.plan_id || raw.planId,
    planName: raw.plan_name || raw.planName,
    quotationId: raw.quotation_id || raw.quotationId || null,
    status: raw.status || "ACTIVE",
    price: raw.price || "0.00",
    currency: raw.currency || "INR",
    billingInterval: raw.billing_interval || raw.billingInterval || "MONTHLY",
    currentPeriodEnd: raw.current_period_end || raw.currentPeriodEnd,
    createdAt: raw.created_at || raw.createdAt,
  }));
}

export async function createSubscription(payload: CreateSubscriptionPayload): Promise<SubscriptionItem> {
  const body = {
    customer_id: payload.customerId,
    plan_id: payload.planId,
    start_date: payload.startDate || new Date().toISOString().split("T")[0],
    lines: payload.lines.map((l) => ({
      product_id: l.productId,
      quantity: Number(l.quantity) || 1,
    })),
  };

  const raw = await apiRequest<any>("/subscriptions", {
    method: "POST",
    body: JSON.stringify(body),
  });

  return {
    id: raw.id,
    subscriptionNumber: raw.subscription_number || raw.subscriptionNumber || `SUB-${raw.id.slice(0, 8)}`,
    customerId: raw.customer_id || raw.customerId,
    customerName: raw.customer_name || raw.customerName,
    planId: raw.plan_id || raw.planId,
    planName: raw.plan_name || raw.planName,
    status: raw.status || "ACTIVE",
    price: raw.price || "0.00",
    currency: raw.currency || "INR",
    billingInterval: raw.billing_interval || raw.billingInterval || "MONTHLY",
    createdAt: raw.created_at || raw.createdAt,
  };
}

// ==========================================
// INVOICES
// ==========================================
export async function fetchInvoices(): Promise<InvoiceRecord[]> {
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
  const data = await apiRequest<PaginatedResponse<any> | any[]>("/payments?page=1&pageSize=50");
  const items = Array.isArray(data) ? data : data.items || [];
  return items.map(normalizePayment);
}

export async function recordPayment(payload: RecordPaymentPayload): Promise<PaymentRecord> {
  const body = {
    invoice_id: payload.invoiceId,
    amount: String(payload.amount).replace(/[^0-9.]/g, ""),
    currency: payload.currency.toUpperCase(),
    method: payload.method,
    reference: payload.reference || null,
    paid_at: new Date().toISOString(),
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
  const data = await apiRequest<PaginatedResponse<NotificationItem> | NotificationItem[]>("/notifications?page=1&pageSize=20");
  return Array.isArray(data) ? data : data.items || [];
}

export async function markNotificationRead(id: string): Promise<void> {
  await apiRequest(`/notifications/${id}/read`, { method: "POST" });
}

export async function markAllNotificationsRead(): Promise<void> {
  await apiRequest("/notifications/read-all", { method: "POST" });
}

// ==========================================
// ANALYTICS (EXACT SUMMARY RESPONSE MAPPING)
// ==========================================
export async function fetchAnalyticsDashboard(currency = "INR"): Promise<AnalyticsDashboard> {
  const raw = await apiRequest<any>(`/analytics/summary?currency=${encodeURIComponent(currency)}`);
  return {
    currency: raw.currency || currency,
    activeSubscriptions: raw.active_subscriptions || raw.activeSubscriptions || 0,
    collectedRevenue: raw.total_collected_revenue !== undefined ? raw.total_collected_revenue : (raw.collected_revenue || raw.collectedRevenue || "0.00"),
    outstandingBalance: raw.total_outstanding !== undefined ? raw.total_outstanding : (raw.outstanding_balance || raw.outstandingBalance || "0.00"),
    overdueInvoiceCount: raw.overdue_invoice_count || raw.overdueInvoiceCount || 0,
    mrr: raw.mrr !== undefined ? raw.mrr : "0.00",
    arr: raw.arr !== undefined ? raw.arr : "0.00",
    totalInvoices: raw.total_invoices || raw.totalInvoices || 0,
    upcomingRenewalsCount: raw.upcoming_renewals || raw.upcomingRenewalsCount || 0,
  };
}
