const BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8765";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`);
  return res.json() as Promise<T>;
}

export interface Position {
  symbol: string;
  description: string;
  qty: number | null;
  cost_basis_per_share: number | null;
  cost_basis_total: number | null;
  current_price: number | null;
  market_value: number | null;
  unrealized_gl_dollars: number | null;
  unrealized_gl_pct: number | null;
  day_change_dollars: number | null;
  day_change_pct: number | null;
  pct_of_account: number | null;
  asset_type: string;
  price_stale: boolean;
}

export interface PositionsResponse {
  snapshot_date: string;
  positions: Position[];
}

export interface PortfolioSummary {
  total_market_value: number;
  total_cost_basis: number;
  total_unrealized_gl_dollars: number;
  total_unrealized_gl_pct: number | null;
  total_day_change: number;
  position_count: number;
  as_of: string;
}

export interface Transaction {
  Date: string;
  Action: string;
  Symbol: string;
  Description: string;
  Quantity: string;
  Price: string;
  "Fees & Comm": string;
  Amount: string;
}

export interface RGLSummaryRow {
  Symbol: string;
  Name: string;
  "Closed Date": string;
  Quantity: string;
  "Closing Price": string;
  Proceeds: string;
  "Cost Basis (CB)": string;
  "Total Gain/Loss ($)": string;
  "Long Term (LT) Gain/Loss ($)": string;
  "Short Term (ST) Gain/Loss ($)": string;
  [key: string]: string;
}

export interface HistorySnapshot {
  date: string;
  total_market_value: number;
  total_cost_basis: number;
  unrealized_gl: number;
  position_count: number;
}

export const api = {
  summary: () => get<PortfolioSummary>("/portfolio/summary"),
  positions: () => get<PositionsResponse>("/positions/current"),
  history: () => get<{ snapshots: HistorySnapshot[] }>("/portfolio/history"),
  transactions: (params?: { from_date?: string; to_date?: string; symbol?: string; action?: string }) => {
    const q = new URLSearchParams(params as Record<string, string>).toString();
    return get<{ count: number; transactions: Transaction[] }>(`/transactions${q ? "?" + q : ""}`);
  },
  rglSummary: (params?: { from_date?: string; to_date?: string }) => {
    const q = new URLSearchParams(params as Record<string, string>).toString();
    return get<{ count: number; rows: RGLSummaryRow[] }>(`/rgl/summary${q ? "?" + q : ""}`);
  },
};
