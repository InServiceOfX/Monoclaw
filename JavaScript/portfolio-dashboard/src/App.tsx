import { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AppShell, Group, Tabs, Title } from "@mantine/core";
import Overview from "./pages/Overview";
import Positions from "./pages/Positions";
import Transactions from "./pages/Transactions";
import RGL from "./pages/RGL";
import Balances from "./pages/Balances";
import Insights from "./pages/Insights";
import MonteCarlo from "./pages/MonteCarlo";
import Earnings from "./pages/Earnings";
import Recommendations from "./pages/Recommendations";

const qc = new QueryClient({ defaultOptions: { queries: { retry: 1, staleTime: 30000 } } });

export default function App() {
  const [tab, setTab] = useState("overview");
  return (
    <QueryClientProvider client={qc}>
      <AppShell header={{ height: 64 }} padding="md">
        <AppShell.Header>
          <Group h="100%" px="md" gap="lg" wrap="nowrap">
            <Title order={4} c="indigo.4" style={{ flexShrink: 0 }}>Portfolio</Title>
            <Tabs value={tab} onChange={v => setTab(v ?? "overview")} variant="pills">
              <Tabs.List>
                <Tabs.Tab value="overview">Overview</Tabs.Tab>
                <Tabs.Tab value="positions">Positions</Tabs.Tab>
                <Tabs.Tab value="balances">Balances</Tabs.Tab>
                <Tabs.Tab value="transactions">Transactions</Tabs.Tab>
                <Tabs.Tab value="rgl">Realized G/L</Tabs.Tab>
                <Tabs.Tab value="insights">Context</Tabs.Tab>
                <Tabs.Tab value="mc">Monte Carlo</Tabs.Tab>
                <Tabs.Tab value="earnings">Earnings</Tabs.Tab>
                <Tabs.Tab value="recommendations">Recs</Tabs.Tab>
              </Tabs.List>
            </Tabs>
          </Group>
        </AppShell.Header>
        <AppShell.Main>
          {tab === "overview" && <Overview />}
          {tab === "positions" && <Positions />}
          {tab === "balances" && <Balances />}
          {tab === "transactions" && <Transactions />}
          {tab === "rgl" && <RGL />}
          {tab === "insights" && <Insights />}
          {tab === "mc" && <MonteCarlo />}
          {tab === "earnings" && <Earnings />}
          {tab === "recommendations" && <Recommendations />}
        </AppShell.Main>
      </AppShell>
    </QueryClientProvider>
  );
}
