"""A) The course examples, reproduced to 0.01 percentage point."""

import numpy as np
import pandas as pd
import pytest

from core.utilities import risk_budget_weights
from logic.covariance import _target, ledoit_wolf_cc, shrinkage_intensity
from logic.diversification import herfindahl_star, shannon_star
from logic.risk import decomposition, gaussian_var_es, sharpe, volatility

TOL = 1e-4  # 0.01 percentage point


def ln5_cov() -> pd.DataFrame:
    """LN 5 Examples 2 and 4: σ = 30/20/15%, ρ12 = 0.8, ρ13 = 0.5, ρ23 = 0.3."""
    vol = np.array([0.30, 0.20, 0.15])
    rho = np.array([[1, 0.8, 0.5], [0.8, 1, 0.3], [0.5, 0.3, 1]])
    return pd.DataFrame(np.outer(vol, vol) * rho)


def test_ln5_example2_risk_decomposition():
    """x = (50, 20, 30)% -> σ = 20.87%, RC = (14.70, 3.33, 2.85)%, RC* = (70.43, 15.93, 13.64)%."""
    table = decomposition(pd.Series([0.5, 0.2, 0.3]), ln5_cov())
    assert volatility(pd.Series([0.5, 0.2, 0.3]), ln5_cov()) == pytest.approx(0.2087, abs=TOL)
    assert np.allclose(table["RC"], [0.1470, 0.0333, 0.0285], atol=TOL)
    assert np.allclose(table["RC*"], [0.7043, 0.1593, 0.1364], atol=TOL)
    assert table["RC"].sum() == pytest.approx(volatility(pd.Series([0.5, 0.2, 0.3]), ln5_cov()))


def test_ln5_example4_erc_and_risk_budgeting():
    """ERC x = (19.69, 32.44, 47.87)%, σ = 16.13%; RB b = (50, 20, 30)%: x = (31.15, 21.90, 46.96)%, σ = 17.49%."""
    erc = risk_budget_weights(ln5_cov())
    assert np.allclose(erc, [0.1969, 0.3244, 0.4787], atol=TOL)
    assert volatility(erc, ln5_cov()) == pytest.approx(0.1613, abs=TOL)
    rb = risk_budget_weights(ln5_cov(), pd.Series([0.5, 0.2, 0.3]))
    assert np.allclose(rb, [0.3115, 0.2190, 0.4696], atol=TOL)
    assert volatility(rb, ln5_cov()) == pytest.approx(0.1749, abs=TOL)
    assert np.allclose(decomposition(rb, ln5_cov())["RC*"], [0.5, 0.2, 0.3], atol=TOL)


def test_ln5_lab_constant_correlation_erc_is_inverse_vol():
    """σ = (30, 25, 20, 15)%, ρ = 0.7 everywhere -> x_i ∝ 1/σ_i."""
    vol = np.array([0.30, 0.25, 0.20, 0.15])
    corr = np.full((4, 4), 0.7)
    np.fill_diagonal(corr, 1.0)
    x = risk_budget_weights(pd.DataFrame(np.outer(vol, vol) * corr))
    assert np.allclose(x, (1 / vol) / (1 / vol).sum(), atol=TOL)


def test_ln6_example8_gaussian_var_es():
    """μ = 0, same portfolio as Example 2: VaR99 = 48.55%, ES99 = 55.62%."""
    var, es = gaussian_var_es(0.0, volatility(pd.Series([0.5, 0.2, 0.3]), ln5_cov()), 0.99)
    assert var == pytest.approx(0.4855, abs=TOL)
    assert es == pytest.approx(0.5562, abs=TOL)


def test_diversification_extremes():
    """Equal weights: H* = 0 and I* = n; one asset: H* = 1."""
    n = 5
    equal = pd.Series(np.full(n, 1 / n))
    assert herfindahl_star(equal) == pytest.approx(0.0)
    assert shannon_star(equal) == pytest.approx(n)
    assert herfindahl_star(pd.Series([1.0, 0, 0, 0, 0])) == pytest.approx(1.0)


def test_ln2_mixing_with_the_risk_free_asset():
    """y = (1 − α) r + α x: σ(y) = α σ(x) and SR(y) = SR(x)."""
    cov, x, mu, r, alpha = ln5_cov(), pd.Series([0.5, 0.2, 0.3]), pd.Series([0.08, 0.06, 0.04]), 0.02, 0.4
    mu_x, sigma_x = float(x @ mu), volatility(x, cov)
    mu_y, sigma_y = (1 - alpha) * r + alpha * mu_x, volatility(alpha * x, cov)
    assert sigma_y == pytest.approx(alpha * sigma_x)
    assert sharpe(mu_y, sigma_y, r) == pytest.approx(sharpe(mu_x, sigma_x, r))


def test_ln3_shrinkage_matches_the_formula_term_by_term():
    """Vectorised δ equals a direct loop over the Ledoit-Wolf (2004) sums, and Σ̂ = δF + (1−δ)S."""
    rng = np.random.default_rng(0)
    x = rng.standard_normal((60, 4)) @ np.diag([1.0, 2.0, 0.5, 1.5])
    x = x - x.mean(axis=0)
    t, n = x.shape
    s = x.T @ x / t
    f, rho_bar = _target(s)
    pi = sum(((x[:, i] * x[:, j] - s[i, j]) ** 2).mean() for i in range(n) for j in range(n))
    def theta(i, j):
        """θ_ii,ij of Ledoit and Wolf (2004)."""
        return ((x[:, i] ** 2 - s[i, i]) * (x[:, i] * x[:, j] - s[i, j])).mean()

    rho = sum(((x[:, i] ** 2 - s[i, i]) ** 2).mean() for i in range(n)) + sum(
        rho_bar / 2 * (np.sqrt(s[j, j] / s[i, i]) * theta(i, j) + np.sqrt(s[i, i] / s[j, j]) * theta(j, i))
        for i in range(n) for j in range(n) if i != j)
    delta = np.clip((pi - rho) / ((f - s) ** 2).sum() / t, 0, 1)
    assert shrinkage_intensity(x, s, f, rho_bar) == pytest.approx(delta)
    shrunk = ledoit_wolf_cc(pd.DataFrame(x)).to_numpy() / 252
    assert np.allclose(shrunk, delta * f + (1 - delta) * s)
