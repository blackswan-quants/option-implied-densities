import numpy as np
import pytest
from numpy.typing import NDArray
from scipy.stats import lognorm

from oid.density.checks import check_density


def _lognormal_density(
    spot: float = 100.0, vol: float = 0.2, maturity: float = 0.25
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    strikes = np.linspace(1.0, 400.0, 4000)
    sigma = vol * np.sqrt(maturity)
    density = lognorm.pdf(strikes, s=sigma, scale=spot * np.exp(-0.5 * sigma**2))
    return strikes, np.asarray(density, dtype=np.float64)


def test_lognormal_density_is_admissible() -> None:
    strikes, density = _lognormal_density()
    mass = check_density(strikes, density, mass_tol=1e-6)
    assert mass == pytest.approx(1.0, abs=1e-6)


def test_negative_density_is_rejected() -> None:
    strikes, density = _lognormal_density()
    density[100] = -1e-3
    with pytest.raises(AssertionError, match="negative"):
        check_density(strikes, density)


def test_unsorted_strikes_are_rejected() -> None:
    strikes, density = _lognormal_density()
    with pytest.raises(AssertionError, match="increasing"):
        check_density(strikes[::-1], density)


def test_missing_mass_is_rejected() -> None:
    strikes, density = _lognormal_density()
    with pytest.raises(AssertionError, match="mass"):
        check_density(strikes, 0.5 * density)
