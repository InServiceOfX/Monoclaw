"""Monte Carlo analytics for local portfolio and watchlist symbols.

This module intentionally contains no account-specific paths or hardcoded
holdings. Callers pass current holdings derived from local Schwab CSVs.

## Simulation methodology (enhanced)
##
## The original implementation used standard Geometric Brownian Motion (GBM):
##   - Draw daily log returns from a multivariate NORMAL distribution
##   - Parameters: historical mean + covariance from the past year
##   - This assumes constant volatility and thin (Gaussian) tails
##
## Three improvements have been added to increase predictive accuracy:
##
## 1. STUDENT-T DISTRIBUTED DRAWS (fat tails)
##    Real equity returns have "fat tails" — extreme moves (crashes, spikes)
##    occur 5-10x more often than a normal distribution predicts. We replace
##    the multivariate normal with a multivariate Student-t distribution.
##    The degrees-of-freedom parameter (df) controls tail heaviness:
##      - df=infinity: equivalent to normal (thin tails)
##      - df=5: typical for daily equity returns (moderate fat tails)
##      - df=3: very heavy tails (suitable for crisis-prone assets)
##    We estimate df from the data using maximum likelihood via scipy.
##
## 2. GARCH(1,1) VOLATILITY FORECASTING (volatility clustering)
##    GBM assumes volatility is constant over time. In reality, high-volatility
##    days cluster together (a big move today predicts big moves tomorrow).
##    GARCH(1,1) models this:
##      sigma_t^2 = omega + alpha * r_{t-1}^2 + beta * sigma_{t-1}^2
##    where alpha captures "shock persistence" and beta captures "vol memory."
##    We fit a GARCH(1,1) model per symbol and use its FORECASTED volatility
##    (not just the historical average) to scale the simulation draws.
##    This means if the market has been choppy recently, the simulation
##    reflects that elevated risk — and vice versa for calm periods.
##
## 3. IMPLIED VOLATILITY BLEND (forward-looking information)
##    Historical volatility is backward-looking. The options market, however,
##    prices in FUTURE expected volatility — including known upcoming events
##    like earnings, FOMC meetings, and product launches. We pull the at-the-
##    money (ATM) implied volatility from yfinance options chains and blend it
##    with our GARCH forecast:
##      blended_vol = IV_WEIGHT * implied_vol + (1 - IV_WEIGHT) * garch_vol
##    Default blend: 40% implied vol, 60% GARCH vol. This makes the simulation
##    partially forward-looking without fully trusting a single noisy IV read.
##    If options data is unavailable (e.g., for ETFs or illiquid names), we
##    fall back to pure GARCH vol.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Weight for blending implied vol with GARCH vol. 0.0 = pure GARCH (backward-
# looking), 1.0 = pure implied vol (forward-looking). 0.4 is a common quant
# default: trusts the market's forward view but doesn't over-rely on a single
# noisy ATM IV snapshot.
# ---------------------------------------------------------------------------
IV_WEIGHT = 0.4

# ---------------------------------------------------------------------------
# Default degrees of freedom for the Student-t distribution if we can't
# estimate it from the data. 5 is a well-studied default for daily equity
# returns — heavy enough to capture fat tails without being so extreme (df=3)
# that simulations become dominated by outliers.
# ---------------------------------------------------------------------------
DEFAULT_STUDENT_T_DF = 5.0

# Minimum history rows needed per symbol to fit models reliably.
MIN_HISTORY_ROWS = 50


@dataclass(frozen=True)
class Holding:
    symbol: str
    description: str
    market_value: float
    asset_type: str = ""


def _clean_symbol(symbol: str) -> str:
    return symbol.strip().upper().replace("/", "-")


def _finite_or_none(value):
    try:
        import math

        v = float(value)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def _percentile(values, pct: float):
    import numpy as np

    return _finite_or_none(np.percentile(values, pct))


def _download_close(symbols: list[str], period: str):
    """Download daily closing prices from Yahoo Finance via yfinance.

    Returns a DataFrame indexed by date with one column per symbol.
    Handles both single-symbol and multi-symbol responses, which yfinance
    returns with different column structures (flat vs MultiIndex).
    """
    import pandas as pd
    import yfinance as yf

    data = yf.download(
        symbols,
        period=period,
        auto_adjust=True,
        progress=False,
        threads=True,
    )
    if data is None or data.empty:
        return pd.DataFrame()

    if isinstance(data.columns, pd.MultiIndex):
        if "Close" in data.columns.get_level_values(0):
            close = data["Close"]
        elif "Adj Close" in data.columns.get_level_values(0):
            close = data["Adj Close"]
        else:
            close = data.xs(data.columns.get_level_values(0)[0], axis=1, level=0)
    else:
        close = data.get("Close") if "Close" in data else data.get("Adj Close")
        if close is None:
            return pd.DataFrame()
        if not hasattr(close, "to_frame"):
            return pd.DataFrame()
        close = close.to_frame(symbols[0])

    if not isinstance(close, pd.DataFrame):
        close = close.to_frame(symbols[0])

    close = close.rename(columns={c: _clean_symbol(str(c)) for c in close.columns})
    close = close.dropna(axis=1, how="all").ffill().dropna(how="all")
    return close


# ============================================================================
# IMPROVEMENT 1: Student-t degrees-of-freedom estimation
# ============================================================================

def _estimate_student_t_df(returns_matrix) -> float:
    """Estimate the degrees-of-freedom (df) for a multivariate Student-t
    distribution by fitting a univariate t to the pooled standardized residuals.

    Why this works:
    ---------------
    If multi-asset returns follow a multivariate t(df, mu, Sigma), then each
    marginal is also t-distributed with the same df. We standardize each
    column to zero mean / unit variance, pool all residuals, and fit a 1D
    Student-t via maximum likelihood. This gives a robust aggregate estimate
    of tail heaviness across the portfolio.

    The fitted df tells us how fat-tailed the return distribution is:
      - df > 30: nearly Gaussian, fat tails are negligible
      - df ~ 5:  moderate fat tails (typical for daily equity returns)
      - df < 4:  very heavy tails (variance of the t-distribution diverges at df<=2)

    We clamp the result to [3, 30] to avoid degenerate simulations:
      - df < 3 would make variance undefined and produce extreme outliers
      - df > 30 is effectively normal, so no point going higher

    Parameters
    ----------
    returns_matrix : np.ndarray
        (T, N) matrix of daily log returns, T time steps, N assets.

    Returns
    -------
    float
        Estimated degrees of freedom, clamped to [3, 30].
    """
    import numpy as np
    from scipy.stats import t as student_t

    # Standardize each column to mean=0, std=1 so we can pool them.
    means = returns_matrix.mean(axis=0)
    stds = returns_matrix.std(axis=0)
    # Guard against zero-variance columns (e.g., a stock that didn't move).
    stds = np.where(stds < 1e-12, 1.0, stds)
    standardized = (returns_matrix - means) / stds

    # Pool all standardized residuals into one 1D array for MLE fitting.
    pooled = standardized.flatten()

    try:
        # scipy.stats.t.fit returns (df, loc, scale) via maximum likelihood.
        df_est, _loc, _scale = student_t.fit(pooled)
        # Clamp to a sensible range.
        return float(np.clip(df_est, 3.0, 30.0))
    except Exception:
        logger.warning("Student-t df estimation failed, using default df=%.1f", DEFAULT_STUDENT_T_DF)
        return DEFAULT_STUDENT_T_DF


# ============================================================================
# IMPROVEMENT 2: GARCH(1,1) per-symbol volatility forecasting
# ============================================================================

def _fit_garch_volatilities(returns, available_symbols: list[str], forecast_days: int) -> dict[str, float]:
    """Fit a GARCH(1,1) model to each symbol's return series and forecast
    the average daily volatility over the simulation horizon.

    GARCH(1,1) model for daily variance:
    ---------------------------------------------------------------
        sigma_t^2 = omega + alpha * epsilon_{t-1}^2 + beta * sigma_{t-1}^2

    where:
        omega  = long-run variance weight (baseline volatility floor)
        alpha  = shock coefficient — how much yesterday's squared return
                 feeds into today's variance (captures "news impact")
        beta   = persistence coefficient — how much yesterday's variance
                 carries forward (captures "volatility memory")
        alpha + beta < 1 is required for stationarity (vol mean-reverts)

    The model is fit with Student-t innovations (dist='t'), which means
    the GARCH fitting itself accounts for fat tails — giving better
    parameter estimates than assuming Gaussian errors.

    We forecast the AVERAGE daily volatility over the simulation horizon
    rather than a full path of time-varying vol. This is a pragmatic
    compromise: a full vol-path simulation (where each day uses a different
    sigma_t) would be more accurate but significantly more complex to
    correlate across assets. The average forecast still captures the key
    insight: if vol has been elevated recently, the GARCH forecast will be
    HIGHER than the naive historical average.

    Parameters
    ----------
    returns : pd.DataFrame
        Daily log returns with columns = symbols.
    available_symbols : list[str]
        Which symbols to fit.
    forecast_days : int
        How many days forward to forecast (sets the horizon for averaging).

    Returns
    -------
    dict[str, float]
        Mapping of symbol -> forecasted average daily volatility (std dev).
        If GARCH fitting fails for a symbol, falls back to simple historical
        std dev for that symbol.
    """
    from arch import arch_model
    import numpy as np

    garch_vols = {}
    for sym in available_symbols:
        series = returns[sym].dropna()
        if len(series) < MIN_HISTORY_ROWS:
            # Not enough data to fit GARCH — use simple historical vol.
            garch_vols[sym] = float(series.std())
            continue
        try:
            # arch library expects returns in percentage points, not decimals.
            # e.g., a 1% return should be 1.0, not 0.01. This affects the scale
            # of omega/alpha/beta but not the model's statistical validity.
            am = arch_model(
                series * 100,   # Convert decimal returns to percentage
                vol="Garch",    # GARCH(1,1) variance model
                p=1,            # Lag order for the ARCH term (alpha)
                q=1,            # Lag order for the GARCH term (beta)
                dist="t",       # Student-t innovations for robust fitting
                mean="Constant",  # Constant mean model (simplest)
            )
            # disp='off' suppresses the convergence output from the optimizer.
            result = am.fit(disp="off", show_warning=False)

            # Forecast variance over the simulation horizon.
            # method='analytic' uses the closed-form GARCH recursion:
            #   E[sigma_{t+h}^2] converges to omega / (1 - alpha - beta) as h -> inf
            # For short horizons, it interpolates between the current conditional
            # variance and this long-run level.
            forecast = result.forecast(horizon=min(forecast_days, 252), method="analytic")

            # forecast.variance gives a DataFrame with one row (last obs) and
            # columns h.1, h.2, ..., h.horizon. Each value is the forecasted
            # VARIANCE (in percentage-squared units) for that day.
            var_forecasts = forecast.variance.values[-1, :]

            # Average daily variance over the horizon, then:
            #   1. Take sqrt to get standard deviation (volatility)
            #   2. Divide by 100 to convert back from percentage to decimal units
            avg_daily_var = float(np.mean(var_forecasts))
            garch_vols[sym] = float(np.sqrt(max(avg_daily_var, 1e-10))) / 100.0

        except Exception as exc:
            # GARCH can fail to converge for symbols with very low variance,
            # very short histories, or numerical issues. Fall back gracefully.
            logger.warning("GARCH fit failed for %s (%s), using historical vol", sym, exc)
            garch_vols[sym] = float(series.std())

    return garch_vols


# ============================================================================
# IMPROVEMENT 3: Implied volatility from options chains
# ============================================================================

def _fetch_implied_volatilities(symbols: list[str]) -> dict[str, float | None]:
    """Fetch the at-the-money (ATM) implied volatility for each symbol from
    yfinance options chains.

    How ATM implied vol is extracted:
    ---------------------------------
    1. Get the nearest-expiry options chain (closest to 30 days out).
    2. Find the call option whose strike is closest to the current stock price.
    3. Read its `impliedVolatility` field (annualized, provided by Yahoo).
    4. Convert from annualized to daily: daily_iv = annual_iv / sqrt(252).

    Why ATM:
    --------
    At-the-money options have the highest trading volume and the tightest
    bid-ask spreads, making their IV the most reliable. Deep OTM/ITM options
    have wider spreads and skew effects that would add noise.

    Why nearest-to-30-day expiry:
    -----------------------------
    Very short-dated options (<7 days) have elevated gamma and can spike on
    minor events. Very long-dated options (>6 months) reflect long-term
    structural vol, not the near-term outlook. ~30 days is the sweet spot
    for a 90-day simulation horizon — it captures upcoming catalysts without
    being too noisy.

    Failure modes:
    --------------
    Returns None for a symbol if:
      - No options chain exists (common for ETFs, ADRs, small-caps)
      - The impliedVolatility field is zero or missing
      - yfinance raises any exception (rate limiting, ticker not found)

    Parameters
    ----------
    symbols : list[str]
        Ticker symbols to look up.

    Returns
    -------
    dict[str, float | None]
        symbol -> annualized implied vol (decimal, e.g. 0.35 = 35%), or None.
    """
    import numpy as np
    import yfinance as yf

    implied_vols: dict[str, float | None] = {}
    for sym in symbols:
        try:
            ticker = yf.Ticker(sym)
            expirations = ticker.options
            if not expirations:
                implied_vols[sym] = None
                continue

            # Pick expiry closest to ~30 days from now for a balance between
            # signal (upcoming events priced in) and noise (very short-dated
            # options are too spiky).
            import datetime
            today = datetime.date.today()
            target = today + datetime.timedelta(days=30)
            best_expiry = min(
                expirations,
                key=lambda e: abs((datetime.date.fromisoformat(e) - target).days),
            )

            chain = ticker.option_chain(best_expiry)
            calls = chain.calls

            # Get current price for ATM strike selection.
            info = ticker.fast_info
            current_price = float(info.get("lastPrice", 0) or info.get("previousClose", 0))
            if current_price <= 0:
                implied_vols[sym] = None
                continue

            # Find the call with strike closest to current price (ATM).
            calls = calls[calls["impliedVolatility"] > 0.001].copy()
            if calls.empty:
                implied_vols[sym] = None
                continue
            calls["strike_dist"] = (calls["strike"] - current_price).abs()
            atm_row = calls.loc[calls["strike_dist"].idxmin()]
            iv = float(atm_row["impliedVolatility"])

            # Yahoo's impliedVolatility is already annualized.
            # Sanity check: IV should be between 1% and 500% annualized.
            if 0.01 < iv < 5.0:
                implied_vols[sym] = iv
            else:
                implied_vols[sym] = None

        except Exception as exc:
            logger.debug("Could not fetch IV for %s: %s", sym, exc)
            implied_vols[sym] = None

    return implied_vols


def _blend_volatilities(
    garch_vols: dict[str, float],
    implied_vols: dict[str, float | None],
    available_symbols: list[str],
    iv_weight: float = IV_WEIGHT,
) -> dict[str, float]:
    """Blend GARCH-forecasted vol with implied vol for each symbol.

    The blend formula:
        blended = iv_weight * (implied_vol / sqrt(252)) + (1 - iv_weight) * garch_vol

    Both vols are in daily standard deviation units after blending.

    If implied vol is not available for a symbol, we use pure GARCH vol.
    This makes the system robust: options data is a bonus, not a requirement.

    Parameters
    ----------
    garch_vols : dict[str, float]
        GARCH-forecasted daily vol (std dev in decimal units).
    implied_vols : dict[str, float | None]
        Annualized implied vol from options (decimal), or None.
    available_symbols : list[str]
        Symbols to blend.
    iv_weight : float
        Weight for implied vol in the blend (0 to 1).

    Returns
    -------
    dict[str, float]
        symbol -> blended daily volatility.
    """
    import numpy as np

    blended = {}
    for sym in available_symbols:
        garch_vol = garch_vols.get(sym, 0.01)
        iv = implied_vols.get(sym)
        if iv is not None and iv > 0:
            # Convert annualized IV to daily standard deviation.
            daily_iv = iv / np.sqrt(252)
            blended[sym] = iv_weight * daily_iv + (1 - iv_weight) * garch_vol
        else:
            # No implied vol available — use pure GARCH forecast.
            blended[sym] = garch_vol
    return blended


# ============================================================================
# Enhanced draw generation: Student-t + adjusted covariance
# ============================================================================

def _generate_enhanced_draws(
    mean_daily,
    cov_daily,
    blended_vols: dict[str, float],
    historical_stds,
    available_symbols: list[str],
    student_t_df: float,
    simulations: int,
    days: int,
    rng,
):
    """Generate simulation draws using the multivariate Student-t distribution
    with a covariance matrix rescaled by GARCH/IV-blended volatilities.

    How the covariance rescaling works:
    ------------------------------------
    The historical covariance matrix encodes both volatilities AND correlations:
        Cov[i,j] = rho[i,j] * sigma_i * sigma_j

    We want to keep the historical CORRELATIONS (which are harder to forecast
    and more stable over time) but replace the per-symbol VOLATILITIES with
    our enhanced GARCH+IV blended estimates. We do this via:

        1. Extract the correlation matrix from the historical covariance:
           R[i,j] = Cov[i,j] / (sigma_i_hist * sigma_j_hist)

        2. Rebuild the covariance using blended vols:
           Cov_new[i,j] = R[i,j] * sigma_i_blended * sigma_j_blended

    This preserves cross-asset correlation structure while using forward-
    looking volatility estimates. It's the standard approach used in risk
    management (Basel III, RiskMetrics).

    How multivariate Student-t sampling works:
    -------------------------------------------
    A multivariate t(df, mu, Sigma) random vector X can be generated as:

        X = mu + Z * sqrt(df / chi2(df))

    where Z ~ N(0, Sigma) and chi2(df) is an independent chi-squared draw.
    This is mathematically equivalent to using scipy.stats.multivariate_t
    but is done manually here for performance (avoiding scipy's overhead
    for large sample counts).

    The sqrt(df / chi2) factor acts as a random "variance multiplier":
      - Most of the time it's close to 1.0 (normal-like behavior)
      - Occasionally it's much larger (producing fat-tail extreme moves)
      - Lower df -> more frequent large multipliers -> fatter tails

    Parameters
    ----------
    mean_daily : np.ndarray
        (N,) vector of historical mean daily log returns.
    cov_daily : np.ndarray
        (N, N) historical covariance matrix.
    blended_vols : dict[str, float]
        Per-symbol blended daily volatility.
    historical_stds : np.ndarray
        (N,) vector of historical daily standard deviations.
    available_symbols : list[str]
        Symbol order matching the covariance matrix columns.
    student_t_df : float
        Degrees of freedom for the Student-t distribution.
    simulations : int
        Number of Monte Carlo simulation paths.
    days : int
        Number of trading days to simulate.
    rng : np.random.Generator
        Numpy random number generator (seeded for reproducibility).

    Returns
    -------
    np.ndarray
        (simulations, days, N) array of daily log return draws.
    """
    import numpy as np

    n_assets = len(available_symbols)

    # Step 1: Extract the correlation matrix from the historical covariance.
    # D_inv is a diagonal matrix of 1/sigma_i for each asset.
    hist_stds_safe = np.where(historical_stds < 1e-12, 1e-12, historical_stds)
    d_inv = np.diag(1.0 / hist_stds_safe)
    correlation = d_inv @ cov_daily @ d_inv

    # Step 2: Rebuild covariance with blended (GARCH+IV) volatilities.
    blended_std_array = np.array(
        [blended_vols.get(sym, hist_stds_safe[i]) for i, sym in enumerate(available_symbols)],
        dtype=float,
    )
    d_new = np.diag(blended_std_array)
    cov_enhanced = d_new @ correlation @ d_new

    # Regularize to ensure positive semi-definiteness (numerical stability).
    cov_enhanced = cov_enhanced + np.eye(n_assets) * 1e-10

    # Step 3: Generate multivariate Student-t draws.
    # Method: X = mu + Z * sqrt(df / W), where:
    #   Z ~ N(0, Sigma_scaled)    (correlated normal draws)
    #   W ~ chi-squared(df)       (independent scalar for tail thickness)
    #
    # We scale Sigma by (df-2)/df so that the resulting t-distribution has
    # the SAME covariance as the input. Without this scaling, the variance
    # of a t(df) is df/(df-2) times the scale matrix, which would inflate
    # our simulated volatilities. This correction ensures our blended vols
    # are respected exactly.
    if student_t_df > 2:
        scale_factor = (student_t_df - 2.0) / student_t_df
    else:
        scale_factor = 1.0
    cov_scaled = cov_enhanced * scale_factor

    try:
        # Draw correlated normal vectors: shape (simulations * days, n_assets).
        normal_draws = rng.multivariate_normal(
            np.zeros(n_assets), cov_scaled, size=simulations * days, check_valid="ignore"
        )
    except Exception:
        # Fallback: if covariance is not PSD, use diagonal only (loses correlations).
        logger.warning("Enhanced covariance not PSD, falling back to diagonal")
        diag_cov = np.diag(np.diag(cov_scaled))
        normal_draws = rng.multivariate_normal(
            np.zeros(n_assets), diag_cov, size=simulations * days, check_valid="ignore"
        )

    # Draw chi-squared values for the t-distribution tail scaling.
    # Each (simulation, day) pair gets one chi-squared draw that scales ALL
    # assets simultaneously — this preserves cross-asset tail dependence
    # (when one asset has a fat-tail event, they all do).
    chi2_draws = rng.chisquare(df=student_t_df, size=simulations * days)

    # The t-distribution scaling factor: sqrt(df / chi2).
    # This is the "random variance multiplier" that creates fat tails.
    t_scale = np.sqrt(student_t_df / chi2_draws)

    # Apply the scaling: multiply each row of normal_draws by its t_scale.
    t_draws = normal_draws * t_scale[:, np.newaxis]

    # Add the mean back to get final log return draws.
    draws = t_draws + mean_daily[np.newaxis, :]

    # Reshape to (simulations, days, n_assets).
    draws = draws.reshape(simulations, days, n_assets)

    return draws


def _metrics(final_values, initial_value: float):
    """Compute summary statistics from the distribution of final simulated values.

    Returns percentiles (p05 through p95), probability of gain/loss,
    Value-at-Risk (VaR), and Conditional VaR (CVaR / Expected Shortfall).

    VaR at 5%: the dollar amount you could lose with 95% confidence.
    CVaR at 5%: the average loss in the worst 5% of scenarios — always
    worse than VaR, and is the preferred risk metric post-Basel III because
    it accounts for how bad the tail actually is, not just where it starts.
    """
    import numpy as np

    losses = final_values[final_values < initial_value]
    p05 = _percentile(final_values, 5)
    cvar_5 = _finite_or_none(losses.mean()) if len(losses) else p05
    return {
        "initial_value": _finite_or_none(initial_value),
        "expected_final": _finite_or_none(final_values.mean()),
        "p05": p05,
        "p25": _percentile(final_values, 25),
        "p50": _percentile(final_values, 50),
        "p75": _percentile(final_values, 75),
        "p95": _percentile(final_values, 95),
        "expected_return_pct": _finite_or_none((final_values.mean() / initial_value - 1) * 100) if initial_value else None,
        "probability_gain_pct": _finite_or_none((final_values > initial_value).mean() * 100),
        "probability_loss_pct": _finite_or_none((final_values < initial_value).mean() * 100),
        "var_5": _finite_or_none(initial_value - p05) if p05 is not None else None,
        "cvar_5": _finite_or_none(initial_value - cvar_5) if cvar_5 is not None else None,
        "sample_count": int(np.asarray(final_values).shape[0]),
    }


def run_monte_carlo(
    holdings: Iterable[Holding],
    candidate_symbols: Iterable[str] = (),
    *,
    days: int = 90,
    simulations: int = 3000,
    period: str = "1y",
    seed: int = 42,
) -> dict:
    """Run an enhanced correlated Monte Carlo portfolio simulation.

    Improvements over standard GBM:
      1. Student-t draws for fat tails (df estimated from data)
      2. GARCH(1,1) per-symbol volatility forecasting
      3. Implied volatility blend from options chains

    The API contract is unchanged: callers get the same JSON structure with
    the same fields. New metadata fields are added to document which
    enhancements were applied.

    Parameters
    ----------
    holdings : Iterable[Holding]
        Current portfolio positions with market values.
    candidate_symbols : Iterable[str]
        Additional symbols to simulate as standalone candidates.
    days : int
        Simulation horizon in trading days (5-252).
    simulations : int
        Number of Monte Carlo paths (500-20000).
    period : str
        Yahoo Finance history period for calibration (e.g. '1y', '2y').
    seed : int
        Random seed for reproducibility.

    Returns
    -------
    dict
        JSON-serializable result with 'portfolio', 'candidates', metadata.
    """
    import numpy as np

    # ---- Validate and clean inputs ----------------------------------------
    clean_holdings: list[Holding] = []
    for h in holdings:
        sym = _clean_symbol(h.symbol)
        if not sym or h.market_value <= 0:
            continue
        clean_holdings.append(Holding(sym, h.description, float(h.market_value), h.asset_type))

    candidate_list = []
    seen_candidates = set()
    for sym in candidate_symbols:
        cleaned = _clean_symbol(sym)
        if cleaned and cleaned not in seen_candidates:
            seen_candidates.add(cleaned)
            candidate_list.append(cleaned)

    portfolio_symbols = [h.symbol for h in clean_holdings]
    all_symbols = sorted(set(portfolio_symbols + candidate_list))
    if not all_symbols:
        return {"error": "No symbols to simulate", "portfolio": None, "candidates": []}

    # ---- Download historical prices ----------------------------------------
    close = _download_close(all_symbols, period)
    if close.empty:
        return {"error": "No historical prices returned", "portfolio": None, "candidates": []}

    # Compute daily log returns. Log returns are additive over time, which is
    # why we use them instead of simple returns for multi-day simulation.
    returns = np.log(close / close.shift(1)).replace([np.inf, -np.inf], np.nan).dropna(how="all")
    available = [s for s in all_symbols if s in returns.columns and returns[s].dropna().shape[0] >= MIN_HISTORY_ROWS]
    missing = [s for s in all_symbols if s not in available]
    if not available:
        return {
            "error": "Not enough historical return data",
            "portfolio": None,
            "candidates": [],
            "missing_symbols": missing,
        }

    returns = returns[available].dropna(how="any")
    if returns.shape[0] < MIN_HISTORY_ROWS:
        return {
            "error": "Not enough overlapping historical return data",
            "portfolio": None,
            "candidates": [],
            "missing_symbols": missing,
        }

    days = max(5, min(int(days), 252))
    simulations = max(500, min(int(simulations), 20000))
    rng = np.random.default_rng(seed)

    # ---- Compute base statistics from historical returns -------------------
    mean_daily = returns.mean().to_numpy(dtype=float)
    cov_daily = returns.cov().to_numpy(dtype=float)
    cov_daily = cov_daily + np.eye(cov_daily.shape[0]) * 1e-10
    historical_stds = returns.std().to_numpy(dtype=float)

    # ---- ENHANCEMENT 1: Estimate Student-t degrees of freedom --------------
    # Fit a Student-t to the pooled standardized residuals to determine how
    # fat-tailed the return distribution is. This replaces the implicit
    # df=infinity (normal) assumption of the original GBM.
    returns_matrix = returns.to_numpy(dtype=float)
    student_t_df = _estimate_student_t_df(returns_matrix)
    logger.info("Estimated Student-t df=%.1f (lower = fatter tails)", student_t_df)

    # ---- ENHANCEMENT 2: GARCH(1,1) volatility forecasting ------------------
    # Fit a GARCH model per symbol to get forward-looking vol estimates that
    # capture recent volatility clustering. If vol has been elevated, the
    # GARCH forecast will be higher than the naive historical average.
    garch_vols = _fit_garch_volatilities(returns, available, forecast_days=days)

    # ---- ENHANCEMENT 3: Implied volatility from options --------------------
    # Pull ATM implied vol from the options market. This injects forward-
    # looking information (earnings, macro events) that historical data alone
    # cannot capture. Blend with GARCH vol using IV_WEIGHT.
    implied_vols = _fetch_implied_volatilities(available)
    blended_vols = _blend_volatilities(garch_vols, implied_vols, available)

    # Track which enhancements were successfully applied per symbol.
    enhancement_details = {}
    for sym in available:
        enhancement_details[sym] = {
            "historical_vol": _finite_or_none(historical_stds[available.index(sym)]),
            "garch_vol": _finite_or_none(garch_vols.get(sym)),
            "implied_vol_annual": _finite_or_none(implied_vols.get(sym)),
            "blended_vol": _finite_or_none(blended_vols.get(sym)),
            "used_implied_vol": implied_vols.get(sym) is not None,
        }

    # ---- Generate enhanced simulation draws --------------------------------
    # Uses Student-t distribution with GARCH+IV blended covariance.
    draws = _generate_enhanced_draws(
        mean_daily=mean_daily,
        cov_daily=cov_daily,
        blended_vols=blended_vols,
        historical_stds=historical_stds,
        available_symbols=available,
        student_t_df=student_t_df,
        simulations=simulations,
        days=days,
        rng=rng,
    )

    # Convert log return draws to cumulative growth factors.
    # exp(cumsum(log_returns)) gives the multiplicative growth from day 0.
    cumulative = np.exp(np.cumsum(draws, axis=1))
    symbol_index = {sym: i for i, sym in enumerate(available)}

    # ---- Portfolio-level simulation ----------------------------------------
    portfolio = None
    used_holdings = [h for h in clean_holdings if h.symbol in symbol_index]
    if used_holdings:
        values = np.array([h.market_value for h in used_holdings], dtype=float)
        indices = [symbol_index[h.symbol] for h in used_holdings]
        # Tensor dot: for each simulation path, multiply each symbol's growth
        # factor by its current market value, then sum across positions to get
        # the total portfolio value at each time step.
        portfolio_paths = np.tensordot(cumulative[:, :, indices], values, axes=([2], [0]))
        initial_value = float(values.sum())
        final_values = portfolio_paths[:, -1]
        bands = []
        for day in range(days):
            day_values = portfolio_paths[:, day]
            bands.append({
                "day": day + 1,
                "p05": _percentile(day_values, 5),
                "p50": _percentile(day_values, 50),
                "p95": _percentile(day_values, 95),
            })

        portfolio = {
            **_metrics(final_values, initial_value),
            "days": days,
            "period": period,
            "symbols_used": [h.symbol for h in used_holdings],
            "symbols_missing": [h.symbol for h in clean_holdings if h.symbol not in symbol_index],
            "bands": bands,
            "note": (
                "Enhanced Monte Carlo: Student-t fat tails (df={:.1f}), "
                "GARCH(1,1) volatility forecasting, implied vol blend (weight={:.0%}). "
                "Uses historical log returns and correlation from Yahoo prices."
            ).format(student_t_df, IV_WEIGHT),
        }

    # ---- Per-holding simulation (individual position risk/reward) -----------
    # Compute the same per-symbol metrics for each portfolio holding so the
    # frontend can rank which existing positions have the best forward outlook.
    # This lets the user see "which of my current holdings should I add to?"
    position_details = []
    annual_mean = returns.mean() * 252
    annual_vol = returns.std() * np.sqrt(252)
    for h in used_holdings:
        idx = symbol_index[h.symbol]
        price = close[h.symbol].dropna().iloc[-1] if h.symbol in close else None
        if price is not None and float(price) > 0:
            simulated_prices = float(price) * cumulative[:, -1, idx]
            initial_price = float(price)
        else:
            simulated_prices = cumulative[:, -1, idx]
            initial_price = 1.0
        metric = _metrics(simulated_prices, initial_price)
        downside = (initial_price - (metric["p05"] or initial_price))
        upside = ((metric["p50"] or initial_price) - initial_price)
        score = _finite_or_none(upside / downside) if downside and downside > 0 else None
        sym = h.symbol
        position_details.append({
            "symbol": sym,
            "description": h.description,
            "market_value": _finite_or_none(h.market_value),
            "last_price": _finite_or_none(price),
            "annual_return_pct": _finite_or_none(annual_mean[sym] * 100) if sym in annual_mean.index else None,
            "annual_vol_pct": _finite_or_none(annual_vol[sym] * 100) if sym in annual_vol.index else None,
            "sharpe_like": _finite_or_none(annual_mean[sym] / annual_vol[sym]) if sym in annual_vol.index and annual_vol[sym] else None,
            "risk_reward_score": score,
            **metric,
        })
    # Sort by risk/reward descending — best opportunities first.
    position_details.sort(key=lambda p: p.get("risk_reward_score") or -999, reverse=True)

    # ---- Candidate-level simulation ----------------------------------------
    candidates = []
    for sym in candidate_list:
        if sym not in symbol_index:
            candidates.append({"symbol": sym, "status": "missing_history"})
            continue
        idx = symbol_index[sym]
        price = close[sym].dropna().iloc[-1] if sym in close else None
        simulated_prices = float(price) * cumulative[:, -1, idx] if price is not None else cumulative[:, -1, idx]
        metric = _metrics(simulated_prices, float(price) if price is not None else 1.0)
        downside = (float(price) - (metric["p05"] or float(price))) if price is not None else None
        upside = ((metric["p50"] or float(price)) - float(price)) if price is not None else None
        score = _finite_or_none(upside / downside) if downside and downside > 0 and upside is not None else None
        candidates.append({
            "symbol": sym,
            "status": "ok",
            "last_price": _finite_or_none(price),
            "annual_return_pct": _finite_or_none(annual_mean[sym] * 100),
            "annual_vol_pct": _finite_or_none(annual_vol[sym] * 100),
            "sharpe_like": _finite_or_none(annual_mean[sym] / annual_vol[sym]) if annual_vol[sym] else None,
            "risk_reward_score": score,
            **metric,
        })

    candidates.sort(key=lambda c: (c.get("status") == "ok", c.get("risk_reward_score") or -999), reverse=True)

    return {
        "portfolio": portfolio,
        "position_details": position_details,
        "candidates": candidates,
        "missing_symbols": missing,
        "history_rows": int(returns.shape[0]),
        "history_start": str(returns.index[0])[:10],
        "history_end": str(returns.index[-1])[:10],
        # New metadata documenting the enhancements applied.
        "enhancements": {
            "student_t_df": _finite_or_none(student_t_df),
            "iv_weight": IV_WEIGHT,
            "garch_model": "GARCH(1,1) with Student-t innovations",
            "per_symbol": enhancement_details,
        },
    }
