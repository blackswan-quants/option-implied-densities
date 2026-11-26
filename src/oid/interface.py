"""
P4 - Option-implied densities around news
Part C: pipeline interface (signatures only, no implementation yet)

Conventions (used by every module):
- k = ln(K / F): log-forward-moneyness. Densities, CDFs and the realised move
  X = ln(S_T / F) all live on this axis.
- Timestamps are timezone-aware (naive datetimes are rejected).
  SPXW are PM-settled: expiry = 16:00 America/New_York on the expiry date.
- T is in years, calendar time: T = (expiry - as_of).total_seconds() / (365 * 24 * 3600).
- r is the annual continuously compounded risk-free rate, D = exp(-r * T).
- F is the forward implied by put-call parity: C - P = D * (F - K).
- w(k) = sigma_impl(k)**2 * T is the total implied variance.
- Prices are in index points.
- The pipeline knows nothing about events: it takes a chain, as_of, expiry and r.
  The link with the event calendar is done downstream (part B).

Chain format (pandas DataFrame, one row per option):
    strike       float   strike K, index points
    option_type  str     "C" or "P"
    bid, ask     float   quotes, index points
    mid          float   (bid + ask) / 2
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional

import numpy as np
import pandas as pd
from numpy.typing import ArrayLike

CHAIN_COLUMNS = ["strike", "option_type", "bid", "ask", "mid"]


# ---------------------------------------------------------------------------
# Objects passed between functions
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SVIParams:
    """Raw SVI parameters for one expiry.

    w(k) = a + b * (rho * (k - m) + sqrt((k - m)**2 + sigma**2))

    Constraints: b >= 0, |rho| < 1, sigma > 0, a + b * sigma * sqrt(1 - rho**2) >= 0.
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
    as_of: datetime            # tz-aware time of the snapshot
    expiry: datetime           # tz-aware expiry time
    T: float                   # years
    F: float                   # forward, index points
    D: float                   # discount factor exp(-rT)

    # density of x = ln(S_T / F)
    k_grid: np.ndarray         # increasing grid of k
    q: np.ndarray              # q(k) on k_grid, integrates to ~1
    cdf: Callable              # cdf(k) = Q(x <= k), any k, values strictly in (0, 1)
    sf: Callable               # sf(k) = Q(x > k), computed directly (not 1 - cdf)
    ppf: Optional[Callable]    # inverse cdf, ppf(p) -> k (optional, for quantiles / IQR)

    # market data
    atm_quotes: pd.DataFrame   # 2 rows, the strikes just below and just above F
                               # columns: strike, call_bid, call_ask, call_mid,
                               #          put_bid, put_ask, put_mid
    k_min_quoted: float        # smallest k actually used in the SVI fit
    k_max_quoted: float        # largest k actually used in the SVI fit

    # fit quality
    svi_params: SVIParams
    svi_rmse_iv: float         # RMSE fitted vs market implied vol (0.01 = 1 vol point)
    g_min: float               # min of g(k) on k_grid, must be >= 0 (no butterfly arbitrage)
    mass_in_grid: float        # integral of q over k_grid, should be close to 1
    n_quotes: int              # number of OTM quotes used in the fit

    def is_ok(self, max_rmse_iv: float = 0.01, min_mass: float = 0.999,
              g_tol: float = 1e-8) -> bool:
        """True if svi_rmse_iv <= max_rmse_iv, mass_in_grid >= min_mass and
        g_min >= -g_tol. Default thresholds are proposals, to agree with B."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Chain preparation
# ---------------------------------------------------------------------------

def time_to_expiry(as_of: datetime, expiry: datetime) -> float:
    """T in years (calendar time) between two tz-aware datetimes.
    Raises ValueError if a datetime is naive or if expiry <= as_of."""
    raise NotImplementedError


def clean_chain(chain: pd.DataFrame, max_rel_spread: float = 0.5,
                min_bid: float = 0.0) -> pd.DataFrame:
    """Remove bad quotes: missing / zero bids, ask < bid, spreads wider than
    max_rel_spread * mid, duplicated strikes. Returns a chain with the same columns."""
    raise NotImplementedError


def implied_forward(chain: pd.DataFrame, r: float, T: float) -> float:
    """Forward F from put-call parity C - P = D (F - K), using the strikes
    where both a call and a put are quoted, closest to the money. Index points."""
    raise NotImplementedError


def atm_quotes(chain: pd.DataFrame, F: float) -> pd.DataFrame:
    """Call and put quotes (bid, ask, mid) at the two strikes bracketing F.
    Both strikes must have a call and a put. Columns as in DensityResult.atm_quotes."""
    raise NotImplementedError


def implied_vols(chain: pd.DataFrame, F: float, r: float, T: float,
                 weighting: str = "inv_spread") -> pd.DataFrame:
    """Black-76 implied vols of OTM options only (puts for K < F, calls for K >= F).
    Returns a DataFrame with columns: strike, k, option_type, mid, iv, w, weight.
    iv is annualised, w = iv**2 * T. weight is used in the SVI fit:
    weighting="inv_spread" -> 1 / (ask - bid), weighting="equal" -> 1."""
    raise NotImplementedError


# ---------------------------------------------------------------------------
# SVI
# ---------------------------------------------------------------------------

def fit_svi(k: np.ndarray, w: np.ndarray, weights: np.ndarray, T: float) -> SVIParams:
    """Weighted least-squares fit of raw SVI to total variance w(k)."""
    raise NotImplementedError


def svi_w(params: SVIParams, k: ArrayLike) -> np.ndarray:
    """Total implied variance w(k)."""
    raise NotImplementedError


def svi_w_derivatives(params: SVIParams, k: ArrayLike) -> tuple[np.ndarray, np.ndarray]:
    """First and second derivatives w'(k), w''(k)."""
    raise NotImplementedError


