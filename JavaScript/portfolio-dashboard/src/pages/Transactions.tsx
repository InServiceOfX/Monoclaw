import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Group, TextInput, Text, Table, Loader, Stack, Select, Button } from "@mantine/core";
import { api } from "../api";

const QUICK_FILTERS = ["Cash Dividend", "Bank Interest", "MoneyLink Transfer"];

export default function Transactions() {
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [symbol, setSymbol] = useState("");
  const [action, setAction] = useState<string | null>(null);

  const actionsQuery = useQuery({
    queryKey: ["transaction-actions"],
    queryFn: api.transactionActions,
    staleTime: 5 * 60 * 1000,
  });

  const params = {
    ...(fromDate && { from_date: fromDate }),
    ...(toDate && { to_date: toDate }),
    ...(symbol && { symbol }),
    ...(action && { action }),
  };
  const { data, isLoading } = useQuery({
    queryKey: ["transactions", params],
    queryFn: () => api.transactions(params),
  });

  const rows = data?.transactions ?? [];
  const capped = rows.slice(0, 500);
  const actionOptions = (actionsQuery.data?.actions ?? []).map(a => ({ value: a, label: a }));

  return (
    <Stack gap="md">
      <Text fw={600} size="lg">Transactions</Text>

      {/* Filters */}
      <Group gap="sm" wrap="wrap">
        <TextInput type="date" label="From" value={fromDate} onChange={e => setFromDate(e.target.value)} size="xs" w={160} />
        <TextInput type="date" label="To" value={toDate} onChange={e => setToDate(e.target.value)} size="xs" w={160} />
        <TextInput
          label="Symbol"
          placeholder="AAPL"
          value={symbol}
          onChange={e => setSymbol(e.target.value.toUpperCase())}
          size="xs"
          w={110}
        />
        <Select
          label="Action"
          placeholder="All actions"
          value={action}
          onChange={setAction}
          data={actionOptions}
          clearable
          searchable
          size="xs"
          w={220}
        />
        <Button
          size="xs"
          variant="subtle"
          onClick={() => { setFromDate(""); setToDate(""); setSymbol(""); setAction(null); }}
          style={{ alignSelf: "flex-end" }}
        >
          Clear
        </Button>
        {isLoading
          ? <Loader size="xs" style={{ alignSelf: "flex-end", marginBottom: 4 }} />
          : <Text size="xs" c="dimmed" style={{ alignSelf: "flex-end", marginBottom: 4 }}>{data?.count ?? 0} rows</Text>
        }
      </Group>

      {/* Quick filters */}
      <Group gap="xs">
        <Text size="xs" c="dimmed">Quick:</Text>
        {QUICK_FILTERS.map(f => (
          <Button
            key={f}
            size="xs"
            variant={action === f ? "filled" : "light"}
            color="indigo"
            onClick={() => setAction(action === f ? null : f)}
          >
            {f}
          </Button>
        ))}
      </Group>

      <Table.ScrollContainer minWidth={800}>
        <Table striped highlightOnHover withColumnBorders verticalSpacing="xs" fz="sm">
          <Table.Thead>
            <Table.Tr>
              {["Date","Action","Symbol","Description","Quantity","Price","Amount"].map(h => (
                <Table.Th key={h} style={{ whiteSpace: "nowrap" }}>{h}</Table.Th>
              ))}
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {capped.map((r, i) => (
              <Table.Tr key={i}>
                <Table.Td style={{ whiteSpace: "nowrap" }}>{r.date_iso ?? r.Date}</Table.Td>
                <Table.Td style={{ whiteSpace: "nowrap" }}>{r.Action}</Table.Td>
                <Table.Td fw={700}>{r.Symbol}</Table.Td>
                <Table.Td style={{ maxWidth: 240, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.Description}</Table.Td>
                <Table.Td ta="right">{r.Quantity}</Table.Td>
                <Table.Td ta="right">{r.Price}</Table.Td>
                <Table.Td ta="right" c={r.Amount?.startsWith("-") ? "red.4" : "teal.4"}>{r.Amount}</Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>

      {rows.length > 500 && (
        <Text size="xs" c="dimmed">Showing 500 of {rows.length} rows — use filters to narrow down.</Text>
      )}
    </Stack>
  );
}
