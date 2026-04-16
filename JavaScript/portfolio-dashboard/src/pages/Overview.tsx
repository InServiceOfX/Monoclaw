import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  SimpleGrid, Paper, Stack, Text, Group, SegmentedControl,
  Skeleton, Alert, Divider, ColorSwatch, Table,
} from "@mantine/core";
import { AreaChart, DonutChart } from "@mantine/charts";
import { api } from "../api";
import { usd, pct } from "../fmt";

const DONUT_COLORS = [
  "indigo.6","yellow.5","teal.5","blue.5","red.5",
  "violet.5","pink.5","cyan.5","orange.5","lime.5",
];

const PERIODS = [
  { label: "1M", value: "1m" },
  { label: "3M", value: "3m" },
  { label: "6M", value: "6m" },
  { label: "1Y", value: "1y" },
  { label: "2Y", value: "2y" },
];

function StatCard({
  title, value, sub, positive,
}: {
  title: string; value: string; sub?: string; positive?: boolean | null;
}) {
  const subColor = positive == null ? "dimmed" : positive ? "teal.4" : "red.4";
  return (
    <Paper withBorder p="md" radius="md">
      <Stack gap={4}>
        <Text size="xs" c="dimmed" tt="uppercase" fw={600} lts={0.5}>{title}</Text>
        <Text
          size="xl" fw={700}
          c={positive == null ? undefined : positive ? "teal.4" : "red.4"}
        >
          {value}
        </Text>
        {sub && <Text size="xs" c={subColor}>{sub}</Text>}
      </Stack>
    </Paper>
  );
}

export default function Overview() {
  const [period, setPeriod] = useState("1y");

  const summary = useQuery({ queryKey: ["summary"], queryFn: api.summary, refetchInterval: 60000 });
  const positions = useQuery({ queryKey: ["positions"], queryFn: api.positions, refetchInterval: 60000 });
  const timeseries = useQuery({ queryKey: ["timeseries", period], queryFn: () => api.timeseries(period) });

  const s = summary.data;
  const glPositive = s ? (s.total_unrealized_gl_dollars >= 0 ? true : false) : null;
  const dayPositive = s ? (s.total_day_change >= 0 ? true : false) : null;

  const top10 = (positions.data?.positions ?? [])
    .filter(p => (p.market_value ?? 0) > 0 && p.cost_basis_total != null)
    .sort((a, b) => (b.market_value ?? 0) - (a.market_value ?? 0))
    .slice(0, 10)
    .map((p, i) => ({ name: p.symbol, value: p.market_value ?? 0, color: DONUT_COLORS[i] }));

  // Merge portfolio + SPY benchmark by date
  const tsData = (() => {
    const series = timeseries.data?.series ?? [];
    const spy = timeseries.data?.benchmark_spy ?? [];
    const spyMap = new Map(spy.map(d => [d.date, d.value]));
    return series.map(d => ({ date: d.date, portfolio: d.value, spy: spyMap.get(d.date) ?? null }));
  })();

  return (
    <Stack gap="lg">
      {/* Stat cards */}
      <SimpleGrid cols={{ base: 2, sm: 4 }} spacing="md">
        <Skeleton visible={summary.isLoading} radius="md">
          <StatCard title="Total Value" value={usd(s?.total_market_value)} />
        </Skeleton>
        <Skeleton visible={summary.isLoading} radius="md">
          <StatCard
            title="Unrealized G/L"
            value={usd(s?.total_unrealized_gl_dollars)}
            sub={pct(s?.total_unrealized_gl_pct)}
            positive={glPositive}
          />
        </Skeleton>
        <Skeleton visible={summary.isLoading} radius="md">
          <StatCard title="Day Change" value={usd(s?.total_day_change)} positive={dayPositive} />
        </Skeleton>
        <Skeleton visible={summary.isLoading} radius="md">
          <StatCard
            title="Positions"
            value={String(s?.position_count ?? "—")}
            sub={`as of ${s?.as_of ?? ""}`}
          />
        </Skeleton>
      </SimpleGrid>

      {/* Charts row */}
      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
        {/* Donut + always-visible legend */}
        <Paper withBorder p="md" radius="md">
          <Text fw={600} mb="sm">Top 10 Holdings</Text>
          <Skeleton visible={positions.isLoading}>
            {top10.length > 0 ? (
              <Stack gap="sm">
                <DonutChart
                  data={top10}
                  h={200}
                  paddingAngle={2}
                  tooltipDataSource="segment"
                  valueFormatter={v => usd(v)}
                  withLabels={false}
                  strokeWidth={1}
                />
                <Table fz="xs" verticalSpacing={4}>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Symbol</Table.Th>
                      <Table.Th ta="right">Value</Table.Th>
                      <Table.Th ta="right">% Portfolio</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {top10.map((h, i) => {
                      const totalMV = top10.reduce((s, x) => s + x.value, 0);
                      const pctShare = totalMV > 0 ? (h.value / (positions.data?.positions.reduce((s, p) => s + (p.market_value ?? 0), 0) || totalMV) * 100) : 0;
                      return (
                        <Table.Tr key={h.name}>
                          <Table.Td>
                            <Group gap={6} wrap="nowrap">
                              <ColorSwatch color={`var(--mantine-color-${DONUT_COLORS[i].replace(".", "-")})`} size={10} />
                              <Text size="xs" fw={600}>{h.name}</Text>
                            </Group>
                          </Table.Td>
                          <Table.Td ta="right"><Text size="xs">{usd(h.value, 0)}</Text></Table.Td>
                          <Table.Td ta="right"><Text size="xs" c="dimmed">{pctShare.toFixed(1)}%</Text></Table.Td>
                        </Table.Tr>
                      );
                    })}
                  </Table.Tbody>
                </Table>
              </Stack>
            ) : (
              <Text c="dimmed" size="sm" ta="center" py="xl">No position data</Text>
            )}
          </Skeleton>
        </Paper>

        {/* Timeseries */}
        <Paper withBorder p="md" radius="md">
          <Group justify="space-between" mb="sm">
            <Text fw={600}>Performance (Current Holdings)</Text>
            <SegmentedControl
              size="xs"
              data={PERIODS}
              value={period}
              onChange={setPeriod}
            />
          </Group>
          <Skeleton visible={timeseries.isLoading}>
            {timeseries.data?.error ? (
              <Alert color="red" title="Error" radius="md">{timeseries.data.error}</Alert>
            ) : tsData.length > 1 ? (
              <>
                <AreaChart
                  data={tsData}
                  dataKey="date"
                  series={[
                    { name: "portfolio", color: "indigo.5", label: "Portfolio" },
                    { name: "spy", color: "gray.5", label: "SPY (normalized)" },
                  ]}
                  h={240}
                  curveType="monotone"
                  withLegend
                  fillOpacity={0.08}
                  yAxisProps={{
                    tickFormatter: (v: number) => `$${(v / 1000).toFixed(0)}k`,
                    width: 64,
                  }}
                  tooltipProps={{
                    formatter: (v: unknown) => usd(v as number),
                  }}
                  connectNulls={false}
                />
                <Text size="xs" c="dimmed" mt={4}>
                  {timeseries.data?.note}
                </Text>
              </>
            ) : (
              <Text c="dimmed" size="sm" ta="center" py="xl">
                Not enough data for timeseries. Download more snapshots and ensure yfinance is installed.
              </Text>
            )}
          </Skeleton>
        </Paper>
      </SimpleGrid>

      <Divider />
      <Text size="xs" c="dimmed">Prices refresh every 60 s via Yahoo Finance. Stale prices marked ⚠.</Text>
    </Stack>
  );
}
