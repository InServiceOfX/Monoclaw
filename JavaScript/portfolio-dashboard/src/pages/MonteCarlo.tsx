import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Alert, Badge, Button, Group, Loader, NumberInput, Paper, Select, SimpleGrid,
  Stack, Table, Text, Tooltip, ScrollArea,
} from "@mantine/core";
import { AreaChart } from "@mantine/charts";
import { api } from "../api";
import type { MonteCarloResponse, Enhancements, PositionDetail } from "../api";
import { pct, usd, num } from "../fmt";

// ── helpers ───────────────────────────────────────────────────────────────────

const volPct = (v: number | null | undefined) =>
  v == null ? "—" : `${(v * 100).toFixed(2)}%`;
const annVolPct = (v: number | null | undefined) =>
  v == null ? "—" : `${(v * 100).toFixed(1)}%`;

function Stat({ title, value, sub, positive }: { title: string; value: string; sub?: string; positive?: boolean | null }) {
  return (
    <Paper withBorder p="md" radius="md">
      <Text size="xs" c="dimmed" tt="uppercase" fw={600} lts={0.5}>{title}</Text>
      <Text size="xl" fw={700} c={positive == null ? undefined : positive ? "teal.4" : "red.4"}>{value}</Text>
      {sub && <Text size="xs" c="dimmed" mt={4}>{sub}</Text>}
    </Paper>
  );
}

// ── Symbol picker ─────────────────────────────────────────────────────────────

function SymbolPicker({
  selected,
  onToggle,
  positions,
}: {
  selected: Set<string>;
  onToggle: (sym: string) => void;
  positions: { symbol: string; market_value: number | null }[];
}) {
  if (positions.length === 0) return null;
  return (
    <Paper withBorder p="sm" radius="md">
      <Text size="xs" c="dimmed" mb="xs">
        Click to add/remove from watchlist. Defaults to top 5 by portfolio size.
      </Text>
      <ScrollArea>
        <Group gap={6} wrap="wrap">
          {positions.map(p => (
            <Button
              key={p.symbol}
              size="xs"
              variant={selected.has(p.symbol) ? "filled" : "light"}
              color={selected.has(p.symbol) ? "indigo" : "gray"}
              onClick={() => onToggle(p.symbol)}
              style={{ fontFamily: "monospace" }}
            >
              {p.symbol}
            </Button>
          ))}
        </Group>
      </ScrollArea>
    </Paper>
  );
}

// ── Model enhancements panel ──────────────────────────────────────────────────

function volRec(s: { historical_vol: number | null; garch_vol: number | null; implied_vol_annual: number | null; blended_vol: number | null; used_implied_vol: boolean }): { label: string; color: string } {
  const garchDelta = (s.garch_vol != null && s.historical_vol != null && s.historical_vol > 0)
    ? (s.garch_vol - s.historical_vol) / s.historical_vol : null;
  const ivHigh = s.used_implied_vol && s.implied_vol_annual != null && s.blended_vol != null
    && s.implied_vol_annual > (s.blended_vol / Math.sqrt(252)) * 1.5;

  if (garchDelta != null && garchDelta > 0.2)
    return { label: "Volatility elevated — caution", color: "red" };
  if (ivHigh)
    return { label: "Market pricing in risk", color: "orange" };
  if (garchDelta != null && garchDelta < -0.1)
    return { label: "Volatility calming — favorable", color: "teal" };
  return { label: "Normal regime", color: "gray" };
}

