import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Badge,
  Group,
  Paper,
  SegmentedControl,
  SimpleGrid,
  Skeleton,
  Stack,
  Table,
  Text,
  Title,
  Tooltip,
} from "@mantine/core";
import { BarChart } from "@mantine/charts";
import { api } from "../api";
import type { RecommendationRec, RecommendationsReport } from "../api";

type Attribution = RecommendationRec["attribution"];

const ATTR_COLOR: Record<Attribution, string> = {
  followed: "green",
  partially_followed: "teal",
  ignored: "gray",
  contrary: "red",
  unknown: "gray",
};

const ATTR_LABEL: Record<Attribution, string> = {
  followed: "Followed",
  partially_followed: "Partial",
  ignored: "Ignored",
  contrary: "Contrary",
  unknown: "Unknown",
};

const CONVICTION_COLOR: Record<string, string> = {
  strong_buy: "green",
  buy: "teal",
  hold: "yellow",
  weak_hold: "orange",
  sell: "red",
};

function fmtPct(v: number | null | undefined) {
  if (v == null) return "—";
  return `${v >= 0 ? "+" : ""}${v.toFixed(1)}%`;
}

function fmtRR(v: number | null | undefined) {
  if (v == null) return "—";
  return v.toFixed(2);
}

function SummaryCards({ summary }: { summary: RecommendationsReport["summary"] }) {
  const byAttr = summary.by_attribution;
  return (
    <SimpleGrid cols={{ base: 2, sm: 4 }} spacing="sm">
      <Paper p="md" withBorder radius="md">
        <Text size="xs" c="dimmed">Total Recs ({summary.days_lookback}d)</Text>
        <Text fw={700} size="xl">{summary.total}</Text>
      </Paper>
      <Paper p="md" withBorder radius="md">
        <Text size="xs" c="dimmed">Follow Rate</Text>
        <Text fw={700} size="xl" c="teal">{summary.follow_rate_pct}%</Text>
      </Paper>
      <Paper p="md" withBorder radius="md">
        <Text size="xs" c="dimmed">Followed / Partial</Text>
        <Text fw={700} size="xl">
          {byAttr.followed ?? 0} / {byAttr.partially_followed ?? 0}
        </Text>
      </Paper>
      <Paper p="md" withBorder radius="md">
        <Text size="xs" c="dimmed">Ignored / Contrary</Text>
        <Text fw={700} size="xl" c="red">
          {byAttr.ignored ?? 0} / {byAttr.contrary ?? 0}
        </Text>
      </Paper>
    </SimpleGrid>
  );
}

function AttributionChart({ byAttr }: { byAttr: Record<string, number> }) {
  const data = Object.entries(byAttr).map(([k, v]) => ({
    attribution: ATTR_LABEL[k as Attribution] ?? k,
    count: v,
  }));
  if (data.length === 0) return null;
  return (
    <Paper p="md" withBorder radius="md">
      <Text size="sm" fw={600} mb="xs">Attribution Breakdown</Text>
      <BarChart
        h={180}
        data={data}
        dataKey="attribution"
        series={[{ name: "count", color: "indigo.5", label: "Recs" }]}
        tickLine="none"
        gridAxis="y"
      />
    </Paper>
  );
}

const DAYS_OPTIONS = [
  { label: "30d", value: "30" },
  { label: "90d", value: "90" },
  { label: "180d", value: "180" },
  { label: "1y", value: "365" },
];

const ATTR_FILTER_OPTIONS = [
  { label: "All", value: "all" },
  { label: "Followed", value: "followed" },
  { label: "Partial", value: "partially_followed" },
  { label: "Ignored", value: "ignored" },
  { label: "Contrary", value: "contrary" },
];

