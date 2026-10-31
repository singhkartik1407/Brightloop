import { useState } from "react"
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
} from "lucide-react"

interface SubscriptionItem {
  id: string
  customer: string
  plan: string
  amount: string
  status: "ACTIVE" | "PAST_DUE" | "TRIAL" | "CANCELED"
  renewalDate: string
}

interface PlanItem {
  id: string
  name: string
  price: string
  interval: string
  activeSubscribers: number
}

interface CustomerRecord {
  id: string
  displayName: string
  companyName: string
  billingEmail: string
  status: "ACTIVE" | "INACTIVE"
  createdDate: string
}

interface InvoiceRecord {
  id: string
  customer: string
  amount: string
  status: "PAID" | "PENDING"
  due: string
}

export default function App() {
  const { user, logout } = useAuth()
  const [activeTab, setActiveTab] = useState<"subscriptions" | "plans" | "customers" | "invoices">("subscriptions")

  // Customer Registry State
  const [customerSearch, setCustomerSearch] = useState("")
  const [isCustomerModalOpen, setIsCustomerModalOpen] = useState(false)
  const [newCustomer, setNewCustomer] = useState({
    displayName: "",
    companyName: "",
    billingEmail: "",
  })

  const [customers, setCustomers] = useState<CustomerRecord[]>([
    {
      id: "cust_001",
      displayName: "Sarah Jenkins",
      companyName: "Acme Cloud Corp",
      billingEmail: "sarah.j@acmecloud.com",
      status: "ACTIVE",
      createdDate: "Oct 12, 2026",
    },
    {
      id: "cust_002",
      displayName: "Marcus Vance",
      companyName: "Apex Design Labs",
      billingEmail: "finance@apexlabs.io",
      status: "ACTIVE",
      createdDate: "Oct 18, 2026",
    },
    {
      id: "cust_003",
      displayName: "Elena Rostova",
      companyName: "Horizon Data Tech",
      billingEmail: "accounts@horizondt.com",
      status: "ACTIVE",
      createdDate: "Oct 24, 2026",
    },
    {
      id: "cust_004",
      displayName: "David Kim",
      companyName: "Nova Dynamics",
      billingEmail: "billing@novadyn.dev",
      status: "ACTIVE",
      createdDate: "Oct 28, 2026",
    },
  ])

  const subscriptions: SubscriptionItem[] = [
    {
      id: "sub_01a",
      customer: "Acme Cloud Corp",
      plan: "Enterprise Pro",
      amount: "$1,249.00",
      status: "ACTIVE",
      renewalDate: "Nov 15, 2026",
    },
    {
      id: "sub_02b",
      customer: "Apex Design Labs",
      plan: "Starter Growth",
      amount: "$299.00",
      status: "ACTIVE",
      renewalDate: "Nov 22, 2026",
    },
    {
      id: "sub_03c",
      customer: "Horizon Data Tech",
      plan: "Usage Hybrid",
      amount: "$780.50",
      status: "PAST_DUE",
      renewalDate: "Nov 01, 2026",
    },
    {
      id: "sub_04d",
      customer: "Nova Dynamics",
      plan: "Starter Growth",
      amount: "$299.00",
      status: "TRIAL",
      renewalDate: "Nov 08, 2026",
    },
  ]

  const plans: PlanItem[] = [
    { id: "p1", name: "Starter Growth", price: "$299.00", interval: "Monthly", activeSubscribers: 142 },
    { id: "p2", name: "Enterprise Pro", price: "$1,249.00", interval: "Monthly", activeSubscribers: 38 },
    { id: "p3", name: "Custom Annual", price: "$12,000.00", interval: "Yearly", activeSubscribers: 12 },
  ]

  const invoices: InvoiceRecord[] = [
    { id: "INV-2026-089", customer: "Acme Cloud Corp", amount: "$1,249.00", status: "PAID", due: "Oct 15, 2026" },
    { id: "INV-2026-090", customer: "Horizon Data Tech", amount: "$780.50", status: "PENDING", due: "Nov 01, 2026" },
    { id: "INV-2026-091", customer: "Apex Design Labs", amount: "$299.00", status: "PAID", due: "Oct 22, 2026" },
    { id: "INV-2026-092", customer: "Nova Dynamics", amount: "$2,040.50", status: "PENDING", due: "Nov 10, 2026" },
  ]

  const getStatusBadge = (status: SubscriptionItem["status"] | "INACTIVE") => {
    switch (status) {
      case "ACTIVE":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-xs font-semibold text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3 h-3" /> ACTIVE
          </span>
        )
      case "PAST_DUE":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-rose-500/10 px-2.5 py-0.5 text-xs font-semibold text-rose-400 border border-rose-500/20">
            <AlertCircle className="w-3 h-3" /> PAST DUE
          </span>
        )
      case "TRIAL":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-blue-500/10 px-2.5 py-0.5 text-xs font-semibold text-blue-400 border border-blue-500/20">
            <Activity className="w-3 h-3" /> TRIAL
          </span>
        )
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-zinc-500/10 px-2.5 py-0.5 text-xs font-semibold text-zinc-400 border border-zinc-500/20">
            INACTIVE
          </span>
        )
    }
  }

  const handleAddCustomer = (e: React.FormEvent) => {
    e.preventDefault()
    if (!newCustomer.displayName || !newCustomer.billingEmail) return

    const created: CustomerRecord = {
      id: `cust_${Date.now().toString().slice(-4)}`,
      displayName: newCustomer.displayName,
      companyName: newCustomer.companyName || "Independent Client",
      billingEmail: newCustomer.billingEmail,
      status: "ACTIVE",
      createdDate: new Date().toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }),
    }

    setCustomers([created, ...customers])
    setNewCustomer({ displayName: "", companyName: "", billingEmail: "" })
    setIsCustomerModalOpen(false)
  }

  const filteredCustomers = customers.filter(
    (c) =>
      c.displayName.toLowerCase().includes(customerSearch.toLowerCase()) ||
      c.companyName.toLowerCase().includes(customerSearch.toLowerCase()) ||
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
                activeTab === "subscriptions"
                  ? "bg-blue-600 text-white"
                  : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100"
              }`}
            >
              <CreditCard className="w-4 h-4" /> Subscriptions
            </button>
            <button
              onClick={() => setActiveTab("plans")}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === "plans"
                  ? "bg-blue-600 text-white"
                  : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100"
              }`}
            >
              <Layers className="w-4 h-4" /> Pricing Plans
            </button>
            <button
              onClick={() => setActiveTab("customers")}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === "customers"
                  ? "bg-blue-600 text-white"
                  : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100"
              }`}
            >
              <Users className="w-4 h-4" /> Customers
            </button>
            <button
              onClick={() => setActiveTab("invoices")}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === "invoices"
                  ? "bg-blue-600 text-white"
                  : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100"
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
              <span className="text-xs text-zinc-500 uppercase tracking-wider font-mono">
                {user?.role || "ADMIN"}
              </span>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={logout}
              className="text-zinc-400 hover:text-red-400"
            >
              <LogOut className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 overflow-y-auto p-8 space-y-8">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Overview & Performance</h2>
          <p className="text-sm text-zinc-400">Authoritative subscription metrics & live customer telemetry.</p>
        </div>

        {/* Header Metrics */}
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
            <div className="text-2xl font-bold text-white">{subscriptions.length + 188}</div>
            <p className="text-xs text-zinc-400">Across 3 active tiers</p>
          </Card>

          <Card className="bg-zinc-900 border-zinc-800 p-5 space-y-2">
            <div className="flex items-center justify-between text-zinc-400">
              <span className="text-xs font-medium">Invoices Pending</span>
              <FileText className="w-4 h-4 text-amber-400" />
            </div>
            <div className="text-2xl font-bold text-white">4</div>
            <p className="text-xs text-amber-400 font-medium">$3,120.00 to collect</p>
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

        {/* Tab 1: Subscriptions */}
        {activeTab === "subscriptions" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-white">Active Subscriptions</h3>
                <p className="text-xs text-zinc-400">Live feed from billing engine</p>
              </div>
              <Button className="bg-blue-600 hover:bg-blue-500 text-white gap-2 text-xs">
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
                      <th className="py-3 px-4 text-right">Actions</th>
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
                        <td className="py-3.5 px-4 text-right">
                          <button className="text-blue-400 hover:underline font-sans text-xs">Manage</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>
        )}

        {/* Tab 2: Pricing Plans */}
        {activeTab === "plans" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-white">Available Plans</h3>
                <p className="text-xs text-zinc-400">Configured in API tier registry</p>
              </div>
              <Button className="bg-blue-600 hover:bg-blue-500 text-white gap-2 text-xs">
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
                  <Button variant="outline" className="w-full border-zinc-700 hover:bg-zinc-800 text-xs">
                    Configure Features
                  </Button>
                </Card>
              ))}
            </div>
          </div>
        )}

        {/* Tab 3: Customers */}
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

            {/* Filter and Search Bar */}
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

            {/* Customers Table */}
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
                      <th className="py-3 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-800/60 text-xs">
                    {filteredCustomers.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="py-8 text-center text-zinc-500">
                          No matching customer profiles found.
                        </td>
                      </tr>
                    ) : (
                      filteredCustomers.map((cust) => (
                        <tr key={cust.id} className="hover:bg-zinc-800/30 transition-colors">
                          <td className="py-3.5 px-4 font-medium text-white">{cust.displayName}</td>
                          <td className="py-3.5 px-4 text-zinc-300 flex items-center gap-1.5">
                            <Building className="w-3.5 h-3.5 text-zinc-500" /> {cust.companyName}
                          </td>
                          <td className="py-3.5 px-4 text-zinc-300 font-mono">
                            <span className="flex items-center gap-1.5">
                              <Mail className="w-3 h-3 text-zinc-500" /> {cust.billingEmail}
                            </span>
                          </td>
                          <td className="py-3.5 px-4">{getStatusBadge(cust.status)}</td>
                          <td className="py-3.5 px-4 text-zinc-400 font-mono">{cust.createdDate}</td>
                          <td className="py-3.5 px-4 text-right">
                            <button className="text-blue-400 hover:underline text-xs">Edit</button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>
        )}

        {/* Tab 4: Invoices */}
        {activeTab === "invoices" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-white">Billing Invoices</h3>
                <p className="text-xs text-zinc-400">Authoritative payment collection & invoice logs</p>
              </div>
              <Button variant="outline" className="border-zinc-800 text-xs text-zinc-300">
                Export CSV
              </Button>
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
                      <th className="py-3 px-4 text-right">PDF</th>
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
                        <td className="py-3.5 px-4 text-right">
                          <button className="text-blue-400 hover:underline font-sans text-xs">Download</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>
        )}
      </main>

      {/* Modal: Add Customer */}
      {isCustomerModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <Card className="w-full max-w-md bg-zinc-900 border-zinc-800 p-6 space-y-5 shadow-2xl">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
              <h3 className="text-base font-bold text-white">Add New Customer</h3>
              <button
                onClick={() => setIsCustomerModalOpen(false)}
                className="text-zinc-400 hover:text-white"
              >
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
                  onChange={(e) =>
                    setNewCustomer({ ...newCustomer, displayName: e.target.value })
                  }
                  className="bg-zinc-950 border-zinc-800 text-sm text-white"
                />
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs text-zinc-300">Company Name</Label>
                <Input
                  placeholder="e.g. Acme Corp (optional)"
                  value={newCustomer.companyName}
                  onChange={(e) =>
                    setNewCustomer({ ...newCustomer, companyName: e.target.value })
                  }
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
                  onChange={(e) =>
                    setNewCustomer({ ...newCustomer, billingEmail: e.target.value })
                  }
                  className="bg-zinc-950 border-zinc-800 text-sm text-white"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setIsCustomerModalOpen(false)}
                  className="border-zinc-800 hover:bg-zinc-800 text-xs text-zinc-300"
                >
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
    </div>
  )
}