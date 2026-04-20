import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Alert, Badge, Button, Group, Loader, NumberInput, Paper, Select, SimpleGrid,
  Stack, Table, Text, TextInput, Tooltip, ThemeIcon,
} from "@mantine/core";
import { AreaChart } from "@mantine/charts";
import { api } from "../api";
import type { MonteCarloResponse, Enhancements, PositionDetail } from "../api";
import { pct, usd, num } from "../fmt";

function Stat({
  title, value, sub, positive,
}: {
  title: string; value: string; sub?: string; positive?: boolean | null;
}) {
  return (
    <Paper withBorder p="md" radius="md">
      <Text size="xs" c="dimmed" tt="uppercase" fw={600} lts={0.5}>{title}</Text>
      <Text size="xl" fw={700} c={positive == null ? undefined : positive ? "teal.4" : "red.4"}>
        {value}
      </Text>
      {sub && <Text size="xs" c="dimmed" mt={4}>{sub}</Text>}
    </Paper>
  );
}

/** Format a small decimal volatility as a percentage string (e.g., 0.0148 -> "1.48%") */
const volPct = (v: number | null | undefined) =>
  v == null ? "—" : `${(v * 100).toFixed(2)}%`;

/** Format annualized vol as percentage (already in decimal, e.g. 0.297 -> "29.7%") */
const annVolPct = (v: number | null | undefined) =>
  v == null ? "—" : `${(v * 100).toFixed(1)}%`;

function EnhancementsPanel({ enhancements }: { enhancements: Enhancements }) {
  const symbols = Object.keys(enhancements.per_symbol).sort();
  const dfVal = enhancements.student_t_df;

  // Classify the fat-tail severity for the badge
  let dfLabel = "Normal-like";
  let dfColor = "gray";
  if (dfVal != null) {
    if (dfVal < 5) { dfLabel = "Very fat tails"; dfColor = "red"; }
    else if (dfVal < 8) { dfLabel = "Moderate fat tails"; dfColor = "yellow"; }
    else if (dfVal < 15) { dfLabel = "Mild fat tails"; dfColor = "blue"; }
    else { dfLabel = "Near-normal"; dfColor = "gray"; }
  }

  return (
    <Paper withBorder p="md" radius="md">
      <Text fw={600} mb="sm">Model Enhancements</Text>

      {/* Summary badges */}
      <Group gap="sm" mb="md" wrap="wrap">
        <Tooltip label={`Student-t degrees of freedom: ${dfVal?.toFixed(1) ?? "N/A"}. Lower = fatter tails = more realistic crash/spike modeling. Normal distribution = df=∞.`}>
          <Badge color={dfColor} variant="light" size="lg" radius="sm">
            Fat Tails: df={dfVal?.toFixed(1) ?? "?"} ({dfLabel})
          </Badge>
        </Tooltip>
        <Tooltip label="GARCH(1,1) captures volatility clustering — if the market has been choppy recently, the simulation reflects elevated risk.">
          <Badge color="violet" variant="light" size="lg" radius="sm">
            GARCH(1,1) Volatility
          </Badge>
        </Tooltip>
        <Tooltip label={`Options-market implied volatility blended at ${(enhancements.iv_weight * 100).toFixed(0)}% weight with GARCH forecast. Makes the simulation forward-looking.`}>
          <Badge color="cyan" variant="light" size="lg" radius="sm">
            Implied Vol Blend: {(enhancements.iv_weight * 100).toFixed(0)}%
          </Badge>
        </Tooltip>
      </Group>

      {/* Per-symbol volatility comparison table */}
      <Text size="sm" fw={500} mb="xs" c="dimmed">Per-Symbol Volatility Comparison (daily)</Text>
      <Table.ScrollContainer minWidth={700}>
        <Table striped highlightOnHover withColumnBorders verticalSpacing="xs" fz="sm">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Symbol</Table.Th>
              <Table.Th style={{ whiteSpace: "nowrap" }}>
                <Tooltip label="Simple standard deviation of daily log returns over the history period. Backward-looking, assumes constant volatility.">
                  <span>Historical Vol</span>
                </Tooltip>
              </Table.Th>
              <Table.Th style={{ whiteSpace: "nowrap" }}>
                <Tooltip label="GARCH(1,1) forecasted daily volatility. Captures recent volatility clustering — if vol has been elevated, this will be higher than historical.">
                  <span>GARCH Vol</span>
                </Tooltip>
              </Table.Th>
              <Table.Th style={{ whiteSpace: "nowrap" }}>
                <Tooltip label="At-the-money implied volatility from the options market (annualized). Forward-looking — prices in upcoming earnings, macro events.">
                  <span>Implied Vol (ann.)</span>
                </Tooltip>
              </Table.Th>
              <Table.Th style={{ whiteSpace: "nowrap" }}>
                <Tooltip label="Final blended daily volatility used in simulation. Combines GARCH forecast with implied vol for the best of both worlds.">
                  <span>Blended Vol</span>
                </Tooltip>
              </Table.Th>
              <Table.Th style={{ whiteSpace: "nowrap" }}>IV Available</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {symbols.map(sym => {
              const s = enhancements.per_symbol[sym];
              // Highlight if GARCH vol differs significantly from historical
              const garchDelta = (s.garch_vol != null && s.historical_vol != null && s.historical_vol > 0)
                ? (s.garch_vol - s.historical_vol) / s.historical_vol
                : null;
              const garchColor = garchDelta == null ? undefined
                : garchDelta > 0.1 ? "red.4"     // GARCH says vol is elevated vs history
                : garchDelta < -0.1 ? "teal.4"   // GARCH says vol has calmed down
                : undefined;

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
                </Table.Tr>
              );
            })}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>
    </Paper>
  );
}

