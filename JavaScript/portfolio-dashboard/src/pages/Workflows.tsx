import { useQuery } from "@tanstack/react-query";
import {
  Badge,
  Card,
  Code,
  Divider,
  Group,
  Loader,
  SimpleGrid,
  Stack,
  Text,
  Title,
  Tooltip,
} from "@mantine/core";

const BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8765";

interface FileInfo {
  exists: boolean;
  modified?: string;
  size_bytes?: number;
  rows?: number;
  as_of?: string;
}

interface WorkflowStatus {
  masters: Record<string, FileInfo>;
  download_logs: Record<string, Record<string, string | null>>;
  outlook: FileInfo;
}

function freshness(modified: string | undefined): {
  label: string;
  color: string;
} {
  if (!modified) return { label: "Unknown", color: "gray" };
  const diff = Date.now() - new Date(modified).getTime();
  const hours = diff / 3600000;
  if (hours < 6) return { label: "Fresh", color: "teal" };
  if (hours < 24) return { label: "Today", color: "blue" };
  if (hours < 48) return { label: "Yesterday", color: "yellow" };
  const days = Math.floor(hours / 24);
  return { label: `${days}d ago`, color: "red" };
}

function fmtDate(iso: string | undefined | null) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

const WORKFLOWS = [
  {
    title: "Schwab Download Dates",
    trigger: "schwab download dates",
    description:
      "Reads download logs and prints the custom date ranges to use on Schwab's export pages today.",
    command:
      "cd ~/.openclaw/workspace/repos/Monoclaw/Python/finance && uv run python schwab_download_ranges.py",
    timing: "Run before downloading from Schwab",
  },
  {
    title: "Ingest Schwab Downloads",
    trigger: "ingest schwab",
    description:
      "Moves files from ~/Downloads to correct subdirectories, rebuilds all master CSVs, updates download logs, and verifies.",
    command: "See TOOLS.md — multi-step workflow",
    timing: "Run after downloading from Schwab",
  },
  {
    title: "Portfolio Outlook",
    trigger: "portfolio outlook",
    description:
      "Runs Monte Carlo (6M, 5000 sims), DOI, and earnings impact. Summarizes projections, probability of gain, and upcoming catalysts.",
    command:
      "cd ~/.openclaw/workspace/repos/Monoclaw/Python/finance && uv run python schwab_portfolio_outlook.py --out /tmp/outlook.json",
    timing: "~2 min. Run anytime for projections.",
  },
  {
    title: "Portfolio Moves",
    trigger: "portfolio moves",
    description:
      "Same data as outlook, but synthesizes actionable buy/sell/trim recommendations with current market context.",
    command: "Same script + web search + synthesis",
    timing: "~3 min. Run when deciding trades.",
  },
];

function WorkflowCard({ wf }: { wf: (typeof WORKFLOWS)[number] }) {
  return (
    <Card shadow="xs" padding="lg" radius="md" withBorder>
      <Group justify="space-between" mb="xs">
        <Text fw={600} size="lg">
          {wf.title}
        </Text>
        <Badge size="sm" variant="light" color="gray">
          {wf.timing}
        </Badge>
      </Group>
      <Text size="sm" c="dimmed" mb="md">
        {wf.description}
      </Text>
      <Text size="xs" fw={500} mb={4}>
        Trigger phrase:
      </Text>
      <Code block style={{ fontSize: 14, padding: "8px 12px" }}>
        {wf.trigger}
      </Code>
    </Card>
  );
}

function MasterRow({
  label,
  info,
}: {
  label: string;
  info: FileInfo | undefined;
}) {
  if (!info || !info.exists)
    return (
      <Group justify="space-between">
        <Text size="sm">{label}</Text>
        <Badge color="red" size="sm">
          Missing
        </Badge>
      </Group>
    );
  const f = freshness(info.modified);
  return (
    <Group justify="space-between">
      <Text size="sm">{label}</Text>
      <Group gap="xs">
        {info.rows != null && (
          <Text size="xs" c="dimmed">
            {info.rows.toLocaleString()} rows
          </Text>
        )}
        <Tooltip label={fmtDate(info.modified)}>
          <Badge color={f.color} size="sm" variant="light">
            {f.label}
          </Badge>
        </Tooltip>
      </Group>
    </Group>
  );
}

export default function Workflows() {
  const { data, isLoading, error } = useQuery<WorkflowStatus>({
    queryKey: ["workflows-status"],
    queryFn: () =>
      fetch(`${BASE}/workflows/status`).then((r) => r.json()),
    staleTime: 60000,
  });

  return (
    <Stack gap="lg">
      <Title order={3}>Workflows</Title>
      <Text size="sm" c="dimmed">
        Type these trigger phrases into your openclaw or Claude Code session.
      </Text>

      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
        {WORKFLOWS.map((wf) => (
          <WorkflowCard key={wf.trigger} wf={wf} />
        ))}
      </SimpleGrid>

      <Divider my="sm" />

      <Title order={4}>Data Freshness</Title>

      {isLoading && <Loader size="sm" />}
      {error && (
        <Text size="sm" c="red">
          Could not load status — is the backend running?
        </Text>
      )}

      {data && (
        <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
          <Card shadow="xs" padding="md" radius="md" withBorder>
            <Text fw={600} mb="sm">
              Master CSVs
            </Text>
            <Stack gap="xs">
              <MasterRow
                label="Positions"
                info={data.masters?.positions}
              />
              <MasterRow
                label="Balances"
                info={data.masters?.balances}
              />
              <MasterRow
                label="RGL Summary"
                info={data.masters?.rgl_summary}
              />
              <MasterRow
                label="RGL Details"
                info={data.masters?.rgl_details}
              />
              <MasterRow
                label="Transactions"
                info={data.masters?.transactions}
              />
            </Stack>
          </Card>

          <Card shadow="xs" padding="md" radius="md" withBorder>
            <Text fw={600} mb="sm">
              Download Logs
            </Text>
            <Stack gap="xs">
              <Group justify="space-between">
                <Text size="sm">Transactions next download</Text>
                <Text size="sm" fw={500}>
                  {data.download_logs?.transactions?.next_download_start ??
                    "—"}
                </Text>
              </Group>
              <Group justify="space-between">
                <Text size="sm">RGL next download</Text>
                <Text size="sm" fw={500}>
                  {data.download_logs?.rgl?.next_download_start ?? "—"}
                </Text>
              </Group>

              <Divider my="xs" />

              <Text fw={600} size="sm">
                Last Outlook Run
              </Text>
              {data.outlook?.exists ? (
                <Group justify="space-between">
                  <Text size="sm">
                    {data.outlook.as_of
                      ? `Data as of ${data.outlook.as_of}`
                      : "File exists"}
                  </Text>
                  <Badge
                    color={freshness(data.outlook.modified).color}
                    size="sm"
                    variant="light"
                  >
                    {fmtDate(data.outlook.modified)}
                  </Badge>
                </Group>
              ) : (
                <Text size="sm" c="dimmed">
                  No outlook run yet — type "portfolio outlook"
                </Text>
              )}
            </Stack>
          </Card>
        </SimpleGrid>
      )}
    </Stack>
  );
}
