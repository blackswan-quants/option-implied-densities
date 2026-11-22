"""Admissibility checks for risk-neutral densities."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def check_density(
    strikes: NDArray[np.float64],
    density: NDArray[np.float64],
    *,
    mass_tol: float = 1e-2,
) -> float:
    """Assert that a density on a strike grid is admissible.

    The density must be finite and non-negative, and its total mass must be
    within ``mass_tol`` of one. Some mass is always lost in the tails
    outside the quoted strikes, so the tolerance should reflect how far the
    grid extends.

    Parameters
    ----------
    strikes : ndarray of shape (n,)
        Strictly increasing strike grid.
    density : ndarray of shape (n,)
        Density values on ``strikes``.
    mass_tol : float, default 1e-2
        Allowed deviation of the total mass from one.

    Returns
    -------
    float
        Total mass of the density, by the trapezoidal rule.

    Raises
    ------
    AssertionError
        If any of the conditions above fails.
    """
    assert strikes.ndim == 1, "strikes must be one-dimensional"
    assert strikes.shape == density.shape, "strikes and density shapes differ"
    assert strikes.size >= 2, "need at least two strikes"
    assert np.all(np.diff(strikes) > 0), "strikes must be strictly increasing"
    assert np.all(np.isfinite(density)), "density has non-finite values"
    assert np.all(density >= 0.0), "density has negative values"

    mass = float(np.trapezoid(density, strikes))
    assert abs(mass - 1.0) <= mass_tol, f"density mass {mass:.4f} is not close to 1"
    return mass
