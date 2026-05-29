import { useQuery } from "@tanstack/react-query";
import { Alert, Badge, Card, Group, Progress, SimpleGrid, Stack, Table, Text, Title } from "@mantine/core";
import { api, type GradedSell, type GradingSummary } from "../api";

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

  const summary = summaryQuery.data;
  const graded = gradedQuery.data;
  const topBottom = topBottomQuery.data;
  const bySymbol = bySymbolQuery.data;
  const sells = graded?.graded_sells ?? [];
  const bestSells = topBottom?.best_sells ?? [];
  const worstSells = topBottom?.worst_sells ?? [];
  const symbolStats = bySymbol?.by_symbol ?? [];
  const isLoading =
    summaryQuery.isLoading || gradedQuery.isLoading || topBottomQuery.isLoading || bySymbolQuery.isLoading;
  const errors = [summaryQuery.error, gradedQuery.error, topBottomQuery.error, bySymbolQuery.error].filter(Boolean);

  return (
    <>
      <Title order={3} mb="md">Trade Quality</Title>

      {isLoading && <Progress mb="md" value={100} animated />}

      {errors.length > 0 && (
        <Alert color="red" mb="md">
          Trade quality data failed to load. Check that the local backend is running.
        </Alert>
      )}

      {summary?.error && (
        <Alert color="yellow" mb="md">
          {summary.error}
        </Alert>
      )}

      <SimpleGrid cols={4} mb="xl">
        <Card withBorder>
          <Text size="sm" c="dimmed">Trader Score</Text>
          <Title order={2} c={summary?.trader_score == null ? undefined : summary.trader_score > 0 ? "teal" : "red"}>
            {summary?.trader_score ?? "—"}
          </Title>
          <Text size="xs" c="dimmed">Median sell quality</Text>
        </Card>

        <Card withBorder>
          <Text size="sm" c="dimmed">Avg Quality Score</Text>
          <Title order={2}>{summary?.avg_quality_score ?? "—"}</Title>
        </Card>

        <Card withBorder>
          <Text size="sm" c="dimmed">Sells Scored</Text>
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
          <Text size="sm" c="dimmed">Sold Near Local Peak</Text>
          <Group>
            <Title order={2}>{summary ? summary.sells_near_local_peak : "—"}</Title>
            <Badge color="orange" variant="light">
              {summary ? `${summary.pct_near_peak}%` : ""}
            </Badge>
          </Group>
        </Card>
      </SimpleGrid>

      <Title order={4} mb="sm">Mature Graded Sells</Title>
      <Table striped highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Date</Table.Th>
            <Table.Th>Symbol</Table.Th>
            <Table.Th>Quality Score</Table.Th>
            <Table.Th>MFE %</Table.Th>
            <Table.Th>Max Drawdown</Table.Th>
            <Table.Th>Near Peak?</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {sells.length === 0 && (
            <Table.Tr>
              <Table.Td colSpan={6} c="dimmed" ta="center">No graded sells yet</Table.Td>
            </Table.Tr>
          )}
          {sells.map((s, i) => (
            <Table.Tr key={i}>
              <Table.Td>{s.date}</Table.Td>
              <Table.Td fw={500}>{s.symbol}</Table.Td>
              <Table.Td c={s.quality_score > 10 ? "teal" : s.quality_score < -10 ? "red" : undefined}>
                {s.quality_score}
                {s.provisional && <Badge ml="xs" color="gray" size="xs">Provisional</Badge>}
              </Table.Td>
              <Table.Td>{s.mfe_pct ?? "—"}</Table.Td>
              <Table.Td c="red">{s.max_drawdown_pct ?? "—"}</Table.Td>
              <Table.Td>
                {s.near_local_peak ? <Badge color="orange" size="sm">Yes</Badge> : "No"}
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
                    {s.sold_too_early && <Badge color="red" size="xs">Sold too early</Badge>}
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
                <Table.Th>Flag</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {worstSells.map((s: any, i: number) => (
                <Table.Tr key={i}>
                  <Table.Td>{s.date}</Table.Td>
                  <Table.Td fw={500}>{s.symbol}</Table.Td>
                  <Table.Td c="red">{s.quality_score}</Table.Td>
                  <Table.Td>
                    {s.sold_too_early && <Badge color="red" size="xs">Sold too early</Badge>}
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Stack>
      </SimpleGrid>

      <Title order={4} mt="xl" mb="sm">Timing Quality by Symbol</Title>
      <Table striped highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Symbol</Table.Th>
            <Table.Th>Sells</Table.Th>
            <Table.Th>Avg Quality</Table.Th>
            <Table.Th>% Near Peak</Table.Th>
            <Table.Th>Avg MFE</Table.Th>
            <Table.Th>Edge</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {symbolStats.length === 0 && (
            <Table.Tr>
              <Table.Td colSpan={6} c="dimmed" ta="center">Not enough data yet</Table.Td>
            </Table.Tr>
          )}
          {symbolStats.map((s: any, i: number) => (
            <Table.Tr key={i}>
              <Table.Td fw={600}>{s.symbol}</Table.Td>
              <Table.Td>{s.sells}</Table.Td>
              <Table.Td c={s.avg_quality_score > 10 ? "teal" : s.avg_quality_score < -5 ? "red" : undefined}>
                {s.avg_quality_score}
              </Table.Td>
              <Table.Td>{s.pct_near_peak}%</Table.Td>
              <Table.Td>{s.avg_mfe_after_sell}</Table.Td>
              <Table.Td>
                <Badge color={s.edge === "Strong" ? "teal" : s.edge === "Weak" ? "red" : "gray"}>
                  {s.edge}
                </Badge>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </>
  );
}
