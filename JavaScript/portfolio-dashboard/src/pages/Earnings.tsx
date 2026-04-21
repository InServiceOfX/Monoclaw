import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Alert, Badge, Group, Loader, NumberInput, Paper, Stack, Table, Text, Tooltip,
} from "@mantine/core";
import { api } from "../api";
import type { EarningsEvent, EarningsImpactResponse, EarningsPosition, EarningsUpcomingAlert } from "../api";
import { pct } from "../fmt";

const signalConfig: Record<string, { color: string; label: string }> = {
  strong_buy: { color: "teal", label: "STRONG BUY" },
  buy: { color: "green", label: "BUY" },
  neutral: { color: "gray", label: "NEUTRAL" },
  volatile: { color: "orange", label: "VOLATILE" },
  avoid: { color: "red", label: "AVOID" },
  insufficient_data: { color: "gray", label: "N/A" },
};

function SignalBadge({ classification }: { classification?: EarningsPosition["classification"] }) {
  if (!classification) return <Badge color="gray" variant="light" size="sm">—</Badge>;
  const cfg = signalConfig[classification.signal] ?? signalConfig.neutral;
  return (
    <Tooltip label={classification.reason}>
      <Badge
        color={cfg.color}
        variant={classification.signal === "avoid" ? "filled" : "light"}
        size="sm"
      >
        {cfg.label}
      </Badge>
    </Tooltip>
  );
}

function UpcomingAlerts({ alerts }: { alerts: EarningsUpcomingAlert[] }) {
  if (alerts.length === 0) return null;
  return (
    <Paper withBorder p="md" radius="md" style={{ borderColor: "var(--mantine-color-yellow-7)" }}>
      <Text fw={600} mb="sm" c="yellow.4">Upcoming Earnings (next 30 days)</Text>
      <Group gap="sm" wrap="wrap">
        {alerts.map(a => (
          <Paper key={a.symbol} withBorder p="sm" radius="sm" w={200}>
            <Text fw={700}>{a.symbol}</Text>
            <Text size="xs" c="dimmed" lineClamp={1}>{a.description}</Text>
            <Text size="sm" mt={4}>{a.date}</Text>
            <Text size="xs" c="dimmed">
              {a.days_until === 0 ? "Today!" : `${a.days_until} day${a.days_until === 1 ? "" : "s"} away`}
            </Text>
            {a.eps_estimate != null && (
              <Text size="xs" mt={2}>EPS est: {a.eps_estimate.toFixed(2)}</Text>
            )}
          </Paper>
        ))}
      </Group>
    </Paper>
  );
}

function HorizonCell({ stats, horizon }: { stats?: EarningsPosition["stats"]; horizon: string }) {
  if (!stats?.sufficient_data) return <Table.Td ta="center" c="dimmed">—</Table.Td>;
  const h = stats[horizon as keyof typeof stats] as { mean: number; win_rate_pct: number; std: number } | null | undefined;
  if (!h || typeof h !== "object" || !("mean" in h)) return <Table.Td ta="center" c="dimmed">—</Table.Td>;
  const color = h.mean >= 0 ? "teal.4" : "red.4";
  return (
    <Table.Td ta="right">
      <Tooltip label={`Win rate: ${h.win_rate_pct.toFixed(0)}% | Std: ${h.std.toFixed(1)}%`}>
        <Text span size="sm" c={color} fw={600}>{h.mean >= 0 ? "+" : ""}{h.mean.toFixed(1)}%</Text>
      </Tooltip>
      <Text size="xs" c="dimmed">{h.win_rate_pct.toFixed(0)}% win</Text>
    </Table.Td>
  );
}

function watchStatusBadge(e: EarningsEvent) {
  if (e.status === "upcoming") return <Badge color="teal" variant="light">upcoming</Badge>;
  if (e.status === "historical") return <Badge color="gray" variant="light">recent only</Badge>;
  if (e.status === "not_applicable") return <Badge color="gray" variant="outline">n/a</Badge>;
  if (e.status === "error") return <Badge color="red" variant="light">error</Badge>;
  return <Badge color="yellow" variant="light">missing</Badge>;
}

function watchStatusDetail(e: EarningsEvent) {
  if (e.status === "error" && e.error) return e.error.replace(/^`|`$/g, "");
  if (e.status === "not_applicable") return "Fund / ETF";
  if (e.status === "unavailable") return "No Yahoo earnings calendar";
  return "";
}

