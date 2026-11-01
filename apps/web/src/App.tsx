import React, { useState, useEffect, useCallback } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Users,
  CreditCard,
  Layers,
  FileText,
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
  Lock,
  RefreshCw,
  Download,
  Send,
  Ban,
  WalletCards,
  Bell,
  Check,
  Package,
  Percent,
  FileCheck2,
} from "lucide-react";

import type {
  SubscriptionItem,
  PlanItem,
  CustomerRecord,
  ProductRecord,
  TaxRuleRecord,
  DiscountRecord,
  QuotationRecord,
  InvoiceRecord,
  PaymentRecord,
  NotificationItem,
  AnalyticsDashboard,
  BillingInterval,
  PaymentMethod,
  TaxType,
  DiscountType,
  ProductType,
} from "@/types/domain.types";

import {
  fetchSubscriptions,
  createSubscription,
  fetchPlans,
  createPlan,
  fetchCustomers,
  createCustomer,
  fetchProducts,
  createProduct,
  fetchTaxRules,
  createTaxRule,
  fetchDiscounts,
  createDiscount,
  fetchQuotations,
  createQuotation,
  acceptQuotation,
  fetchInvoices,
  confirmInvoice,
  cancelInvoice,
  sendInvoice,
  downloadInvoicePdf,
  fetchPayments,
  recordPayment,
  fetchNotifications,
  markNotificationRead,
  markAllNotificationsRead,
  fetchAnalyticsDashboard,
} from "@/services/domain.service";
import { APP_CONFIG, USE_MOCK } from "@/services/mock.config";