function EnhancementsPanel({ enhancements }: { enhancements: Enhancements }) {
  const symbols = Object.keys(enhancements.per_symbol).sort();
  const dfVal = enhancements.student_t_df;

  let dfLabel = "Normal-like"; let dfColor = "gray";
  if (dfVal != null) {
    if (dfVal < 5) { dfLabel = "Very fat tails"; dfColor = "red"; }
    else if (dfVal < 8) { dfLabel = "Moderate fat tails"; dfColor = "yellow"; }
    else if (dfVal < 15) { dfLabel = "Mild fat tails"; dfColor = "blue"; }
    else { dfLabel = "Near-normal"; dfColor = "gray"; }
  }

  return (
    <Paper withBorder p="md" radius="md">
      <Text fw={600} mb="sm">Model Enhancements</Text>
      <Group gap="sm" mb="md" wrap="wrap">
        <Tooltip label={`Student-t degrees of freedom: ${dfVal?.toFixed(1) ?? "N/A"}. Lower = fatter tails = more realistic crash/spike modeling. Normal distribution = infinite df.`}>
          <Badge color={dfColor} variant="light" size="lg" radius="sm">
            Fat Tails: df={dfVal?.toFixed(1) ?? "?"} ({dfLabel})
          </Badge>
        </Tooltip>
        <Tooltip label="GARCH(1,1) = Generalized AutoRegressive Conditional Heteroskedasticity. It captures volatility clustering — recent choppy markets raise the forecast risk.">
          <Badge color="violet" variant="light" size="lg" radius="sm">GARCH(1,1) Volatility Clustering</Badge>
        </Tooltip>
        <Tooltip label={`Options-market implied volatility blended at ${(enhancements.iv_weight * 100).toFixed(0)}% weight. 'Implied' because it's derived from what options traders are paying to hedge — forward-looking, not historical.`}>
          <Badge color="cyan" variant="light" size="lg" radius="sm">
            Implied Volatility Blend: {(enhancements.iv_weight * 100).toFixed(0)}%
          </Badge>
        </Tooltip>
      </Group>

      <Text size="sm" fw={500} mb="xs" c="dimmed">Per-Symbol Volatility Breakdown (daily unless noted)</Text>
      <Table.ScrollContainer minWidth={820}>
        <Table striped highlightOnHover withColumnBorders verticalSpacing="xs" fz="sm">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Symbol</Table.Th>
              <Table.Th style={{ whiteSpace: "nowrap" }}>
                <Tooltip label="Standard deviation of daily log-returns over the history window. Simple, backward-looking — assumes volatility is constant over time.">
                  <span style={{ cursor: "help", borderBottom: "1px dashed" }}>Historical Volatility</span>
                </Tooltip>
              </Table.Th>
              <Table.Th style={{ whiteSpace: "nowrap" }}>
                <Tooltip label="GARCH(1,1) forecast: Generalized AutoRegressive Conditional Heteroskedasticity. Captures volatility clustering — if markets have been choppy lately, this will be higher than historical. Red = elevated vs history, teal = calming.">
                  <span style={{ cursor: "help", borderBottom: "1px dashed" }}>GARCH Volatility</span>
                </Tooltip>
              </Table.Th>
              <Table.Th style={{ whiteSpace: "nowrap" }}>
                <Tooltip label="Annualized at-the-money implied volatility from the options market. 'Implied' because it's reverse-engineered from option prices — reflects what traders expect, including upcoming earnings or macro events.">
                  <span style={{ cursor: "help", borderBottom: "1px dashed" }}>Implied Volatility (ann.)</span>
                </Tooltip>
              </Table.Th>
              <Table.Th style={{ whiteSpace: "nowrap" }}>
                <Tooltip label="Final daily volatility used in simulation. Blends GARCH forecast with implied volatility so the model is both historically grounded and forward-looking.">
                  <span style={{ cursor: "help", borderBottom: "1px dashed" }}>Blended Volatility</span>
                </Tooltip>
              </Table.Th>
              <Table.Th style={{ whiteSpace: "nowrap" }}>IV Used</Table.Th>
              <Table.Th style={{ whiteSpace: "nowrap" }}>
                <Tooltip label="Signal based on GARCH vs historical divergence and implied volatility. Use as a heads-up, not a trade signal.">
                  <span style={{ cursor: "help", borderBottom: "1px dashed" }}>Signal</span>
                </Tooltip>
              </Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {symbols.map(sym => {
              const s = enhancements.per_symbol[sym];
              const garchDelta = (s.garch_vol != null && s.historical_vol != null && s.historical_vol > 0)
                ? (s.garch_vol - s.historical_vol) / s.historical_vol : null;
              const garchColor = garchDelta == null ? undefined
                : garchDelta > 0.1 ? "red.4" : garchDelta < -0.1 ? "teal.4" : undefined;
              const rec = volRec(s);
              return (
                <Table.Tr key={sym}>
                  <Table.Td fw={700}>{sym}</Table.Td>
                  <Table.Td ta="right">{volPct(s.historical_vol)}</Table.Td>
                  <Table.Td ta="right" c={garchColor}>
                    {volPct(s.garch_vol)}
                    {garchDelta != null && Math.abs(garchDelta) > 0.1 && (
                      <Text span size="xs" c="dimmed" ml={4}>
                        ({garchDelta > 0 ? "↑" : "↓"}{Math.abs(garchDelta * 100).toFixed(0)}%)
                      </Text>
                    )}
                  </Table.Td>
                  <Table.Td ta="right">{annVolPct(s.implied_vol_annual)}</Table.Td>
                  <Table.Td ta="right" fw={600}>{volPct(s.blended_vol)}</Table.Td>
                  <Table.Td ta="center">
                    <Badge color={s.used_implied_vol ? "teal" : "gray"} variant="light" size="sm">
                      {s.used_implied_vol ? "Yes" : "No"}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Badge color={rec.color} variant="light" size="sm" radius="sm">{rec.label}</Badge>
                  </Table.Td>
                </Table.Tr>
              );
            })}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>
    </Paper>
  );
}

