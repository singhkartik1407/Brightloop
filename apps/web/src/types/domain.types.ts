export type BillingInterval = "DAILY" | "WEEKLY" | "MONTHLY" | "YEARLY";
export type SubscriptionStatus = "DRAFT" | "TRIAL" | "ACTIVE" | "PAUSED" | "PAST_DUE" | "CANCELED" | "CLOSED";
export type UserRole = "ADMIN" | "STAFF" | "CUSTOMER";
export type InvoiceStatus = "DRAFT" | "CONFIRMED" | "PARTIALLY_PAID" | "OVERDUE" | "PAID" | "CANCELLED";
export type PaymentMethod = "CASH" | "BANK_TRANSFER" | "UPI" | "CARD" | "CHEQUE" | "GATEWAY" | "OTHER";
export type PaymentStatus = "PENDING" | "SUCCEEDED" | "FAILED" | "REFUNDED";

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
  allowPause?: boolean;
  allowEarlyClose?: boolean;
  allowRenewal?: boolean;
  autoCloseAtEnd?: boolean;
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
  invoiceNumber: string;
  customerId: string;
  customerName?: string;
  subscriptionId?: string | null;
  status: InvoiceStatus;
  currency: string;
  subtotal: string | number;
  taxTotal: string | number;
  total: string | number;
  amountPaid: string | number;
  amountDue: string | number;
  issueDate: string;
  dueDate: string;
  createdAt?: string;
}

export interface PaymentRecord {
  id: string;
  paymentNumber: string;
  invoiceId: string;
  customerId: string;
  amount: string | number;
  currency: string;
  method: PaymentMethod;
  status: PaymentStatus;
  reference?: string | null;
  notes?: string | null;
  paymentDate: string;
  createdAt?: string;
}

export interface RecordPaymentPayload {
  invoiceId: string;
  amount: string | number;
  currency: string;
  method: PaymentMethod;
  reference?: string;
  notes?: string;
}

export interface NotificationItem {
  id: string;
  title: string;
  message: string;
  isRead: boolean;
  eventType?: string;
  resourceId?: string | null;
  createdAt: string;
}

export interface DashboardMetrics {
  activeSubscriptions: number;
  collectedRevenue: number | string;
  outstandingBalance: number | string;
  overdueInvoiceCount: number;
  mrr: number | string;
  arr: number | string;
  totalInvoiceCount: number;
  upcomingRenewalsCount?: number;
}
