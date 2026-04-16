export const usd = (v: number | null | undefined, decimals = 2) =>
  v == null ? "—" : v.toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: decimals, maximumFractionDigits: decimals });

export const pct = (v: number | null | undefined, decimals = 2) =>
  v == null ? "—" : `${v >= 0 ? "+" : ""}${v.toFixed(decimals)}%`;

export const num = (v: number | null | undefined, decimals = 2) =>
  v == null ? "—" : v.toFixed(decimals);

export const glColor = (v: number | null | undefined) =>
  v == null ? "" : v >= 0 ? "#16a34a" : "#dc2626";
