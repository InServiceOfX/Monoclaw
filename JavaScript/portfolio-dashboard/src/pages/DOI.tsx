import { useQuery } from "@tanstack/react-query";
import {
  Alert,
  Badge,
  Group,
  Loader,
  Paper,
  ScrollArea,
  SimpleGrid,
  Stack,
  Table,
  Text,
  Tooltip,
} from "@mantine/core";
import { api } from "../api";
import type { DOIIndexInfo, DOISnapshot, DOITicker } from "../api";
import { usd } from "../fmt";

function fmtSigned(v: number | null | undefined, decimals = 2) {
  if (v == null) return "—";
  return `${v >= 0 ? "+" : ""}${v.toFixed(decimals)}`;
}

function fmtPct01(v: number | null | undefined, decimals = 1) {
  if (v == null) return "—";
  return `${(v * 100).toFixed(decimals)}%`;
}

function avg(values: Array<number | null | undefined>) {
  const present = values.filter((v): v is number => v != null);
  if (present.length === 0) return null;
  return present.reduce((sum, value) => sum + value, 0) / present.length;
}

function doiColor(value: number | null | undefined, cashWarning = false) {
  if (cashWarning) return "yellow.4";
  if (value == null) return "gray.5";
  if (value > 0.2) return "teal.4";
  if (value < -0.2) return "red.4";
  return "gray.3";
}

function doiCellColor(value: number | null | undefined) {
  if (value == null) return "gray.5";
  if (value > 0.2) return "teal.4";
  if (value < -0.2) return "red.4";
  return "gray.3";
}

function cashColor(cashPct: number | null | undefined) {
  if (cashPct == null) return "gray.3";
  if (cashPct < 0.05) return "yellow.4";
  if (cashPct <= 0.3) return "teal.4";
  return "gray.3";
}

function regimeColor(regime: number | null | undefined) {
  if (regime == null) return "gray.3";
  if (regime < -0.3) return "teal.4";
  if (regime > 0.3) return "red.4";
  return "gray.3";
}

function topProbColor(prob: number | null | undefined) {
  if (prob == null) return "gray.3";
  if (prob > 0.7) return "red.4";
  if (prob >= 0.5) return "yellow.4";
  return "teal.4";
}

function actionLabel(snapshot: DOISnapshot) {
  if (snapshot.cash_deficit_warning) return "🚨 Cash deficit";
  if (snapshot.portfolio_doi > 0.2) return "Deploy bias";
  if (snapshot.portfolio_doi < -0.2) return "Trim bias";
  return "Hold";
}

function drawdownPct(ticker: DOITicker) {
  if (ticker.current_price == null || ticker.high_52w == null || ticker.high_52w === 0) return null;
  return (ticker.high_52w - ticker.current_price) / ticker.high_52w;
}

function actionColor(action: DOITicker["action"]) {
  switch (action) {
    case "deploy":
      return "green";
    case "trim":
      return "red";
    case "hold":
      return "gray";
    default:
      return "dark";
  }
}

function actionCounts(tickers: DOITicker[]) {
  return tickers.reduce(
    (acc, ticker) => {
      acc[ticker.action] += 1;
      return acc;
    },
    { deploy: 0, hold: 0, trim: 0, data_missing: 0 } as Record<DOITicker["action"], number>,
  );
}

function indexInterpretation(info: DOIIndexInfo) {
  if ((info.local_top_prob ?? 0) > 0.7 || (info.regime_score ?? 0) > 0.3) return "Near top - trim window";
  if ((info.regime_score ?? 0) < -0.3) return "Modest dip - buyable";
  return "Neutral";
}

function StatCard({
  title,
  value,
  subtitle,
  color,
}: {
  title: string;
  value: string;
  subtitle: string;
  color: string;
}) {
  return (
    <Paper withBorder p="md" radius="md">
      <Text size="xs" c="dimmed" tt="uppercase" fw={600} lts={0.5}>{title}</Text>
      <Text size="xl" fw={700} c={color}>{value}</Text>
      <Text size="xs" c="dimmed" mt={4}>{subtitle}</Text>
    </Paper>
  );
}

