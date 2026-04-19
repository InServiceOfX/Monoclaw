import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Group, TextInput, Text, Table, Stack, SimpleGrid, Paper, Loader,
} from "@mantine/core";
import { BarChart, AreaChart } from "@mantine/charts";
import { api } from "../api";
import type { RGLSummaryRow } from "../api";
import { usd } from "../fmt";

function parseNum(s: string | null | undefined): number {
  return parseFloat((s ?? "").replace(/[$,%]/g, "").replace(/,/g, "")) || 0;
}

function glColor(v: number) {
  return v >= 0 ? "teal.4" : "red.4";
}

function monthKey(row: RGLSummaryRow): string | null {
  if (row.closed_date_iso) return row.closed_date_iso.slice(0, 7);
  const raw = row["Closed Date"];
  const m = raw?.match(/^(\d{1,2})\/\d{1,2}\/(\d{4})/);
  if (!m) return null;
  return `${m[2]}-${m[1].padStart(2, "0")}`;
}

function monthLabel(month: string): string {
  const [year, mm] = month.split("-");
  return `${year}-${mm}`;
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
    if (!bySymbol[sym]) bySymbol[sym] = { symbol: sym, name: r.Name ?? "", total: 0, lt: 0, st: 0 };
    bySymbol[sym].total += parseNum(r["Total Gain/Loss ($)"]);
    bySymbol[sym].lt += parseNum(r["Long Term (LT) Gain/Loss ($)"]);
    bySymbol[sym].st += parseNum(r["Short Term (ST) Gain/Loss ($)"]);
  }
  const agg = Object.values(bySymbol).sort((a, b) => b.total - a.total);

  const totalGL = agg.reduce((s, r) => s + r.total, 0);
  const totalLT = agg.reduce((s, r) => s + r.lt, 0);
  const totalST = agg.reduce((s, r) => s + r.st, 0);

  // Monthly G/L from raw rows (split into gain/loss for diverging bars)
  const monthly: Record<string, number> = {};
  for (const r of rows) {
    const month = monthKey(r);
    if (!month) continue;
    monthly[month] = (monthly[month] ?? 0) + parseNum(r["Total Gain/Loss ($)"]);
  }
  const monthlyData = Object.entries(monthly)
    .sort(([a], [b]) => a.localeCompare(b))
    .reduce<{
      running: number;
      data: { month: string; label: string; gain: number; loss: number; cumulative: number }[];
    }>((acc, [month, total]) => {
      const cumulative = acc.running + total;
      return {
        running: cumulative,
        data: [
          ...acc.data,
          {
            month,
            label: monthLabel(month),
            gain: total > 0 ? total : 0,
            loss: total < 0 ? total : 0,
            cumulative,
          },
        ],
      };
    }, { running: 0, data: [] }).data;

  return (
    <Stack gap="md">
      <Text fw={600} size="lg">Realized Gains & Losses</Text>

      <Group gap="sm" align="flex-end">
        <TextInput
          type="date"
          label="From"
          value={fromDate}
          onChange={e => setFromDate(e.target.value)}
          size="xs"
          w={160}
        />
        <TextInput
          type="date"
          label="To"
          value={toDate}
          onChange={e => setToDate(e.target.value)}
          size="xs"
          w={160}
        />
        {isLoading
          ? <Loader size="xs" mb={6} />
          : <Text size="xs" c="dimmed" mb={6}>{agg.length} symbols</Text>
        }
      </Group>

      {/* Summary cards */}
      <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="md">
        <Paper withBorder p="md" radius="md">
          <Text size="xs" c="dimmed" tt="uppercase" fw={600} lts={0.5}>Total G/L</Text>
          <Text size="xl" fw={700} c={glColor(totalGL)}>{usd(totalGL)}</Text>
          <Text size="xs" c="dimmed" mt={4}>RGL data starts 2024-01-01 (Schwab UI limitation)</Text>
        </Paper>
        <Paper withBorder p="md" radius="md">
          <Text size="xs" c="dimmed" tt="uppercase" fw={600} lts={0.5}>Long-Term G/L</Text>
          <Text size="xl" fw={700} c={glColor(totalLT)}>{usd(totalLT)}</Text>
        </Paper>
        <Paper withBorder p="md" radius="md">
          <Text size="xs" c="dimmed" tt="uppercase" fw={600} lts={0.5}>Short-Term G/L</Text>
          <Text size="xl" fw={700} c={glColor(totalST)}>{usd(totalST)}</Text>
        </Paper>
      </SimpleGrid>

      {/* Charts */}
      {monthlyData.length > 0 && (
        <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
          <Paper withBorder p="md" radius="md">
              <Text fw={600} mb="sm" size="sm">Monthly Realized G/L</Text>
            <BarChart
              data={monthlyData}
              dataKey="label"
              series={[
                { name: "gain", color: "teal.5", label: "Gain" },
                { name: "loss", color: "red.5", label: "Loss" },
              ]}
              type="stacked"
              h={220}
              withLegend
              yAxisProps={{ tickFormatter: (v: number) => `$${(v / 1000).toFixed(0)}k`, width: 60 }}
              tooltipProps={{ formatter: (v: unknown) => usd(v as number) }}
              xAxisProps={{ tick: { fontSize: 10 } }}
            />
          </Paper>

          <Paper withBorder p="md" radius="md">
            <Text fw={600} mb="sm" size="sm">Cumulative Realized G/L</Text>
            <AreaChart
              data={monthlyData}
              dataKey="label"
              series={[{ name: "cumulative", color: totalGL >= 0 ? "teal.5" : "red.5", label: "Cumulative" }]}
              h={220}
              curveType="monotone"
              fillOpacity={0.15}
              yAxisProps={{ tickFormatter: (v: number) => `$${(v / 1000).toFixed(0)}k`, width: 60 }}
              tooltipProps={{ formatter: (v: unknown) => usd(v as number) }}
              xAxisProps={{ tick: { fontSize: 10 } }}
            />
          </Paper>
        </SimpleGrid>
      )}

      {/* Per-symbol table */}
      <Table.ScrollContainer minWidth={600}>
        <Table striped highlightOnHover withColumnBorders verticalSpacing="xs" fz="sm">
          <Table.Thead>
            <Table.Tr>
              {["Symbol","Name","Total G/L","Long-Term G/L","Short-Term G/L"].map(h => (
                <Table.Th key={h}>{h}</Table.Th>
              ))}
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {agg.map(r => (
              <Table.Tr key={r.symbol}>
                <Table.Td fw={700}>{r.symbol}</Table.Td>
                <Table.Td style={{ maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.name}</Table.Td>
                <Table.Td ta="right" c={glColor(r.total)}>{usd(r.total)}</Table.Td>
                <Table.Td ta="right" c={glColor(r.lt)}>{usd(r.lt)}</Table.Td>
                <Table.Td ta="right" c={glColor(r.st)}>{usd(r.st)}</Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>
    </Stack>
  );
}