export default function App() {
  const { user, login, logout, isLoading: authLoading, error: authContextError, clearError } = useAuth();
  const [activeTab, setActiveTab] = useState<
    "subscriptions" | "plans" | "customers" | "products" | "taxes" | "quotations" | "invoices" | "payments"
  >("subscriptions");
  const [loading, setLoading] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [successNotice, setSuccessNotice] = useState<string | null>(null);

  const [loginEmail, setLoginEmail] = useState("admin@brightloop.com");
  const [loginPassword, setLoginPassword] = useState("password123");
  const [isSubmittingAuth, setIsSubmittingAuth] = useState(false);

  // Live Records
  const [subscriptions, setSubscriptions] = useState<SubscriptionItem[]>([]);
  const [plans, setPlans] = useState<PlanItem[]>([]);
  const [customers, setCustomers] = useState<CustomerRecord[]>([]);
  const [products, setProducts] = useState<ProductRecord[]>([]);
  const [taxRules, setTaxRules] = useState<TaxRuleRecord[]>([]);
  const [discounts, setDiscounts] = useState<DiscountRecord[]>([]);
  const [quotations, setQuotations] = useState<QuotationRecord[]>([]);
  const [invoices, setInvoices] = useState<InvoiceRecord[]>([]);
  const [payments, setPayments] = useState<PaymentRecord[]>([]);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [analytics, setAnalytics] = useState<AnalyticsDashboard | null>(null);

  const [isNotifOpen, setIsNotifOpen] = useState(false);

  // Modals
  const [isCustomerModalOpen, setIsCustomerModalOpen] = useState(false);
  const [isSubModalOpen, setIsSubModalOpen] = useState(false);
  const [isPlanModalOpen, setIsPlanModalOpen] = useState(false);
  const [isProductModalOpen, setIsProductModalOpen] = useState(false);
  const [isTaxModalOpen, setIsTaxModalOpen] = useState(false);
  const [isDiscountModalOpen, setIsDiscountModalOpen] = useState(false);
  const [isQuoteModalOpen, setIsQuoteModalOpen] = useState(false);
  const [isPaymentModalOpen, setIsPaymentModalOpen] = useState(false);
  const [selectedInvoiceForPayment, setSelectedInvoiceForPayment] = useState<InvoiceRecord | null>(null);

  const [modalSubmitting, setModalSubmitting] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  const [customerSearch, setCustomerSearch] = useState("");

  // Payloads
  const [newCustomer, setNewCustomer] = useState({ displayName: "", companyName: "", billingEmail: "", phone: "", billingState: "Maharashtra" });
  const [newSub, setNewSub] = useState({ customerId: "", planId: "", productId: "" });
  const [newPlan, setNewPlan] = useState({
    name: "",
    price: "",
    currency: APP_CONFIG.DEFAULT_CURRENCY,
    billingInterval: "MONTHLY" as BillingInterval,
    intervalCount: 1,
  });
  const [newProduct, setNewProduct] = useState({ name: "", sku: "", salesPrice: "", currency: APP_CONFIG.DEFAULT_CURRENCY, type: "SERVICE" as ProductType });
  const [newTax, setNewTax] = useState({ name: "", code: "", taxType: "IGST" as TaxType, ratePercentage: "18.00", isInclusive: false });
  const [newDiscount, setNewDiscount] = useState({ name: "", code: "", discountType: "PERCENTAGE" as DiscountType, value: "10.00", maxUsage: 100 });
  const [newQuote, setNewQuote] = useState({
    customerId: "",
    planId: "",
    productId: "",
    quantity: 1,
    discountCode: "",
  });
  const [newPayment, setNewPayment] = useState({
    amount: "",
    currency: APP_CONFIG.DEFAULT_CURRENCY,
    method: "UPI" as PaymentMethod,
    reference: "",
  });

  const loadDomainData = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    setApiError(null);
    try {
      const [subsData, plansData, custsData, prodsData, taxesData, discsData, quotesData, invsData, paysData, notifsData, analyticsData] =
        await Promise.all([
          fetchSubscriptions().catch(() => []),
          fetchPlans().catch(() => []),
          fetchCustomers().catch(() => []),
          fetchProducts().catch(() => []),
          fetchTaxRules().catch(() => []),
          fetchDiscounts().catch(() => []),
          fetchQuotations().catch(() => []),
          fetchInvoices().catch(() => []),
          fetchPayments().catch(() => []),
          fetchNotifications().catch(() => []),
          fetchAnalyticsDashboard("INR").catch(() => null),
        ]);
      setSubscriptions(subsData);
      setPlans(plansData);
      setCustomers(custsData);
      setProducts(prodsData);
      setTaxRules(taxesData);
      setDiscounts(discsData);
      setQuotations(quotesData);
      setInvoices(invsData);
      setPayments(paysData);
      setNotifications(notifsData);
      setAnalytics(analyticsData);

      if (custsData.length > 0) {
        setNewSub((prev) => ({ ...prev, customerId: prev.customerId || custsData[0].id }));
        setNewQuote((prev) => ({ ...prev, customerId: prev.customerId || custsData[0].id }));
      }
      if (plansData.length > 0) {
        setNewSub((prev) => ({ ...prev, planId: prev.planId || plansData[0].id }));
        setNewQuote((prev) => ({ ...prev, planId: prev.planId || plansData[0].id }));
      }
      if (prodsData.length > 0) {
        setNewSub((prev) => ({ ...prev, productId: prev.productId || prodsData[0].id }));
        setNewQuote((prev) => ({ ...prev, productId: prev.productId || prodsData[0].id }));
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to load live backend records.";
      setApiError(message);
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    if (user) {
      loadDomainData();
    }
  }, [user, loadDomainData]);

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    setIsSubmittingAuth(true);
    try {
      await login({ email: loginEmail.trim(), password: loginPassword });
    } catch {
      // Handled in context
    } finally {
      setIsSubmittingAuth(false);
    }
  };

  const handleAddCustomer = async (e: React.FormEvent) => {
    e.preventDefault();
    setModalError(null);
    setModalSubmitting(true);
    try {
      const created = await createCustomer(newCustomer);
      setCustomers((prev) => [created, ...prev]);
      setNewCustomer({ displayName: "", companyName: "", billingEmail: "", phone: "", billingState: "Maharashtra" });
      setIsCustomerModalOpen(false);
      setSuccessNotice("Customer created successfully.");
    } catch (err: unknown) {
      setModalError(err instanceof Error ? err.message : "Failed to create customer.");
    } finally {
      setModalSubmitting(false);
    }
  };

  const handleAddPlan = async (e: React.FormEvent) => {
    e.preventDefault();
    setModalError(null);
    setModalSubmitting(true);
    try {
      const created = await createPlan(newPlan);
      setPlans((prev) => [...prev, created]);
      setNewPlan({
        name: "",
        price: "",
        currency: APP_CONFIG.DEFAULT_CURRENCY,
        billingInterval: "MONTHLY",
        intervalCount: 1,
      });
      setIsPlanModalOpen(false);
      setSuccessNotice("Pricing plan published.");
    } catch (err: unknown) {
      setModalError(err instanceof Error ? err.message : "Failed to publish plan.");
    } finally {
      setModalSubmitting(false);
    }
  };

  const handleAddProduct = async (e: React.FormEvent) => {
    e.preventDefault();
    setModalError(null);
    setModalSubmitting(true);
    try {
      const created = await createProduct(newProduct);
      setProducts((prev) => [created, ...prev]);
      setNewProduct({ name: "", sku: "", salesPrice: "", currency: APP_CONFIG.DEFAULT_CURRENCY, type: "SERVICE" });
      setIsProductModalOpen(false);
      setSuccessNotice("Product catalog item created.");
    } catch (err: unknown) {
      setModalError(err instanceof Error ? err.message : "Failed to create product.");
    } finally {
      setModalSubmitting(false);
    }
  };

  const handleAddTax = async (e: React.FormEvent) => {
    e.preventDefault();
    setModalError(null);
    setModalSubmitting(true);
    try {
      const created = await createTaxRule(newTax);
      setTaxRules((prev) => [created, ...prev]);
      setNewTax({ name: "", code: "", taxType: "IGST", ratePercentage: "18.00", isInclusive: false });
      setIsTaxModalOpen(false);
      setSuccessNotice("Tax rule configured.");
    } catch (err: unknown) {
      setModalError(err instanceof Error ? err.message : "Failed to configure tax rule.");
    } finally {
      setModalSubmitting(false);
    }
  };

  const handleAddDiscount = async (e: React.FormEvent) => {
    e.preventDefault();
    setModalError(null);
    setModalSubmitting(true);
    try {
      const created = await createDiscount(newDiscount);
      setDiscounts((prev) => [created, ...prev]);
      setNewDiscount({ name: "", code: "", discountType: "PERCENTAGE", value: "10.00", maxUsage: 100 });
      setIsDiscountModalOpen(false);
      setSuccessNotice("Discount rule published.");
    } catch (err: unknown) {
      setModalError(err instanceof Error ? err.message : "Failed to create discount.");
    } finally {
      setModalSubmitting(false);
    }
  };

  const handleAddQuotation = async (e: React.FormEvent) => {
    e.preventDefault();
    setModalError(null);
    const resolvedProductId = newQuote.productId || (products[0] ? products[0].id : "");
    if (!newQuote.customerId || !newQuote.planId || !resolvedProductId) {
      setModalError("Please select customer, plan, and a product line.");
      return;
    }
    setModalSubmitting(true);
    try {
      const created = await createQuotation({
        customerId: newQuote.customerId,
        planId: newQuote.planId,
        lines: [
          {
            productId: resolvedProductId,
            quantity: Number(newQuote.quantity) || 1,
          },
        ],
        discountCode: newQuote.discountCode || undefined,
      });
      setQuotations((prev) => [created, ...prev]);
      setIsQuoteModalOpen(false);
      setSuccessNotice("Quotation calculated and generated by backend.");
    } catch (err: unknown) {
      setModalError(err instanceof Error ? err.message : "Failed to calculate quotation.");
    } finally {
      setModalSubmitting(false);
    }
  };

  const handleAcceptQuotation = async (id: string) => {
    try {
      const res = await acceptQuotation(id);
      setQuotations((prev) => prev.map((q) => (q.id === id ? { ...q, status: "ACCEPTED", subscriptionId: res.subscriptionId } : q)));
      setSuccessNotice(`Quotation accepted! Subscription auto-provisioned: ${res.subscriptionId.slice(0, 8)}`);
      loadDomainData();
    } catch (err: unknown) {
      setApiError(err instanceof Error ? err.message : "Failed to accept quotation.");
    }
  };

  const handleAddSubscription = async (e: React.FormEvent) => {
    e.preventDefault();
    setModalError(null);
    if (!newSub.customerId || !newSub.planId) {
      setModalError("Select both customer and plan.");
      return;
    }
    const resolvedProductId = newSub.productId || (products[0] ? products[0].id : null);
    if (!resolvedProductId) {
      setModalError("No product found in catalog. Please create a catalog product first.");
      return;
    }
    setModalSubmitting(true);
    try {
      const created = await createSubscription({
        customerId: newSub.customerId,
        planId: newSub.planId,
        lines: [
          {
            productId: resolvedProductId,
            quantity: 1,
          },
        ],
      });
      setSubscriptions((prev) => [created, ...prev]);
      setIsSubModalOpen(false);
      setSuccessNotice("Subscription provisioned successfully.");
    } catch (err: unknown) {
      setModalError(err instanceof Error ? err.message : "Failed to provision subscription.");
    } finally {
      setModalSubmitting(false);
    }
  };

  const handleConfirmInvoice = async (id: string) => {
    try {
      const updated = await confirmInvoice(id);
      setInvoices((prev) => prev.map((inv) => (inv.id === id ? updated : inv)));
      setSuccessNotice("Invoice confirmed successfully.");
    } catch (err: unknown) {
      setApiError(err instanceof Error ? err.message : "Failed to confirm invoice.");
    }
  };

  const handleCancelInvoice = async (id: string) => {
    try {
      const updated = await cancelInvoice(id);
      setInvoices((prev) => prev.map((inv) => (inv.id === id ? updated : inv)));
      setSuccessNotice("Invoice cancelled.");
    } catch (err: unknown) {
      setApiError(err instanceof Error ? err.message : "Failed to cancel invoice.");
    }
  };

  const handleSendInvoice = async (id: string) => {
    try {
      const res = await sendInvoice(id);
      setSuccessNotice(res.message || "Invoice notification queued.");
    } catch (err: unknown) {
      setApiError(err instanceof Error ? err.message : "Failed to queue invoice send.");
    }
  };

  const handleDownloadPdf = async (id: string, num?: string) => {
    try {
      await downloadInvoicePdf(id, num || `INV-${id.slice(0, 8)}`);
    } catch (err: unknown) {
      setApiError(err instanceof Error ? err.message : "Failed to download PDF.");
    }
  };

  const openPaymentModal = (invoice: InvoiceRecord) => {
    setSelectedInvoiceForPayment(invoice);
    setNewPayment({
      amount: String(invoice.amountDue || invoice.totalAmount),
      currency: invoice.currency || APP_CONFIG.DEFAULT_CURRENCY,
      method: "UPI",
      reference: "",
    });
    setModalError(null);
    setIsPaymentModalOpen(true);
  };

  const handleRecordPayment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedInvoiceForPayment) return;
    setModalError(null);
    setModalSubmitting(true);
    try {
      const payment = await recordPayment({
        invoiceId: selectedInvoiceForPayment.id,
        amount: newPayment.amount,
        currency: newPayment.currency,
        method: newPayment.method,
        reference: newPayment.reference,
      });
      setPayments((prev) => [payment, ...prev]);
      setIsPaymentModalOpen(false);
      setSuccessNotice("Payment recorded and allocated.");
      loadDomainData();
    } catch (err: unknown) {
      setModalError(err instanceof Error ? err.message : "Failed to record payment.");
    } finally {
      setModalSubmitting(false);
    }
  };

  const handleMarkOneRead = async (id: string) => {
    await markNotificationRead(id);
    setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, isRead: true } : n)));
  };

  const handleMarkAllRead = async () => {
    await markAllNotificationsRead();
    setNotifications((prev) => prev.map((n) => ({ ...n, isRead: true })));
  };

  const unreadCount = notifications.filter((n) => !n.isRead).length;

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "ACTIVE":
      case "PAID":
      case "SUCCEEDED":
      case "ACCEPTED":
        return <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-xs font-semibold text-emerald-400 border border-emerald-500/20"><CheckCircle2 className="w-3 h-3" /> {status}</span>;
      case "PAST_DUE":
      case "OVERDUE":
      case "FAILED":
      case "CANCELLED":
      case "REJECTED":
        return <span className="inline-flex items-center gap-1 rounded-full bg-rose-500/10 px-2 py-0.5 text-xs font-semibold text-rose-400 border border-rose-500/20"><AlertCircle className="w-3 h-3" /> {status}</span>;
      case "CONFIRMED":
      case "PARTIALLY_PAID":
      case "PENDING":
      case "SENT":
        return <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/10 px-2 py-0.5 text-xs font-semibold text-amber-400 border border-amber-500/20">{status}</span>;
      default:
        return <span className="inline-flex items-center gap-1 rounded-full bg-zinc-500/10 px-2 py-0.5 text-xs font-semibold text-zinc-400 border border-zinc-500/20">{status}</span>;
    }
  };

  const term = (customerSearch || "").trim().toLowerCase();
  const filteredCustomers = customers.filter((c) => {
    if (!term) return true;
    const nameMatch = c.displayName ? c.displayName.toLowerCase().includes(term) : false;
    const compMatch = c.companyName ? c.companyName.toLowerCase().includes(term) : false;
    const emailMatch = c.billingEmail ? c.billingEmail.toLowerCase().includes(term) : false;
    return nameMatch || compMatch || emailMatch;
  });

  // Customer display label resolver
  const getCustomerLabel = (c: CustomerRecord) => {
    if (c.companyName) return `${c.displayName} (${c.companyName})`;
    return c.displayName;
  };

  if (authLoading) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-zinc-950 text-zinc-400 gap-2">
        <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
        <span className="text-sm font-medium">Validating security session...</span>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="flex min-h-screen w-full items-center justify-center bg-zinc-950 px-4 text-zinc-100">
        <Card className="w-full max-w-md bg-zinc-900 border-zinc-800 p-8 shadow-2xl space-y-6">
          <div className="flex flex-col items-center text-center space-y-2">
            <div className="h-12 w-12 rounded-xl bg-blue-600 flex items-center justify-center font-bold text-white text-xl shadow-lg shadow-blue-500/30">
              B
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-white">Sign in to BrightLoop</h1>
            <p className="text-xs text-zinc-400">Subscription & Billing Engine Portal</p>
          </div>

          {authContextError && (
            <div className="flex items-center gap-2 rounded-lg bg-rose-500/10 border border-rose-500/20 p-3 text-xs text-rose-400">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{authContextError}</span>
            </div>
          )}

          <form onSubmit={handleLoginSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <Label className="text-xs text-zinc-300">Email Address</Label>
              <div className="relative">
                <Mail className="absolute left-3 top-2.5 h-4 w-4 text-zinc-500" />
                <Input
                  required
                  type="email"
                  value={loginEmail}
                  onChange={(e) => setLoginEmail(e.target.value)}
                  placeholder="admin@brightloop.com"
                  className="pl-9 bg-zinc-950 border-zinc-800 text-sm text-white"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs text-zinc-300">Password</Label>
              <div className="relative">
                <Lock className="absolute left-3 top-2.5 h-4 w-4 text-zinc-500" />
                <Input
                  required
                  type="password"
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                  placeholder="••••••••"
                  className="pl-9 bg-zinc-950 border-zinc-800 text-sm text-white"
                />
              </div>
            </div>

            <Button
              type="submit"
              disabled={isSubmittingAuth}
              className="w-full bg-blue-600 hover:bg-blue-500 text-white font-medium py-2.5 text-sm transition-all shadow-md shadow-blue-600/20"
            >
              {isSubmittingAuth ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin mr-2" /> Connecting...
                </>
              ) : (
                "Sign In"
              )}
            </Button>
          </form>

          <div className="rounded-lg bg-zinc-950 border border-zinc-800 p-3 text-xs text-zinc-400 space-y-1 font-mono">
            <div className="flex justify-between">
              <span>Mode:</span>
              <span className={USE_MOCK ? "text-amber-400" : "text-emerald-400"}>
                {USE_MOCK ? "MOCK_MODE" : "LIVE_FASTAPI_BACKEND"}
              </span>
            </div>
            <div className="flex justify-between">
              <span>Base URL:</span>
              <span className="truncate max-w-[200px]">{APP_CONFIG.API_BASE_URL}</span>
            </div>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex h-screen w-full bg-zinc-950 text-zinc-100">
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
              onClick={() => setActiveTab("quotations")}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === "quotations" ? "bg-blue-600 text-white" : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100"
              }`}
            >
              <FileCheck2 className="w-4 h-4" /> Quotations
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
              onClick={() => setActiveTab("products")}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === "products" ? "bg-blue-600 text-white" : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100"
              }`}
            >
              <Package className="w-4 h-4" /> Catalog Products
            </button>
            <button
              onClick={() => setActiveTab("taxes")}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === "taxes" ? "bg-blue-600 text-white" : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100"
              }`}
            >
              <Percent className="w-4 h-4" /> Tax & Discounts
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
            <button
              onClick={() => setActiveTab("payments")}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === "payments" ? "bg-blue-600 text-white" : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100"
              }`}
            >
              <WalletCards className="w-4 h-4" /> Payments
            </button>
          </nav>
        </div>

        <div className="border-t border-zinc-800 pt-4">
          <div className="flex items-center justify-between">
            <div className="overflow-hidden">
              <p className="text-sm font-semibold truncate text-white">{user.email}</p>
              <span className="text-xs text-blue-400 uppercase tracking-wider font-mono font-medium">
                {user.role}
              </span>
            </div>
            <Button
              variant="ghost"
              size="icon"
              title="Log out"
              onClick={logout}
              className="text-zinc-400 hover:text-rose-400 hover:bg-zinc-800"
            >
              <LogOut className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto p-8 space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold tracking-tight text-white">Commercial & Revenue Operations</h2>
            <p className="text-sm text-zinc-400">PostgreSQL synchronized via FastAPI v1 routes.</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="relative">
              <Button
                variant="outline"
                size="icon"
                onClick={() => setIsNotifOpen(!isNotifOpen)}
                className="relative border-zinc-800 text-zinc-300 hover:bg-zinc-900"
              >
                <Bell className="w-4 h-4" />
                {unreadCount > 0 && (
                  <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-blue-600 text-[10px] font-bold text-white">
                    {unreadCount}
                  </span>
                )}
              </Button>

              {isNotifOpen && (
                <Card className="absolute right-0 mt-2 w-80 bg-zinc-900 border-zinc-800 p-4 shadow-xl z-50 space-y-3">
                  <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
                    <span className="text-xs font-semibold text-white">Notifications ({unreadCount} unread)</span>
                    {unreadCount > 0 && (
                      <button onClick={handleMarkAllRead} className="text-[11px] text-blue-400 hover:underline">
                        Mark all read
                      </button>
                    )}
                  </div>
                  <div className="max-h-60 overflow-y-auto space-y-2">
                    {notifications.length === 0 ? (
                      <p className="text-xs text-zinc-500 text-center py-4">No notifications yet.</p>
                    ) : (
                      notifications.map((n) => (
                        <div
                          key={n.id}
                          className={`p-2 rounded text-xs space-y-1 transition-colors ${
                            n.isRead ? "bg-zinc-950/40 text-zinc-400" : "bg-zinc-800/60 text-zinc-100"
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-semibold text-white">{n.title}</span>
                            {!n.isRead && (
                              <button onClick={() => handleMarkOneRead(n.id)} title="Mark read" className="text-blue-400 hover:text-white">
                                <Check className="w-3 h-3" />
                              </button>
                            )}
                          </div>
                          <p className="text-[11px] text-zinc-400">{n.message}</p>
                        </div>
                      ))
                    )}
                  </div>
                </Card>
              )}
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={loadDomainData}
              disabled={loading}
              className="border-zinc-800 text-zinc-300 hover:bg-zinc-900 gap-1.5 text-xs"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} /> Refresh Live Data
            </Button>
          </div>
        </div>

        {apiError && (
          <div className="flex items-center justify-between rounded-lg bg-rose-500/10 border border-rose-500/20 p-4 text-xs text-rose-400">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{apiError}</span>
            </div>
            <Button variant="ghost" size="sm" onClick={() => setApiError(null)} className="h-auto p-1 text-rose-400">
              <X className="w-3.5 h-3.5" />
            </Button>
          </div>
        )}

        {successNotice && (
          <div className="flex items-center justify-between rounded-lg bg-emerald-500/10 border border-emerald-500/20 p-3 text-xs text-emerald-400">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{successNotice}</span>
            </div>
            <Button variant="ghost" size="sm" onClick={() => setSuccessNotice(null)} className="h-auto p-1 text-emerald-400">
              <X className="w-3.5 h-3.5" />
            </Button>
          </div>
        )}

        {/* Dashboard Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card className="bg-zinc-900 border-zinc-800 p-5 space-y-2">
            <div className="flex items-center justify-between text-zinc-400">
              <span className="text-xs font-medium">Monthly Recurring Revenue (MRR)</span>
              <TrendingUp className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="text-2xl font-bold text-white">
              ₹{analytics ? analytics.mrr : "0.00"}
            </div>
            <p className="text-xs text-emerald-400 font-medium">
              ARR: ₹{analytics ? analytics.arr : "0.00"}
            </p>
          </Card>

          <Card className="bg-zinc-900 border-zinc-800 p-5 space-y-2">
            <div className="flex items-center justify-between text-zinc-400">
              <span className="text-xs font-medium">Collected Revenue</span>
              <WalletCards className="w-4 h-4 text-blue-400" />
            </div>
            <div className="text-2xl font-bold text-white">
              ₹{analytics ? analytics.collectedRevenue : "0.00"}
            </div>
            <p className="text-xs text-zinc-400">Settled payments</p>
          </Card>

          <Card className="bg-zinc-900 border-zinc-800 p-5 space-y-2">
            <div className="flex items-center justify-between text-zinc-400">
              <span className="text-xs font-medium">Active Subscriptions</span>
              <CreditCard className="w-4 h-4 text-purple-400" />
            </div>
            <div className="text-2xl font-bold text-white">
              {analytics ? analytics.activeSubscriptions : subscriptions.length}
            </div>
            <p className="text-xs text-zinc-400">Active billing accounts</p>
          </Card>

          <Card className="bg-zinc-900 border-zinc-800 p-5 space-y-2">
            <div className="flex items-center justify-between text-zinc-400">
              <span className="text-xs font-medium">Quotations Created</span>
              <FileCheck2 className="w-4 h-4 text-amber-400" />
            </div>
            <div className="text-2xl font-bold text-white">{quotations.length}</div>
            <p className="text-xs text-zinc-400">Backend calculated proposals</p>
          </Card>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20 text-zinc-400 gap-2">
            <Loader2 className="w-5 h-5 animate-spin text-blue-500" />
            <span className="text-sm">Synchronizing live records from database...</span>
          </div>
        ) : (
          <>
            {/* Subscriptions */}
            {activeTab === "subscriptions" && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-white">Active Subscriptions</h3>
                    <p className="text-xs text-zinc-400">Governed by plan policy flags</p>
                  </div>
                  <Button
                    onClick={() => {
                      setModalError(null);
                      setIsSubModalOpen(true);
                    }}
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
                          <th className="py-3 px-4">Subscription ID</th>
                          <th className="py-3 px-4">Customer</th>
                          <th className="py-3 px-4">Plan</th>
                          <th className="py-3 px-4">Price</th>
                          <th className="py-3 px-4">Status</th>
                          <th className="py-3 px-4">Interval</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-zinc-800/60 font-mono text-xs">
                        {subscriptions.length === 0 ? (
                          <tr><td colSpan={6} className="py-8 text-center text-zinc-500">No subscriptions found.</td></tr>
                        ) : (
                          subscriptions.map((sub) => (
                            <tr key={sub.id} className="hover:bg-zinc-800/30 transition-colors">
                              <td className="py-3.5 px-4 font-semibold text-white">{sub.subscriptionNumber || sub.id.slice(0, 8)}</td>
                              <td className="py-3.5 px-4 text-zinc-300 font-sans">{sub.customerName || sub.customerId}</td>
                              <td className="py-3.5 px-4 text-zinc-300 font-sans">{sub.planName || sub.planId}</td>
                              <td className="py-3.5 px-4 text-white font-semibold">{sub.currency} {sub.price}</td>
                              <td className="py-3.5 px-4">{getStatusBadge(sub.status)}</td>
                              <td className="py-3.5 px-4 text-zinc-400">{sub.billingInterval}</td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </Card>
              </div>
            )}

            {/* Quotations */}
            {activeTab === "quotations" && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-white">Commercial Quotations</h3>
                    <p className="text-xs text-zinc-400">Authoritative server calculation & instant subscription provisioning</p>
                  </div>
                  <Button
                    onClick={() => {
                      setModalError(null);
                      setIsQuoteModalOpen(true);
                    }}
                    className="bg-blue-600 hover:bg-blue-500 text-white gap-2 text-xs"
                  >
                    <Plus className="w-3.5 h-3.5" /> Create Quotation
                  </Button>
                </div>

                <Card className="bg-zinc-900 border-zinc-800 overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                      <thead className="bg-zinc-950/60 text-xs uppercase text-zinc-400 border-b border-zinc-800">
                        <tr>
                          <th className="py-3 px-4">Quote #</th>
                          <th className="py-3 px-4">Customer</th>
                          <th className="py-3 px-4">Subtotal</th>
                          <th className="py-3 px-4">Tax Amount</th>
                          <th className="py-3 px-4">Final Total</th>
                          <th className="py-3 px-4">Status</th>
                          <th className="py-3 px-4 text-right">Action</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-zinc-800/60 font-mono text-xs">
                        {quotations.length === 0 ? (
                          <tr><td colSpan={7} className="py-8 text-center text-zinc-500">No quotations generated yet.</td></tr>
                        ) : (
                          quotations.map((q) => (
                            <tr key={q.id} className="hover:bg-zinc-800/30 transition-colors">
                              <td className="py-3.5 px-4 font-semibold text-white">{q.quotationNumber || q.id.slice(0, 8)}</td>
                              <td className="py-3.5 px-4 font-sans text-zinc-300">{q.customerName || q.customerId.slice(0, 8)}</td>
                              <td className="py-3.5 px-4 text-zinc-300">{q.currency} {q.subtotal}</td>
                              <td className="py-3.5 px-4 text-amber-400">{q.currency} {q.taxAmount}</td>
                              <td className="py-3.5 px-4 text-white font-bold">{q.currency} {q.totalAmount}</td>
                              <td className="py-3.5 px-4">{getStatusBadge(q.status)}</td>
                              <td className="py-3.5 px-4 text-right font-sans">
                                {q.status !== "ACCEPTED" && (
                                  <Button
                                    size="sm"
                                    onClick={() => handleAcceptQuotation(q.id)}
                                    className="h-7 text-[11px] bg-emerald-600 hover:bg-emerald-500 text-white"
                                  >
                                    Accept & Provision
                                  </Button>
                                )}
                                {q.status === "ACCEPTED" && (
                                  <span className="text-[11px] text-zinc-500 font-mono">
                                    Sub: {q.subscriptionId?.slice(0, 8) || "Linked"}
                                  </span>
                                )}
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

            {/* Plans */}
            {activeTab === "plans" && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-white">Available Plans</h3>
                    <p className="text-xs text-zinc-400">Validated against billing_interval and currency schema</p>
                  </div>
                  <Button
                    onClick={() => {
                      setModalError(null);
                      setIsPlanModalOpen(true);
                    }}
                    className="bg-blue-600 hover:bg-blue-500 text-white gap-2 text-xs"
                  >
                    <Plus className="w-3.5 h-3.5" /> Add Tier
                  </Button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {plans.map((p) => (
                    <Card key={p.id} className="bg-zinc-900 border-zinc-800 p-6 flex flex-col justify-between space-y-4">
                      <div>
                        <div className="flex justify-between items-start">
                          <h4 className="text-base font-bold text-white">{p.name}</h4>
                          <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-zinc-800 text-zinc-400">{p.currency}</span>
                        </div>
                        <div className="mt-3 text-3xl font-extrabold text-white">
                          ₹{p.price}{" "}
                          <span className="text-xs text-zinc-500 font-normal">/{p.billingInterval.toLowerCase()}</span>
                        </div>
                        <p className="mt-4 text-xs text-zinc-400">{p.description || `Configured ${p.billingInterval} recurring tier`}</p>
                      </div>
                    </Card>
                  ))}
                </div>
              </div>
            )}

            {/* Catalog Products */}
            {activeTab === "products" && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-white">Catalog Products</h3>
                    <p className="text-xs text-zinc-400">Products and variants (/api/v1/products)</p>
                  </div>
                  <Button
                    onClick={() => {
                      setModalError(null);
                      setIsProductModalOpen(true);
                    }}
                    className="bg-blue-600 hover:bg-blue-500 text-white gap-2 text-xs"
                  >
                    <Plus className="w-3.5 h-3.5" /> Add Product
                  </Button>
                </div>

                <Card className="bg-zinc-900 border-zinc-800 overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                      <thead className="bg-zinc-950/60 text-xs uppercase text-zinc-400 border-b border-zinc-800">
                        <tr>
                          <th className="py-3 px-4">Product Name</th>
                          <th className="py-3 px-4">SKU</th>
                          <th className="py-3 px-4">Type</th>
                          <th className="py-3 px-4">Sales Price</th>
                          <th className="py-3 px-4">Status</th>
                          <th className="py-3 px-4">Product UUID</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-zinc-800/60 text-xs">
                        {products.length === 0 ? (
                          <tr><td colSpan={6} className="py-8 text-center text-zinc-500">No products configured in catalog.</td></tr>
                        ) : (
                          products.map((p) => (
                            <tr key={p.id} className="hover:bg-zinc-800/30 transition-colors">
                              <td className="py-3.5 px-4 font-medium text-white">{p.name}</td>
                              <td className="py-3.5 px-4 font-mono text-zinc-300">{p.sku}</td>
                              <td className="py-3.5 px-4 text-zinc-400">{p.type}</td>
                              <td className="py-3.5 px-4 text-white font-semibold">{p.currency} {p.salesPrice}</td>
                              <td className="py-3.5 px-4">{getStatusBadge(p.isActive ? "ACTIVE" : "INACTIVE")}</td>
                              <td className="py-3.5 px-4 text-zinc-500 font-mono text-[11px]">{p.id}</td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </Card>
              </div>
            )}

            {/* Taxes & Discounts */}
            {activeTab === "taxes" && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-base font-semibold text-white">Tax Rules (GST Engine)</h3>
                      <p className="text-xs text-zinc-400">Classifications: CGST, SGST, IGST, Generic</p>
                    </div>
                    <Button onClick={() => setIsTaxModalOpen(true)} size="sm" className="bg-blue-600 hover:bg-blue-500 text-xs">
                      <Plus className="w-3.5 h-3.5 mr-1" /> Add Rule
                    </Button>
                  </div>
                  <Card className="bg-zinc-900 border-zinc-800 p-4 divide-y divide-zinc-800">
                    {taxRules.length === 0 ? (
                      <p className="text-xs text-zinc-500 text-center py-4">No tax rules created.</p>
                    ) : (
                      taxRules.map((t) => (
                        <div key={t.id} className="py-2.5 flex justify-between items-center text-xs">
                          <div>
                            <p className="font-semibold text-white">{t.name} ({t.code})</p>
                            <span className="text-[10px] text-zinc-400">{t.taxType} &bull; {t.isInclusive ? "Inclusive" : "Exclusive"}</span>
                          </div>
                          <span className="font-mono text-amber-400 font-semibold">{t.ratePercentage}%</span>
                        </div>
                      ))
                    )}
                  </Card>
                </div>

                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-base font-semibold text-white">Discount Rules</h3>
                      <p className="text-xs text-zinc-400">Policy: Highest saving wins (non-stacking)</p>
                    </div>
                    <Button onClick={() => setIsDiscountModalOpen(true)} size="sm" className="bg-blue-600 hover:bg-blue-500 text-xs">
                      <Plus className="w-3.5 h-3.5 mr-1" /> Add Discount
                    </Button>
                  </div>
                  <Card className="bg-zinc-900 border-zinc-800 p-4 divide-y divide-zinc-800">
                    {discounts.length === 0 ? (
                      <p className="text-xs text-zinc-500 text-center py-4">No discount rules created.</p>
                    ) : (
                      discounts.map((d) => (
                        <div key={d.id} className="py-2.5 flex justify-between items-center text-xs">
                          <div>
                            <p className="font-semibold text-white">{d.name} ({d.code})</p>
                            <span className="text-[10px] text-zinc-400">{d.discountType} &bull; Max usage: {d.maxUsage || "Unlimited"}</span>
                          </div>
                          <span className="font-mono text-emerald-400 font-semibold">
                            {d.discountType === "PERCENTAGE" ? `${d.value}%` : `₹${d.value}`}
                          </span>
                        </div>
                      ))
                    )}
                  </Card>
                </div>
              </div>
            )}

            {/* Customers */}
            {activeTab === "customers" && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-white">Customer Registry</h3>
                    <p className="text-xs text-zinc-400">PostgreSQL verified accounts</p>
                  </div>
                  <Button
                    onClick={() => {
                      setModalError(null);
                      setIsCustomerModalOpen(true);
                    }}
                    className="bg-blue-600 hover:bg-blue-500 text-white gap-2 text-xs"
                  >
                    <Plus className="w-3.5 h-3.5" /> Add Customer
                  </Button>
                </div>

                <div className="flex items-center gap-3">
                  <div className="relative flex-1 max-w-sm">
                    <Search className="absolute left-3 top-2.5 h-4 w-4 text-zinc-500" />
                    <Input
                      placeholder="Search name, company, email..."
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
                          <th className="py-3 px-4">State</th>
                          <th className="py-3 px-4">Status</th>
                          <th className="py-3 px-4">Customer UUID</th>
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
                              <span className="flex items-center gap-1.5"><Mail className="w-3 h-3 text-zinc-500" /> {cust.billingEmail || "—"}</span>
                            </td>
                            <td className="py-3.5 px-4 text-zinc-400 font-sans">{cust.billingState}</td>
                            <td className="py-3.5 px-4">{getStatusBadge(cust.status || "ACTIVE")}</td>
                            <td className="py-3.5 px-4 text-zinc-500 font-mono text-[11px]">{cust.id}</td>
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
                    <h3 className="text-lg font-semibold text-white">Invoices Ledger</h3>
                    <p className="text-xs text-zinc-400">Synced with backend /api/v1/invoices</p>
                  </div>
                </div>

                <Card className="bg-zinc-900 border-zinc-800 overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                      <thead className="bg-zinc-950/60 text-xs uppercase text-zinc-400 border-b border-zinc-800">
                        <tr>
                          <th className="py-3 px-4">Invoice #</th>
                          <th className="py-3 px-4">Total Amount</th>
                          <th className="py-3 px-4">Due Balance</th>
                          <th className="py-3 px-4">Status</th>
                          <th className="py-3 px-4">Due Date</th>
                          <th className="py-3 px-4 text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-zinc-800/60 text-xs font-mono">
                        {invoices.length === 0 ? (
                          <tr><td colSpan={6} className="py-8 text-center text-zinc-500">No invoices generated yet.</td></tr>
                        ) : (
                          invoices.map((inv) => (
                            <tr key={inv.id} className="hover:bg-zinc-800/30 transition-colors">
                              <td className="py-3.5 px-4 font-semibold text-white">{inv.invoiceNumber || inv.id.slice(0, 8)}</td>
                              <td className="py-3.5 px-4 text-white">{inv.currency} {inv.totalAmount}</td>
                              <td className="py-3.5 px-4 text-zinc-300">{inv.currency} {inv.amountDue}</td>
                              <td className="py-3.5 px-4">{getStatusBadge(inv.status)}</td>
                              <td className="py-3.5 px-4 text-zinc-400">{inv.dueDate}</td>
                              <td className="py-3.5 px-4 text-right font-sans space-x-1.5">
                                {inv.status === "DRAFT" && (
                                  <Button size="sm" variant="outline" onClick={() => handleConfirmInvoice(inv.id)} className="h-7 text-[11px] border-zinc-700">
                                    Confirm
                                  </Button>
                                )}
                                {(inv.status === "CONFIRMED" || inv.status === "PARTIALLY_PAID" || inv.status === "OVERDUE") && (
                                  <Button size="sm" onClick={() => openPaymentModal(inv)} className="h-7 text-[11px] bg-emerald-600 hover:bg-emerald-500 text-white">
                                    Record Payment
                                  </Button>
                                )}
                                <Button size="sm" variant="ghost" onClick={() => handleDownloadPdf(inv.id, inv.invoiceNumber)} title="Download PDF" className="h-7 w-7 p-0 text-zinc-400 hover:text-white">
                                  <Download className="w-3.5 h-3.5" />
                                </Button>
                                <Button size="sm" variant="ghost" onClick={() => handleSendInvoice(inv.id)} title="Send Invoice" className="h-7 w-7 p-0 text-zinc-400 hover:text-white">
                                  <Send className="w-3.5 h-3.5" />
                                </Button>
                                {inv.status === "DRAFT" && (
                                  <Button size="sm" variant="ghost" onClick={() => handleCancelInvoice(inv.id)} title="Cancel Invoice" className="h-7 w-7 p-0 text-rose-400 hover:text-rose-300">
                                    <Ban className="w-3.5 h-3.5" />
                                  </Button>
                                )}
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

            {/* Payments */}
            {activeTab === "payments" && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-white">Payment Allocations</h3>
                    <p className="text-xs text-zinc-400">Directly recorded via /api/v1/payments</p>
                  </div>
                </div>

                <Card className="bg-zinc-900 border-zinc-800 overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                      <thead className="bg-zinc-950/60 text-xs uppercase text-zinc-400 border-b border-zinc-800">
                        <tr>
                          <th className="py-3 px-4">Payment #</th>
                          <th className="py-3 px-4">Invoice ID</th>
                          <th className="py-3 px-4">Amount</th>
                          <th className="py-3 px-4">Method</th>
                          <th className="py-3 px-4">Status</th>
                          <th className="py-3 px-4">Recorded Date</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-zinc-800/60 font-mono text-xs">
                        {payments.length === 0 ? (
                          <tr><td colSpan={6} className="py-8 text-center text-zinc-500">No payment transactions recorded.</td></tr>
                        ) : (
                          payments.map((p) => (
                            <tr key={p.id} className="hover:bg-zinc-800/30 transition-colors">
                              <td className="py-3.5 px-4 font-semibold text-white">{p.paymentNumber || p.id.slice(0, 8)}</td>
                              <td className="py-3.5 px-4 text-zinc-400">{p.invoiceId.slice(0, 8)}</td>
                              <td className="py-3.5 px-4 text-emerald-400 font-semibold">{p.currency} {p.amount}</td>
                              <td className="py-3.5 px-4 text-zinc-300 font-sans">{p.method}</td>
                              <td className="py-3.5 px-4">{getStatusBadge(p.status)}</td>
                              <td className="py-3.5 px-4 text-zinc-400">{p.createdAt.split("T")[0]}</td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </Card>
              </div>
            )}
          </>
        )}
      </main>

      {/* Modal: Customer */}
      {isCustomerModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <Card className="w-full max-w-md bg-zinc-900 border-zinc-800 p-6 space-y-5">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
              <h3 className="text-base font-bold text-white">Add Customer</h3>
              <button onClick={() => setIsCustomerModalOpen(false)} className="text-zinc-400 hover:text-white"><X className="w-4 h-4" /></button>
            </div>
            {modalError && <div className="p-2.5 rounded bg-rose-500/10 border border-rose-500/20 text-xs text-rose-400">{modalError}</div>}
            <form onSubmit={handleAddCustomer} className="space-y-4">
              <div className="space-y-1.5">
                <Label className="text-xs text-zinc-300">Display Name *</Label>
                <Input required value={newCustomer.displayName} onChange={(e) => setNewCustomer({ ...newCustomer, displayName: e.target.value })} className="bg-zinc-950 border-zinc-800 text-sm text-white" />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-zinc-300">Company Name</Label>
                <Input value={newCustomer.companyName} onChange={(e) => setNewCustomer({ ...newCustomer, companyName: e.target.value })} className="bg-zinc-950 border-zinc-800 text-sm text-white" />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-zinc-300">Billing Email *</Label>
                <Input required type="email" value={newCustomer.billingEmail} onChange={(e) => setNewCustomer({ ...newCustomer, billingEmail: e.target.value })} className="bg-zinc-950 border-zinc-800 text-sm text-white" />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-zinc-300">Billing State (Demo: Maharashtra) *</Label>
                <Input required value={newCustomer.billingState} onChange={(e) => setNewCustomer({ ...newCustomer, billingState: e.target.value })} className="bg-zinc-950 border-zinc-800 text-sm text-white" />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <Button type="button" variant="outline" onClick={() => setIsCustomerModalOpen(false)} className="border-zinc-800 text-xs">Cancel</Button>
                <Button type="submit" disabled={modalSubmitting} className="bg-blue-600 hover:bg-blue-500 text-xs text-white">Create Customer</Button>
              </div>
            </form>
          </Card>
        </div>
      )}

      {/* Modal: Plan */}
      {isPlanModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <Card className="w-full max-w-md bg-zinc-900 border-zinc-800 p-6 space-y-5">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
              <h3 className="text-base font-bold text-white">Add Pricing Tier</h3>
              <button onClick={() => setIsPlanModalOpen(false)} className="text-zinc-400 hover:text-white"><X className="w-4 h-4" /></button>
            </div>
            {modalError && <div className="p-2.5 rounded bg-rose-500/10 border border-rose-500/20 text-xs text-rose-400">{modalError}</div>}
            <form onSubmit={handleAddPlan} className="space-y-4">
              <div className="space-y-1.5">
                <Label className="text-xs text-zinc-300">Plan Name *</Label>
                <Input required value={newPlan.name} onChange={(e) => setNewPlan({ ...newPlan, name: e.target.value })} className="bg-zinc-950 border-zinc-800 text-sm text-white" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-xs text-zinc-300">Price *</Label>
                  <Input required placeholder="499.00" value={newPlan.price} onChange={(e) => setNewPlan({ ...newPlan, price: e.target.value })} className="bg-zinc-950 border-zinc-800 text-sm text-white font-mono" />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs text-zinc-300">Currency *</Label>
                  <Input required value={newPlan.currency} onChange={(e) => setNewPlan({ ...newPlan, currency: e.target.value.toUpperCase() })} className="bg-zinc-950 border-zinc-800 text-sm text-white font-mono uppercase" />
                </div>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-zinc-300">Billing Interval *</Label>
                <select value={newPlan.billingInterval} onChange={(e) => setNewPlan({ ...newPlan, billingInterval: e.target.value as BillingInterval })} className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-sm text-white focus:outline-none">
                  <option value="DAILY">Daily</option>
                  <option value="WEEKLY">Weekly</option>
                  <option value="MONTHLY">Monthly</option>
                  <option value="YEARLY">Yearly</option>
                </select>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <Button type="button" variant="outline" onClick={() => setIsPlanModalOpen(false)} className="border-zinc-800 text-xs">Cancel</Button>
                <Button type="submit" disabled={modalSubmitting} className="bg-blue-600 hover:bg-blue-500 text-xs text-white">Publish Plan Tier</Button>
              </div>
            </form>
          </Card>
        </div>
      )}

      {/* Modal: Product */}
      {isProductModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <Card className="w-full max-w-md bg-zinc-900 border-zinc-800 p-6 space-y-5">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
              <h3 className="text-base font-bold text-white">Add Catalog Product</h3>
              <button onClick={() => setIsProductModalOpen(false)} className="text-zinc-400 hover:text-white"><X className="w-4 h-4" /></button>
            </div>
            {modalError && <div className="p-2.5 rounded bg-rose-500/10 border border-rose-500/20 text-xs text-rose-400">{modalError}</div>}
            <form onSubmit={handleAddProduct} className="space-y-4">
              <div className="space-y-1.5">
                <Label className="text-xs text-zinc-300">Product Name *</Label>
                <Input required value={newProduct.name} onChange={(e) => setNewProduct({ ...newProduct, name: e.target.value })} className="bg-zinc-950 border-zinc-800 text-sm text-white" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-xs text-zinc-300">SKU Code *</Label>
                  <Input required placeholder="SKU-PROD-01" value={newProduct.sku} onChange={(e) => setNewProduct({ ...newProduct, sku: e.target.value })} className="bg-zinc-950 border-zinc-800 text-sm text-white font-mono uppercase" />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs text-zinc-300">Sales Price *</Label>
                  <Input required placeholder="199.00" value={newProduct.salesPrice} onChange={(e) => setNewProduct({ ...newProduct, salesPrice: e.target.value })} className="bg-zinc-950 border-zinc-800 text-sm text-white font-mono" />
                </div>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-zinc-300">Classification *</Label>
                <select value={newProduct.type} onChange={(e) => setNewProduct({ ...newProduct, type: e.target.value as ProductType })} className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-sm text-white focus:outline-none">
                  <option value="SERVICE">Service</option>
                  <option value="GOODS">Goods / Physical</option>
                </select>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <Button type="button" variant="outline" onClick={() => setIsProductModalOpen(false)} className="border-zinc-800 text-xs">Cancel</Button>
                <Button type="submit" disabled={modalSubmitting} className="bg-blue-600 hover:bg-blue-500 text-xs text-white">Save Product</Button>
              </div>
            </form>
          </Card>
        </div>
      )}

      {/* Modal: Tax */}
      {isTaxModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <Card className="w-full max-w-md bg-zinc-900 border-zinc-800 p-6 space-y-5">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
              <h3 className="text-base font-bold text-white">Add Tax Rule</h3>
              <button onClick={() => setIsTaxModalOpen(false)} className="text-zinc-400 hover:text-white"><X className="w-4 h-4" /></button>
            </div>
            {modalError && <div className="p-2.5 rounded bg-rose-500/10 border border-rose-500/20 text-xs text-rose-400">{modalError}</div>}
            <form onSubmit={handleAddTax} className="space-y-4">
              <div className="space-y-1.5">
                <Label className="text-xs text-zinc-300">Tax Name *</Label>
                <Input required value={newTax.name} onChange={(e) => setNewTax({ ...newTax, name: e.target.value })} className="bg-zinc-950 border-zinc-800 text-sm text-white" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-xs text-zinc-300">Code *</Label>
                  <Input required placeholder="GST-18" value={newTax.code} onChange={(e) => setNewTax({ ...newTax, code: e.target.value })} className="bg-zinc-950 border-zinc-800 text-sm text-white font-mono uppercase" />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs text-zinc-300">Rate (%) *</Label>
                  <Input required placeholder="18.00" value={newTax.ratePercentage} onChange={(e) => setNewTax({ ...newTax, ratePercentage: e.target.value })} className="bg-zinc-950 border-zinc-800 text-sm text-white font-mono" />
                </div>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-zinc-300">Tax Classification *</Label>
                <select value={newTax.taxType} onChange={(e) => setNewTax({ ...newTax, taxType: e.target.value as TaxType })} className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-sm text-white focus:outline-none">
                  <option value="IGST">IGST (Inter-state)</option>
                  <option value="CGST">CGST (Central)</option>
                  <option value="SGST">SGST (State)</option>
                  <option value="GENERIC">Generic</option>
                </select>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <Button type="button" variant="outline" onClick={() => setIsTaxModalOpen(false)} className="border-zinc-800 text-xs">Cancel</Button>
                <Button type="submit" disabled={modalSubmitting} className="bg-blue-600 hover:bg-blue-500 text-xs text-white">Save Rule</Button>
              </div>
            </form>
          </Card>
        </div>
      )}

      {/* Modal: Discount */}
      {isDiscountModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <Card className="w-full max-w-md bg-zinc-900 border-zinc-800 p-6 space-y-5">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
              <h3 className="text-base font-bold text-white">Add Discount Rule</h3>
              <button onClick={() => setIsDiscountModalOpen(false)} className="text-zinc-400 hover:text-white"><X className="w-4 h-4" /></button>
            </div>
            {modalError && <div className="p-2.5 rounded bg-rose-500/10 border border-rose-500/20 text-xs text-rose-400">{modalError}</div>}
            <form onSubmit={handleAddDiscount} className="space-y-4">
              <div className="space-y-1.5">
                <Label className="text-xs text-zinc-300">Discount Name *</Label>
                <Input required value={newDiscount.name} onChange={(e) => setNewDiscount({ ...newDiscount, name: e.target.value })} className="bg-zinc-950 border-zinc-800 text-sm text-white" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-xs text-zinc-300">Promo Code *</Label>
                  <Input required placeholder="SAVE20" value={newDiscount.code} onChange={(e) => setNewDiscount({ ...newDiscount, code: e.target.value })} className="bg-zinc-950 border-zinc-800 text-sm text-white font-mono uppercase" />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs text-zinc-300">Value *</Label>
                  <Input required placeholder="20.00" value={newDiscount.value} onChange={(e) => setNewDiscount({ ...newDiscount, value: e.target.value })} className="bg-zinc-950 border-zinc-800 text-sm text-white font-mono" />
                </div>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-zinc-300">Type *</Label>
                <select value={newDiscount.discountType} onChange={(e) => setNewDiscount({ ...newDiscount, discountType: e.target.value as DiscountType })} className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-sm text-white focus:outline-none">
                  <option value="PERCENTAGE">Percentage (%)</option>
                  <option value="FIXED">Fixed Amount (₹)</option>
                </select>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <Button type="button" variant="outline" onClick={() => setIsDiscountModalOpen(false)} className="border-zinc-800 text-xs">Cancel</Button>
                <Button type="submit" disabled={modalSubmitting} className="bg-blue-600 hover:bg-blue-500 text-xs text-white">Save Discount</Button>
              </div>
            </form>
          </Card>
        </div>
      )}

      {/* Modal: Quotation Builder */}
      {isQuoteModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <Card className="w-full max-w-md bg-zinc-900 border-zinc-800 p-6 space-y-5">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
              <div>
                <h3 className="text-base font-bold text-white">Create Commercial Quote</h3>
                <p className="text-xs text-zinc-400">Backend calculates authoritative GST and discounts</p>
              </div>
              <button onClick={() => setIsQuoteModalOpen(false)} className="text-zinc-400 hover:text-white"><X className="w-4 h-4" /></button>
            </div>
            {modalError && <div className="p-2.5 rounded bg-rose-500/10 border border-rose-500/20 text-xs text-rose-400">{modalError}</div>}
            <form onSubmit={handleAddQuotation} className="space-y-4">
              <div className="space-y-1.5">
                <Label className="text-xs text-zinc-300">Select Customer *</Label>
                <select value={newQuote.customerId} onChange={(e) => setNewQuote({ ...newQuote, customerId: e.target.value })} className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-sm text-white focus:outline-none">
                  {customers.map((c) => <option key={c.id} value={c.id}>{getCustomerLabel(c)}</option>)}
                </select>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-zinc-300">Select Plan Tier *</Label>
                <select value={newQuote.planId} onChange={(e) => setNewQuote({ ...newQuote, planId: e.target.value })} className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-sm text-white focus:outline-none">
                  {plans.map((p) => <option key={p.id} value={p.id}>{p.name} — ₹{p.price} ({p.billingInterval})</option>)}
                </select>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-zinc-300">Product Line *</Label>
                <select value={newQuote.productId} onChange={(e) => setNewQuote({ ...newQuote, productId: e.target.value })} className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-sm text-white focus:outline-none">
                  {products.map((pr) => <option key={pr.id} value={pr.id}>{pr.name} ({pr.sku})</option>)}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-xs text-zinc-300">Quantity *</Label>
                  <Input type="number" min="1" value={newQuote.quantity} onChange={(e) => setNewQuote({ ...newQuote, quantity: parseInt(e.target.value, 10) || 1 })} className="bg-zinc-950 border-zinc-800 text-sm text-white font-mono" />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs text-zinc-300">Discount Code (Optional)</Label>
                  <Input placeholder="e.g. EARLY10" value={newQuote.discountCode} onChange={(e) => setNewQuote({ ...newQuote, discountCode: e.target.value })} className="bg-zinc-950 border-zinc-800 text-sm text-white font-mono uppercase" />
                </div>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <Button type="button" variant="outline" onClick={() => setIsQuoteModalOpen(false)} className="border-zinc-800 text-xs">Cancel</Button>
                <Button type="submit" disabled={modalSubmitting || customers.length === 0 || plans.length === 0} className="bg-blue-600 hover:bg-blue-500 text-xs text-white">Generate Quote</Button>
              </div>
            </form>
          </Card>
        </div>
      )}

      {/* Modal: Subscription */}
      {isSubModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <Card className="w-full max-w-md bg-zinc-900 border-zinc-800 p-6 space-y-5">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
              <h3 className="text-base font-bold text-white">Create Subscription</h3>
              <button onClick={() => setIsSubModalOpen(false)} className="text-zinc-400 hover:text-white"><X className="w-4 h-4" /></button>
            </div>
            {modalError && <div className="p-2.5 rounded bg-rose-500/10 border border-rose-500/20 text-xs text-rose-400">{modalError}</div>}
            <form onSubmit={handleAddSubscription} className="space-y-4">
              <div className="space-y-1.5">
                <Label className="text-xs text-zinc-300">Customer *</Label>
                <select value={newSub.customerId} onChange={(e) => setNewSub({ ...newSub, customerId: e.target.value })} className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-sm text-white focus:outline-none">
                  {customers.map((c) => <option key={c.id} value={c.id}>{getCustomerLabel(c)}</option>)}
                </select>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-zinc-300">Plan Tier *</Label>
                <select value={newSub.planId} onChange={(e) => setNewSub({ ...newSub, planId: e.target.value })} className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-sm text-white focus:outline-none">
                  {plans.map((p) => <option key={p.id} value={p.id}>{p.name} — ₹{p.price} ({p.billingInterval})</option>)}
                </select>
              </div>
              {products.length > 0 && (
                <div className="space-y-1.5">
                  <Label className="text-xs text-zinc-300">Catalog Product *</Label>
                  <select value={newSub.productId || products[0].id} onChange={(e) => setNewSub({ ...newSub, productId: e.target.value })} className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-sm text-white focus:outline-none">
                    {products.map((pr) => <option key={pr.id} value={pr.id}>{pr.name} ({pr.sku})</option>)}
                  </select>
                </div>
              )}
              <div className="flex justify-end gap-2 pt-2">
                <Button type="button" variant="outline" onClick={() => setIsSubModalOpen(false)} className="border-zinc-800 text-xs">Cancel</Button>
                <Button type="submit" disabled={modalSubmitting || customers.length === 0 || plans.length === 0} className="bg-blue-600 hover:bg-blue-500 text-xs text-white">Confirm & Provision</Button>
              </div>
            </form>
          </Card>
        </div>
      )}

      {/* Modal: Record Payment */}
      {isPaymentModalOpen && selectedInvoiceForPayment && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <Card className="w-full max-w-md bg-zinc-900 border-zinc-800 p-6 space-y-5">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
              <div>
                <h3 className="text-base font-bold text-white">Record Invoice Payment</h3>
                <p className="text-xs text-zinc-400 font-mono">Invoice: {selectedInvoiceForPayment.invoiceNumber || selectedInvoiceForPayment.id}</p>
              </div>
              <button onClick={() => setIsPaymentModalOpen(false)} className="text-zinc-400 hover:text-white"><X className="w-4 h-4" /></button>
            </div>
            {modalError && <div className="p-2.5 rounded bg-rose-500/10 border border-rose-500/20 text-xs text-rose-400">{modalError}</div>}
            <form onSubmit={handleRecordPayment} className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-xs text-zinc-300">Amount *</Label>
                  <Input required value={newPayment.amount} onChange={(e) => setNewPayment({ ...newPayment, amount: e.target.value })} className="bg-zinc-950 border-zinc-800 text-sm text-white font-mono" />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs text-zinc-300">Currency</Label>
                  <Input disabled value={newPayment.currency} className="bg-zinc-950 border-zinc-800 text-sm text-zinc-400 font-mono uppercase" />
                </div>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-zinc-300">Payment Method *</Label>
                <select value={newPayment.method} onChange={(e) => setNewPayment({ ...newPayment, method: e.target.value as PaymentMethod })} className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-sm text-white focus:outline-none">
                  <option value="UPI">UPI</option>
                  <option value="BANK_TRANSFER">Bank Transfer</option>
                  <option value="CARD">Card</option>
                  <option value="CASH">Cash</option>
                  <option value="CHEQUE">Cheque</option>
                  <option value="OTHER">Other</option>
                </select>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-zinc-300">Transaction Reference / UTR</Label>
                <Input placeholder="e.g. UTR-982348123" value={newPayment.reference} onChange={(e) => setNewPayment({ ...newPayment, reference: e.target.value })} className="bg-zinc-950 border-zinc-800 text-sm text-white font-mono" />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <Button type="button" variant="outline" onClick={() => setIsPaymentModalOpen(false)} className="border-zinc-800 text-xs">Cancel</Button>
                <Button type="submit" disabled={modalSubmitting} className="bg-emerald-600 hover:bg-emerald-500 text-xs text-white">Record & Allocate</Button>
              </div>
            </form>
          </Card>
        </div>
      )}
    </div>
  );
}
