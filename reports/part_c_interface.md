# Part C: pipeline interface

Kamil (Part C)

The file `interface.py` sets up the structure of the pipeline: the objects that get passed between functions and the signature of each function. None of the functions are written yet (they all raise `NotImplementedError`), the idea is that each of us can now implement a piece on their own, and Francesco can already write the H1/H2 code against the output object.

The order of the steps is: `clean_chain`, then `implied_forward`, then `atm_quotes` and `implied_vols`, then `fit_svi`, and finally `svi_g`, `density`, `svi_cdf` and `svi_sf`, which together fill a `DensityResult`. `run_pipeline` does all of this in one call.

## Conventions

Everything is on the axis k = ln(K/F), the same one as Francesco's realised move X = ln(S_T/F). Datetimes must be timezone-aware, and for SPXW I put the expiry at 16:00 New York time. T is the number of calendar seconds between `as_of` and `expiry` divided by the seconds in a year. r is continuously compounded with D = exp(-rT), F comes from put-call parity, and w(k) = iv^2 * T. Prices are in index points.

The chain we feed in is just a pandas DataFrame with the columns `strike`, `option_type` ("C" or "P"), `bid`, `ask` and `mid`. The pipeline doesn't know anything about events, matching chains to releases is done afterwards with the calendar.

## Objects

`SVIParams` holds the five raw SVI parameters (a, b, rho, m, sigma) plus T. It is frozen so the fitted values can't be changed by mistake.

`DensityResult` is what comes out of `run_pipeline`, one per snapshot, and it has everything from section 7 of Francesco's plan:

- the snapshot info: `as_of`, `expiry`, `T`, `F`, `D`
- the density: `k_grid` and `q`, plus `cdf(k)` and `sf(k)`, which work at any k and stay strictly between 0 and 1 because they are computed from the SVI formula and not from the grid (sf is computed directly, not as 1 - cdf). I also added an optional `ppf`, the inverse cdf, which should help for the interquantile range.
- `atm_quotes`, with the call and put bid/ask/mid at the two strikes around F, and `k_min_quoted` / `k_max_quoted` for the range used in the fit
- the quality checks: `svi_rmse_iv`, `g_min`, `mass_in_grid`, `n_quotes`, the fitted `svi_params`, and a method `is_ok()` that says if the snapshot passes

## Functions

`time_to_expiry` computes T and refuses naive datetimes. `clean_chain` removes zero bids, crossed quotes, very wide spreads and duplicate strikes. `implied_forward` gets F from put-call parity using the strikes near the money, and `atm_quotes` picks the two strikes around F.

`implied_vols` computes Black-76 vols for the out-of-the-money options only and returns k, iv, w and a weight for each quote. `fit_svi` fits SVI by weighted least squares. `svi_w`, `svi_w_derivatives` and `svi_g` give w, its derivatives and g(k), where g >= 0 means no butterfly arbitrage.

`make_k_grid` builds a grid of plus or minus a number of ATM standard deviations, `density` gives q(k) with the Gatheral-Jacquier formula, and `svi_sf` / `svi_cdf` give the closed-form tails, sf = N(d2) - phi(d2) w'/(2 sqrt(w)). This is the same thing as Francesco's 1 + e^(-k) c'(k) for the cdf, just written for SVI.

Finally `make_synthetic_chain` prices a Black-Scholes chain, adds noise to the quotes, and returns the true density so we can check the pipeline before using real data.

## Parameters

I put every threshold as an argument with a default value, so we can change them without touching the code. The defaults are only my proposals:

- `max_rel_spread = 0.5` (spread at most 50% of the mid) and `min_bid = 0` in `clean_chain`
- `weighting = "inv_spread"` (weight 1/spread, or "equal") in `implied_vols`
- `n_sd = 10` and `n_points = 2001` for the grid
- in `is_ok`: `max_rmse_iv = 0.01` (1 vol point), `min_mass = 0.999` and `g_tol = 1e-8`

`run_pipeline(chain, as_of, expiry, r, ...)` takes the same arguments and passes them on.
