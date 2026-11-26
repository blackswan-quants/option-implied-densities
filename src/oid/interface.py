
"""Pipeline interface for P4, option-implied densities around news (Part C).
 
Signatures only, no implementation yet.
 
Conventions (used by every module):
 
- k = ln(K / F): log-forward-moneyness. Densities, CDFs and the realised move
  X = ln(S_T / F) all live on this axis.
- Timestamps are timezone-aware (naive datetimes are rejected).
  SPXW are PM-settled: expiry = 16:00 America/New_York on the expiry date.
- T is in years, calendar time:
  T = (expiry - as_of).total_seconds() / (365 * 24 * 3600).
- r is the annual continuously compounded risk-free rate, D = exp(-r * T).
- F is the forward implied by put-call parity: C - P = D * (F - K).
- w(k) = sigma_impl(k)**2 * T is the total implied variance.
- Prices are in index points.
- The pipeline knows nothing about events: it takes a chain, as_of, expiry
  and r. The link with the event calendar is done downstream (part B).
 
Chain format (pandas DataFrame, one row per option):
 
- strike: float, strike K in index points
- option_type: str, "C" or "P"
- bid, ask: float, quotes in index points
- mid: float, (bid + ask) / 2
"""
 
from __future__ import annotations
 
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any
 
import numpy as np
import numpy.typing as npt
import pandas as pd
 
FloatArray = npt.NDArray[np.float64]
"""Array of floats."""
 
DistFn = Callable[[npt.ArrayLike], FloatArray]
"""Function of k (or p for ppf) returning an array, e.g. cdf, sf, ppf."""
 
CHAIN_COLUMNS = ["strike", "option_type", "bid", "ask", "mid"]
 
 
# ---------------------------------------------------------------------------
# Objects passed between functions
# ---------------------------------------------------------------------------
 
 
@dataclass(frozen=True)
class SVIParams:
    """Raw SVI parameters for one expiry.
 
    w(k) = a + b * (rho * (k - m) + sqrt((k - m)**2 + sigma**2))
 
    Constraints: b >= 0, |rho| < 1, sigma > 0,
    a + b * sigma * sqrt(1 - rho**2) >= 0.
    T is stored so that w can be turned back into implied vols.
    """
 
    a: float
    b: float
    rho: float
    m: float
    sigma: float
    T: float
 
 
@dataclass
class DensityResult:
    """Output of run_pipeline for one snapshot (one chain, one expiry).
 
    This is what part B uses for H1 and H2.
    """
 
    # snapshot
    as_of: datetime  # tz-aware time of the snapshot
    expiry: datetime  # tz-aware expiry time
    T: float  # years
    F: float  # forward, index points
    D: float  # discount factor exp(-rT)
 
    # density of x = ln(S_T / F)
    k_grid: FloatArray  # increasing grid of k
    q: FloatArray  # q(k) on k_grid, integrates to ~1
    cdf: DistFn  # Q(x <= k), any k, values strictly in (0, 1)
    sf: DistFn  # Q(x > k), computed directly (not 1 - cdf)
    ppf: DistFn | None  # inverse cdf, ppf(p) -> k (optional, for quantiles / IQR)
 
    # market data
    # 2 rows, the strikes just below and just above F. Columns: strike,
    # call_bid, call_ask, call_mid, put_bid, put_ask, put_mid
    atm_quotes: pd.DataFrame
    k_min_quoted: float  # smallest k actually used in the SVI fit
    k_max_quoted: float  # largest k actually used in the SVI fit
 
    # fit quality
    svi_params: SVIParams
    svi_rmse_iv: float  # RMSE fitted vs market implied vol (0.01 = 1 vol point)
    g_min: float  # min of g(k) on k_grid, must be >= 0 (no butterfly arbitrage)
    mass_in_grid: float  # integral of q over k_grid, should be close to 1
    n_quotes: int  # number of OTM quotes used in the fit
 
    def is_ok(
        self,
        max_rmse_iv: float = 0.01,
        min_mass: float = 0.999,
        g_tol: float = 1e-8,
    ) -> bool:
        """Check whether the snapshot passes the quality checks.
 
        Default thresholds are proposals, to agree with B.
 
        Parameters
        ----------
        max_rmse_iv : float
            Maximum allowed svi_rmse_iv.
        min_mass : float
            Minimum allowed mass_in_grid.
        g_tol : float
            Numerical tolerance, the check is g_min >= -g_tol.
 
        Returns
        -------
        bool
            True if all checks pass.
        """
        raise NotImplementedError
 
 
