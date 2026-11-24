"""Small, numpy-only utilities for structure ensembles and probability ranking."""

from itertools import combinations
from math import comb

import numpy as np


KB_EV = 8.617333262145e-5
COMPOSITIONS = ("0.0", "0.1", "0.2", "0.3", "0.4", "0.5", "0.6")
STATES = ("low", "mid", "high")


def occupancy_profiles(x_index):
    """Enumerate exact count profiles for a nominal 20-P supercell."""
    if not isinstance(x_index, int) or x_index not in range(len(COMPOSITIONS)):
        raise ValueError("composition index must be an integer from 0 to 6")
    cl_total = 20 + 2 * x_index
    li_total = 120 - 2 * x_index
    for cl_a in range(cl_total - 20, 21):
        cl_b = cl_total - cl_a
        yield {
            "x": COMPOSITIONS[x_index], "P": 20, "Li": li_total,
            "S_framework": 80, "S": 120 - cl_total, "Cl": cl_total,
            "atoms": li_total + 140, "Cl_A": cl_a, "Cl_B": cl_b,
            "S_A": 20 - cl_a, "S_B": 20 - cl_b,
            "Li_removed_vs_x0": 120 - li_total,
            "anion_assignments_without_symmetry_or_geometry": comb(20, cl_a) * comb(20, cl_b),
        }


def normalize_logs(log_weights):
    log_weights = np.asarray(log_weights, dtype=float)
    maximum = log_weights.max()
    if not np.isfinite(maximum) or np.any(np.isnan(log_weights)):
        raise ValueError("at least one finite log weight is required")
    probability = np.exp(log_weights - maximum)
    partition = probability.sum()
    return probability / partition, maximum + np.log(partition)


def boltzmann_prior(cell_ev, freeze_temperature_k, degeneracy=None, proposal_probability=None):
    """Weight indexed states, or independent proposal draws with target/proposal.

    For rows that already contain family free energies, omit degeneracy.
    For deterministic selection/enumeration omit proposal_probability. For actual
    equilibrium-chain draws use equilibrium_frequencies instead.
    """
    ev = np.asarray(cell_ev, dtype=float)
    if ev.ndim != 1 or not ev.size or not np.isfinite(ev).all():
        raise ValueError("cell energies must be a nonempty finite vector")
    if freeze_temperature_k <= 0 or not np.isfinite(freeze_temperature_k):
        raise ValueError("freeze temperature must be finite, in kelvin and positive")
    log_w = -(ev - ev.min()) / (KB_EV * freeze_temperature_k)
    if degeneracy is not None:
        g = np.asarray(degeneracy, dtype=float)
        if g.shape != ev.shape or not (np.isfinite(g) & (g > 0)).all():
            raise ValueError("degeneracies must be positive and match the energies")
        log_w += np.log(g)
    if proposal_probability is not None:
        q = np.asarray(proposal_probability, dtype=float)
        if q.shape != ev.shape or not (np.isfinite(q) & (q > 0) & (q <= 1)).all():
            raise ValueError("proposal probabilities must belong to (0, 1] and match the draws")
        log_w -= np.log(q)
    return normalize_logs(log_w)[0]


def equilibrium_frequencies(family_ids):
    """Estimate a marginal from already equilibrated, retained chain draws."""
    ids, counts = np.unique(family_ids, return_counts=True)
    if not ids.size:
        raise ValueError("at least one retained equilibrium draw is required")
    return dict(zip(ids, counts / counts.sum()))


def effective_support(probability):
    return float(1 / np.square(probability).sum())


def whitened_residuals(forward, observation, covariance):
    forward = np.asarray(forward, dtype=float)
    observation = np.asarray(observation, dtype=float)
    covariance = np.asarray(covariance, dtype=float)
    if (forward.ndim != 2 or observation.shape != forward.shape[1:]
            or covariance.shape != (observation.size, observation.size)
            or not np.isfinite(forward).all() or not np.isfinite(observation).all()
            or not np.isfinite(covariance).all() or not np.allclose(covariance, covariance.T)):
        raise ValueError("finite forward observations and a symmetric covariance are required")
    cholesky = np.linalg.cholesky(covariance)
    return np.linalg.solve(cholesky, (forward - observation).T).T


