import { useQuery } from "@tanstack/react-query";
import { AreaChart } from "@mantine/charts";
import {
  Group, Loader, Paper, SimpleGrid, Stack, Table, Text,
} from "@mantine/core";
import { api } from "../api";
import type { BalanceRow } from "../api";
import { pct, usd } from "../fmt";

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

export default function Balances() {
  const { data, isLoading } = useQuery({ queryKey: ["balances"], queryFn: api.balances });
  const rows = data?.rows ?? [];
  const latest = data?.latest;
  const chartData = rows
    .filter(r => r.snapshot_date_iso && r.account_value != null)
    .map(r => ({
      date: r.snapshot_date_iso!,
      account: r.account_value ?? 0,
      cash: r.cash ?? 0,
      securities: r.securities_value ?? 0,
    }));
  const history = [...rows].reverse();

  return (
    <Stack gap="md">
      <Group gap="sm">
        <Text fw={600} size="lg">Balances</Text>
        {isLoading ? <Loader size="xs" /> : <Text size="xs" c="dimmed">{rows.length} snapshots</Text>}
      </Group>

      <SimpleGrid cols={{ base: 1, sm: 4 }} spacing="md">
        <Stat
          title="Account Value"
          value={usd(latest?.account_value)}
          sub={latest ? `${latest.SnapshotDate} ${latest.SnapshotTime}` : undefined}
        />
        <Stat
          title="Day Change"
          value={usd(latest?.day_change)}
          sub={pct(latest?.day_change_pct)}
          positive={latest?.day_change == null ? null : latest.day_change >= 0}
        />
        <Stat title="Cash" value={usd(latest?.cash)} sub="Cash & investments" />
        <Stat title="Securities" value={usd(latest?.securities_value)} sub="Market value" />
      </SimpleGrid>

      <Paper withBorder p="md" radius="md">
        <Text fw={600} mb="sm">Account Value Over Time</Text>
        {chartData.length > 1 ? (
          <AreaChart
            data={chartData}
            dataKey="date"
            series={[
              { name: "account", color: "indigo.5", label: "Account" },
              { name: "cash", color: "teal.5", label: "Cash" },
              { name: "securities", color: "yellow.5", label: "Securities" },
            ]}
            h={280}
            curveType="monotone"
            withLegend
            fillOpacity={0.08}
            yAxisProps={{ tickFormatter: (v: number) => `$${(v / 1000).toFixed(0)}k`, width: 64 }}
            tooltipProps={{ formatter: (v: unknown) => usd(v as number) }}
          />
        ) : (
          <Text c="dimmed" size="sm" py="xl" ta="center">
            More balance snapshots will turn this into a trend chart.
          </Text>
        )}
      </Paper>

      <Table.ScrollContainer minWidth={760}>
        <Table striped highlightOnHover withColumnBorders verticalSpacing="xs" fz="sm">
          <Table.Thead>
            <Table.Tr>
              {["Date", "Account", "Day", "Day %", "Cash", "Securities", "Available Trade", "Settled"].map(h => (
                <Table.Th key={h} style={{ whiteSpace: "nowrap" }}>{h}</Table.Th>
              ))}
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {history.map((r: BalanceRow) => (
              <Table.Tr key={`${r.SnapshotDate}-${r.SnapshotTime}`}>
                <Table.Td style={{ whiteSpace: "nowrap" }}>{r.snapshot_date_iso ?? r.SnapshotDate}</Table.Td>
                <Table.Td ta="right">{usd(r.account_value)}</Table.Td>
                <Table.Td ta="right" c={(r.day_change ?? 0) >= 0 ? "teal.4" : "red.4"}>{usd(r.day_change)}</Table.Td>
                <Table.Td ta="right" c={(r.day_change_pct ?? 0) >= 0 ? "teal.4" : "red.4"}>{pct(r.day_change_pct)}</Table.Td>
                <Table.Td ta="right">{usd(r.cash)}</Table.Td>
                <Table.Td ta="right">{usd(r.securities_value)}</Table.Td>
                <Table.Td ta="right">{usd(r.available_to_trade)}</Table.Td>
                <Table.Td ta="right">{usd(r.settled_funds)}</Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>
    </Stack>
  );
}