# ---------------------------------------------------------------------------
# Chain preparation
# ---------------------------------------------------------------------------
 
 
def time_to_expiry(as_of: datetime, expiry: datetime) -> float:
    """Compute T in years (calendar time) between two tz-aware datetimes.
 
    Parameters
    ----------
    as_of : datetime
        Snapshot time, timezone-aware.
    expiry : datetime
        Expiry time, timezone-aware.
 
    Returns
    -------
    float
        Time to expiry in years.
 
    Raises
    ------
    ValueError
        If a datetime is naive or if expiry <= as_of.
    """
    raise NotImplementedError
 
 
def clean_chain(
    chain: pd.DataFrame,
    max_rel_spread: float = 0.5,
    min_bid: float = 0.0,
) -> pd.DataFrame:
    """Remove bad quotes from a chain.
 
    Drops missing or zero bids, ask < bid, spreads wider than
    max_rel_spread * mid and duplicated strikes.
 
    Parameters
    ----------
    chain : pd.DataFrame
        Raw chain with columns CHAIN_COLUMNS.
    max_rel_spread : float
        Maximum (ask - bid) / mid.
    min_bid : float
        Quotes with bid <= min_bid are dropped.
 
    Returns
    -------
    pd.DataFrame
        Cleaned chain with the same columns.
    """
    raise NotImplementedError
 
 
def implied_forward(chain: pd.DataFrame, r: float, T: float) -> float:  # noqa: N803
    """Compute the forward F from put-call parity C - P = D (F - K).
 
    Uses the strikes where both a call and a put are quoted, closest to the
    money.
 
    Parameters
    ----------
    chain : pd.DataFrame
        Cleaned chain.
    r : float
        Annual continuously compounded rate.
    T : float
        Time to expiry in years.
 
    Returns
    -------
    float
        Forward, index points.
    """
    raise NotImplementedError
 
 
def atm_quotes(chain: pd.DataFrame, F: float) -> pd.DataFrame:  # noqa: N803
    """Get the call and put quotes at the two strikes bracketing F.
 
    Both strikes must have a call and a put.
 
    Parameters
    ----------
    chain : pd.DataFrame
        Cleaned chain.
    F : float
        Forward, index points.
 
    Returns
    -------
    pd.DataFrame
        Two rows, columns as in DensityResult.atm_quotes.
    """
    raise NotImplementedError
 
 
def implied_vols(
    chain: pd.DataFrame,
    F: float,  # noqa: N803
    r: float,
    T: float,  # noqa: N803
    weighting: str = "inv_spread",
) -> pd.DataFrame:
    """Compute Black-76 implied vols of OTM options only.
 
    Puts for K < F, calls for K >= F.
 
    Parameters
    ----------
    chain : pd.DataFrame
        Cleaned chain.
    F : float
        Forward, index points.
    r : float
        Annual continuously compounded rate.
    T : float
        Time to expiry in years.
    weighting : str
        Weights for the SVI fit: "inv_spread" gives 1 / (ask - bid),
        "equal" gives 1.
 
    Returns
    -------
    pd.DataFrame
        Columns strike, k, option_type, mid, iv, w, weight. iv is annualised
        and w = iv**2 * T.
    """
    raise NotImplementedError
 
 
# ---------------------------------------------------------------------------
# SVI
# ---------------------------------------------------------------------------
 
 
def fit_svi(
    k: FloatArray,
    w: FloatArray,
    weights: FloatArray,
    T: float,  # noqa: N803
) -> SVIParams:
    """Fit raw SVI to total variance w(k) by weighted least squares.
 
    Parameters
    ----------
    k : FloatArray
        Log-forward-moneyness of the quotes.
    w : FloatArray
        Market total implied variance.
    weights : FloatArray
        Weight of each quote.
    T : float
        Time to expiry in years.
 
    Returns
    -------
    SVIParams
        Fitted parameters.
    """
    raise NotImplementedError
 
 
def svi_w(params: SVIParams, k: npt.ArrayLike) -> FloatArray:
    """Compute the total implied variance w(k).
 
    Parameters
    ----------
    params : SVIParams
        SVI parameters.
    k : array_like
        Log-forward-moneyness.
 
    Returns
    -------
    FloatArray
        w(k).
    """
    raise NotImplementedError
 
 
def svi_w_derivatives(
    params: SVIParams, k: npt.ArrayLike
) -> tuple[FloatArray, FloatArray]:
    """Compute the first and second derivatives of w.
 
    Parameters
    ----------
    params : SVIParams
        SVI parameters.
    k : array_like
        Log-forward-moneyness.
 
    Returns
    -------
    tuple of FloatArray
        w'(k) and w''(k).
    """
    raise NotImplementedError
 
 
def svi_g(params: SVIParams, k: npt.ArrayLike) -> FloatArray:
    """Compute the Gatheral-Jacquier function g(k).
 
    g = (1 - k w' / (2w))**2 - (w'**2 / 4) (1/w + 1/4) + w'' / 2.
    No butterfly arbitrage <=> g(k) >= 0 for all k.
 
    Parameters
    ----------
    params : SVIParams
        SVI parameters.
    k : array_like
        Log-forward-moneyness.
 
    Returns
    -------
    FloatArray
        g(k).
    """
    raise NotImplementedError
 
 
