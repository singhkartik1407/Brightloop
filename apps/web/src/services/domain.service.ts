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
    salesPrice: raw.sales_price !== undefined ? raw.sales_price : (raw.salesPrice !== undefined ? raw.salesPrice : (raw.basePrice || "0.00")),
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
  // Authoritative fallback chain: total -> total_amount -> totalAmount
  const totalVal = raw.total !== undefined ? raw.total : (raw.total_amount !== undefined ? raw.total_amount : (raw.totalAmount !== undefined ? raw.totalAmount : "0.00"));
  const taxVal = raw.tax_total !== undefined ? raw.tax_total : (raw.taxTotal !== undefined ? raw.taxTotal : (raw.tax_amount !== undefined ? raw.tax_amount : (raw.taxAmount || "0.00")));
  const discountVal = raw.discount_total !== undefined ? raw.discount_total : (raw.discountTotal !== undefined ? raw.discountTotal : (raw.discount_amount !== undefined ? raw.discount_amount : (raw.discountAmount || "0.00")));
  const subtotalVal = raw.subtotal !== undefined ? raw.subtotal : (raw.sub_total !== undefined ? raw.sub_total : "0.00");

  return {
    id: raw.id,
    quotationNumber: raw.quotation_number || raw.quotationNumber || `QUO-${raw.id.slice(0, 8)}`,
    customerId: raw.customer_id || raw.customerId,
    customerName: raw.customer_name || raw.customerName,
    planId: raw.plan_id || raw.planId,
    planName: raw.plan_name || raw.planName,
    status: raw.status || "DRAFT",
    subtotal: subtotalVal,
    taxAmount: taxVal,
    discountAmount: discountVal,
    totalAmount: totalVal,
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
    totalAmount: raw.total_amount !== undefined ? raw.total_amount : (raw.totalAmount !== undefined ? raw.totalAmount : (raw.total || "0.00")),
    amountDue: raw.amount_due !== undefined ? raw.amount_due : (raw.amountDue !== undefined ? raw.amountDue : (raw.due_amount || "0.00")),
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
// TAX RULES
// ==========================================
export async function fetchTaxRules(): Promise<TaxRuleRecord[]> {
  const data = await apiRequest<PaginatedResponse<any> | any[]>("/tax-rules?page=1&pageSize=50");
  const items = Array.isArray(data) ? data : data.items || [];
  return items.map((raw) => ({
    id: raw.id,
    name: raw.name || "Tax Rule",
    code: raw.code || "TAX",
    taxType: raw.tax_type || raw.taxType || "IGST",
    ratePercent: Number(raw.rate_percent !== undefined ? raw.rate_percent : (raw.ratePercent !== undefined ? raw.ratePercent : (raw.rate_percentage || 0))),
    jurisdiction: raw.jurisdiction || "National",
    isInclusive: Boolean(raw.is_inclusive !== undefined ? raw.is_inclusive : raw.isInclusive),
    isActive: Boolean(raw.is_active !== undefined ? raw.is_active : true),
    createdAt: raw.created_at || raw.createdAt || new Date().toISOString(),
  }));
}

export async function createTaxRule(payload: CreateTaxRulePayload): Promise<TaxRuleRecord> {
  // Schema strictly expects ratePercent as numeric and forbids extra inputs
  const body = {
    name: payload.name.trim(),
    code: payload.code.trim().toUpperCase(),
    taxType: payload.taxType,
    ratePercent: Number(payload.ratePercent),
    jurisdiction: payload.jurisdiction || "National",
    isInclusive: Boolean(payload.isInclusive),
  };

  const res = await apiRequest<any>("/tax-rules", {
    method: "POST",
    body: JSON.stringify(body),
  });

  return {
    id: res.id,
    name: res.name,
    code: res.code,
    taxType: res.tax_type || res.taxType || payload.taxType,
    ratePercent: Number(res.rate_percent !== undefined ? res.rate_percent : (res.ratePercent !== undefined ? res.ratePercent : payload.ratePercent)),
    jurisdiction: res.jurisdiction || payload.jurisdiction,
    isInclusive: Boolean(res.is_inclusive !== undefined ? res.is_inclusive : payload.isInclusive),
    isActive: Boolean(res.is_active !== undefined ? res.is_active : true),
    createdAt: res.created_at || res.createdAt || new Date().toISOString(),
  };
}

// ==========================================
// DISCOUNT RULES
// ==========================================
export async function fetchDiscounts(): Promise<DiscountRecord[]> {
  const data = await apiRequest<PaginatedResponse<any> | any[]>("/discount-rules?page=1&pageSize=50");
  const items = Array.isArray(data) ? data : data.items || [];
  return items.map((raw) => ({
    id: raw.id,
    name: raw.name || "Discount",
    code: raw.code || "DISC",
    discountType: raw.discount_type || raw.discountType || "PERCENTAGE",
    value: raw.value || 0,
    scope: raw.scope || "GLOBAL",
    startsAt: raw.starts_at || raw.startsAt || new Date().toISOString(),
    endsAt: raw.ends_at || raw.endsAt || new Date(Date.now() + 365 * 86400000).toISOString(),
    isActive: Boolean(raw.is_active !== undefined ? raw.is_active : true),
    createdAt: raw.created_at || raw.createdAt || new Date().toISOString(),
  }));
}

export async function createDiscount(payload: CreateDiscountPayload): Promise<DiscountRecord> {
  // Required fields per schema: scope, startsAt, endsAt. Unsupported max_usage removed.
  const now = new Date();
  const oneYearLater = new Date(now.getTime() + 365 * 24 * 60 * 60 * 1000);

  const body = {
    name: payload.name.trim(),
    code: payload.code.trim().toUpperCase(),
    discountType: payload.discountType,
    value: String(payload.value).replace(/[^0-9.]/g, ""),
    scope: payload.scope || "GLOBAL",
    startsAt: payload.startsAt || now.toISOString(),
    endsAt: payload.endsAt || oneYearLater.toISOString(),
  };

  const res = await apiRequest<any>("/discount-rules", {
    method: "POST",
    body: JSON.stringify(body),
  });

  return {
    id: res.id,
    name: res.name,
    code: res.code,
    discountType: res.discount_type || res.discountType || payload.discountType,
    value: res.value || payload.value,
    scope: res.scope || payload.scope || "GLOBAL",
    startsAt: res.starts_at || res.startsAt || body.startsAt,
    endsAt: res.ends_at || res.endsAt || body.endsAt,
    isActive: Boolean(res.is_active !== undefined ? res.is_active : true),
    createdAt: res.created_at || res.createdAt || new Date().toISOString(),
  };
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
  return items.map((raw) => {
    // Resolve price from root, plan object, or plan price attribute
    const resolvedPrice =
      raw.price !== undefined && raw.price !== null && raw.price !== "0.00" && raw.price !== 0
        ? raw.price
        : (raw.plan?.price || raw.plan_price || raw.recurring_amount || raw.total_amount || raw.amount || "0.00");

    return {
      id: raw.id,
      subscriptionNumber: raw.subscription_number || raw.subscriptionNumber || `SUB-${raw.id.slice(0, 8)}`,
      customerId: raw.customer_id || raw.customerId,
      customerName: raw.customer_name || raw.customerName,
      planId: raw.plan_id || raw.planId,
      planName: raw.plan_name || raw.planName || raw.plan?.name,
      quotationId: raw.quotation_id || raw.quotationId || null,
      status: raw.status || "ACTIVE",
      price: resolvedPrice,
      currency: raw.currency || (raw.plan && raw.plan.currency) || "INR",
      billingInterval: raw.billing_interval || raw.billingInterval || (raw.plan && raw.plan.billing_interval) || "MONTHLY",
      currentPeriodEnd: raw.current_period_end || raw.currentPeriodEnd,
      createdAt: raw.created_at || raw.createdAt,
    };
  });
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
    planName: raw.plan_name || raw.planName || raw.plan?.name,
    status: raw.status || "ACTIVE",
    price: raw.price || raw.plan?.price || "0.00",
    currency: raw.currency || "INR",
    billingInterval: raw.billing_interval || raw.billingInterval || "MONTHLY",
    createdAt: raw.created_at || raw.createdAt,
  };
}

// ==========================================
// INVOICES & PAYMENTS & NOTIFICATIONS & ANALYTICS
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
