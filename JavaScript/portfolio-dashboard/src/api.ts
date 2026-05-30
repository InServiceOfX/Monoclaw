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
  date_iso?: string | null;
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
  closed_date_iso?: string | null;
  Quantity: string;
  "Closing Price": string;
  Proceeds: string;
  "Cost Basis (CB)": string;
  "Total Gain/Loss ($)": string;
  "Long Term (LT) Gain/Loss ($)": string;
  "Short Term (ST) Gain/Loss ($)": string;
  [key: string]: string | null | undefined;
}

export interface HistorySnapshot {
  date: string;
  total_market_value: number;
  total_cost_basis: number;
  unrealized_gl: number;
  position_count: number;
}

export interface BalanceRow {
  SnapshotDate: string;
  SnapshotTime: string;
  "Account Value": string;
  "Day Change": string;
  "Day Change %": string;
  "Cash & Cash Investments": string;
  "Market Value (Securities)": string;
  "Available to Trade (Cash)": string;
  "Settled Funds": string;
  "Available to Withdraw": string;
  snapshot_date_iso: string | null;
  account_value: number | null;
  day_change: number | null;
  day_change_pct: number | null;
  cash: number | null;
  securities_value: number | null;
  available_to_trade: number | null;
  settled_funds: number | null;
  available_to_withdraw: number | null;
}

export interface PortfolioContext {
  snapshot_date: string;
  total_securities_value: number;
  cash_value: number;
  cash_pct: number | null;
  top_holdings: {
    symbol: string;
    description: string;
    market_value: number;
    weight_pct: number | null;
    unrealized_gl: number | null;
    unrealized_gl_pct: number | null;
    rating: string;
    asset_type: string;
  }[];
  realized_ytd: {
    total: number;
    short_term: number;
    long_term: number;
    wash_sale_rows: number;
  };
  flags: { severity: "info" | "medium" | "high"; label: string; detail: string }[];
  note: string;
}

export interface EarningsEvent {
  symbol: string;
  description: string;
  asset_type: string;
  market_value: number;
  weight_pct: number | null;
  next_earnings_date: string | null;
  previous_earnings_date: string | null;
  eps_estimate: number | null;
  reported_eps: number | null;
  surprise_pct: number | null;
  status: "upcoming" | "historical" | "not_applicable" | "unavailable" | "error";
  error?: string;
}

export interface MonteCarloMetric {
  initial_value: number | null;
  expected_final: number | null;
  p05: number | null;
  p25: number | null;
  p50: number | null;
  p75: number | null;
  p95: number | null;
  expected_return_pct: number | null;
  probability_gain_pct: number | null;
  probability_loss_pct: number | null;
  var_5: number | null;
  cvar_5: number | null;
  sample_count: number;
}

export interface SymbolEnhancement {
  historical_vol: number | null;
  garch_vol: number | null;
  implied_vol_annual: number | null;
  blended_vol: number | null;
  used_implied_vol: boolean;
}

export interface Enhancements {
  student_t_df: number | null;
  iv_weight: number;
  garch_model: string;
  per_symbol: Record<string, SymbolEnhancement>;
}

export interface PositionDetail extends MonteCarloMetric {
  symbol: string;
  description: string;
  market_value: number | null;
  last_price: number | null;
  annual_return_pct: number | null;
  annual_vol_pct: number | null;
  sharpe_like: number | null;
  risk_reward_score: number | null;
}

export interface MonteCarloResponse {
  snapshot_date: string;
  portfolio_position_count: number;
  watchlist: string[];
  error?: string;
  history_rows?: number;
  history_start?: string;
  history_end?: string;
  missing_symbols?: string[];
  enhancements?: Enhancements;
  position_details?: PositionDetail[];
  portfolio: (MonteCarloMetric & {
    days: number;
    period: string;
    symbols_used: string[];
    symbols_missing: string[];
    bands: { day: number; p05: number | null; p50: number | null; p95: number | null }[];
    note: string;
  }) | null;
  candidates: (MonteCarloMetric & {
    symbol: string;
    status: "ok" | "missing_history";
    last_price: number | null;
    annual_return_pct: number | null;
    annual_vol_pct: number | null;
    sharpe_like: number | null;
    risk_reward_score: number | null;
  })[];
}

export interface EarningsHorizonStats {
  mean: number;
  median: number;
  std: number;
  win_rate_pct: number;
  best: number;
  worst: number;
  count: number;
}