def svi_g(params: SVIParams, k: ArrayLike) -> np.ndarray:
    """Gatheral-Jacquier g(k):
    g = (1 - k w' / (2w))**2 - (w'**2 / 4) (1/w + 1/4) + w'' / 2.
    No butterfly arbitrage <=> g(k) >= 0 for all k."""
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Density
# ---------------------------------------------------------------------------

def make_k_grid(params: SVIParams, n_sd: float = 10.0, n_points: int = 2001) -> np.ndarray:
    """Uniform k grid of +/- n_sd ATM standard deviations (sqrt(w(0)))."""
    raise NotImplementedError


def density(params: SVIParams, k_grid: np.ndarray) -> np.ndarray:
    """q(k) = g(k) / sqrt(2 pi w(k)) * exp(-d2(k)**2 / 2),
    d2(k) = -k / sqrt(w(k)) - sqrt(w(k)) / 2."""
    raise NotImplementedError


def svi_sf(params: SVIParams, k: ArrayLike) -> np.ndarray:
    """Analytic survival function Q(x > k) = N(d2) - phi(d2) w'(k) / (2 sqrt(w(k))).
    Valid at any k, not only on the grid."""
    raise NotImplementedError


def svi_cdf(params: SVIParams, k: ArrayLike) -> np.ndarray:
    """Analytic CDF Q(x <= k) = N(-d2) + phi(d2) w'(k) / (2 sqrt(w(k)))."""
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------

def run_pipeline(chain: pd.DataFrame, as_of: datetime, expiry: datetime, r: float,
                 max_rel_spread: float = 0.5, min_bid: float = 0.0,
                 weighting: str = "inv_spread", n_sd: float = 10.0,
                 n_points: int = 2001) -> DensityResult:
    """chain -> clean -> F -> IVs -> SVI -> density, cdf, sf, flags.
    as_of and expiry must be tz-aware. r annual, continuously compounded.
    The optional arguments are passed to clean_chain, implied_vols and make_k_grid;
    their defaults are proposals, to be tuned on the synthetic tests."""
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Synthetic data (validation)
# ---------------------------------------------------------------------------

def make_synthetic_chain(model: dict, strikes: np.ndarray, as_of: datetime,
                         expiry: datetime, r: float, noise: float,
                         seed: int = 0) -> tuple[pd.DataFrame, Callable]:
    """Price a chain under a known model and add quote noise.

    model: e.g. {"name": "bs", "S0": 5000.0, "sigma": 0.15, "div_yield": 0.0}
    noise: s.d. of the noise added to the mid prices, index points.
    Returns (chain, true_density) where true_density(k) is the exact q(k)."""
    raise NotImplementedError
