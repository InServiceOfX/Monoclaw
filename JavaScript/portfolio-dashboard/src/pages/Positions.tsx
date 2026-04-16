import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Group, TextInput, Text, Badge, Table, Loader, Stack,
} from "@mantine/core";
import { api } from "../api";
import type { Position } from "../api";
import { usd, pct } from "../fmt";

type SortKey = keyof Position;

export default function Positions() {
  const { data, isLoading } = useQuery({ queryKey: ["positions"], queryFn: api.positions, refetchInterval: 60000 });
  const [sortKey, setSortKey] = useState<SortKey>("market_value");
  const [sortAsc, setSortAsc] = useState(false);
  const [filter, setFilter] = useState("");

  const positions = (data?.positions ?? [])
    .filter(p => !filter || p.symbol.includes(filter.toUpperCase()) || p.description.toLowerCase().includes(filter.toLowerCase()))
    .sort((a, b) => {
      const av = a[sortKey] ?? -Infinity;
      const bv = b[sortKey] ?? -Infinity;
      const cmp = av < bv ? -1 : av > bv ? 1 : 0;
      return sortAsc ? cmp : -cmp;
    });

  type Col = { key: SortKey; label: string; fmt: (p: Position) => string; align?: "right"; gl?: boolean };
  const cols: Col[] = [
    { key: "symbol", label: "Symbol", fmt: p => p.symbol },
    { key: "description", label: "Name", fmt: p => p.description.slice(0, 30) },
    { key: "qty", label: "Qty", fmt: p => p.qty == null ? "—" : String(p.qty), align: "right" },
    { key: "current_price", label: "Price", fmt: p => usd(p.current_price), align: "right" },
    { key: "market_value", label: "Mkt Value", fmt: p => usd(p.market_value), align: "right" },
    { key: "cost_basis_total", label: "Cost Basis", fmt: p => usd(p.cost_basis_total), align: "right" },
    { key: "unrealized_gl_dollars", label: "Unreal G/L $", fmt: p => usd(p.unrealized_gl_dollars), align: "right", gl: true },
    { key: "unrealized_gl_pct", label: "Unreal G/L %", fmt: p => pct(p.unrealized_gl_pct), align: "right", gl: true },
    { key: "day_change_pct", label: "Day %", fmt: p => pct(p.day_change_pct), align: "right", gl: true },
    { key: "pct_of_account", label: "% Acct", fmt: p => pct(p.pct_of_account), align: "right" },
  ];

  function glColor(v: number | null | undefined) {
    return v == null ? undefined : v >= 0 ? "teal.4" : "red.4";
  }

  function handleSort(key: SortKey) {
    if (sortKey === key) setSortAsc(!sortAsc);
    else { setSortKey(key); setSortAsc(false); }
  }

  return (
    <Stack gap="md">
      <Group>
        <Text fw={600} size="lg">Positions ({positions.length})</Text>
        <TextInput
          placeholder="Filter symbol / name…"
          value={filter}
          onChange={e => setFilter(e.target.value)}
          size="xs"
          w={220}
        />
        <Text size="xs" c="dimmed">as of {data?.snapshot_date}</Text>
        {isLoading && <Loader size="xs" />}
      </Group>

      <Table.ScrollContainer minWidth={900}>
        <Table striped highlightOnHover withColumnBorders verticalSpacing="xs" fz="sm">
          <Table.Thead>
            <Table.Tr>
              {cols.map(c => (
                <Table.Th
                  key={c.key}
                  style={{ cursor: "pointer", whiteSpace: "nowrap", textAlign: c.align ?? "left" }}
                  onClick={() => handleSort(c.key)}
                >
                  {c.label} {sortKey === c.key ? (sortAsc ? "▲" : "▼") : ""}
                </Table.Th>
              ))}
              <Table.Th style={{ width: 28 }} />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {positions.map(p => (
              <Table.Tr key={p.symbol}>
                {cols.map(c => {
                  const glVal = c.gl ? (p[c.key] as number | null) : null;
                  return (
                    <Table.Td
                      key={c.key}
                      style={{ textAlign: c.align ?? "left", whiteSpace: "nowrap" }}
                    >
                      <Text
                        size="sm"
                        fw={c.key === "symbol" ? 700 : undefined}
                        c={c.gl ? glColor(glVal) : undefined}
                      >
                        {c.fmt(p)}
                      </Text>
                    </Table.Td>
                  );
                })}
                <Table.Td>
                  {p.price_stale && (
                    <Badge size="xs" color="orange" variant="light">stale</Badge>
                  )}
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>
    </Stack>
  );
}