export interface EarningsHistoricalEvent {
  date: string;
  eps_estimate: number | null;
  reported_eps: number | null;
  surprise_pct: number | null;
  "1d_pct": number | null;
  "5d_pct": number | null;
  "15d_pct": number | null;
  "30d_pct": number | null;
}

export interface EarningsClassification {
  signal: "strong_buy" | "buy" | "neutral" | "volatile" | "avoid" | "insufficient_data";
  reason: string;
}

export interface EarningsPosition {
  symbol: string;
  description: string;
  status: string;
  next_earnings_date?: string | null;
  days_until_earnings?: number | null;
  next_eps_estimate?: number | null;
  events?: EarningsHistoricalEvent[];
  stats?: {
    sufficient_data: boolean;
    event_count: number;
    beat_rate_pct?: number | null;
    avg_surprise_pct?: number | null;
    "1d"?: EarningsHorizonStats | null;
    "5d"?: EarningsHorizonStats | null;
    "15d"?: EarningsHorizonStats | null;
    "30d"?: EarningsHorizonStats | null;
  };
  classification?: EarningsClassification;
  error?: string;
}

export interface EarningsUpcomingAlert {
  symbol: string;
  description: string;
  date: string;
  days_until: number;
  eps_estimate: number | null;
}

export interface EarningsImpactResponse {
  snapshot_date: string;
  error?: string;
  positions: EarningsPosition[];
  upcoming_alerts: EarningsUpcomingAlert[];
  horizons?: number[];
  note?: string;
}

export interface ForwardReturns {
  "1d"?: number | null;
  "7d"?: number | null;
  "30d"?: number | null;
  "90d"?: number | null;
}

export interface SpyAlpha {
  "1d"?: number | null;
  "7d"?: number | null;
  "30d"?: number | null;
  "90d"?: number | null;
}

export interface RecommendationRec {
  id: string;
  symbol: string;
  action: string;
  conviction: string | null;
  timestamp: string;
  risk_reward_score: number | null;
  expected_return: number | null;
  prob_gain: number | null;
  attribution: "followed" | "partially_followed" | "ignored" | "contrary" | "unknown";
  matched_trade: {
    date: string;
    action: string;
    quantity: string;
    price: string;
    amount: string;
  } | null;
  forward_returns: ForwardReturns | null;
  spy_alpha: SpyAlpha | null;
}

export interface RecommendationsReport {
  recommendations: RecommendationRec[];
  summary: {
    total: number;
    days_lookback: number;
    by_attribution: Record<string, number>;
    by_conviction: Record<string, number>;
    follow_rate_pct: number;
    match_report_date: string | null;
    perf_report_date: string | null;
  };
  generated_at: string;
}

export interface DOITicker {
  symbol: string;
  current_price: number | null;
  high_52w: number | null;
  drawdown_score: number | null;
  index_regime_score: number | null;
  cash_availability_score: number | null;
  conviction_score: number | null;
  momentum_exhaustion: number | null;
  breadth_deterioration: number | null;
  doi: number | null;
  action: "deploy" | "hold" | "trim" | "data_missing";
  size_hint_dollars: number | null;
}

export interface DOIIndexInfo {
  local_top_prob: number | null;
  regime_score: number | null;
}

export interface DOISnapshot {
  as_of: string;
  weights: {
    w1: number;
    w2: number;
    w3: number;
    w4: number;
    w5: number;
    w6: number;
  };
  portfolio_doi: number;
  cash_deficit_warning: boolean;
  cash_pct: number | null;
  tickers: DOITicker[];
  indices: {
    SPX: DOIIndexInfo;
    QQQ: DOIIndexInfo;
    DJI: DOIIndexInfo;
  };
}

export interface GradingSummary {
  trader_score: number | null;
  avg_quality_score: number | null;
  total_sells_scored: number;
  total_sells?: number;
  candidates_scanned?: number;
  provisional_skipped?: number;
  sells_near_local_peak: number;
  pct_near_peak: number;
  error?: string;
}

export interface GradedSell {
  date: string;
  symbol: string;
  action?: string;
  quality_score: number;
  mfe_pct: number | null;
  max_drawdown_pct: number | null;
  near_local_peak: boolean;
  provisional?: boolean;
  sold_too_early?: boolean;
}

