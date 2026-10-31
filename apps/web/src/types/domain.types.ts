export interface SubscriptionItem {
  id: string
  customerId: string
  customer: string
  planId: string
  plan: string
  amount: string
  status: "ACTIVE" | "PAST_DUE" | "TRIAL" | "CANCELED"
  renewalDate: string
}

export interface PlanItem {
  id: string
  name: string
  price: string
  interval: "MONTHLY" | "YEARLY"
  activeSubscribers: number
}

export interface CustomerRecord {
  id: string
  displayName: string
  companyName: string | null
  billingEmail: string
  status: "ACTIVE" | "INACTIVE"
  createdDate: string
}

export interface InvoiceRecord {
  id: string
  subscriptionId?: string
  customer: string
  amount: string
  status: "PAID" | "PENDING"
  due: string
}

export interface CreateSubscriptionPayload {
  customerId: string
  planId: string
}

export interface CreatePlanPayload {
  name: string
  price: string
  interval: "MONTHLY" | "YEARLY"
}

export interface CreateCustomerPayload {
  displayName: string
  companyName?: string
  billingEmail: string
}