function EarningsWatch() {
  const earnings = useQuery({ queryKey: ["portfolio-earnings"], queryFn: () => api.earnings(25), staleTime: 6 * 60 * 60 * 1000 });
  const events = earnings.data?.events ?? [];

  return (
    <Paper withBorder p="md" radius="md">
      <Group justify="space-between" mb="sm">
        <Group gap="sm">
          <Text fw={600}>Earnings Watch</Text>
          {earnings.isLoading && <Loader size="xs" />}
        </Group>
        {earnings.data?.note && <Text size="xs" c="dimmed">{earnings.data.note}</Text>}
      </Group>
      {earnings.data?.error ? (
        <Alert color="red" title="Earnings unavailable" radius="md">{earnings.data.error}</Alert>
      ) : (
        <Table.ScrollContainer minWidth={920}>
          <Table striped highlightOnHover withColumnBorders verticalSpacing="xs" fz="sm">
            <Table.Thead>
              <Table.Tr>
                {["Symbol", "Name", "Status", "Next", "Previous", "EPS Est.", "Reported EPS", "Surprise", "Weight"].map(h => (
                  <Table.Th key={h} style={{ whiteSpace: "nowrap" }}>{h}</Table.Th>
                ))}
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {events.map(e => (
                <Table.Tr key={e.symbol}>
                  <Table.Td fw={700}>{e.symbol}</Table.Td>
                  <Table.Td style={{ maxWidth: 260, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{e.description}</Table.Td>
                  <Table.Td>
                    <Stack gap={2}>
                      {watchStatusBadge(e)}
                      {watchStatusDetail(e) && <Text size="xs" c="dimmed">{watchStatusDetail(e)}</Text>}
                    </Stack>
                  </Table.Td>
                  <Table.Td style={{ whiteSpace: "nowrap" }}>{e.next_earnings_date ?? "—"}</Table.Td>
                  <Table.Td style={{ whiteSpace: "nowrap" }}>{e.previous_earnings_date ?? "—"}</Table.Td>
                  <Table.Td ta="right">{e.eps_estimate ?? "—"}</Table.Td>
                  <Table.Td ta="right">{e.reported_eps ?? "—"}</Table.Td>
                  <Table.Td ta="right" c={(e.surprise_pct ?? 0) >= 0 ? "teal.4" : "red.4"}>{pct(e.surprise_pct)}</Table.Td>
                  <Table.Td ta="right">{pct(e.weight_pct)}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      )}
    </Paper>
  );
}

export default function Earnings() {
  const [maxPositions, setMaxPositions] = useState(25);

  const query = useQuery<EarningsImpactResponse>({
    queryKey: ["earnings-impact", maxPositions],
    queryFn: () => api.earningsImpact(maxPositions),
    staleTime: 30 * 60 * 1000,
  });

  const data = query.data;
  const positions = data?.positions ?? [];

  return (
    <Stack gap="md">
      <Group gap="sm" align="flex-end">
        <Text fw={600} size="lg">Earnings Impact Analysis</Text>
        {query.isFetching && <Loader size="xs" />}
        <NumberInput
          label="Positions"
          value={maxPositions}
          onChange={v => setMaxPositions(Number(v) || 25)}
          min={1} max={75} size="xs" w={100}
        />
      </Group>

      <Alert color="blue" variant="light" radius="md">
        Historical post-earnings price moves for your portfolio positions. Shows how each stock
        typically reacts at 1, 5, 15, and 30 trading days after reporting. Signals are base-rate
        summaries — not predictions.
      </Alert>

      {data?.error && <Alert color="red" title="Error" radius="md">{data.error}</Alert>}

      {/* Upcoming earnings alerts */}
      {data?.upcoming_alerts && <UpcomingAlerts alerts={data.upcoming_alerts} />}

      {/* Main analysis table */}
      <Paper withBorder p="md" radius="md">
        <Group justify="space-between" mb="sm">
          <Text fw={600}>Post-Earnings Price Impact</Text>
          <Text size="xs" c="dimmed">Hover cells for win rate & volatility</Text>
        </Group>
        <Table.ScrollContainer minWidth={1100}>
          <Table striped highlightOnHover withColumnBorders verticalSpacing="xs" fz="sm">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Symbol</Table.Th>
                <Table.Th>Description</Table.Th>
                <Table.Th style={{ whiteSpace: "nowrap" }}>
                  <Tooltip label="Next scheduled earnings report date"><span>Next Report</span></Tooltip>
                </Table.Th>
                <Table.Th style={{ whiteSpace: "nowrap" }}>
                  <Tooltip label="How often the company beats EPS estimates"><span>Beat Rate</span></Tooltip>
                </Table.Th>
                <Table.Th style={{ whiteSpace: "nowrap" }}>
                  <Tooltip label="Average EPS surprise percentage"><span>Avg Surprise</span></Tooltip>
                </Table.Th>
                <Table.Th style={{ whiteSpace: "nowrap" }}>
                  <Tooltip label="Average 1-day price change after earnings. Hover for win rate."><span>1d Move</span></Tooltip>
                </Table.Th>
                <Table.Th style={{ whiteSpace: "nowrap" }}>
                  <Tooltip label="Average 5-day price change after earnings"><span>5d Move</span></Tooltip>
                </Table.Th>
                <Table.Th style={{ whiteSpace: "nowrap" }}>
                  <Tooltip label="Average 15-day price change after earnings"><span>15d Move</span></Tooltip>
                </Table.Th>
                <Table.Th style={{ whiteSpace: "nowrap" }}>
                  <Tooltip label="Average 30-day price change after earnings"><span>30d Move</span></Tooltip>
                </Table.Th>
                <Table.Th style={{ whiteSpace: "nowrap" }}>
                  <Tooltip label="Historical earnings play signal based on win rates and average returns. STRONG BUY = 70%+ win rate & >3% avg gain at 30d. AVOID = <40% win rate or avg loss >3%.">
                    <span>Signal</span>
                  </Tooltip>
                </Table.Th>
                <Table.Th style={{ whiteSpace: "nowrap" }}>
                  <Tooltip label="Number of past earnings events analyzed"><span>Events</span></Tooltip>
                </Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {positions.map(p => {
                const nextDate = p.next_earnings_date;
                const daysUntil = p.days_until_earnings;
                const isImminent = daysUntil != null && daysUntil <= 14;

                return (
                  <Table.Tr key={p.symbol} bg={isImminent ? "rgba(255, 200, 0, 0.04)" : undefined}>
                    <Table.Td fw={700}>{p.symbol}</Table.Td>
                    <Table.Td maw={180} style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {p.description}
                    </Table.Td>
                    <Table.Td style={{ whiteSpace: "nowrap" }}>
                      {nextDate ? (
                        <Group gap={4}>
                          <Text size="sm">{nextDate}</Text>
                          {daysUntil != null && daysUntil <= 30 && (
                            <Badge
                              color={daysUntil <= 7 ? "red" : daysUntil <= 14 ? "yellow" : "blue"}
                              variant="light" size="xs"
                            >
                              {daysUntil}d
                            </Badge>
                          )}
                        </Group>
                      ) : (
                        <Text size="sm" c="dimmed">—</Text>
                      )}
                    </Table.Td>
                    <Table.Td ta="right">
                      {p.stats?.beat_rate_pct != null
                        ? <Text size="sm" c={p.stats.beat_rate_pct >= 70 ? "teal.4" : p.stats.beat_rate_pct < 50 ? "red.4" : undefined}>{p.stats.beat_rate_pct.toFixed(0)}%</Text>
                        : <Text size="sm" c="dimmed">—</Text>
                      }
                    </Table.Td>
                    <Table.Td ta="right">
                      {p.stats?.avg_surprise_pct != null
                        ? <Text size="sm" c={p.stats.avg_surprise_pct >= 0 ? "teal.4" : "red.4"}>{p.stats.avg_surprise_pct >= 0 ? "+" : ""}{p.stats.avg_surprise_pct.toFixed(1)}%</Text>
                        : <Text size="sm" c="dimmed">—</Text>
                      }
                    </Table.Td>
                    <HorizonCell stats={p.stats} horizon="1d" />
                    <HorizonCell stats={p.stats} horizon="5d" />
                    <HorizonCell stats={p.stats} horizon="15d" />
                    <HorizonCell stats={p.stats} horizon="30d" />
                    <Table.Td ta="center">
                      <SignalBadge classification={p.classification} />
                    </Table.Td>
                    <Table.Td ta="center" c="dimmed">
                      {p.stats?.event_count ?? "—"}
                    </Table.Td>
                  </Table.Tr>
                );
              })}
              {positions.length === 0 && !query.isFetching && (
                <Table.Tr>
                  <Table.Td colSpan={11}>
                    <Text size="sm" c="dimmed" ta="center" py="md">No positions to analyze.</Text>
                  </Table.Td>
                </Table.Tr>
              )}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      </Paper>

      {data?.note && <Text size="xs" c="dimmed">{data.note}</Text>}

      <EarningsWatch />
    </Stack>
  );
}
