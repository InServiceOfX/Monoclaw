import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";

export default function Transactions() {
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [symbol, setSymbol] = useState("");
  const [action, setAction] = useState("");

  const params = {
    ...(fromDate && { from_date: fromDate }),
    ...(toDate && { to_date: toDate }),
    ...(symbol && { symbol }),
    ...(action && { action }),
  };
  const { data, isLoading } = useQuery({
    queryKey: ["transactions", params],
    queryFn: () => api.transactions(params),
  });

  const inp: React.CSSProperties = { padding: "0.35rem 0.6rem", borderRadius: "0.375rem", border: "1px solid #d1d5db", fontSize: "0.8rem" };
  const th: React.CSSProperties = { padding: "0.5rem 0.75rem", textAlign: "left", fontSize: "0.75rem", color: "#6b7280", borderBottom: "2px solid #e5e7eb", whiteSpace: "nowrap" };
  const td: React.CSSProperties = { padding: "0.4rem 0.75rem", fontSize: "0.8rem", borderBottom: "1px solid #f3f4f6", whiteSpace: "nowrap" };

  const rows = data?.transactions ?? [];

  return (
    <div style={{ padding: "1.5rem" }}>
      <h2 style={{ marginBottom: "1rem" }}>Transactions</h2>
      <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", marginBottom: "1rem" }}>
        <label style={{ display: "flex", gap: "0.4rem", alignItems: "center", fontSize: "0.8rem" }}>
          From <input type="date" style={inp} value={fromDate} onChange={e => setFromDate(e.target.value)} />
        </label>
        <label style={{ display: "flex", gap: "0.4rem", alignItems: "center", fontSize: "0.8rem" }}>
          To <input type="date" style={inp} value={toDate} onChange={e => setToDate(e.target.value)} />
        </label>
        <input style={inp} placeholder="Symbol" value={symbol} onChange={e => setSymbol(e.target.value.toUpperCase())} />
        <input style={inp} placeholder="Action (Buy, Sell, …)" value={action} onChange={e => setAction(e.target.value)} />
        <span style={{ fontSize: "0.75rem", color: "#6b7280", alignSelf: "center" }}>{isLoading ? "…" : `${data?.count ?? 0} rows`}</span>
      </div>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              {["Date","Action","Symbol","Description","Quantity","Price","Amount"].map(h => <th key={h} style={th}>{h}</th>)}
            </tr>
          </thead>
          <tbody>
            {rows.slice(0, 500).map((r, i) => (
              <tr key={i}>
                <td style={td}>{r.Date}</td>
                <td style={td}>{r.Action}</td>
                <td style={{ ...td, fontWeight: 600 }}>{r.Symbol}</td>
                <td style={{ ...td, maxWidth: "220px", overflow: "hidden", textOverflow: "ellipsis" }}>{r.Description}</td>
                <td style={td}>{r.Quantity}</td>
                <td style={td}>{r.Price}</td>
                <td style={{ ...td, color: r.Amount?.startsWith("-") ? "#dc2626" : "#16a34a" }}>{r.Amount}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length > 500 && <p style={{ color: "#6b7280", fontSize: "0.75rem", padding: "0.5rem" }}>Showing 500 of {rows.length} rows. Use filters to narrow down.</p>}
      </div>
    </div>
  );
}
