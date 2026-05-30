import { useQuery } from "@tanstack/react-query";
import {
  Alert,
  Badge,
  Card,
  Group,
  Progress,
  SimpleGrid,
  Stack,
  Table,
  Text,
  ThemeIcon,
  Title,
  Tooltip,
} from "@mantine/core";
import {
  api,
  type GradedSell,
  type GradingPatternsResponse,
  type GradingSummary,
} from "../api";

const METRIC_TIPS: Record<string, string> = {
  trader_score:
    "Median quality score across all graded sells. Range: -100 (always sell too early) to +100 (perfect timing). Above 0 = net positive timing.",
  avg_quality:
    "Mean quality score — more affected by outliers than the median Trader Score. Large gap between median and mean signals a few very bad (or very good) sells.",
  quality_score:
    "Per-sell composite: (avoided drop x1.2) - (missed gain x0.9) + (realized profit x0.5) - volatility penalty. Positive = sold at a good time.",
  mfe: "Maximum Favorable Excursion — how much the stock rallied in the 30 days after you sold. High MFE = you left money on the table.",
  max_drawdown:
    "Deepest % the stock fell below your sell price in 30 days. Negative = stock dropped (your sell was validated). Positive = it never dipped.",
  near_peak:
    "Whether the sell happened within 3 trading days of a local price peak (rolling 20-day window, 8% prominence).",
  edge: "Strong (avg quality > 15): great timing. Neutral (-5 to 15): average. Weak (< -5): consistently leaving money on the table.",
  sold_too_early:
    "Flagged when MFE exceeds 15% — the stock rallied significantly after the sell.",
};

function Tip({
  label,
  tip,
  children,
}: {
  label?: string;
  tip: string;
  children?: React.ReactNode;
}) {
  return (
    <Tooltip label={tip} multiline w={300} withArrow>
      <Text
        size="sm"
        c="dimmed"
        style={{ cursor: "help", textDecoration: "underline dotted" }}
        component="span"
      >
        {children ?? label}
      </Text>
    </Tooltip>
  );
}

function TipTh({ children, tip }: { children: React.ReactNode; tip: string }) {
  return (
    <Table.Th>
      <Tooltip label={tip} multiline w={280} withArrow>
        <Text
          size="sm"
          fw={600}
          style={{ cursor: "help", textDecoration: "underline dotted" }}
          component="span"
        >
          {children}
        </Text>
      </Tooltip>
    </Table.Th>
  );
}

function severityColor(severity: string) {
  if (severity === "high") return "red";
  if (severity === "medium") return "orange";
  if (severity === "low") return "yellow";
  return "teal";
}

function patternIcon(type: string) {
  if (type === "sells_too_early") return "!";
  if (type === "good_timing") return "✓";
  return "≈";
}

