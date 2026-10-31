export type BillingInterval = "DAILY" | "WEEKLY" | "MONTHLY" | "YEARLY";
export type SubscriptionStatus = "DRAFT" | "TRIAL" | "ACTIVE" | "PAUSED" | "PAST_DUE" | "CANCELED" | "CLOSED";
export type UserRole = "ADMIN" | "STAFF" | "CUSTOMER";
export type InvoiceStatus = "DRAFT" | "CONFIRMED" | "PARTIALLY_PAID" | "OVERDUE" | "PAID" | "CANCELLED";
export type PaymentMethod = "CASH" | "BANK_TRANSFER" | "UPI" | "CARD" | "CHEQUE" | "GATEWAY" | "OTHER";
export type PaymentStatus = "PENDING" | "SUCCEEDED" | "FAILED" | "REFUNDED";
export type NotificationType = "INVOICE_ISSUED" | "INVOICE_SENT" | "PAYMENT_RECEIVED" | "SUBSCRIPTION_UPGRADED" | "OTHER";
export type TaxType = "GENERIC" | "CGST" | "SGST" | "IGST" | "OTHER";
export type DiscountType = "FIXED" | "PERCENTAGE";
export type QuotationStatus = "DRAFT" | "SENT" | "ACCEPTED" | "REJECTED" | "EXPIRED";

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages?: number;
}

export interface User {
  id: string;
  email: string;
  role: UserRole;
  isActive: boolean;
  createdAt: string;
  updatedAt?: string;
}

export interface CustomerRecord {
  id: string;
  displayName: string;
  companyName: string | null;
  billingEmail: string;
  phone?: string | null;
  status: "ACTIVE" | "INACTIVE" | "ARCHIVED";
  createdAt: string;
  updatedAt?: string;
}

export interface CreateCustomerPayload {
  displayName: string;
  billingEmail: string;
  companyName?: string | null;
  phone?: string | null;
}

export interface ProductRecord {
  id: string;
  name: string;
  description?: string | null;
  sku: string;
  basePrice: string | number;
  currency: string;
  isActive: boolean;
  createdAt: string;
}

export interface CreateProductPayload {
  name: string;
  description?: string;
  sku: string;
  basePrice: string;
  currency: string;
}

export interface PlanItem {
  id: string;
  name: string;
  description?: string | null;
  price: string | number;
  currency: string;
  billingInterval: BillingInterval;
  intervalCount: number;
  trialDays?: number;
  isActive: boolean;
  activeSubscribers?: number;
  createdAt?: string;
}

export interface CreatePlanPayload {
  name: string;
  description?: string;
  price: string;
  currency: string;
  billingInterval: BillingInterval;
  intervalCount: number;
}

export interface TaxRuleRecord {
  id: string;
  name: string;
  code: string;
  taxType: TaxType;
  ratePercentage: string | number;
  jurisdiction?: string;
  isInclusive: boolean;
  isActive: boolean;
  createdAt: string;
}

export interface CreateTaxRulePayload {
  name: string;
  code: string;
  taxType: TaxType;
  ratePercentage: string;
  jurisdiction?: string;
  isInclusive: boolean;
}

export interface DiscountRecord {
  id: string;
  name: string;
  code: string;
  discountType: DiscountType;
  value: string | number;
  maxUsage?: number | null;
  isActive: boolean;
  createdAt: string;
}

export interface CreateDiscountPayload {
  name: string;
  code: string;
  discountType: DiscountType;
  value: string;
  maxUsage?: number;
}

export interface QuotationLineItem {
  productId: string;
  quantity: number;
  unitPrice: string | number;
}

export interface QuotationRecord {
  id: string;
  quotationNumber?: string;
  customerId: string;
  customerName?: string;
  planId: string;
  planName?: string;
  status: QuotationStatus;
  subtotal: string | number;
  taxAmount: string | number;
  discountAmount: string | number;
  totalAmount: string | number;
  currency: string;
  subscriptionId?: string | null;
  createdAt: string;
}

export interface CreateQuotationPayload {
  customerId: string;
  planId: string;
  currency: string;
  lines: QuotationLineItem[];
  taxRuleIds?: string[];
  discountCode?: string;
}

export interface SubscriptionItem {
  id: string;
  subscriptionNumber?: string;
  customerId: string;
  customerName?: string;
  planId: string;
  planName?: string;
  quotationId?: string | null;
  status: SubscriptionStatus;
  currency: string;
  price: string | number;
  billingInterval: BillingInterval;
  currentPeriodStart?: string;
  currentPeriodEnd?: string;
  nextBillingDate?: string;
  cancelAtPeriodEnd?: boolean;
  createdAt?: string;
}

export interface CreateSubscriptionPayload {
  customerId: string;
  planId: string;
  startDate?: string;
  currency?: string;
}

export interface InvoiceRecord {
  id: string;
  invoiceNumber?: string;
  customerId: string;
  customerName?: string;
  subscriptionId?: string | null;
  totalAmount: string | number;
  amountDue: string | number;
  currency: string;
  status: InvoiceStatus;
  dueDate: string;
  createdAt: string;
}

export interface PaymentRecord {
  id: string;
  paymentNumber?: string;
  invoiceId: string;
  amount: string | number;
  currency: string;
  method: PaymentMethod;
  status: PaymentStatus;
  reference?: string | null;
  createdAt: string;
}

export interface RecordPaymentPayload {
  invoiceId: string;
  amount: string;
  currency: string;
  method: PaymentMethod;
  reference?: string;
}

export interface NotificationItem {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  isRead: boolean;
  resourceType?: string | null;
  resourceId?: string | null;
  createdAt: string;
}

export interface AnalyticsDashboard {
  currency: string;
  activeSubscriptions: number;
  collectedRevenue: string | number;
  outstandingBalance: string | number;
  overdueInvoiceCount: number;
  mrr: string | number;
  arr: string | number;
  totalInvoices: number;
  upcomingRenewalsCount?: number;
}
