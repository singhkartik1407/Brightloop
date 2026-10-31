import { useState, useEffect } from "react"
import { useAuth } from "@/contexts/AuthContext"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Users,
  CreditCard,
  Layers,
  FileText,
  Activity,
  LogOut,
  TrendingUp,
  AlertCircle,
  Plus,
  CheckCircle2,
  Search,
  X,
  Mail,
  Building,
  Loader2,
} from "lucide-react"

import type {
  SubscriptionItem,
  PlanItem,
  CustomerRecord,
  InvoiceRecord,
} from "@/types/domain.types"

import {
  fetchSubscriptions,
  createSubscription,
  fetchPlans,
  createPlan,
  fetchCustomers,
  createCustomer,
  fetchInvoices,
} from "@/services/domain.service"

export default function App() {
  const { user, logout } = useAuth()
  const [activeTab, setActiveTab] = useState<"subscriptions" | "plans" | "customers" | "invoices">("subscriptions")
  const [loading, setLoading] = useState(true)

  // Data State
  const [subscriptions, setSubscriptions] = useState<SubscriptionItem[]>([])
  const [plans, setPlans] = useState<PlanItem[]>([])
  const [customers, setCustomers] = useState<CustomerRecord[]>([])
  const [invoices, setInvoices] = useState<InvoiceRecord[]>([])

  // Modal States
  const [isCustomerModalOpen, setIsCustomerModalOpen] = useState(false)
  const [isSubModalOpen, setIsSubModalOpen] = useState(false)
  const [isPlanModalOpen, setIsPlanModalOpen] = useState(false)

  // Form Inputs
  const [customerSearch, setCustomerSearch] = useState("")
  const [newCustomer, setNewCustomer] = useState({ displayName: "", companyName: "", billingEmail: "" })
  const [newSub, setNewSub] = useState({ customerId: "", planId: "" })
  const [newPlan, setNewPlan] = useState({ name: "", price: "", interval: "MONTHLY" as "MONTHLY" | "YEARLY" })

  // Initial Data Load
  useEffect(() => {
    async function loadData() {
      setLoading(true)
      try {
        const [subsData, plansData, custsData, invsData] = await Promise.all([
          fetchSubscriptions(),
          fetchPlans(),
          fetchCustomers(),
          fetchInvoices(),
        ])
        setSubscriptions(subsData)
        setPlans(plansData)
        setCustomers(custsData)
        setInvoices(invsData)
        if (custsData[0]) setNewSub((prev) => ({ ...prev, customerId: custsData[0].id }))
        if (plansData[0]) setNewSub((prev) => ({ ...prev, planId: plansData[0].id }))
      } catch (err) {
        console.error("Failed to load domain data", err)
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [])

  const handleAddCustomer = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newCustomer.displayName || !newCustomer.billingEmail) return
    const created = await createCustomer(newCustomer)
    setCustomers((prev) => [created, ...prev])
    setNewCustomer({ displayName: "", companyName: "", billingEmail: "" })
    setIsCustomerModalOpen(false)
  }

  const handleAddSubscription = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newSub.customerId || !newSub.planId) return
    const created = await createSubscription(newSub)
    setSubscriptions((prev) => [created, ...prev])
    setIsSubModalOpen(false)
  }

  const handleAddPlan = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newPlan.name || !newPlan.price) return
    const created = await createPlan(newPlan)
    setPlans((prev) => [...prev, created])
    setNewPlan({ name: "", price: "", interval: "MONTHLY" })
    setIsPlanModalOpen(false)
  }

  const getStatusBadge = (status: SubscriptionItem["status"] | "INACTIVE") => {
    switch (status) {
      case "ACTIVE":
        return <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-xs font-semibold text-emerald-400 border border-emerald-500/20"><CheckCircle2 className="w-3 h-3" /> ACTIVE</span>
      case "PAST_DUE":
        return <span className="inline-flex items-center gap-1 rounded-full bg-rose-500/10 px-2.5 py-0.5 text-xs font-semibold text-rose-400 border border-rose-500/20"><AlertCircle className="w-3 h-3" /> PAST DUE</span>
      case "TRIAL":
        return <span className="inline-flex items-center gap-1 rounded-full bg-blue-500/10 px-2.5 py-0.5 text-xs font-semibold text-blue-400 border border-blue-500/20"><Activity className="w-3 h-3" /> TRIAL</span>
      default:
        return <span className="inline-flex items-center gap-1 rounded-full bg-zinc-500/10 px-2.5 py-0.5 text-xs font-semibold text-zinc-400 border border-zinc-500/20">INACTIVE</span>
    }
  }

  const filteredCustomers = customers.filter(
    (c) =>
      c.displayName.toLowerCase().includes(customerSearch.toLowerCase()) ||
      (c.companyName && c.companyName.toLowerCase().includes(customerSearch.toLowerCase())) ||
      c.billingEmail.toLowerCase().includes(customerSearch.toLowerCase())
  )

  return (
    <div className="flex h-screen w-full bg-zinc-950 text-zinc-100">
      {/* Sidebar */}
      <aside className="w-64 border-r border-zinc-800 bg-zinc-900/40 p-4 flex flex-col justify-between">
        <div className="space-y-6">
          <div className="flex items-center gap-3 px-2">
            <div className="h-8 w-8 rounded-lg bg-blue-600 flex items-center justify-center font-bold text-white shadow-lg shadow-blue-500/30">
              B
            </div>
            <div>
              <h1 className="font-bold text-sm tracking-wide">BRIGHTLOOP</h1>
              <p className="text-xs text-zinc-500">Subscription Engine</p>
            </div>
          </div>

          <nav className="space-y-1">
            <button
              onClick={() => setActiveTab("subscriptions")}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === "subscriptions" ? "bg-blue-600 text-white" : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100"
              }`}
            >
              <CreditCard className="w-4 h-4" /> Subscriptions
            </button>
            <button
              onClick={() => setActiveTab("plans")}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === "plans" ? "bg-blue-600 text-white" : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100"
              }`}
            >
              <Layers className="w-4 h-4" /> Pricing Plans
            </button>
            <button
              onClick={() => setActiveTab("customers")}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === "customers" ? "bg-blue-600 text-white" : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100"
              }`}
            >
              <Users className="w-4 h-4" /> Customers
            </button>
            <button
              onClick={() => setActiveTab("invoices")}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === "invoices" ? "bg-blue-600 text-white" : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100"
              }`}
            >
              <FileText className="w-4 h-4" /> Invoices
            </button>
          </nav>
        </div>

        {/* User Card */}
        <div className="border-t border-zinc-800 pt-4">
          <div className="flex items-center justify-between">
            <div className="overflow-hidden">
              <p className="text-sm font-semibold truncate">{user?.email || "Admin User"}</p>
              <span className="text-xs text-zinc-500 uppercase tracking-wider font-mono">{user?.role || "ADMIN"}</span>
            </div>
            <Button variant="ghost" size="icon" onClick={logout} className="text-zinc-400 hover:text-red-400">
              <LogOut className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto p-8 space-y-8">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Overview & Performance</h2>
          <p className="text-sm text-zinc-400">Authoritative subscription metrics & live customer telemetry.</p>
        </div>

        {/* Metric Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card className="bg-zinc-900 border-zinc-800 p-5 space-y-2">
            <div className="flex items-center justify-between text-zinc-400">
              <span className="text-xs font-medium">Monthly Recurring Revenue</span>
              <TrendingUp className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="text-2xl font-bold text-white">$42,890.00</div>
            <p className="text-xs text-emerald-400 font-medium">+14.2% from last month</p>
          </Card>

          <Card className="bg-zinc-900 border-zinc-800 p-5 space-y-2">
            <div className="flex items-center justify-between text-zinc-400">
              <span className="text-xs font-medium">Active Subscriptions</span>
              <Users className="w-4 h-4 text-blue-400" />
            </div>
            <div className="text-2xl font-bold text-white">{subscriptions.length}</div>
            <p className="text-xs text-zinc-400">Live active accounts</p>
          </Card>

          <Card className="bg-zinc-900 border-zinc-800 p-5 space-y-2">
            <div className="flex items-center justify-between text-zinc-400">
              <span className="text-xs font-medium">Invoices Pending</span>
              <FileText className="w-4 h-4 text-amber-400" />
            </div>
            <div className="text-2xl font-bold text-white">
              {invoices.filter((i) => i.status === "PENDING").length}
            </div>
            <p className="text-xs text-amber-400 font-medium">Awaiting clearing</p>
          </Card>

          <Card className="bg-zinc-900 border-zinc-800 p-5 space-y-2">
            <div className="flex items-center justify-between text-zinc-400">
              <span className="text-xs font-medium">Churn Rate</span>
              <Activity className="w-4 h-4 text-purple-400" />
            </div>
            <div className="text-2xl font-bold text-white">1.1%</div>
            <p className="text-xs text-emerald-400 font-medium">-0.3% improvement</p>
          </Card>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20 text-zinc-400 gap-2">
            <Loader2 className="w-5 h-5 animate-spin" /> Loading live contract data...
          </div>
        ) : (
          <>
            {/* Subscriptions */}
            {activeTab === "subscriptions" && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-white">Active Subscriptions</h3>
                    <p className="text-xs text-zinc-400">Live feed synced with billing engine</p>
                  </div>
                  <Button
                    onClick={() => setIsSubModalOpen(true)}
                    className="bg-blue-600 hover:bg-blue-500 text-white gap-2 text-xs"
                  >
                    <Plus className="w-3.5 h-3.5" /> Create Subscription
                  </Button>
                </div>

                <Card className="bg-zinc-900 border-zinc-800 overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                      <thead className="bg-zinc-950/60 text-xs uppercase text-zinc-400 border-b border-zinc-800">
                        <tr>
                          <th className="py-3 px-4">Customer</th>
                          <th className="py-3 px-4">Plan</th>
                          <th className="py-3 px-4">Amount</th>
                          <th className="py-3 px-4">Status</th>
                          <th className="py-3 px-4">Next Renewal</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-zinc-800/60 font-mono text-xs">
                        {subscriptions.map((sub) => (
                          <tr key={sub.id} className="hover:bg-zinc-800/30 transition-colors">
                            <td className="py-3.5 px-4 font-sans font-medium text-white">{sub.customer}</td>
                            <td className="py-3.5 px-4 text-zinc-300 font-sans">{sub.plan}</td>
                            <td className="py-3.5 px-4 text-white font-semibold">{sub.amount}</td>
                            <td className="py-3.5 px-4">{getStatusBadge(sub.status)}</td>
                            <td className="py-3.5 px-4 text-zinc-400">{sub.renewalDate}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Card>
              </div>
            )}

            {/* Plans */}
            {activeTab === "plans" && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-white">Available Plans</h3>
                    <p className="text-xs text-zinc-400">Configured in API tier registry</p>
                  </div>
                  <Button
                    onClick={() => setIsPlanModalOpen(true)}
                    className="bg-blue-600 hover:bg-blue-500 text-white gap-2 text-xs"
                  >
                    <Plus className="w-3.5 h-3.5" /> Add Tier
                  </Button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {plans.map((p) => (
                    <Card key={p.id} className="bg-zinc-900 border-zinc-800 p-6 flex flex-col justify-between space-y-4">
                      <div>
                        <h4 className="text-base font-bold text-white">{p.name}</h4>
                        <div className="mt-2 text-3xl font-extrabold text-white">
                          {p.price}{" "}
                          <span className="text-xs text-zinc-500 font-normal">/{p.interval.toLowerCase()}</span>
                        </div>
                        <p className="mt-4 text-xs text-zinc-400">{p.activeSubscribers} organizations enrolled</p>
                      </div>
                    </Card>
                  ))}
                </div>
              </div>
            )}

            {/* Customers */}
            {activeTab === "customers" && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-white">Customer Registry</h3>
                    <p className="text-xs text-zinc-400">Manage verified accounts and billing profiles</p>
                  </div>
                  <Button
                    onClick={() => setIsCustomerModalOpen(true)}
                    className="bg-blue-600 hover:bg-blue-500 text-white gap-2 text-xs"
                  >
                    <Plus className="w-3.5 h-3.5" /> Add Customer
                  </Button>
                </div>

                <div className="flex items-center gap-3">
                  <div className="relative flex-1 max-w-sm">
                    <Search className="absolute left-3 top-2.5 h-4 w-4 text-zinc-500" />
                    <Input
                      placeholder="Search customer, company or email..."
                      value={customerSearch}
                      onChange={(e) => setCustomerSearch(e.target.value)}
                      className="pl-9 bg-zinc-900 border-zinc-800 text-xs text-white"
                    />
                  </div>
                </div>

                <Card className="bg-zinc-900 border-zinc-800 overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                      <thead className="bg-zinc-950/60 text-xs uppercase text-zinc-400 border-b border-zinc-800">
                        <tr>
                          <th className="py-3 px-4">Contact Name</th>
                          <th className="py-3 px-4">Company</th>
                          <th className="py-3 px-4">Billing Email</th>
                          <th className="py-3 px-4">Status</th>
                          <th className="py-3 px-4">Added Date</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-zinc-800/60 text-xs">
                        {filteredCustomers.map((cust) => (
                          <tr key={cust.id} className="hover:bg-zinc-800/30 transition-colors">
                            <td className="py-3.5 px-4 font-medium text-white">{cust.displayName}</td>
                            <td className="py-3.5 px-4 text-zinc-300 flex items-center gap-1.5">
                              <Building className="w-3.5 h-3.5 text-zinc-500" /> {cust.companyName || "Direct"}
                            </td>
                            <td className="py-3.5 px-4 text-zinc-300 font-mono">
                              <span className="flex items-center gap-1.5">
                                <Mail className="w-3 h-3 text-zinc-500" /> {cust.billingEmail}
                              </span>
                            </td>
                            <td className="py-3.5 px-4">{getStatusBadge(cust.status)}</td>
                            <td className="py-3.5 px-4 text-zinc-400 font-mono">{cust.createdDate}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Card>
              </div>
            )}

            {/* Invoices */}
            {activeTab === "invoices" && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-white">Billing Invoices</h3>
                    <p className="text-xs text-zinc-400">Authoritative payment collection & invoice logs</p>
                  </div>
                </div>

                <Card className="bg-zinc-900 border-zinc-800 overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                      <thead className="bg-zinc-950/60 text-xs uppercase text-zinc-400 border-b border-zinc-800">
                        <tr>
                          <th className="py-3 px-4">Invoice #</th>
                          <th className="py-3 px-4">Customer</th>
                          <th className="py-3 px-4">Amount</th>
                          <th className="py-3 px-4">Status</th>
                          <th className="py-3 px-4">Due Date</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-zinc-800/60 text-xs font-mono">
                        {invoices.map((inv) => (
                          <tr key={inv.id} className="hover:bg-zinc-800/30 transition-colors">
                            <td className="py-3.5 px-4 font-semibold text-white">{inv.id}</td>
                            <td className="py-3.5 px-4 font-sans text-zinc-300">{inv.customer}</td>
                            <td className="py-3.5 px-4 text-white font-semibold">{inv.amount}</td>
                            <td className="py-3.5 px-4">
                              <span
                                className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold ${
                                  inv.status === "PAID"
                                    ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                                    : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                                }`}
                              >
                                {inv.status}
                              </span>
                            </td>
                            <td className="py-3.5 px-4 text-zinc-400">{inv.due}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Card>
              </div>
            )}
          </>
        )}
      </main>

      {/* Modal: Add Customer */}
      {isCustomerModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <Card className="w-full max-w-md bg-zinc-900 border-zinc-800 p-6 space-y-5">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
              <h3 className="text-base font-bold text-white">Add New Customer</h3>
              <button onClick={() => setIsCustomerModalOpen(false)} className="text-zinc-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>
            <form onSubmit={handleAddCustomer} className="space-y-4">
              <div className="space-y-1.5">
                <Label className="text-xs text-zinc-300">Display Name</Label>
                <Input
                  required
                  placeholder="e.g. Rachel Adams"
                  value={newCustomer.displayName}
                  onChange={(e) => setNewCustomer({ ...newCustomer, displayName: e.target.value })}
                  className="bg-zinc-950 border-zinc-800 text-sm text-white"
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-zinc-300">Company Name</Label>
                <Input
                  placeholder="e.g. Acme Corp (optional)"
                  value={newCustomer.companyName}
                  onChange={(e) => setNewCustomer({ ...newCustomer, companyName: e.target.value })}
                  className="bg-zinc-950 border-zinc-800 text-sm text-white"
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-zinc-300">Billing Email</Label>
                <Input
                  required
                  type="email"
                  placeholder="billing@company.com"
                  value={newCustomer.billingEmail}
                  onChange={(e) => setNewCustomer({ ...newCustomer, billingEmail: e.target.value })}
                  className="bg-zinc-950 border-zinc-800 text-sm text-white"
                />
              </div>
              <div className="flex items-center justify-end gap-2 pt-2">
                <Button type="button" variant="outline" onClick={() => setIsCustomerModalOpen(false)} className="border-zinc-800 text-xs">
                  Cancel
                </Button>
                <Button type="submit" className="bg-blue-600 hover:bg-blue-500 text-xs text-white">
                  Create Customer
                </Button>
              </div>
            </form>
          </Card>
        </div>
      )}

      {/* Modal: Create Subscription */}
      {isSubModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <Card className="w-full max-w-md bg-zinc-900 border-zinc-800 p-6 space-y-5">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
              <h3 className="text-base font-bold text-white">Create Subscription</h3>
              <button onClick={() => setIsSubModalOpen(false)} className="text-zinc-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>
            <form onSubmit={handleAddSubscription} className="space-y-4">
              <div className="space-y-1.5">
                <Label className="text-xs text-zinc-300">Customer</Label>
                <select
                  value={newSub.customerId}
                  onChange={(e) => setNewSub({ ...newSub, customerId: e.target.value })}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-sm text-white focus:outline-none"
                >
                  {customers.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.displayName} ({c.companyName || "Direct"})
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-zinc-300">Pricing Tier</Label>
                <select
                  value={newSub.planId}
                  onChange={(e) => setNewSub({ ...newSub, planId: e.target.value })}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-sm text-white focus:outline-none"
                >
                  {plans.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} — {p.price}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex items-center justify-end gap-2 pt-2">
                <Button type="button" variant="outline" onClick={() => setIsSubModalOpen(false)} className="border-zinc-800 text-xs">
                  Cancel
                </Button>
                <Button type="submit" className="bg-blue-600 hover:bg-blue-500 text-xs text-white">
                  Confirm & Provision
                </Button>
              </div>
            </form>
          </Card>
        </div>
      )}

      {/* Modal: Add Tier */}
      {isPlanModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <Card className="w-full max-w-md bg-zinc-900 border-zinc-800 p-6 space-y-5">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
              <h3 className="text-base font-bold text-white">Add Pricing Tier</h3>
              <button onClick={() => setIsPlanModalOpen(false)} className="text-zinc-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>
            <form onSubmit={handleAddPlan} className="space-y-4">
              <div className="space-y-1.5">
                <Label className="text-xs text-zinc-300">Plan Name</Label>
                <Input
                  required
                  placeholder="e.g. Scale Growth"
                  value={newPlan.name}
                  onChange={(e) => setNewPlan({ ...newPlan, name: e.target.value })}
                  className="bg-zinc-950 border-zinc-800 text-sm text-white"
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-zinc-300">Price (e.g. $499.00)</Label>
                <Input
                  required
                  placeholder="$499.00"
                  value={newPlan.price}
                  onChange={(e) => setNewPlan({ ...newPlan, price: e.target.value })}
                  className="bg-zinc-950 border-zinc-800 text-sm text-white"
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-zinc-300">Billing Interval</Label>
                <select
                  value={newPlan.interval}
                  onChange={(e) => setNewPlan({ ...newPlan, interval: e.target.value as "MONTHLY" | "YEARLY" })}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-sm text-white focus:outline-none"
                >
                  <option value="MONTHLY">Monthly</option>
                  <option value="YEARLY">Yearly</option>
                </select>
              </div>
              <div className="flex items-center justify-end gap-2 pt-2">
                <Button type="button" variant="outline" onClick={() => setIsPlanModalOpen(false)} className="border-zinc-800 text-xs">
                  Cancel
                </Button>
                <Button type="submit" className="bg-blue-600 hover:bg-blue-500 text-xs text-white">
                  Publish Tier
                </Button>
              </div>
            </form>
          </Card>
        </div>
      )}
    </div>
  )
}
