export type BillingInterval = "DAILY" | "WEEKLY" | "MONTHLY" | "YEARLY";
export type SubscriptionStatus = "DRAFT" | "TRIAL" | "ACTIVE" | "PAUSED" | "PAST_DUE" | "CANCELED" | "CLOSED";
export type UserRole = "ADMIN" | "STAFF" | "CUSTOMER";

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
  customer: string;
  amount: string;
  currency: string;
  status: "PAID" | "PENDING" | "FAILED";
  due: string;
  isMock: true;
}