// ── Top / Bottom positions ────────────────────────────────────────────────────

const POSITION_COLS = [
  { key: "symbol", label: "Symbol", tip: null },
  { key: "description", label: "Description", tip: null },
  { key: "market_value", label: "Mkt Value", tip: null },
  { key: "last_price", label: "Price", tip: null },
  { key: "p50", label: "P50", tip: "Simulated median price — the most likely outcome." },
  { key: "p05", label: "P05", tip: "5th-percentile price: the 'bad scenario' floor with 95% confidence." },
  { key: "expected_return_pct", label: "Expected %", tip: "Mean simulated return across all runs." },
  { key: "probability_gain_pct", label: "Gain Prob.", tip: "Fraction of simulations where the final price beats today's price." },
  { key: "sharpe_like", label: "Sharpe-ish", tip: "Annual return ÷ annual volatility. >1.0 is strong." },
  { key: "risk_reward_score", label: "Risk/Reward", tip: "Median upside ÷ 5th-pct downside. >1.0 means expected gain exceeds worst-case loss." },
] as const;

function PositionTable({ positions, title, titleColor, bottomN }: {
  positions: PositionDetail[];
  title: string;
  titleColor?: string;
  bottomN?: boolean;
}) {
  const list = bottomN
    ? [...positions].sort((a, b) => (a.risk_reward_score ?? -999) - (b.risk_reward_score ?? -999))
    : positions;

  return (
    <Paper withBorder p="md" radius="md" style={bottomN ? { borderColor: "var(--mantine-color-red-7)" } : undefined}>
      <Group justify="space-between" mb="sm">
        <Group gap="xs">
          <Text fw={600} c={titleColor}>{title}</Text>
          <Tooltip label={bottomN
            ? "Worst-ranked holdings by Risk/Reward. Gain Prob < 50% = simulation says more likely to lose than gain."
            : "Existing holdings ranked by simulated Risk/Reward. Higher = more favorable forward outlook."}>
            <Badge color={bottomN ? "red" : "indigo"} variant="light" size="sm" radius="sm">?</Badge>
          </Tooltip>
        </Group>
      </Group>
      <Table.ScrollContainer minWidth={1100}>
        <Table striped highlightOnHover withColumnBorders verticalSpacing="xs" fz="sm">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>#</Table.Th>
              {POSITION_COLS.map(c => (
                <Table.Th key={c.key} style={{ whiteSpace: "nowrap" }}>
                  {c.tip ? (
                    <Tooltip label={c.tip}><span style={{ cursor: "help", borderBottom: "1px dashed" }}>{c.label}</span></Tooltip>
                  ) : c.label}
                </Table.Th>
              ))}
              <Table.Th>Signal</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {list.map((p, i) => {
              const rr = p.risk_reward_score;
              const rrColor = rr == null ? undefined : rr >= 1.0 ? "teal.4" : rr >= 0.5 ? "yellow.4" : "red.4";
              const gainProb = p.probability_gain_pct ?? 50;
              const isBearish = gainProb < 50;
              return (
                <Table.Tr key={p.symbol} bg={bottomN && isBearish ? "rgba(255,0,0,0.04)" : undefined}>
                  <Table.Td ta="center" fw={700} c="dimmed">{i + 1}</Table.Td>
                  <Table.Td fw={700}>{p.symbol}</Table.Td>
                  <Table.Td maw={180} style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{p.description}</Table.Td>
                  <Table.Td ta="right">{usd(p.market_value)}</Table.Td>
                  <Table.Td ta="right">{usd(p.last_price)}</Table.Td>
                  <Table.Td ta="right" c={(p.p50 ?? 0) >= (p.last_price ?? 0) ? "teal.4" : "red.4"}>{usd(p.p50)}</Table.Td>
                  <Table.Td ta="right" c="red.4">{usd(p.p05)}</Table.Td>
                  <Table.Td ta="right" c={(p.expected_return_pct ?? 0) >= 0 ? "teal.4" : "red.4"}>{pct(p.expected_return_pct)}</Table.Td>
                  <Table.Td ta="right" c={isBearish ? "red.4" : undefined} fw={isBearish && bottomN ? 700 : undefined}>{pct(gainProb)}</Table.Td>
                  <Table.Td ta="right">{num(p.sharpe_like)}</Table.Td>
                  <Table.Td ta="right" fw={700} c={rrColor}>{num(rr)}</Table.Td>
                  <Table.Td ta="center">
                    {isBearish ? (
                      <Tooltip label={`Gain probability ${gainProb.toFixed(1)}% — simulation favors a loss.`}>
                        <Badge color="red" variant="filled" size="sm">SELL</Badge>
                      </Tooltip>
                    ) : rr != null && rr < 0.3 ? (
                      <Tooltip label="Low risk/reward — upside small vs downside.">
                        <Badge color="orange" variant="light" size="sm">TRIM</Badge>
                      </Tooltip>
                    ) : rr != null && rr >= 1.5 && !bottomN ? (
                      <Badge color="teal" variant="light" size="sm">ADD</Badge>
                    ) : (
                      <Badge color="gray" variant="light" size="sm">HOLD</Badge>
                    )}
                  </Table.Td>
                </Table.Tr>
              );
            })}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>
    </Paper>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

const DEFAULT_WATCHLIST_COUNT = 5;

export default function MonteCarlo() {
  const [selectedSymbols, setSelectedSymbols] = useState<Set<string>>(new Set());
  const [watchlistInitialised, setWatchlistInitialised] = useState(false);
  const [submittedSymbols, setSubmittedSymbols] = useState("");
  const [days, setDays] = useState(90);
  const [simulations, setSimulations] = useState(3000);
  const [period, setPeriod] = useState("1y");
  const [maxPositions, setMaxPositions] = useState(25);
  const [topN, setTopN] = useState(10);

  const positionsQuery = useQuery({ queryKey: ["positions"], queryFn: api.positions, staleTime: 60000 });
  const allPositions = (positionsQuery.data?.positions ?? [])
    .filter(p => p.cost_basis_total != null && (p.market_value ?? 0) > 0)
    .sort((a, b) => (b.market_value ?? 0) - (a.market_value ?? 0));

  // Seed watchlist to top N by portfolio size on first load
  useEffect(() => {
    if (!watchlistInitialised && allPositions.length > 0) {
      const top = allPositions.slice(0, DEFAULT_WATCHLIST_COUNT).map(p => p.symbol);
      setSelectedSymbols(new Set(top));
      setWatchlistInitialised(true);
    }
  }, [allPositions, watchlistInitialised]);

  function toggleSymbol(sym: string) {
    setSelectedSymbols(prev => {
      const next = new Set(prev);
      next.has(sym) ? next.delete(sym) : next.add(sym);
      return next;
    });
  }

  const watchlistStr = Array.from(selectedSymbols).join(",");

  const query = useQuery<MonteCarloResponse>({
    queryKey: ["monte-carlo", submittedSymbols, days, simulations, period, maxPositions],
    queryFn: () => api.monteCarlo({ symbols: submittedSymbols, days, simulations, period, max_positions: maxPositions }),
    enabled: true,
    staleTime: 10 * 60 * 1000,
  });

  const data = query.data;
  const portfolio = data?.portfolio;
  const bands = portfolio?.bands ?? [];
  const enhancements = data?.enhancements;

  return (
    <Stack gap="md">
      {/* Controls */}
      <Group gap="sm" align="flex-end" wrap="wrap">
        <Text fw={600} size="lg">Monte Carlo</Text>
        {query.isFetching && <Loader size="xs" />}
        <NumberInput label="Days" value={days} onChange={v => setDays(Number(v) || 90)} min={5} max={252} size="xs" w={90} />
        <NumberInput label="Runs" value={simulations} onChange={v => setSimulations(Number(v) || 3000)} min={500} max={20000} step={500} size="xs" w={110} />
        <NumberInput label="Positions" value={maxPositions} onChange={v => setMaxPositions(Number(v) || 25)} min={1} max={75} size="xs" w={110} />
        <NumberInput label="Top/Bottom N" value={topN} onChange={v => setTopN(Number(v) || 10)} min={1} max={75} size="xs" w={100} />
        <Select label="History" value={period} onChange={v => setPeriod(v ?? "1y")} data={["6mo", "1y", "2y", "5y"]} size="xs" w={90} />
        <Button size="xs" onClick={() => setSubmittedSymbols(watchlistStr)}>Run</Button>
      </Group>

      {/* Symbol picker */}
      <SymbolPicker
        selected={selectedSymbols}
        onToggle={toggleSymbol}
        positions={allPositions}
      />
      {selectedSymbols.size > 0 && (
        <Text size="xs" c="dimmed">
          Watchlist: <strong>{Array.from(selectedSymbols).join(", ")}</strong> — click Run to simulate.
        </Text>
      )}

      <Alert color="blue" variant="light" radius="md">
        Enhanced Monte Carlo: Student-t fat tails, GARCH(1,1) volatility clustering, options-market implied volatility blend.
        Uses current portfolio holdings plus selected watchlist symbols.
      </Alert>

      {data?.error && <Alert color="red" title="Simulation unavailable" radius="md">{data.error}</Alert>}

      {portfolio && (
        <>
          <SimpleGrid cols={{ base: 1, sm: 4 }} spacing="md">
            <Stat title="Expected Final" value={usd(portfolio.expected_final)} sub={`${portfolio.days} trading days`} positive={portfolio.expected_return_pct == null ? null : portfolio.expected_return_pct >= 0} />
            <Stat title="Median Return" value={pct(portfolio.expected_return_pct)} sub="Mean simulated return" positive={portfolio.expected_return_pct == null ? null : portfolio.expected_return_pct >= 0} />
            <Stat title="5% Downside (VaR)" value={usd(portfolio.var_5)} sub="Value-at-Risk, fat-tailed" positive={false} />
            <Stat title="Loss Probability" value={pct(portfolio.probability_loss_pct)} sub={`${portfolio.sample_count} runs`} />
          </SimpleGrid>

          <Paper withBorder p="md" radius="md">
            <Group justify="space-between" mb="sm">
              <Text fw={600}>Portfolio Risk Bands</Text>
              <Text size="xs" c="dimmed">{data?.history_start} → {data?.history_end} · {portfolio.symbols_used.length} symbols</Text>
            </Group>
            <AreaChart
              data={bands}
              dataKey="day"
              series={[
                { name: "p95", color: "teal.5", label: "95th percentile" },
                { name: "p50", color: "indigo.5", label: "Median" },
                { name: "p05", color: "red.5", label: "5th percentile" },
              ]}
              h={300}
              curveType="monotone"
              withLegend
              fillOpacity={0.08}
              yAxisProps={{ tickFormatter: (v: number) => `$${(v / 1000).toFixed(0)}k`, width: 64 }}
              tooltipProps={{ formatter: (v: unknown) => usd(v as number) }}
            />
            <Text size="xs" c="dimmed" mt={4}>{portfolio.note}</Text>
            {portfolio.symbols_missing.length > 0 && (
              <Text size="xs" c="yellow.4" mt={4}>Missing history: {portfolio.symbols_missing.join(", ")}</Text>
            )}
          </Paper>
        </>
      )}

      {enhancements && <EnhancementsPanel enhancements={enhancements} />}

      {data?.position_details && data.position_details.length > 0 && (
        <PositionTable positions={data.position_details.slice(0, topN)} title={`Top ${topN} — Buy / Add Candidates`} />
      )}
      {data?.position_details && data.position_details.length > 0 && (
        <PositionTable positions={data.position_details} title={`Bottom ${topN} — Sell Candidates`} titleColor="red.4" bottomN />
      )}

      {/* Watchlist standalone runs */}
      <Paper withBorder p="md" radius="md">
        <Group justify="space-between" mb="sm">
          <Text fw={600}>Watchlist Standalone Runs</Text>
          <Text size="xs" c="dimmed">
            {submittedSymbols ? `Symbols: ${submittedSymbols}` : "Select symbols above and click Run"}
          </Text>
        </Group>
        <Table.ScrollContainer minWidth={980}>
          <Table striped highlightOnHover withColumnBorders verticalSpacing="xs" fz="sm">
            <Table.Thead>
              <Table.Tr>
                {["Symbol","Status","Price","Expected %","P05","P50","P95","Gain Prob.","Ann. Volatility","Sharpe-ish","Risk/Reward","Signal"].map(h => (
                  <Table.Th key={h} style={{ whiteSpace: "nowrap" }}>{h}</Table.Th>
                ))}
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {(data?.candidates ?? []).map(c => {
                const rr = c.risk_reward_score;
                const gainProb = c.probability_gain_pct ?? 50;
                const isBuy = rr != null && rr >= 1.0 && gainProb >= 55 && (c.sharpe_like ?? 0) >= 0.5;
                const isSell = gainProb < 50 || (rr != null && rr < 0.3);
                return (
                  <Table.Tr key={c.symbol}>
                    <Table.Td fw={700}>{c.symbol}</Table.Td>
                    <Table.Td>
                      <Badge color={c.status === "ok" ? "teal" : "yellow"} variant="light" size="sm">
                        {c.status === "ok" ? "ok" : "no history"}
                      </Badge>
                    </Table.Td>
                    <Table.Td ta="right">{usd(c.last_price)}</Table.Td>
                    <Table.Td ta="right" c={(c.expected_return_pct ?? 0) >= 0 ? "teal.4" : "red.4"}>{pct(c.expected_return_pct)}</Table.Td>
                    <Table.Td ta="right">{usd(c.p05)}</Table.Td>
                    <Table.Td ta="right">{usd(c.p50)}</Table.Td>
                    <Table.Td ta="right">{usd(c.p95)}</Table.Td>
                    <Table.Td ta="right">{pct(gainProb)}</Table.Td>
                    <Table.Td ta="right">{annVolPct(c.annual_vol_pct)}</Table.Td>
                    <Table.Td ta="right">{num(c.sharpe_like)}</Table.Td>
                    <Table.Td ta="right">{num(rr)}</Table.Td>
                    <Table.Td ta="center">
                      {isBuy ? (
                        <Tooltip label="Risk/Reward ≥ 1.0, Gain Prob ≥ 55%, Sharpe ≥ 0.5 — simulation favors entry.">
                          <Badge color="teal" variant="filled" size="sm">BUY</Badge>
                        </Tooltip>
                      ) : isSell ? (
                        <Badge color="red" variant="light" size="sm">PASS</Badge>
                      ) : (
                        <Badge color="gray" variant="light" size="sm">WATCH</Badge>
                      )}
                    </Table.Td>
                  </Table.Tr>
                );
              })}
              {(data?.candidates ?? []).length === 0 && (
                <Table.Tr>
                  <Table.Td colSpan={12}>
                    <Text size="sm" c="dimmed" ta="center" py="md">Select symbols in the picker above and click Run.</Text>
                  </Table.Td>
                </Table.Tr>
              )}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      </Paper>
    </Stack>
  );
}
