import { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AppShell, Group, Tabs, Title } from "@mantine/core";
import Overview from "./pages/Overview";
import Positions from "./pages/Positions";
import Transactions from "./pages/Transactions";
import RGL from "./pages/RGL";

const qc = new QueryClient({ defaultOptions: { queries: { retry: 1, staleTime: 30000 } } });

export default function App() {
  const [tab, setTab] = useState("overview");
  return (
    <QueryClientProvider client={qc}>
      <AppShell header={{ height: 56 }} padding="md">
        <AppShell.Header>
          <Group h="100%" px="md" gap="xl">
            <Title order={4} c="indigo.4" style={{ flexShrink: 0 }}>Portfolio</Title>
            <Tabs value={tab} onChange={v => setTab(v ?? "overview")} variant="pills">
              <Tabs.List>
                <Tabs.Tab value="overview">Overview</Tabs.Tab>
                <Tabs.Tab value="positions">Positions</Tabs.Tab>
                <Tabs.Tab value="transactions">Transactions</Tabs.Tab>
                <Tabs.Tab value="rgl">Realized G/L</Tabs.Tab>
              </Tabs.List>
            </Tabs>
          </Group>
        </AppShell.Header>
        <AppShell.Main>
          {tab === "overview" && <Overview />}
          {tab === "positions" && <Positions />}
          {tab === "transactions" && <Transactions />}
          {tab === "rgl" && <RGL />}
        </AppShell.Main>
      </AppShell>
    </QueryClientProvider>
  );
}
