# PROGRESS.md — Python/finance

## Completed
| Item | Status | Notes |
|------|--------|-------|
| Portfolio dashboard API | ✅ | Positions, balances, context, earnings, and Monte Carlo endpoints exist. |
| DOI backend MVP | ✅ | Added DOI engine, `/doi/snapshot`, and private conviction seed flow. |
| Trade Quality endpoint repair | ✅ | Grading endpoints now use the existing transaction CSV fallback, bounded recent-sell scoring, cached price-history misses, and provisional neutral scores for very recent sells. |

## In Progress
| Item | Branch | Status | Notes |
|------|--------|--------|-------|
| Analytics polish follow-up | feat/doi-deployment-index | 🔄 | Monitor DOI latency and tune score formulas after frontend integration. |

## Not Started
| Item | Priority | Notes |
|------|----------|-------|
| DOI frontend UI | medium | Backend-first task; React wiring is separate work. |

## Last Worked On
**2026-05-29** — Repaired Trade Quality backend data flow and latency: fixed transaction master fallback, removed misuse of transaction amount as realized-gain percentage, cached empty yfinance history responses, bounded page-load grading work, made very recent sells provisional instead of blocking on unavailable forward history, and changed summary/top-bottom/by-symbol scoring to skip the recent provisional block and score mature historical sells.

**2026-04-28** — Created `Python/finance` handoff docs, implemented the DOI engine and `/doi/snapshot`, seeded the private conviction file on first run, and validated the endpoint locally on port `8766` because `8765` was already occupied by another process.