function HeaderStrip({ data }: { data: DOISnapshot }) {
  const regimeAvg = avg([
    data.indices.SPX?.regime_score,
    data.indices.QQQ?.regime_score,
    data.indices.DJI?.regime_score,
  ]);
  const topProbEntries = Object.entries(data.indices).map(([symbol, info]) => ({
    symbol,
    prob: info.local_top_prob,
  }));
  const topProb = topProbEntries.reduce<{ symbol: string; prob: number | null } | null>((best, entry) => {
    if (entry.prob == null) return best;
    if (best == null || (best.prob ?? -Infinity) < entry.prob) return entry;
    return best;
  }, null);

  return (
    <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} spacing="sm">
      <StatCard
        title="Portfolio DOI"
        value={fmtSigned(data.portfolio_doi)}
        subtitle={actionLabel(data)}
        color={doiColor(data.portfolio_doi, data.cash_deficit_warning)}
      />
      <StatCard
        title="Cash %"
        value={fmtPct01(data.cash_pct)}
        subtitle="of account value"
        color={cashColor(data.cash_pct)}
      />
      <StatCard
        title="Index Regime"
        value={fmtSigned(regimeAvg)}
        subtitle={`SPX ${fmtSigned(data.indices.SPX?.regime_score)}, QQQ ${fmtSigned(data.indices.QQQ?.regime_score)}, DJI ${fmtSigned(data.indices.DJI?.regime_score)}`}
        color={regimeColor(regimeAvg)}
      />
      <StatCard
        title="Local Top Probability"
        value={topProb ? `${topProb.symbol} ${fmtPct01(topProb.prob)}` : "—"}
        subtitle="highest across SPX / QQQ / DJI"
        color={topProbColor(topProb?.prob)}
      />
    </SimpleGrid>
  );
}

