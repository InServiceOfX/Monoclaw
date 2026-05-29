import { useQuery } from "@tanstack/react-query";
import { Card, Group, SimpleGrid, Table, Text, Title, Badge, Stack } from "@mantine/core";
import { api } from "../api";

interface GradingSummary {
  trader_score: number;
  avg_quality_score: number;
  total_sells_scored: number;
  sells_near_local_peak: number;
  pct_near_peak: number;
}

interface GradedSell {
  date: string;
  symbol: string;
  quality_score: number;
  mfe_pct: number | null;
  max_drawdown_pct: number | null;
  near_local_peak: boolean;
}

export default function TradeQuality() {
  const { data: summary } = useQuery<GradingSummary>({
    queryKey: ["grading-summary"],
    queryFn: () => api("/grading/summary"),
  });

  const { data: graded } = useQuery<{ graded_sells: GradedSell[] }>({
    queryKey: ["transactions-grading"],
    queryFn: () => api("/transactions/grading?limit=30"),
  });

  const { data: topBottom } = useQuery<any>({
    queryKey: ["grading-top-bottom"],
    queryFn: () => api("/grading/top-bottom?limit=5"),
  });

  const sells = graded?.graded_sells ?? [];
  const bestSells = topBottom?.best_sells ?? [];
  const worstSells = topBottom?.worst_sells ?? [];

  return (
    <>
      <Title order={3} mb="md">Trade Quality</Title>

      <SimpleGrid cols={4} mb="xl">
        <Card withBorder>
          <Text size="sm" c="dimmed">Trader Score</Text>
          <Title order={2} c={summary && summary.trader_score > 0 ? "teal" : "red"}>
            {summary ? summary.trader_score : "—"}
          </Title>
          <Text size="xs" c="dimmed">Median sell quality</Text>
        </Card>

        <Card withBorder>
          <Text size="sm" c="dimmed">Avg Quality Score</Text>
          <Title order={2}>{summary ? summary.avg_quality_score : "—"}</Title>
        </Card>

        <Card withBorder>
          <Text size="sm" c="dimmed">Sells Scored</Text>
          <Title order={2}>{summary ? summary.total_sells_scored : "—"}</Title>
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

      <Title order={4} mb="sm">Recent Graded Sells</Title>
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
    </>
  );
}
