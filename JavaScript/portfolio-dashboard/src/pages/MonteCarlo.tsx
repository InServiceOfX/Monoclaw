import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Alert, Badge, Button, Group, Loader, NumberInput, Paper, Select, SimpleGrid,
  Stack, Table, Text, TextInput,
} from "@mantine/core";
import { AreaChart } from "@mantine/charts";
import { api } from "../api";
import type { MonteCarloResponse } from "../api";
import { pct, usd, num } from "../fmt";

function Stat({
  title, value, sub, positive,
}: {
  title: string; value: string; sub?: string; positive?: boolean | null;
}) {
  return (
    <Paper withBorder p="md" radius="md">
      <Text size="xs" c="dimmed" tt="uppercase" fw={600} lts={0.5}>{title}</Text>
      <Text size="xl" fw={700} c={positive == null ? undefined : positive ? "teal.4" : "red.4"}>
        {value}
      </Text>
      {sub && <Text size="xs" c="dimmed" mt={4}>{sub}</Text>}
    </Paper>
  );
}

export default function MonteCarlo() {
  const [symbols, setSymbols] = useState("");
  const [submittedSymbols, setSubmittedSymbols] = useState("");
  const [days, setDays] = useState(90);
  const [simulations, setSimulations] = useState(3000);
  const [period, setPeriod] = useState("1y");
  const [maxPositions, setMaxPositions] = useState(25);

  const query = useQuery<MonteCarloResponse>({
    queryKey: ["monte-carlo", submittedSymbols, days, simulations, period, maxPositions],
    queryFn: () => api.monteCarlo({
      symbols: submittedSymbols,
      days,
      simulations,
      period,
      max_positions: maxPositions,
    }),
    enabled: true,
    staleTime: 10 * 60 * 1000,
  });

  const data = query.data;
  const portfolio = data?.portfolio;
  const bands = portfolio?.bands ?? [];

  return (
    <Stack gap="md">
      <Group gap="sm" align="flex-end" wrap="wrap">
        <Text fw={600} size="lg">Monte Carlo</Text>
        {query.isFetching && <Loader size="xs" />}
        <TextInput
          label="Watchlist"
          placeholder="AMD, META, QQQ"
          value={symbols}
          onChange={e => setSymbols(e.target.value.toUpperCase())}
          size="xs"
          w={260}
        />
        <NumberInput label="Days" value={days} onChange={v => setDays(Number(v) || 90)} min={5} max={252} size="xs" w={90} />
        <NumberInput label="Runs" value={simulations} onChange={v => setSimulations(Number(v) || 3000)} min={500} max={20000} step={500} size="xs" w={110} />
        <NumberInput label="Positions" value={maxPositions} onChange={v => setMaxPositions(Number(v) || 25)} min={1} max={75} size="xs" w={110} />
        <Select
          label="History"
          value={period}
          onChange={v => setPeriod(v ?? "1y")}
          data={["6mo", "1y", "2y", "5y"]}
          size="xs"
          w={90}
        />
        <Button size="xs" onClick={() => setSubmittedSymbols(symbols.trim())}>Run</Button>
      </Group>

      <Alert color="blue" variant="light" radius="md">
        Uses current holdings from local Schwab CSVs plus optional watchlist symbols. This is risk context based on historical Yahoo returns and correlation, not a price prediction.
      </Alert>

      {data?.error && <Alert color="red" title="Simulation unavailable" radius="md">{data.error}</Alert>}

      {portfolio && (
        <>
          <SimpleGrid cols={{ base: 1, sm: 4 }} spacing="md">
            <Stat title="Expected Final" value={usd(portfolio.expected_final)} sub={`${portfolio.days} trading days`} positive={portfolio.expected_return_pct == null ? null : portfolio.expected_return_pct >= 0} />
            <Stat title="Median Return" value={pct(portfolio.expected_return_pct)} sub="Mean simulated return" positive={portfolio.expected_return_pct == null ? null : portfolio.expected_return_pct >= 0} />
            <Stat title="5% Downside" value={usd(portfolio.var_5)} sub="Value-at-risk from start" positive={false} />
            <Stat title="Loss Probability" value={pct(portfolio.probability_loss_pct)} sub={`${portfolio.sample_count} runs`} />
          </SimpleGrid>

          <Paper withBorder p="md" radius="md">
            <Group justify="space-between" mb="sm">
              <Text fw={600}>Portfolio Risk Bands</Text>
              <Text size="xs" c="dimmed">
                {data?.history_start} to {data?.history_end}; {portfolio.symbols_used.length} symbols
              </Text>
            </Group>
            <AreaChart
              data={bands}
              dataKey="day"
              series={[
                { name: "p95", color: "teal.5", label: "95th percentile" },
                { name: "p50", color: "indigo.5", label: "Median" },
                { name: "p05", color: "red.5", label: "5th percentile" },
              ]}
              h={300}
              curveType="monotone"
              withLegend
              fillOpacity={0.08}
              yAxisProps={{ tickFormatter: (v: number) => `$${(v / 1000).toFixed(0)}k`, width: 64 }}
              tooltipProps={{ formatter: (v: unknown) => usd(v as number) }}
            />
            <Text size="xs" c="dimmed" mt={4}>{portfolio.note}</Text>
            {portfolio.symbols_missing.length > 0 && (
              <Text size="xs" c="yellow.4" mt={4}>Missing history: {portfolio.symbols_missing.join(", ")}</Text>
            )}
          </Paper>
        </>
      )}

      <Paper withBorder p="md" radius="md">
        <Group justify="space-between" mb="sm">
          <Text fw={600}>Watchlist Standalone Runs</Text>
          <Text size="xs" c="dimmed">Enter symbols above, then Run</Text>
        </Group>
        <Table.ScrollContainer minWidth={980}>
          <Table striped highlightOnHover withColumnBorders verticalSpacing="xs" fz="sm">
            <Table.Thead>
              <Table.Tr>
                {["Symbol", "Status", "Price", "Expected", "P05", "P50", "P95", "Gain Prob.", "Ann. Vol", "Sharpe-ish", "Risk/Reward"].map(h => (
                  <Table.Th key={h} style={{ whiteSpace: "nowrap" }}>{h}</Table.Th>
                ))}
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {(data?.candidates ?? []).map(c => (
                <Table.Tr key={c.symbol}>
                  <Table.Td fw={700}>{c.symbol}</Table.Td>
                  <Table.Td>
                    <Badge color={c.status === "ok" ? "teal" : "yellow"} variant="light">
                      {c.status === "ok" ? "ok" : "missing"}
                    </Badge>
                  </Table.Td>
                  <Table.Td ta="right">{usd(c.last_price)}</Table.Td>
                  <Table.Td ta="right" c={(c.expected_return_pct ?? 0) >= 0 ? "teal.4" : "red.4"}>{pct(c.expected_return_pct)}</Table.Td>
                  <Table.Td ta="right">{usd(c.p05)}</Table.Td>
                  <Table.Td ta="right">{usd(c.p50)}</Table.Td>
                  <Table.Td ta="right">{usd(c.p95)}</Table.Td>
                  <Table.Td ta="right">{pct(c.probability_gain_pct)}</Table.Td>
                  <Table.Td ta="right">{pct(c.annual_vol_pct)}</Table.Td>
                  <Table.Td ta="right">{num(c.sharpe_like)}</Table.Td>
                  <Table.Td ta="right">{num(c.risk_reward_score)}</Table.Td>
                </Table.Tr>
              ))}
              {(data?.candidates ?? []).length === 0 && (
                <Table.Tr>
                  <Table.Td colSpan={11}>
                    <Text size="sm" c="dimmed" ta="center" py="md">No watchlist symbols submitted yet.</Text>
                  </Table.Td>
                </Table.Tr>
              )}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      </Paper>
    </Stack>
  );
}
