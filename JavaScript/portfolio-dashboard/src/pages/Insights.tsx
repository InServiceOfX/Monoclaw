import { useQuery } from "@tanstack/react-query";
import {
  Alert, Group, Loader, Paper, SimpleGrid, Stack, Table, Text,
} from "@mantine/core";
import { api } from "../api";
import { pct, usd } from "../fmt";

function severityColor(severity: string) {
  if (severity === "high") return "red";
  if (severity === "medium") return "yellow";
  return "blue";
}

export default function Insights() {
  const context = useQuery({ queryKey: ["portfolio-context"], queryFn: api.context });
  const c = context.data;

  return (
    <Stack gap="md">
      <Group gap="sm">
        <Text fw={600} size="lg">Portfolio Context</Text>
        {context.isLoading && <Loader size="xs" />}
        <Text size="xs" c="dimmed">local analytics; earnings via Yahoo/yfinance</Text>
      </Group>

      {c?.note && <Alert color="blue" variant="light" radius="md">{c.note}</Alert>}

      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
        <Paper withBorder p="md" radius="md">
          <Text fw={600} mb="sm">Risk Flags</Text>
          <Stack gap="xs">
            {(c?.flags ?? []).length === 0 && <Text size="sm" c="dimmed">No concentration, cash, tax, or wash-sale flags from the current rules.</Text>}
            {(c?.flags ?? []).map(flag => (
              <Alert key={`${flag.label}-${flag.detail}`} color={severityColor(flag.severity)} variant="light" radius="md" title={flag.label}>
                {flag.detail}
              </Alert>
            ))}
          </Stack>
        </Paper>

        <Paper withBorder p="md" radius="md">
          <Text fw={600} mb="sm">Tax Snapshot</Text>
          <Table fz="sm" verticalSpacing="xs">
            <Table.Tbody>
              <Table.Tr>
                <Table.Td c="dimmed">YTD realized</Table.Td>
                <Table.Td ta="right" c={(c?.realized_ytd.total ?? 0) >= 0 ? "teal.4" : "red.4"}>{usd(c?.realized_ytd.total)}</Table.Td>
              </Table.Tr>
              <Table.Tr>
                <Table.Td c="dimmed">Short-term</Table.Td>
                <Table.Td ta="right" c={(c?.realized_ytd.short_term ?? 0) >= 0 ? "teal.4" : "red.4"}>{usd(c?.realized_ytd.short_term)}</Table.Td>
              </Table.Tr>
              <Table.Tr>
                <Table.Td c="dimmed">Long-term</Table.Td>
                <Table.Td ta="right" c={(c?.realized_ytd.long_term ?? 0) >= 0 ? "teal.4" : "red.4"}>{usd(c?.realized_ytd.long_term)}</Table.Td>
              </Table.Tr>
              <Table.Tr>
                <Table.Td c="dimmed">Wash-sale rows</Table.Td>
                <Table.Td ta="right">{c?.realized_ytd.wash_sale_rows ?? "—"}</Table.Td>
              </Table.Tr>
              <Table.Tr>
                <Table.Td c="dimmed">Cash allocation</Table.Td>
                <Table.Td ta="right">{pct(c?.cash_pct)}</Table.Td>
              </Table.Tr>
            </Table.Tbody>
          </Table>
        </Paper>
      </SimpleGrid>

      <Paper withBorder p="md" radius="md">
        <Text fw={600} mb="sm">Top Holdings Context</Text>
        <Table.ScrollContainer minWidth={760}>
          <Table striped highlightOnHover withColumnBorders verticalSpacing="xs" fz="sm">
            <Table.Thead>
              <Table.Tr>
                {["Symbol", "Name", "Value", "Weight", "Unreal G/L", "Unreal %", "Rating", "Type"].map(h => (
                  <Table.Th key={h} style={{ whiteSpace: "nowrap" }}>{h}</Table.Th>
                ))}
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {(c?.top_holdings ?? []).map(h => (
                <Table.Tr key={h.symbol}>
                  <Table.Td fw={700}>{h.symbol}</Table.Td>
                  <Table.Td style={{ maxWidth: 260, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{h.description}</Table.Td>
                  <Table.Td ta="right">{usd(h.market_value)}</Table.Td>
                  <Table.Td ta="right">{pct(h.weight_pct)}</Table.Td>
                  <Table.Td ta="right" c={(h.unrealized_gl ?? 0) >= 0 ? "teal.4" : "red.4"}>{usd(h.unrealized_gl)}</Table.Td>
                  <Table.Td ta="right" c={(h.unrealized_gl_pct ?? 0) >= 0 ? "teal.4" : "red.4"}>{pct(h.unrealized_gl_pct)}</Table.Td>
                  <Table.Td>{h.rating || "—"}</Table.Td>
                  <Table.Td>{h.asset_type || "—"}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      </Paper>

    </Stack>
  );
}