function IndicesPanel({ indices }: { indices: DOISnapshot["indices"] }) {
  const rows = Object.entries(indices) as Array<[keyof DOISnapshot["indices"], DOIIndexInfo]>;
  return (
    <Paper withBorder p="md" radius="md">
      <Text fw={600} mb="sm">Index Regime & Top Probability</Text>
      <Table striped withTableBorder>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Index</Table.Th>
            <Table.Th>Regime Score</Table.Th>
            <Table.Th>Local Top Prob</Table.Th>
            <Table.Th>Interpretation</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {rows.map(([symbol, info]) => (
            <Table.Tr key={symbol}>
              <Table.Td fw={700} style={{ fontFamily: "monospace" }}>{symbol}</Table.Td>
              <Table.Td c={regimeColor(info.regime_score)}>{fmtSigned(info.regime_score)}</Table.Td>
              <Table.Td c={topProbColor(info.local_top_prob)}>{fmtPct01(info.local_top_prob)}</Table.Td>
              <Table.Td c="dimmed">{indexInterpretation(info)}</Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Paper>
  );
}

function DOIHeaderCounts({ tickers }: { tickers: DOITicker[] }) {
  const counts = actionCounts(tickers);
  return (
    <Group gap="xs">
      <Badge color="green" variant="light">{counts.deploy} deploy</Badge>
      <Badge color="gray" variant="light">{counts.hold} hold</Badge>
      <Badge color="red" variant="light">{counts.trim} trim</Badge>
      {counts.data_missing > 0 && (
        <Badge color="dark" variant="light">{counts.data_missing} data missing</Badge>
      )}
    </Group>
  );
}

function DOITable({ tickers }: { tickers: DOITicker[] }) {
  const sorted = [...tickers].sort((a, b) => (b.doi ?? -Infinity) - (a.doi ?? -Infinity));
  return (
    <Paper withBorder p="md" radius="md">
      <Group justify="space-between" mb="sm">
        <Text fw={600}>Ticker Breakdown</Text>
        <DOIHeaderCounts tickers={tickers} />
      </Group>
      <ScrollArea mah={480}>
        <Table striped withTableBorder>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Symbol</Table.Th>
              <Table.Th>Action</Table.Th>
              <Table.Th>
                <Tooltip label="DOI = w1·drawdown + w2·index_regime + w3·cash_avail + w4·conviction − w5·momentum − w6·breadth">
                  <span style={{ cursor: "help", borderBottom: "1px dashed" }}>DOI Score</span>
                </Tooltip>
              </Table.Th>
              <Table.Th>Drawdown</Table.Th>
              <Table.Th>Conviction</Table.Th>
              <Table.Th>
                <Tooltip label="Momentum exhaustion approximates overbought pressure. Higher values mean less attractive entry timing.">
                  <span style={{ cursor: "help", borderBottom: "1px dashed" }}>Momentum</span>
                </Tooltip>
              </Table.Th>
              <Table.Th>Suggested Size</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {sorted.map((ticker) => {
              const drawdown = drawdownPct(ticker);
              const missing = ticker.doi == null;
              return (
                <Table.Tr key={ticker.symbol} style={missing ? { opacity: 0.65 } : undefined}>
                  <Table.Td fw={700} style={{ fontFamily: "monospace" }}>{ticker.symbol}</Table.Td>
                  <Table.Td>
                    <Badge color={actionColor(ticker.action)} variant="light" style={ticker.action === "data_missing" ? { opacity: 0.7 } : undefined}>
                      {ticker.action}
                    </Badge>
                  </Table.Td>
                  <Table.Td c={missing ? "dimmed" : doiCellColor(ticker.doi)} fw={600}>
                    {missing ? "—" : fmtSigned(ticker.doi)}
                  </Table.Td>
                  <Table.Td c={!missing && drawdown != null && drawdown > 0.15 ? "red.4" : undefined}>
                    {missing ? "—" : fmtPct01(drawdown)}
                  </Table.Td>
                  <Table.Td>{missing ? "—" : fmtPct01(ticker.conviction_score)}</Table.Td>
                  <Table.Td>{missing ? "—" : fmtPct01(ticker.momentum_exhaustion)}</Table.Td>
                  <Table.Td>{missing || !ticker.size_hint_dollars ? "—" : usd(ticker.size_hint_dollars, 0)}</Table.Td>
                </Table.Tr>
              );
            })}
          </Table.Tbody>
        </Table>
      </ScrollArea>
    </Paper>
  );
}

function WeightsFooter({ weights }: { weights: DOISnapshot["weights"] }) {
  return (
    <Paper withBorder p="sm" radius="md">
      <Group gap={4} wrap="wrap">
        <Text size="xs" c="dimmed" style={{ fontFamily: "monospace" }}>
          w1 (drawdown) {weights.w1.toFixed(2)} · w2 (regime) {weights.w2.toFixed(2)} · w3 (cash) {weights.w3.toFixed(2)} · w4 (conviction) {weights.w4.toFixed(2)} · w5 (momentum) {weights.w5.toFixed(2)} · w6 (breadth) {weights.w6.toFixed(2)}
        </Text>
      </Group>
    </Paper>
  );
}

export default function DOI() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["doi-snapshot"],
    queryFn: () => api.doi(),
    staleTime: 60_000,
  });

  if (isLoading) {
    return (
      <Stack gap="md" align="center" py="xl">
        <Loader />
        <Text c="dimmed" size="sm">Loading DOI snapshot...</Text>
      </Stack>
    );
  }

  if (error || !data) {
    return (
      <Alert color="red" title="DOI unavailable">
        Failed to load `/doi/snapshot`. Check that the finance API is running.
      </Alert>
    );
  }

  return (
    <Stack gap="md">
      <Group justify="space-between" align="flex-start">
        <Text fw={700} size="lg">Deployment Opportunity Index</Text>
        <Text size="xs" c="dimmed">as of {data.as_of}</Text>
      </Group>

      <HeaderStrip data={data} />

      {data.cash_deficit_warning && (
        <Alert color="yellow" title="Cash Deficit Warning" icon={<span>⚠</span>}>
          Deploy signals exist but cash is below 5% of account. Consider trimming overextended names to raise dry powder.
        </Alert>
      )}

      <IndicesPanel indices={data.indices} />
      <DOITable tickers={data.tickers} />
      <WeightsFooter weights={data.weights} />
    </Stack>
  );
}
