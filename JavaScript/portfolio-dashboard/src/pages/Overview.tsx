import { useQuery } from "@tanstack/react-query";
import { PieChart, Pie, Cell, LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { api } from "../api";
import { usd, pct, glColor } from "../fmt";

const COLORS = ["#6366f1","#f59e0b","#10b981","#3b82f6","#ef4444","#8b5cf6","#ec4899","#14b8a6","#f97316","#84cc16"];

export default function Overview() {
  const summary = useQuery({ queryKey: ["summary"], queryFn: api.summary, refetchInterval: 60000 });
  const positions = useQuery({ queryKey: ["positions"], queryFn: api.positions, refetchInterval: 60000 });
  const history = useQuery({ queryKey: ["history"], queryFn: api.history });

  const s = summary.data;
  const top10 = (positions.data?.positions ?? [])
    .filter(p => (p.market_value ?? 0) > 0)
    .sort((a, b) => (b.market_value ?? 0) - (a.market_value ?? 0))
    .slice(0, 10)
    .map(p => ({ name: p.symbol, value: p.market_value ?? 0 }));

  const historyData = (history.data?.snapshots ?? []).map(s => ({
    date: s.date,
    value: s.total_market_value,
    cost: s.total_cost_basis,
  }));

  return (
    <div style={{ padding: "1.5rem" }}>
      {/* Summary cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem", marginBottom: "2rem" }}>
        <Card title="Total Value" value={usd(s?.total_market_value)} />
        <Card title="Unrealized G/L" value={usd(s?.total_unrealized_gl_dollars)} color={glColor(s?.total_unrealized_gl_dollars)} sub={pct(s?.total_unrealized_gl_pct)} />
        <Card title="Day Change" value={usd(s?.total_day_change)} color={glColor(s?.total_day_change)} />
        <Card title="Positions" value={String(s?.position_count ?? "—")} sub={`as of ${s?.as_of ?? ""}`} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: "2rem" }}>
        {/* Allocation donut */}
        <div>
          <h3 style={{ marginBottom: "0.5rem" }}>Top 10 Holdings</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie data={top10} cx="50%" cy="50%" innerRadius={60} outerRadius={110} dataKey="value" nameKey="name" label={({ name }) => name}>
                {top10.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip formatter={(v) => usd(v as number)} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Portfolio value over time */}
        <div>
          <h3 style={{ marginBottom: "0.5rem" }}>Portfolio Value Over Time</h3>
          {historyData.length < 2 ? (
            <p style={{ color: "#6b7280", fontSize: "0.875rem" }}>
              Only 1 snapshot available. More data points will appear as you download weekly snapshots.
            </p>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={historyData}>
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis tickFormatter={v => `$${((v as number)/1000).toFixed(0)}k`} width={60} />
                <Tooltip formatter={(v) => usd(v as number)} />
                <Legend />
                <Line type="monotone" dataKey="value" stroke="#6366f1" name="Market Value" dot={false} strokeWidth={2} />
                <Line type="monotone" dataKey="cost" stroke="#9ca3af" name="Cost Basis" dot={false} strokeDasharray="4 2" />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </div>
  );
}

function Card({ title, value, sub, color }: { title: string; value: string; sub?: string; color?: string }) {
  return (
    <div style={{ background: "#f9fafb", borderRadius: "0.5rem", padding: "1rem", border: "1px solid #e5e7eb" }}>
      <div style={{ fontSize: "0.75rem", color: "#6b7280", marginBottom: "0.25rem" }}>{title}</div>
      <div style={{ fontSize: "1.5rem", fontWeight: 700, color: color ?? "#111827" }}>{value}</div>
      {sub && <div style={{ fontSize: "0.75rem", color: color ?? "#6b7280" }}>{sub}</div>}
    </div>
  );
}