export interface GradingTransactionsResponse {
  graded_sells: GradedSell[];
  count: number;
  total_sells?: number;
  candidates_scanned?: number;
  provisional_skipped?: number;
  generated_at: string;
  error?: string;
}

export interface GradingTopBottomResponse {
  best_sells: GradedSell[];
  worst_sells: GradedSell[];
  total_sells?: number;
  candidates_scanned?: number;
  generated_at: string;
  error?: string;
}

export interface GradingSymbolSummary {
  symbol: string;
  sells: number;
  avg_quality_score: number;
  pct_near_peak: number;
  avg_mfe_after_sell: number;
  edge: "Strong" | "Weak" | "Neutral";
}

export interface GradingBySymbolResponse {
  by_symbol: GradingSymbolSummary[];
  symbols_analyzed: number;
  total_sells?: number;
  candidates_scanned?: number;
  generated_at: string;
  error?: string;
}

export interface GradingPattern {
  symbol: string;
  type: "sells_too_early" | "good_timing" | "decent_timing";
  severity: "high" | "medium" | "low" | "none";
  still_held: boolean;
  sells: number;
  avg_quality: number;
  avg_mfe: number;
  message: string;
  correction: string;
}

export interface GradingPatternsSummary {
  total_patterns: number;
  early_sell_count: number;
  early_sell_still_held: string[];
  good_timing_count: number;
  overall_avg_quality: number | null;
  overall_avg_mfe: number | null;
  top_correction: string;
}

export interface GradingPatternsResponse {
  patterns: GradingPattern[];
  summary: GradingPatternsSummary;
  generated_at: string;
  error?: string;
}

export const api = {
  summary: () => get<PortfolioSummary>("/portfolio/summary"),
  positions: () => get<PositionsResponse>("/positions/current"),
  history: () => get<{ snapshots: HistorySnapshot[] }>("/portfolio/history"),
  balances: () => get<{ count: number; rows: BalanceRow[]; latest: BalanceRow | null }>("/balances"),
  context: () => get<PortfolioContext>("/portfolio/context"),
  earnings: (limit = 20) => get<{ snapshot_date: string; events: EarningsEvent[]; note: string; error?: string }>(`/portfolio/earnings?limit=${limit}`),
  earningsImpact: (maxPositions = 25) => get<EarningsImpactResponse>(`/portfolio/earnings-impact?max_positions=${maxPositions}`),
  monteCarlo: (params: { symbols?: string; days?: number; simulations?: number; period?: string; max_positions?: number }) => {
    const q = new URLSearchParams(
      Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== "")
        .map(([k, v]) => [k, String(v)]),
    ).toString();
    return get<MonteCarloResponse>(`/portfolio/monte-carlo${q ? "?" + q : ""}`);
  },
  transactionActions: () => get<{ actions: string[] }>("/transactions/actions"),
  transactions: (params?: { from_date?: string; to_date?: string; symbol?: string; action?: string }) => {
    const q = new URLSearchParams(params as Record<string, string>).toString();
    return get<{ count: number; transactions: Transaction[] }>(`/transactions${q ? "?" + q : ""}`);
  },
  rglSummary: (params?: { from_date?: string; to_date?: string }) => {
    const q = new URLSearchParams(params as Record<string, string>).toString();
    return get<{ count: number; rows: RGLSummaryRow[] }>(`/rgl/summary${q ? "?" + q : ""}`);
  },
  timeseries: (period = "1y") =>
    get<{
      series: { date: string; value: number }[];
      benchmark_spy: { date: string; value: number }[];
      note: string;
      period: string;
      error?: string;
    }>(`/portfolio/timeseries?period=${period}`),
  doi: () => get<DOISnapshot>("/doi/snapshot"),
  gradingSummary: () => get<GradingSummary>("/grading/summary"),
  gradingTransactions: (limit = 30, includeProvisional = false) =>
    get<GradingTransactionsResponse>(`/transactions/grading?limit=${limit}&include_provisional=${includeProvisional}`),
  gradingTopBottom: (limit = 5) => get<GradingTopBottomResponse>(`/grading/top-bottom?limit=${limit}`),
  gradingBySymbol: () => get<GradingBySymbolResponse>("/grading/by-symbol"),
  gradingPatterns: () => get<GradingPatternsResponse>("/grading/patterns"),
  recommendations: (days = 90) =>
    get<RecommendationsReport>(`/recommendations/report?days=${days}`),
};