export default function TradeQuality() {
  const summaryQuery = useQuery<GradingSummary>({
    queryKey: ["grading-summary"],
    queryFn: () => api.gradingSummary(),
  });

  const gradedQuery = useQuery<{ graded_sells: GradedSell[] }>({
    queryKey: ["transactions-grading"],
    queryFn: () => api.gradingTransactions(30),
  });

  const topBottomQuery = useQuery<any>({
    queryKey: ["grading-top-bottom"],
    queryFn: () => api.gradingTopBottom(5),
  });

  const bySymbolQuery = useQuery<any>({
    queryKey: ["grading-by-symbol"],
    queryFn: () => api.gradingBySymbol(),
  });

  const patternsQuery = useQuery<GradingPatternsResponse>({
    queryKey: ["grading-patterns"],
    queryFn: () => api.gradingPatterns(),
  });

  const summary = summaryQuery.data;
  const graded = gradedQuery.data;
  const topBottom = topBottomQuery.data;
  const bySymbol = bySymbolQuery.data;
  const patterns = patternsQuery.data;
  const sells = graded?.graded_sells ?? [];
  const bestSells = topBottom?.best_sells ?? [];
  const worstSells = topBottom?.worst_sells ?? [];
  const symbolStats = bySymbol?.by_symbol ?? [];
  const isLoading =
    summaryQuery.isLoading ||
    gradedQuery.isLoading ||
    topBottomQuery.isLoading ||
    bySymbolQuery.isLoading;
  const errors = [
    summaryQuery.error,
    gradedQuery.error,
    topBottomQuery.error,
    bySymbolQuery.error,
  ].filter(Boolean);

  return (
    <>
      <Title order={3} mb="md">
        Trade Quality
      </Title>

      {isLoading && <Progress mb="md" value={100} animated />}

      {errors.length > 0 && (
        <Alert color="red" mb="md">
          Trade quality data failed to load. Check that the local backend is
          running.
        </Alert>
      )}

      {summary?.error && (
        <Alert color="yellow" mb="md">
          {summary.error}
        </Alert>
      )}

      <SimpleGrid cols={4} mb="xl">
        <Card withBorder>
          <Tip tip={METRIC_TIPS.trader_score}>Trader Score</Tip>
          <Title
            order={2}
            c={
              summary?.trader_score == null
                ? undefined
                : summary.trader_score > 0
                  ? "teal"
                  : "red"
            }
          >
            {summary?.trader_score ?? "—"}
          </Title>
          <Text size="xs" c="dimmed">
            Median sell quality
          </Text>
        </Card>

        <Card withBorder>
          <Tip tip={METRIC_TIPS.avg_quality}>Avg Quality Score</Tip>
          <Title order={2}>{summary?.avg_quality_score ?? "—"}</Title>
        </Card>

        <Card withBorder>
          <Text size="sm" c="dimmed">
            Sells Scored
          </Text>
          <Title order={2}>{summary?.total_sells_scored ?? "—"}</Title>
          {summary?.candidates_scanned != null && (
            <Text size="xs" c="dimmed">
              {summary.candidates_scanned} mature candidates scanned
            </Text>
          )}
          {summary?.provisional_skipped ? (
            <Text size="xs" c="dimmed">
              {summary.provisional_skipped} recent provisional skipped
            </Text>
          ) : null}
        </Card>

        <Card withBorder>
          <Tip tip={METRIC_TIPS.near_peak}>Sold Near Local Peak</Tip>
          <Group>
            <Title order={2}>
              {summary ? summary.sells_near_local_peak : "—"}
            </Title>
            <Badge color="orange" variant="light">
              {summary ? `${summary.pct_near_peak}%` : ""}
            </Badge>
          </Group>
        </Card>
      </SimpleGrid>

      <Title order={4} mb="sm">
        Mature Graded Sells
      </Title>
      <Table striped highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Date</Table.Th>
            <Table.Th>Symbol</Table.Th>
            <TipTh tip={METRIC_TIPS.quality_score}>Quality Score</TipTh>
            <TipTh tip={METRIC_TIPS.mfe}>MFE %</TipTh>
            <TipTh tip={METRIC_TIPS.max_drawdown}>Max Drawdown</TipTh>
            <TipTh tip={METRIC_TIPS.near_peak}>Near Peak?</TipTh>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {sells.length === 0 && (
            <Table.Tr>
              <Table.Td colSpan={6} c="dimmed" ta="center">
                No graded sells yet
              </Table.Td>
            </Table.Tr>
          )}
          {sells.map((s, i) => (
            <Table.Tr key={i}>
              <Table.Td>{s.date}</Table.Td>
              <Table.Td fw={500}>{s.symbol}</Table.Td>
              <Table.Td
                c={
                  s.quality_score > 10
                    ? "teal"
                    : s.quality_score < -10
                      ? "red"
                      : undefined
                }
              >
                {s.quality_score}
                {s.provisional && (
                  <Badge ml="xs" color="gray" size="xs">
                    Provisional
                  </Badge>
                )}
              </Table.Td>
              <Table.Td>{s.mfe_pct ?? "—"}</Table.Td>
              <Table.Td c="red">{s.max_drawdown_pct ?? "—"}</Table.Td>
              <Table.Td>
                {s.near_local_peak ? (
                  <Badge color="orange" size="sm">
                    Yes
                  </Badge>
                ) : (
                  "No"
                )}
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>

      <SimpleGrid cols={2} mt="xl">
        <Stack>
          <Title order={4}>Best Timed Sells</Title>
          <Table striped>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Date</Table.Th>
                <Table.Th>Symbol</Table.Th>
                <Table.Th>Score</Table.Th>
                <Table.Th>Flag</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {bestSells.map((s: any, i: number) => (
                <Table.Tr key={i}>
                  <Table.Td>{s.date}</Table.Td>
                  <Table.Td fw={500}>{s.symbol}</Table.Td>
                  <Table.Td c="teal">{s.quality_score}</Table.Td>
                  <Table.Td>
                    {s.sold_too_early && (
                      <Badge color="red" size="xs">
                        Sold too early
                      </Badge>
                    )}
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Stack>

        <Stack>
          <Title order={4}>Worst Timed Sells</Title>
          <Table striped>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Date</Table.Th>
                <Table.Th>Symbol</Table.Th>
                <Table.Th>Score</Table.Th>
                <TipTh tip={METRIC_TIPS.sold_too_early}>Flag</TipTh>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {worstSells.map((s: any, i: number) => (
                <Table.Tr key={i}>
                  <Table.Td>{s.date}</Table.Td>
                  <Table.Td fw={500}>{s.symbol}</Table.Td>
                  <Table.Td c="red">{s.quality_score}</Table.Td>
                  <Table.Td>
                    {s.sold_too_early && (
                      <Badge color="red" size="xs">
                        SOLD TOO EARLY
                      </Badge>
                    )}
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Stack>
      </SimpleGrid>

      <Title order={4} mt="xl" mb="sm">
        Timing Quality by Symbol
      </Title>
      <Table striped highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Symbol</Table.Th>
            <Table.Th>Sells</Table.Th>
            <TipTh tip={METRIC_TIPS.quality_score}>Avg Quality</TipTh>
            <TipTh tip={METRIC_TIPS.near_peak}>% Near Peak</TipTh>
            <TipTh tip={METRIC_TIPS.mfe}>Avg MFE</TipTh>
            <TipTh tip={METRIC_TIPS.edge}>Edge</TipTh>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {symbolStats.length === 0 && (
            <Table.Tr>
              <Table.Td colSpan={6} c="dimmed" ta="center">
                Not enough data yet
              </Table.Td>
            </Table.Tr>
          )}
          {symbolStats.map((s: any, i: number) => (
            <Table.Tr key={i}>
              <Table.Td fw={600}>{s.symbol}</Table.Td>
              <Table.Td>{s.sells}</Table.Td>
              <Table.Td
                c={
                  s.avg_quality_score > 10
                    ? "teal"
                    : s.avg_quality_score < -5
                      ? "red"
                      : undefined
                }
              >
                {s.avg_quality_score}
              </Table.Td>
              <Table.Td>{s.pct_near_peak}%</Table.Td>
              <Table.Td>{s.avg_mfe_after_sell}</Table.Td>
              <Table.Td>
                <Badge
                  color={
                    s.edge === "Strong"
                      ? "teal"
                      : s.edge === "Weak"
                        ? "red"
                        : "gray"
                  }
                >
                  {s.edge}
                </Badge>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>

      <Title order={4} mt="xl" mb="sm">
        Patterns & Corrections
      </Title>

      {patternsQuery.isLoading && <Progress value={100} animated mb="md" />}
      {patternsQuery.error && (
        <Text size="sm" c="red" mb="md">
          Could not load patterns.
        </Text>
      )}

      {patterns && (
        <Stack gap="md">
          {patterns.summary.early_sell_still_held.length > 0 && (
            <Alert color="orange" variant="light">
              <Text fw={600} size="sm" mb={4}>
                Active positions you tend to sell too early:{" "}
                {patterns.summary.early_sell_still_held.join(", ")}
              </Text>
              <Text size="sm">{patterns.summary.top_correction}</Text>
            </Alert>
          )}

          {patterns.patterns.length === 0 && (
            <Text size="sm" c="dimmed">
              Not enough graded sells to detect patterns yet.
            </Text>
          )}

          <SimpleGrid cols={{ base: 1, md: 2 }} spacing="sm">
            {patterns.patterns.map((p) => (
              <Card
                key={p.symbol}
                withBorder
                padding="sm"
                radius="md"
                style={{
                  borderLeft: `4px solid var(--mantine-color-${severityColor(p.severity)}-6)`,
                }}
              >
                <Group justify="space-between" mb={4}>
                  <Group gap="xs">
                    <ThemeIcon
                      size="sm"
                      variant="light"
                      color={severityColor(p.severity)}
                      radius="xl"
                    >
                      <Text size="xs" fw={700}>
                        {patternIcon(p.type)}
                      </Text>
                    </ThemeIcon>
                    <Text fw={600} size="sm">
                      {p.symbol}
                    </Text>
                    {p.still_held && (
                      <Badge size="xs" variant="dot" color="blue">
                        Still held
                      </Badge>
                    )}
                  </Group>
                  <Group gap={4}>
                    <Text size="xs" c="dimmed">
                      {p.sells} sells
                    </Text>
                    <Badge
                      size="xs"
                      variant="light"
                      color={severityColor(p.severity)}
                    >
                      avg {p.avg_quality > 0 ? "+" : ""}
                      {p.avg_quality}
                    </Badge>
                  </Group>
                </Group>
                <Text size="sm" c="dimmed">
                  {p.message}
                </Text>
                <Text size="sm" fw={500} mt={4}>
                  {p.correction}
                </Text>
              </Card>
            ))}
          </SimpleGrid>
        </Stack>
      )}
    </>
  );
}