# ---------------------------------------------------------------------------
# Density
# ---------------------------------------------------------------------------
 
 
def make_k_grid(
    params: SVIParams, n_sd: float = 10.0, n_points: int = 2001
) -> FloatArray:
    """Build a uniform k grid of +/- n_sd ATM standard deviations.
 
    The ATM standard deviation is sqrt(w(0)).
 
    Parameters
    ----------
    params : SVIParams
        SVI parameters.
    n_sd : float
        Half-width of the grid in ATM standard deviations.
    n_points : int
        Number of grid points.
 
    Returns
    -------
    FloatArray
        Increasing grid of k.
    """
    raise NotImplementedError
 
 
def density(params: SVIParams, k_grid: FloatArray) -> FloatArray:
    """Compute the density q(k) of x = ln(S_T / F).
 
    q(k) = g(k) / sqrt(2 pi w(k)) * exp(-d2(k)**2 / 2), with
    d2(k) = -k / sqrt(w(k)) - sqrt(w(k)) / 2.
 
    Parameters
    ----------
    params : SVIParams
        SVI parameters.
    k_grid : FloatArray
        Grid of k.
 
    Returns
    -------
    FloatArray
        q(k) on k_grid.
    """
    raise NotImplementedError
 
 
def svi_sf(params: SVIParams, k: npt.ArrayLike) -> FloatArray:
    """Compute the analytic survival function Q(x > k).
 
    sf(k) = N(d2) - phi(d2) w'(k) / (2 sqrt(w(k))). Valid at any k, not only
    on the grid.
 
    Parameters
    ----------
    params : SVIParams
        SVI parameters.
    k : array_like
        Log-forward-moneyness.
 
    Returns
    -------
    FloatArray
        Q(x > k).
    """
    raise NotImplementedError
 
 
def svi_cdf(params: SVIParams, k: npt.ArrayLike) -> FloatArray:
    """Compute the analytic CDF Q(x <= k).
 
    cdf(k) = N(-d2) + phi(d2) w'(k) / (2 sqrt(w(k))).
 
    Parameters
    ----------
    params : SVIParams
        SVI parameters.
    k : array_like
        Log-forward-moneyness.
 
    Returns
    -------
    FloatArray
        Q(x <= k).
    """
    raise NotImplementedError
 
 
# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------
 
 
def run_pipeline(
    chain: pd.DataFrame,
    as_of: datetime,
    expiry: datetime,
    r: float,
    max_rel_spread: float = 0.5,
    min_bid: float = 0.0,
    weighting: str = "inv_spread",
    n_sd: float = 10.0,
    n_points: int = 2001,
) -> DensityResult:
    """Run the full pipeline on one chain.
 
    Chain -> clean -> F -> IVs -> SVI -> density, cdf, sf, flags. The optional
    arguments are passed to clean_chain, implied_vols and make_k_grid; their
    defaults are proposals, to be tuned on the synthetic tests.
 
    Parameters
    ----------
    chain : pd.DataFrame
        Raw chain with columns CHAIN_COLUMNS.
    as_of : datetime
        Snapshot time, timezone-aware.
    expiry : datetime
        Expiry time, timezone-aware.
    r : float
        Annual continuously compounded rate.
    max_rel_spread : float
        See clean_chain.
    min_bid : float
        See clean_chain.
    weighting : str
        See implied_vols.
    n_sd : float
        See make_k_grid.
    n_points : int
        See make_k_grid.
 
    Returns
    -------
    DensityResult
        Density, cdf, sf, market quotes and quality flags.
    """
    raise NotImplementedError
 
 
# ---------------------------------------------------------------------------
# Synthetic data (validation)
# ---------------------------------------------------------------------------
 
 
def make_synthetic_chain(
    model: dict[str, Any],
    strikes: FloatArray,
    as_of: datetime,
    expiry: datetime,
    r: float,
    noise: float,
    seed: int = 0,
) -> tuple[pd.DataFrame, DistFn]:
    """Price a chain under a known model and add quote noise.
 
    Parameters
    ----------
    model : dict
        Model and its parameters, e.g.
        {"name": "bs", "S0": 5000.0, "sigma": 0.15, "div_yield": 0.0}.
    strikes : FloatArray
        Strikes, index points.
    as_of : datetime
        Snapshot time, timezone-aware.
    expiry : datetime
        Expiry time, timezone-aware.
    r : float
        Annual continuously compounded rate.
    noise : float
        Standard deviation of the noise added to the mid prices, index points.
    seed : int
        Seed of the random generator.
 
    Returns
    -------
    tuple
        (chain, true_density), where true_density(k) is the exact q(k).
    """
    raise NotImplementedError
