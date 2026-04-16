import { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Overview from "./pages/Overview";
import Positions from "./pages/Positions";
import Transactions from "./pages/Transactions";
import RGL from "./pages/RGL";

const qc = new QueryClient({ defaultOptions: { queries: { retry: 1, staleTime: 30000 } } });

type Tab = "overview" | "positions" | "transactions" | "rgl";

const TABS: { key: Tab; label: string }[] = [
  { key: "overview", label: "Overview" },
  { key: "positions", label: "Positions" },
  { key: "transactions", label: "Transactions" },
  { key: "rgl", label: "Realized G/L" },
];

export default function App() {
  const [tab, setTab] = useState<Tab>("overview");

  return (
    <QueryClientProvider client={qc}>
      <div style={{ fontFamily: "system-ui, sans-serif", minHeight: "100vh", background: "#fff" }}>
        <nav style={{ borderBottom: "1px solid #e5e7eb", display: "flex", alignItems: "center", padding: "0 1.5rem" }}>
          <span style={{ fontWeight: 700, fontSize: "1rem", color: "#111827", paddingRight: "2rem", paddingTop: "1rem", paddingBottom: "1rem" }}>
            Portfolio
          </span>
          {TABS.map(t => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              style={{
                background: "none", border: "none", padding: "1rem 1.25rem", cursor: "pointer",
                fontSize: "0.875rem", fontWeight: tab === t.key ? 600 : 400,
                color: tab === t.key ? "#4f46e5" : "#6b7280",
                borderBottom: tab === t.key ? "2px solid #4f46e5" : "2px solid transparent",
                marginBottom: "-1px",
              }}
            >
              {t.label}
            </button>
          ))}
        </nav>
        {tab === "overview" && <Overview />}
        {tab === "positions" && <Positions />}
        {tab === "transactions" && <Transactions />}
        {tab === "rgl" && <RGL />}
      </div>
    </QueryClientProvider>
  );
}
