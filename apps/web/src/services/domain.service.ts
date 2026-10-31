import { apiRequest } from "./api"
import { USE_MOCK } from "./mock.config"
import type {
  SubscriptionItem,
  PlanItem,
  CustomerRecord,
  InvoiceRecord,
  CreateSubscriptionPayload,
  CreatePlanPayload,
  CreateCustomerPayload,
} from "@/types/domain.types"

let mockSubscriptions: SubscriptionItem[] = [
  { id: "sub_01a", customerId: "cust_001", customer: "Acme Cloud Corp", planId: "p2", plan: "Enterprise Pro", amount: "$1,249.00", status: "ACTIVE", renewalDate: "Nov 15, 2026" },
  { id: "sub_02b", customerId: "cust_002", customer: "Apex Design Labs", planId: "p1", plan: "Starter Growth", amount: "$299.00", status: "ACTIVE", renewalDate: "Nov 22, 2026" },
  { id: "sub_03c", customerId: "cust_003", customer: "Horizon Data Tech", planId: "p2", plan: "Enterprise Pro", amount: "$780.50", status: "PAST_DUE", renewalDate: "Nov 01, 2026" },
  { id: "sub_04d", customerId: "cust_004", customer: "Nova Dynamics", planId: "p1", plan: "Starter Growth", amount: "$299.00", status: "TRIAL", renewalDate: "Nov 08, 2026" },
]

let mockPlans: PlanItem[] = [
  { id: "p1", name: "Starter Growth", price: "$299.00", interval: "MONTHLY", activeSubscribers: 142 },
  { id: "p2", name: "Enterprise Pro", price: "$1,249.00", interval: "MONTHLY", activeSubscribers: 38 },
  { id: "p3", name: "Custom Annual", price: "$12,000.00", interval: "YEARLY", activeSubscribers: 12 },
]

let mockCustomers: CustomerRecord[] = [
  { id: "cust_001", displayName: "Sarah Jenkins", companyName: "Acme Cloud Corp", billingEmail: "sarah.j@acmecloud.com", status: "ACTIVE", createdDate: "Oct 12, 2026" },
  { id: "cust_002", displayName: "Marcus Vance", companyName: "Apex Design Labs", billingEmail: "finance@apexlabs.io", status: "ACTIVE", createdDate: "Oct 18, 2026" },
  { id: "cust_003", displayName: "Elena Rostova", companyName: "Horizon Data Tech", billingEmail: "accounts@horizondt.com", status: "ACTIVE", createdDate: "Oct 24, 2026" },
  { id: "cust_004", displayName: "David Kim", companyName: "Nova Dynamics", billingEmail: "billing@novadyn.dev", status: "ACTIVE", createdDate: "Oct 28, 2026" },
]

let mockInvoices: InvoiceRecord[] = [
  { id: "INV-2026-089", customer: "Acme Cloud Corp", amount: "$1,249.00", status: "PAID", due: "Oct 15, 2026" },
  { id: "INV-2026-090", customer: "Horizon Data Tech", amount: "$780.50", status: "PENDING", due: "Nov 01, 2026" },
  { id: "INV-2026-091", customer: "Apex Design Labs", amount: "$299.00", status: "PAID", due: "Oct 22, 2026" },
  { id: "INV-2026-092", customer: "Nova Dynamics", amount: "$2,040.50", status: "PENDING", due: "Nov 10, 2026" },
]

export async function fetchSubscriptions(): Promise<SubscriptionItem[]> {
  if (USE_MOCK) return [...mockSubscriptions]
  const res = await apiRequest<{ items: SubscriptionItem[] }>("/subscriptions")
  return res.items
}

export async function createSubscription(data: CreateSubscriptionPayload): Promise<SubscriptionItem> {
  if (USE_MOCK) {
    const cust = mockCustomers.find((c) => c.id === data.customerId)
    const plan = mockPlans.find((p) => p.id === data.planId)
    const newSub: SubscriptionItem = {
      id: `sub_${Date.now().toString().slice(-4)}`,
      customerId: data.customerId,
      customer: cust ? cust.companyName || cust.displayName : "Direct Client",
      planId: data.planId,
      plan: plan ? plan.name : "Custom Tier",
      amount: plan ? plan.price : "$100.00",
      status: "ACTIVE",
      renewalDate: "Dec 01, 2026",
    }
    mockSubscriptions = [newSub, ...mockSubscriptions]
    return newSub
  }
  return apiRequest<SubscriptionItem>("/subscriptions", {
    method: "POST",
    body: JSON.stringify(data),
  })
}

export async function fetchPlans(): Promise<PlanItem[]> {
  if (USE_MOCK) return [...mockPlans]
  const res = await apiRequest<{ items: PlanItem[] }>("/plans")
  return res.items
}

export async function createPlan(data: CreatePlanPayload): Promise<PlanItem> {
  if (USE_MOCK) {
    const newPlan: PlanItem = {
      id: `p_${Date.now().toString().slice(-4)}`,
      name: data.name,
      price: data.price.startsWith("$") ? data.price : `$${data.price}`,
      interval: data.interval,
      activeSubscribers: 0,
    }
    mockPlans = [...mockPlans, newPlan]
    return newPlan
  }
  return apiRequest<PlanItem>("/plans", {
    method: "POST",
    body: JSON.stringify(data),
  })
}

export async function fetchCustomers(): Promise<CustomerRecord[]> {
  if (USE_MOCK) return [...mockCustomers]
  const res = await apiRequest<{ items: CustomerRecord[] }>("/customers")
  return res.items
}

export async function createCustomer(data: CreateCustomerPayload): Promise<CustomerRecord> {
  if (USE_MOCK) {
    const newCust: CustomerRecord = {
      id: `cust_${Date.now().toString().slice(-4)}`,
      displayName: data.displayName,
      companyName: data.companyName || null,
      billingEmail: data.billingEmail,
      status: "ACTIVE",
      createdDate: new Date().toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }),
    }
    mockCustomers = [newCust, ...mockCustomers]
    return newCust
  }
  return apiRequest<CustomerRecord>("/customers", {
    method: "POST",
    body: JSON.stringify(data),
  })
}

export async function fetchInvoices(): Promise<InvoiceRecord[]> {
  if (USE_MOCK) return [...mockInvoices]
  const res = await apiRequest<{ items: InvoiceRecord[] }>("/invoices")
  return res.items
}
