/**
 * Global Configuration for Backend Integration
 * Set USE_MOCK to false to communicate with the live FastAPI backend on port 8000.
 * In live mode, only unimplemented modules (Invoices, Payments) use isolated mock data.
 */
export const USE_MOCK = false;

export const APP_CONFIG = {
  API_BASE_URL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1",
  DEFAULT_CURRENCY: "INR",
  DEFAULT_PAGE_SIZE: 20,
};
