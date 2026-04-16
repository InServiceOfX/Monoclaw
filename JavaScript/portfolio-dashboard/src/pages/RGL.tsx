import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import type { RGLSummaryRow } from "../api";
import { usd, glColor } from "../fmt";

function parseNum(s: string): number {
  return parseFloat(s.replace(/[$,%]/g, "").replace(",", "")) || 0;
}

export default function RGL() {
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");

  const params = { ...(fromDate && { from_date: fromDate }), ...(toDate && { to_date: toDate }) };
  const { data, isLoading } = useQuery({ queryKey: ["rgl", params], queryFn: () => api.rglSummary(params) });

  const rows: RGLSummaryRow[] = data?.rows ?? [];

  // Aggregate per symbol
  const bySymbol: Record<string, { symbol: string; name: string; total: number; lt: number; st: number }> = {};
  for (const r of rows) {
    const sym = r.Symbol;
    if (!bySymbol[sym]) bySymbol[sym] = { symbol: sym, name: r.Name || r["Name"] || "", total: 0, lt: 0, st: 0 };
    bySymbol[sym].total += parseNum(r["Total Gain/Loss ($)"]);
    bySymbol[sym].lt += parseNum(r["Long Term (LT) Gain/Loss ($)"]);
    bySymbol[sym].st += parseNum(r["Short Term (ST) Gain/Loss ($)"]);
  }
  const agg = Object.values(bySymbol).sort((a, b) => b.total - a.total);

  const totalGL = agg.reduce((s, r) => s + r.total, 0);
  const totalLT = agg.reduce((s, r) => s + r.lt, 0);
  const totalST = agg.reduce((s, r) => s + r.st, 0);

  const inp: React.CSSProperties = { padding: "0.35rem 0.6rem", borderRadius: "0.375rem", border: "1px solid #d1d5db", fontSize: "0.8rem" };
  const th: React.CSSProperties = { padding: "0.5rem 0.75rem", textAlign: "left", fontSize: "0.75rem", color: "#6b7280", borderBottom: "2px solid #e5e7eb" };
  const td: React.CSSProperties = { padding: "0.4rem 0.75rem", fontSize: "0.8rem", borderBottom: "1px solid #f3f4f6" };

  return (
    <div style={{ padding: "1.5rem" }}>
      <h2 style={{ marginBottom: "1rem" }}>Realized Gains & Losses</h2>

      <div style={{ display: "flex", gap: "0.75rem", marginBottom: "1.5rem", flexWrap: "wrap" }}>
        <label style={{ display: "flex", gap: "0.4rem", alignItems: "center", fontSize: "0.8rem" }}>
          From <input type="date" style={inp} value={fromDate} onChange={e => setFromDate(e.target.value)} />
        </label>
        <label style={{ display: "flex", gap: "0.4rem", alignItems: "center", fontSize: "0.8rem" }}>
          To <input type="date" style={inp} value={toDate} onChange={e => setToDate(e.target.value)} />
        </label>
        <span style={{ fontSize: "0.75rem", color: "#6b7280", alignSelf: "center" }}>{isLoading ? "…" : `${agg.length} symbols`}</span>
      </div>

      {/* Summary cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem", marginBottom: "2rem" }}>
        <SCard title="Total G/L" value={usd(totalGL)} color={glColor(totalGL)} note="Note: RGL data starts 2024-01-01 (Schwab UI limitation)" />
        <SCard title="Long-Term G/L" value={usd(totalLT)} color={glColor(totalLT)} />
        <SCard title="Short-Term G/L" value={usd(totalST)} color={glColor(totalST)} />
      </div>

      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            {["Symbol","Name","Total G/L","Long-Term G/L","Short-Term G/L"].map(h => <th key={h} style={th}>{h}</th>)}
          </tr>
        </thead>
        <tbody>
          {agg.map(r => (
            <tr key={r.symbol}>
              <td style={{ ...td, fontWeight: 600 }}>{r.symbol}</td>
              <td style={{ ...td, maxWidth: "200px", overflow: "hidden", textOverflow: "ellipsis" }}>{r.name}</td>
              <td style={{ ...td, color: glColor(r.total) }}>{usd(r.total)}</td>
              <td style={{ ...td, color: glColor(r.lt) }}>{usd(r.lt)}</td>
              <td style={{ ...td, color: glColor(r.st) }}>{usd(r.st)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SCard({ title, value, color, note }: { title: string; value: string; color?: string; note?: string }) {
  return (
    <div style={{ background: "#f9fafb", borderRadius: "0.5rem", padding: "1rem", border: "1px solid #e5e7eb" }}>
      <div style={{ fontSize: "0.75rem", color: "#6b7280", marginBottom: "0.25rem" }}>{title}</div>
      <div style={{ fontSize: "1.4rem", fontWeight: 700, color: color ?? "#111827" }}>{value}</div>
      {note && <div style={{ fontSize: "0.65rem", color: "#9ca3af", marginTop: "0.25rem" }}>{note}</div>}
    </div>
  );
}