def bme(prior, forward, observation, covariance, lam):
    """Solve the positive-lambda whitened dual via damped Newton iteration."""
    prior = np.asarray(prior, dtype=float)
    if (not np.isfinite(lam) or lam <= 0 or prior.ndim != 1
            or not (np.isfinite(prior) & (prior >= 0)).all() or not np.isclose(prior.sum(), 1)):
        raise ValueError("BME requires a normalized nonnegative prior and finite lambda > 0")
    residuals = whitened_residuals(forward, observation, covariance)
    if residuals.shape[0] != prior.size:
        raise ValueError("one prior probability is required per family")
    support = prior > 0
    d = residuals[support]
    log_prior = np.log(prior[support])
    dual = np.zeros(d.shape[1])
    ridge = lam * np.eye(d.shape[1])

    def objective(candidate):
        weights, log_partition = normalize_logs(log_prior - d @ candidate)
        return weights, log_partition + lam / 2 * (candidate @ candidate)

    for _ in range(70):
        weights, value = objective(dual)
        center = weights @ d
        gradient = lam * dual - center
        if np.linalg.norm(gradient, ord=np.inf) < 1e-8:
            out = np.zeros_like(prior)
            out[support] = weights
            return out
        centered = d - center
        hessian = centered.T @ (weights[:, None] * centered) + ridge
        step = np.linalg.solve(hessian, gradient)
        scale = 1.0
        for _ in range(40):
            proposed = dual - scale * step
            if objective(proposed)[1] <= value - 1e-4 * scale * (gradient @ step) + 2e-14:
                dual = proposed
                break
            scale /= 2
        else:
            raise ArithmeticError("BME line search failed")
    raise ArithmeticError("BME did not reach the gradient tolerance")


def support_gap_2d(whitened_family_offsets):
    """Mahalanobis distance to the convex hull for two linear forward observables."""
    d = np.asarray(whitened_family_offsets, dtype=float)
    if d.ndim != 2 or d.shape[1] != 2 or not len(d):
        raise ValueError("support gap expects two whitened observables per family")
    for a, b, c in combinations(d, 3):
        bases = np.stack([b - a, c - a], axis=1)
        if abs(np.linalg.det(bases)) < 1e-12:
            continue
        u, v = np.linalg.solve(bases, -a)
        if min(u, v, 1 - u - v) >= -1e-10:
            return 0.0
    best_squared = np.square(d).sum(axis=1).min()
    for a, b in combinations(d, 2):
        direction = b - a
        length_squared = direction @ direction
        if length_squared > 0:
            closest = a + np.clip(-a @ direction / length_squared, 0, 1) * direction
            best_squared = min(best_squared, closest @ closest)
    return float(np.sqrt(best_squared))


def pair_probabilities(joint_draws, delta):
    """Triples of per-world win / reverse / near-tie probabilities.

    Draws are indexed by (shared-parameter draw, conditional joint draw, x).
    """
    values = np.asarray(joint_draws, dtype=float)
    if values.ndim != 3 or not all(values.shape) or not np.isfinite(values).all():
        raise ValueError("expect finite score draws indexed by (world, repetition, x)")
    if delta < 0 or not np.isfinite(delta):
        raise ValueError("delta must be finite and nonnegative")
    diff = values[:, :, :, None] - values[:, :, None, :]
    wins = (diff > delta).mean(axis=1)
    losses = wins.transpose(0, 2, 1)
    ties = (np.abs(diff) <= delta).mean(axis=1)
    return np.stack([wins, losses, ties], axis=-1)


def weighted_ecdf(samples, weights, grid):
    samples = np.asarray(samples, dtype=float)
    weights = np.asarray(weights, dtype=float)
    if (samples.ndim != 1 or samples.shape != weights.shape or not len(samples)
            or not (np.isfinite(weights) & (weights >= 0)).all() or weights.sum() <= 0
            or not np.isfinite(samples).all()):
        raise ValueError("positive total weight on a finite sample set is required")
    idx = np.argsort(samples, kind="stable")
    cumulative = np.r_[0, np.cumsum(weights[idx]) / weights.sum()]
    return np.clip(cumulative[np.searchsorted(samples[idx], grid, side="right")], 0, 1)
