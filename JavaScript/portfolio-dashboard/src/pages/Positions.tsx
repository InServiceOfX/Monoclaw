import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import type { Position } from "../api";
import { usd, pct, glColor } from "../fmt";

type SortKey = keyof Position;

export default function Positions() {
  const { data, isLoading } = useQuery({ queryKey: ["positions"], queryFn: api.positions, refetchInterval: 60000 });
  const [sortKey, setSortKey] = useState<SortKey>("market_value");
  const [sortAsc, setSortAsc] = useState(false);
  const [filter, setFilter] = useState("");

  if (isLoading) return <p style={{ padding: "1.5rem" }}>Loading…</p>;

  const positions = (data?.positions ?? [])
    .filter(p => !filter || p.symbol.includes(filter.toUpperCase()) || p.description.toLowerCase().includes(filter.toLowerCase()))
    .sort((a, b) => {
      const av = a[sortKey] ?? -Infinity;
      const bv = b[sortKey] ?? -Infinity;
      const cmp = av < bv ? -1 : av > bv ? 1 : 0;
      return sortAsc ? cmp : -cmp;
    });

  const cols: { key: SortKey; label: string; fmt: (p: Position) => string; color?: (p: Position) => string }[] = [
    { key: "symbol", label: "Symbol", fmt: p => p.symbol },
    { key: "description", label: "Name", fmt: p => p.description.slice(0, 28) },
    { key: "qty", label: "Qty", fmt: p => String(p.qty ?? "—") },
    { key: "current_price", label: "Price", fmt: p => usd(p.current_price) },
    { key: "market_value", label: "Mkt Value", fmt: p => usd(p.market_value) },
    { key: "cost_basis_total", label: "Cost Basis", fmt: p => usd(p.cost_basis_total) },
    { key: "unrealized_gl_dollars", label: "Unreal G/L $", fmt: p => usd(p.unrealized_gl_dollars), color: p => glColor(p.unrealized_gl_dollars) },
    { key: "unrealized_gl_pct", label: "Unreal G/L %", fmt: p => pct(p.unrealized_gl_pct), color: p => glColor(p.unrealized_gl_pct) },
    { key: "day_change_pct", label: "Day %", fmt: p => pct(p.day_change_pct), color: p => glColor(p.day_change_pct) },
    { key: "pct_of_account", label: "% Acct", fmt: p => pct(p.pct_of_account) },
  ];

  const th: React.CSSProperties = { padding: "0.5rem 0.75rem", textAlign: "left", fontSize: "0.75rem", color: "#6b7280", cursor: "pointer", whiteSpace: "nowrap", borderBottom: "2px solid #e5e7eb" };
  const td: React.CSSProperties = { padding: "0.4rem 0.75rem", fontSize: "0.8rem", borderBottom: "1px solid #f3f4f6", whiteSpace: "nowrap" };

  return (
    <div style={{ padding: "1.5rem" }}>
      <div style={{ display: "flex", gap: "1rem", marginBottom: "1rem", alignItems: "center" }}>
        <h2 style={{ margin: 0 }}>Positions ({positions.length})</h2>
        <input value={filter} onChange={e => setFilter(e.target.value)} placeholder="Filter symbol / name…" style={{ padding: "0.35rem 0.75rem", borderRadius: "0.375rem", border: "1px solid #d1d5db", fontSize: "0.875rem" }} />
        <span style={{ fontSize: "0.75rem", color: "#6b7280" }}>as of {data?.snapshot_date}</span>
      </div>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
          <thead>
            <tr>
              {cols.map(c => (
                <th key={c.key} style={{ ...th, background: sortKey === c.key ? "#f3f4f6" : undefined }} onClick={() => { sortKey === c.key ? setSortAsc(!sortAsc) : (setSortKey(c.key), setSortAsc(false)); }}>
                  {c.label} {sortKey === c.key ? (sortAsc ? "▲" : "▼") : ""}
                </th>
              ))}
              <th style={th}>⚠</th>
            </tr>
          </thead>
          <tbody>
            {positions.map(p => (
              <tr key={p.symbol} style={{ background: "white" }}>
                {cols.map(c => (
                  <td key={c.key} style={{ ...td, color: c.color ? c.color(p) : undefined, fontWeight: c.key === "symbol" ? 600 : undefined }}>
                    {c.fmt(p)}
                  </td>
                ))}
                <td style={td}>{p.price_stale ? "⚠" : ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