export default function Recommendations() {
  const [days, setDays] = useState("90");
  const [attrFilter, setAttrFilter] = useState("all");

  const { data, isLoading, error } = useQuery({
    queryKey: ["recommendations", days],
    queryFn: () => api.recommendations(Number(days)),
    staleTime: 60_000,
  });

  const recs = data?.recommendations ?? [];
  const summary = data?.summary;

  const filtered =
    attrFilter === "all" ? recs : recs.filter((r) => r.attribution === attrFilter);

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <Title order={4}>Recommendations</Title>
        <Group gap="xs">
          <Text size="xs" c="dimmed">Lookback:</Text>
          <SegmentedControl size="xs" value={days} onChange={setDays} data={DAYS_OPTIONS} />
        </Group>
      </Group>

      {isLoading && (
        <Stack gap="xs">
          <Skeleton height={80} radius="md" />
          <Skeleton height={200} radius="md" />
          <Skeleton height={300} radius="md" />
        </Stack>
      )}

      {error && (
        <Text c="red">Failed to load recommendations. Is the API running?</Text>
      )}

      {!isLoading && !error && summary && (
        <>
          <SummaryCards summary={summary} />

          <SimpleGrid cols={{ base: 1, md: 2 }} spacing="sm">
            <AttributionChart byAttr={summary.by_attribution} />
            <Paper p="md" withBorder radius="md">
              <Text size="sm" fw={600} mb="xs">By Conviction</Text>
              {Object.entries(summary.by_conviction).map(([k, v]) => (
                <Group key={k} justify="space-between" mb={4}>
                  <Badge color={CONVICTION_COLOR[k] ?? "gray"} variant="light" size="sm">
                    {k}
                  </Badge>
                  <Text size="sm" fw={500}>{v}</Text>
                </Group>
              ))}
            </Paper>
          </SimpleGrid>

          <Paper withBorder radius="md" p="sm">
            <Group mb="sm" gap="xs">
              <Text size="sm" fw={600}>Filter:</Text>
              {ATTR_FILTER_OPTIONS.map((o) => (
                <Badge
                  key={o.value}
                  color={o.value === "all" ? "indigo" : (ATTR_COLOR[o.value as Attribution] ?? "gray")}
                  variant={attrFilter === o.value ? "filled" : "light"}
                  style={{ cursor: "pointer" }}
                  onClick={() => setAttrFilter(o.value)}
                >
                  {o.label}
                </Badge>
              ))}
            </Group>

            {filtered.length === 0 ? (
              <Text size="sm" c="dimmed">No recommendations match this filter.</Text>
            ) : (
              <Table.ScrollContainer minWidth={900}>
                <Table striped highlightOnHover withColumnBorders fz="xs">
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Date</Table.Th>
                      <Table.Th>Symbol</Table.Th>
                      <Table.Th>Action</Table.Th>
                      <Table.Th>Conviction</Table.Th>
                      <Table.Th>R/R</Table.Th>
                      <Table.Th>P(Gain)</Table.Th>
                      <Table.Th>Attribution</Table.Th>
                      <Table.Th>Trade</Table.Th>
                      <Table.Th>1d Ret</Table.Th>
                      <Table.Th>7d Ret</Table.Th>
                      <Table.Th>30d Ret</Table.Th>
                      <Table.Th>1d α</Table.Th>
                      <Table.Th>7d α</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {filtered.map((r) => {
                      const ret = r.forward_returns;
                      const alpha = r.spy_alpha;
                      const trade = r.matched_trade;
                      return (
                        <Table.Tr key={r.id}>
                          <Table.Td c="dimmed">{r.timestamp.slice(0, 10)}</Table.Td>
                          <Table.Td fw={600}>{r.symbol}</Table.Td>
                          <Table.Td>
                            <Badge
                              color={
                                r.action === "buy" || r.action === "add"
                                  ? "green"
                                  : r.action === "sell" || r.action === "trim"
                                  ? "red"
                                  : "gray"
                              }
                              variant="light"
                              size="xs"
                            >
                              {r.action}
                            </Badge>
                          </Table.Td>
                          <Table.Td>
                            {r.conviction ? (
                              <Badge
                                color={CONVICTION_COLOR[r.conviction] ?? "gray"}
                                variant="light"
                                size="xs"
                              >
                                {r.conviction}
                              </Badge>
                            ) : "—"}
                          </Table.Td>
                          <Table.Td fw={500}>{fmtRR(r.risk_reward_score)}</Table.Td>
                          <Table.Td>
                            {r.prob_gain != null ? `${(r.prob_gain * 100).toFixed(0)}%` : "—"}
                          </Table.Td>
                          <Table.Td>
                            <Badge color={ATTR_COLOR[r.attribution]} variant="light" size="xs">
                              {ATTR_LABEL[r.attribution]}
                            </Badge>
                          </Table.Td>
                          <Table.Td>
                            {trade ? (
                              <Tooltip
                                label={`${trade.action} ${trade.quantity} @ ${trade.price} on ${trade.date}`}
                                withArrow
                              >
                                <Text
                                  size="xs"
                                  c="dimmed"
                                  style={{ cursor: "help", textDecoration: "underline dotted" }}
                                >
                                  {trade.date}
                                </Text>
                              </Tooltip>
                            ) : "—"}
                          </Table.Td>
                          <Table.Td c={ret?.["1d"] != null ? (ret["1d"]! >= 0 ? "teal" : "red") : "dimmed"}>
                            {fmtPct(ret?.["1d"])}
                          </Table.Td>
                          <Table.Td c={ret?.["7d"] != null ? (ret["7d"]! >= 0 ? "teal" : "red") : "dimmed"}>
                            {fmtPct(ret?.["7d"])}
                          </Table.Td>
                          <Table.Td c={ret?.["30d"] != null ? (ret["30d"]! >= 0 ? "teal" : "red") : "dimmed"}>
                            {fmtPct(ret?.["30d"])}
                          </Table.Td>
                          <Table.Td c={alpha?.["1d"] != null ? (alpha["1d"]! >= 0 ? "teal" : "red") : "dimmed"}>
                            {fmtPct(alpha?.["1d"])}
                          </Table.Td>
                          <Table.Td c={alpha?.["7d"] != null ? (alpha["7d"]! >= 0 ? "teal" : "red") : "dimmed"}>
                            {fmtPct(alpha?.["7d"])}
                          </Table.Td>
                        </Table.Tr>
                      );
                    })}
                  </Table.Tbody>
                </Table>
              </Table.ScrollContainer>
            )}
          </Paper>
        </>
      )}

      {!isLoading && !error && recs.length === 0 && (
        <Paper p="xl" withBorder radius="md">
          <Text c="dimmed" ta="center">No recommendations logged in the last {days} days.</Text>
        </Paper>
      )}
    </Stack>
  );
}