function TopPositions({ positions, topN }: { positions: PositionDetail[]; topN: number }) {
  const top = positions.slice(0, topN);
  if (top.length === 0) return null;

  return (
    <Paper withBorder p="md" radius="md">
      <Group justify="space-between" mb="sm">
        <Group gap="xs">
          <Text fw={600}>Top {topN} Positions by Risk/Reward</Text>
          <Tooltip label="Your existing holdings ranked by simulated Risk/Reward score (median upside / 5th-percentile downside). Higher = more favorable forward outlook. Use this to decide which positions to add to.">
            <Badge color="indigo" variant="light" size="sm" radius="sm">?</Badge>
          </Tooltip>
        </Group>
        <Text size="xs" c="dimmed">From your current portfolio holdings</Text>
      </Group>
      <Table.ScrollContainer minWidth={1100}>
        <Table striped highlightOnHover withColumnBorders verticalSpacing="xs" fz="sm">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>#</Table.Th>
              <Table.Th>Symbol</Table.Th>
              <Table.Th>Description</Table.Th>
              <Table.Th style={{ whiteSpace: "nowrap" }}>Mkt Value</Table.Th>
              <Table.Th style={{ whiteSpace: "nowrap" }}>Price</Table.Th>
              <Table.Th style={{ whiteSpace: "nowrap" }}>
                <Tooltip label="Simulated median price (P50). The most likely outcome."><span>P50</span></Tooltip>
              </Table.Th>
              <Table.Th style={{ whiteSpace: "nowrap" }}>
                <Tooltip label="5th percentile price — the 'bad scenario' floor with 95% confidence."><span>P05</span></Tooltip>
              </Table.Th>
              <Table.Th style={{ whiteSpace: "nowrap" }}>
                <Tooltip label="Expected return percentage from simulation."><span>Expected</span></Tooltip>
              </Table.Th>
              <Table.Th style={{ whiteSpace: "nowrap" }}>
                <Tooltip label="Probability that the simulated final price is higher than the current price."><span>Gain Prob.</span></Tooltip>
              </Table.Th>
              <Table.Th style={{ whiteSpace: "nowrap" }}>
                <Tooltip label="Annualized return / annualized volatility. Higher = better historical risk-adjusted returns. > 1.0 is good."><span>Sharpe-ish</span></Tooltip>
              </Table.Th>
              <Table.Th style={{ whiteSpace: "nowrap" }}>
                <Tooltip label="Median upside / 5th-pct downside. Higher = more favorable. > 1.0 means median gain exceeds worst-case loss."><span>Risk/Reward</span></Tooltip>
              </Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {top.map((p, i) => {
              const rr = p.risk_reward_score;
              const rrColor = rr == null ? undefined : rr >= 1.0 ? "teal.4" : rr >= 0.5 ? "yellow.4" : "red.4";
              return (
                <Table.Tr key={p.symbol}>
                  <Table.Td ta="center" fw={700} c="dimmed">{i + 1}</Table.Td>
                  <Table.Td fw={700}>{p.symbol}</Table.Td>
                  <Table.Td maw={200} style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {p.description}
                  </Table.Td>
                  <Table.Td ta="right">{usd(p.market_value)}</Table.Td>
                  <Table.Td ta="right">{usd(p.last_price)}</Table.Td>
                  <Table.Td ta="right" c={(p.p50 ?? 0) >= (p.last_price ?? 0) ? "teal.4" : "red.4"}>
                    {usd(p.p50)}
                  </Table.Td>
                  <Table.Td ta="right" c="red.4">{usd(p.p05)}</Table.Td>
                  <Table.Td ta="right" c={(p.expected_return_pct ?? 0) >= 0 ? "teal.4" : "red.4"}>
                    {pct(p.expected_return_pct)}
                  </Table.Td>
                  <Table.Td ta="right">{pct(p.probability_gain_pct)}</Table.Td>
                  <Table.Td ta="right">{num(p.sharpe_like)}</Table.Td>
                  <Table.Td ta="right" fw={700} c={rrColor}>
                    {num(rr)}
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

function BottomPositions({ positions, bottomN }: { positions: PositionDetail[]; bottomN: number }) {
  // Sort ascending by risk/reward (worst first) — the opposite of position_details
  // which comes pre-sorted descending from the backend.
  const sorted = [...positions].sort(
    (a, b) => (a.risk_reward_score ?? -999) - (b.risk_reward_score ?? -999),
  );
  const bottom = sorted.slice(0, bottomN);
  if (bottom.length === 0) return null;

  return (
    <Paper withBorder p="md" radius="md" style={{ borderColor: "var(--mantine-color-red-7)" }}>
      <Group justify="space-between" mb="sm">
        <Group gap="xs">
          <Text fw={600} c="red.4">Bottom {bottomN} — Sell Candidates</Text>
          <Tooltip label="Your worst-ranked holdings by Risk/Reward. Positions with Gain Prob < 50% are flagged — the simulation says you're more likely to lose than gain. Consider trimming or exiting these.">
            <Badge color="red" variant="light" size="sm" radius="sm">?</Badge>
          </Tooltip>
        </Group>
        <Text size="xs" c="dimmed">Lowest simulated Risk/Reward in portfolio</Text>
      </Group>
      <Table.ScrollContainer minWidth={1100}>
        <Table striped highlightOnHover withColumnBorders verticalSpacing="xs" fz="sm">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>#</Table.Th>
              <Table.Th>Symbol</Table.Th>
              <Table.Th>Description</Table.Th>
              <Table.Th style={{ whiteSpace: "nowrap" }}>Mkt Value</Table.Th>
              <Table.Th style={{ whiteSpace: "nowrap" }}>Price</Table.Th>
              <Table.Th style={{ whiteSpace: "nowrap" }}>
                <Tooltip label="Simulated median price (P50). The most likely outcome."><span>P50</span></Tooltip>
              </Table.Th>
              <Table.Th style={{ whiteSpace: "nowrap" }}>
                <Tooltip label="5th percentile price — the 'bad scenario' floor with 95% confidence."><span>P05</span></Tooltip>
              </Table.Th>
              <Table.Th style={{ whiteSpace: "nowrap" }}>
                <Tooltip label="Expected return percentage from simulation."><span>Expected</span></Tooltip>
              </Table.Th>
              <Table.Th style={{ whiteSpace: "nowrap" }}>
                <Tooltip label="Probability the price ends higher than current. Below 50% = more likely to lose."><span>Gain Prob.</span></Tooltip>
              </Table.Th>
              <Table.Th style={{ whiteSpace: "nowrap" }}>
                <Tooltip label="Annualized return / annualized volatility."><span>Sharpe-ish</span></Tooltip>
              </Table.Th>
              <Table.Th style={{ whiteSpace: "nowrap" }}>
                <Tooltip label="Median upside / 5th-pct downside. Lower = worse outlook."><span>Risk/Reward</span></Tooltip>
              </Table.Th>
              <Table.Th style={{ whiteSpace: "nowrap" }}>Signal</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {bottom.map((p, i) => {
              const rr = p.risk_reward_score;
              const rrColor = rr == null ? undefined : rr >= 1.0 ? "teal.4" : rr >= 0.5 ? "yellow.4" : "red.4";
              const gainProb = p.probability_gain_pct ?? 50;
              const isBearish = gainProb < 50;

              return (
                <Table.Tr key={p.symbol} bg={isBearish ? "rgba(255, 0, 0, 0.04)" : undefined}>
                  <Table.Td ta="center" fw={700} c="dimmed">{i + 1}</Table.Td>
                  <Table.Td fw={700}>{p.symbol}</Table.Td>
                  <Table.Td maw={200} style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {p.description}
                  </Table.Td>
                  <Table.Td ta="right">{usd(p.market_value)}</Table.Td>
                  <Table.Td ta="right">{usd(p.last_price)}</Table.Td>
                  <Table.Td ta="right" c={(p.p50 ?? 0) >= (p.last_price ?? 0) ? "teal.4" : "red.4"}>
                    {usd(p.p50)}
                  </Table.Td>
                  <Table.Td ta="right" c="red.4">{usd(p.p05)}</Table.Td>
                  <Table.Td ta="right" c={(p.expected_return_pct ?? 0) >= 0 ? "teal.4" : "red.4"}>
                    {pct(p.expected_return_pct)}
                  </Table.Td>
                  <Table.Td ta="right" c={isBearish ? "red.4" : undefined} fw={isBearish ? 700 : undefined}>
                    {pct(p.probability_gain_pct)}
                  </Table.Td>
                  <Table.Td ta="right">{num(p.sharpe_like)}</Table.Td>
                  <Table.Td ta="right" fw={700} c={rrColor}>
                    {num(rr)}
                  </Table.Td>
                  <Table.Td ta="center">
                    {isBearish ? (
                      <Tooltip label={`Gain probability is only ${gainProb.toFixed(1)}% — simulation says this position is more likely to lose value.`}>
                        <Badge color="red" variant="filled" size="sm">SELL</Badge>
                      </Tooltip>
                    ) : rr != null && rr < 0.3 ? (
                      <Tooltip label="Very low risk/reward — upside is small relative to downside risk.">
                        <Badge color="orange" variant="light" size="sm">TRIM</Badge>
                      </Tooltip>
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

export default function MonteCarlo() {
  const [symbols, setSymbols] = useState("");
  const [submittedSymbols, setSubmittedSymbols] = useState("");
  const [days, setDays] = useState(90);
  const [simulations, setSimulations] = useState(3000);
  const [period, setPeriod] = useState("1y");
  const [maxPositions, setMaxPositions] = useState(25);
  const [topN, setTopN] = useState(10);

  const query = useQuery<MonteCarloResponse>({
    queryKey: ["monte-carlo", submittedSymbols, days, simulations, period, maxPositions],
    queryFn: () => api.monteCarlo({
      symbols: submittedSymbols,
      days,
      simulations,
      period,
      max_positions: maxPositions,
    }),
    enabled: true,
    staleTime: 10 * 60 * 1000,
  });

  const data = query.data;
  const portfolio = data?.portfolio;
  const bands = portfolio?.bands ?? [];
  const enhancements = data?.enhancements;

  return (
    <Stack gap="md">
      <Group gap="sm" align="flex-end" wrap="wrap">
        <Text fw={600} size="lg">Monte Carlo</Text>
        {query.isFetching && <Loader size="xs" />}
        <TextInput
          label="Watchlist"
          placeholder="AMD, META, QQQ"
          value={symbols}
          onChange={e => setSymbols(e.target.value.toUpperCase())}
          size="xs"
          w={260}
        />
        <NumberInput label="Days" value={days} onChange={v => setDays(Number(v) || 90)} min={5} max={252} size="xs" w={90} />
        <NumberInput label="Runs" value={simulations} onChange={v => setSimulations(Number(v) || 3000)} min={500} max={20000} step={500} size="xs" w={110} />
        <NumberInput label="Positions" value={maxPositions} onChange={v => setMaxPositions(Number(v) || 25)} min={1} max={75} size="xs" w={110} />
        <NumberInput label="Top N" value={topN} onChange={v => setTopN(Number(v) || 10)} min={1} max={75} size="xs" w={80} />
        <Select
          label="History"
          value={period}
          onChange={v => setPeriod(v ?? "1y")}
          data={["6mo", "1y", "2y", "5y"]}
          size="xs"
          w={90}
        />
        <Button size="xs" onClick={() => setSubmittedSymbols(symbols.trim())}>Run</Button>
      </Group>

      <Alert color="blue" variant="light" radius="md">
        Enhanced Monte Carlo with Student-t fat tails, GARCH(1,1) volatility forecasting, and options-implied volatility blend. Uses current holdings from local Schwab CSVs plus optional watchlist symbols.
      </Alert>

      {data?.error && <Alert color="red" title="Simulation unavailable" radius="md">{data.error}</Alert>}

      {portfolio && (
        <>
          <SimpleGrid cols={{ base: 1, sm: 4 }} spacing="md">
            <Stat title="Expected Final" value={usd(portfolio.expected_final)} sub={`${portfolio.days} trading days`} positive={portfolio.expected_return_pct == null ? null : portfolio.expected_return_pct >= 0} />
            <Stat title="Median Return" value={pct(portfolio.expected_return_pct)} sub="Mean simulated return" positive={portfolio.expected_return_pct == null ? null : portfolio.expected_return_pct >= 0} />
            <Stat title="5% Downside" value={usd(portfolio.var_5)} sub="Value-at-risk (fat-tailed)" positive={false} />
            <Stat title="Loss Probability" value={pct(portfolio.probability_loss_pct)} sub={`${portfolio.sample_count} runs`} />
          </SimpleGrid>

          <Paper withBorder p="md" radius="md">
            <Group justify="space-between" mb="sm">
              <Text fw={600}>Portfolio Risk Bands</Text>
              <Text size="xs" c="dimmed">
                {data?.history_start} to {data?.history_end}; {portfolio.symbols_used.length} symbols
              </Text>
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

      {/* Model Enhancements panel — shows the three improvements */}
      {enhancements && <EnhancementsPanel enhancements={enhancements} />}

      {/* Top Positions — existing holdings ranked by risk/reward */}
      {data?.position_details && data.position_details.length > 0 && (
        <TopPositions positions={data.position_details} topN={topN} />
      )}

      {/* Bottom Positions — sell candidates ranked by worst risk/reward */}
      {data?.position_details && data.position_details.length > 0 && (
        <BottomPositions positions={data.position_details} bottomN={topN} />
      )}

      <Paper withBorder p="md" radius="md">
        <Group justify="space-between" mb="sm">
          <Text fw={600}>Watchlist Standalone Runs</Text>
          <Text size="xs" c="dimmed">Enter symbols above, then Run</Text>
        </Group>
        <Table.ScrollContainer minWidth={980}>
          <Table striped highlightOnHover withColumnBorders verticalSpacing="xs" fz="sm">
            <Table.Thead>
              <Table.Tr>
                {["Symbol", "Status", "Price", "Expected", "P05", "P50", "P95", "Gain Prob.", "Ann. Vol", "Sharpe-ish", "Risk/Reward"].map(h => (
                  <Table.Th key={h} style={{ whiteSpace: "nowrap" }}>{h}</Table.Th>
                ))}
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {(data?.candidates ?? []).map(c => (
                <Table.Tr key={c.symbol}>
                  <Table.Td fw={700}>{c.symbol}</Table.Td>
                  <Table.Td>
                    <Badge color={c.status === "ok" ? "teal" : "yellow"} variant="light">
                      {c.status === "ok" ? "ok" : "missing"}
                    </Badge>
                  </Table.Td>
                  <Table.Td ta="right">{usd(c.last_price)}</Table.Td>
                  <Table.Td ta="right" c={(c.expected_return_pct ?? 0) >= 0 ? "teal.4" : "red.4"}>{pct(c.expected_return_pct)}</Table.Td>
                  <Table.Td ta="right">{usd(c.p05)}</Table.Td>
                  <Table.Td ta="right">{usd(c.p50)}</Table.Td>
                  <Table.Td ta="right">{usd(c.p95)}</Table.Td>
                  <Table.Td ta="right">{pct(c.probability_gain_pct)}</Table.Td>
                  <Table.Td ta="right">{pct(c.annual_vol_pct)}</Table.Td>
                  <Table.Td ta="right">{num(c.sharpe_like)}</Table.Td>
                  <Table.Td ta="right">{num(c.risk_reward_score)}</Table.Td>
                </Table.Tr>
              ))}
              {(data?.candidates ?? []).length === 0 && (
                <Table.Tr>
                  <Table.Td colSpan={11}>
                    <Text size="sm" c="dimmed" ta="center" py="md">No watchlist symbols submitted yet.</Text>
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
