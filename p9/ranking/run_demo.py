"""Run the P9 configuration-weighting demonstration on synthetic inputs only."""

import argparse
import csv
import hashlib
import json
from decimal import Decimal
from itertools import combinations, product
from math import log
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np

from model import (COMPOSITIONS, STATES, bme, boltzmann_prior, effective_support,
                   normalize_logs, occupancy_profiles, pair_probabilities,
                   support_gap_2d, weighted_ecdf, whitened_residuals)


HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "outputs"
MO_BENCHMARK = HERE.parent / "evidence" / "mo_s1.csv"
SEED = 20261124
N_TRAJECTORIES = 6
LAMBDA = 1.0
LAMBDAS = (0.25, 1.0, 4.0)
PRIMARY_DELTA = log(1.10)
DELTA_GRID = (0.0, log(1.05), PRIMARY_DELTA, log(1.20))
LOG_THRESH = log(1.30)
FREEZE_K = 675.0
EXP_COV = np.array([[0.060 ** 2, 0.00084], [0.00084, 0.070 ** 2]])
FORWARD_COV = np.array([[0.030 ** 2, 0.00018], [0.00018, 0.035 ** 2]])
SHARED_COV = np.array([[0.025 ** 2, 0.00024], [0.00024, 0.030 ** 2]])
FIT_COV = EXP_COV + FORWARD_COV + SHARED_COV
HOLDOUT_SD = 0.055


def write_csv(path, rows):
    rows = list(rows)
    with NamedTemporaryFile("w", newline="", encoding="utf-8", dir=path.parent, delete=False) as stream:
        temporary_path = Path(stream.name)
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    temporary_path.replace(path)


def integer_cell_options():
    """Rank example determinant-20 row-basis transforms, not crystal structures."""
    basis = np.array([[0, 0.5, 0.5], [0.5, 0, 0.5], [0.5, 0.5, 0]])
    ranked = []
    for a, b in product(range(1, 21), repeat=2):
        if 20 % (a * b):
            continue
        c = 20 // (a * b)
        for u, v, w in product(range(a), range(a), range(b)):
            cell = [[a, 0, 0], [u, b, 0], [v, w, c]]
            singular = np.linalg.svd(np.array(cell) @ basis, compute_uv=False)
            ranked.append((float(singular[0] / singular[-1]), cell))
    ranked.sort(key=lambda item: item[0])
    return [dict(option=i, transform_row_major=json.dumps(cell), determinant=20,
                 nominal_P=20, basis_condition_ratio=ratio,
                 status="integer_shape_candidates_only")
            for i, (ratio, cell) in enumerate(ranked[:6], 1)]


def make_synthetic_inputs(rng):
    """Return synthetic family records, proxy structure observables and toy traces."""
    records = []
    energy_rows, deg_rows, forward_rows, observed_rows, traces = [], [], [], [], []
    offsets = np.array([0.08, 0.24, 0.31, 0.39, 0.29, 0.45, 0.23])
    for x_index, x in enumerate(COMPOSITIONS):
        strata = np.array_split(list(occupancy_profiles(x_index)), len(STATES))
        profiles = [stratum[i] for stratum in strata for i in (0, len(stratum) // 2, len(stratum) - 1)]
        cl_a = np.array([r["Cl_A"] for r in profiles])
        cl_b = np.array([r["Cl_B"] for r in profiles])
        imbalance = (cl_a - cl_b) / 20
        within = np.linspace(-1.0, 1.0, len(cl_a))
        motif = np.sin((np.arange(len(cl_a)) + x_index / 2) * 1.6)
        energy = 0.045 * within ** 2 + 0.018 * motif + 0.022 * within * (x_index - 3) / 3
        energy = energy - energy.min()
        # Arbitrary toy degeneracies for discrete hypotheses, not crystal degeneracies.
        deg = np.array([1, 2, 2, 3, 1, 2, 3, 2, 1])
        forward = np.stack([cl_a / 20, 0.48 + 0.17 * motif + 0.08 * imbalance,
                            0.42 + 0.17 * within ** 2 - 0.09 * motif], axis=1)
        pseudo_calibration = normalize_logs(-0.7 * within + 0.55 * motif + 0.15 * x_index * within)[0]
        observed = pseudo_calibration @ forward + np.array([0.011, -0.02, 0.015 * np.cos(x_index)])
        mean_transport = offsets[x_index] + (0.38 - 0.038 * x_index) * within + 0.13 * motif
        trajectory_sd = 0.10 + 0.03 * np.abs(within)
        trajectories = mean_transport[:, None] + rng.normal(size=(len(cl_a), N_TRAJECTORIES)) * trajectory_sd[:, None]
        current_records = []
        for family, profile in enumerate(profiles):
            state = STATES[family // 3]
            current_records.append({
                **profile, "family_id": f"SYN-x{x}-f{family:02d}", "structure_state": state,
                "parent_structure": "abstract_20P_count_model",
                "selection": "deterministic_left_middle_right_per_stratum",
                "proposal_q": "not_applicable_unique_support",
                "local_pattern_proxy": float(motif[family]), "cell_relative_eV_synthetic": float(energy[family]),
                "toy_degeneracy": int(deg[family]), "forward_site_proxy": float(forward[family, 0]),
                "forward_pair_proxy": float(forward[family, 1]), "heldout_proxy": float(forward[family, 2]),
                "synthetic_only": "true",
            })
        records.append(current_records)
        energy_rows.append(energy)
        deg_rows.append(deg)
        forward_rows.append(forward)
        observed_rows.append(observed)
        traces.append(trajectories)
    return records, *map(np.asarray, (energy_rows, deg_rows, forward_rows, observed_rows, traces))


def structure_diagnostics(energy, g, forward, observed):
    rows = []
    for i, x in enumerate(COMPOSITIONS):
        f, z = forward[i], observed[i]
        thermal = boltzmann_prior(energy[i], FREEZE_K, g[i])
        centered = whitened_residuals(f[:, :2], z[:2], FIT_COV)
        support_gap = support_gap_2d(centered[thermal > 0])
        feature_rank = np.linalg.matrix_rank(centered[1:] - centered[:1])
        for lam in LAMBDAS:
            weights = bme(thermal, f[:, :2], z[:2], FIT_COV, lam)
            output = weights @ f
            with_support = weights > 0
            rows.append(dict(
                x=x, lambda_value=lam, training_site_observed=z[0], training_site_predicted=output[0],
                training_pair_observed=z[1], training_pair_predicted=output[1],
                weighted_residual_norm=float(np.linalg.norm(weights @ centered)),
                distance_to_hull_mahalanobis=support_gap, affine_rank=int(feature_rank),
                family_count=len(weights), unidentifiable_affine_directions=len(weights) - 1 - feature_rank,
                prior_effective_families=effective_support(thermal),
                posterior_effective_families=effective_support(weights), max_posterior_weight=float(weights.max()),
                kl_divergence=float(weights[with_support] @ np.log(weights[with_support] / thermal[with_support])),
                heldout_observed=z[2], heldout_prior_predicted=float(thermal @ f[:, 2]),
                heldout_posterior_predicted=output[2], heldout_standardized_residual=(output[2] - z[2]) / HOLDOUT_SD,
                synthetic_only="true",
            ))
    return rows


def support_stress_rows(forward, observed):
    for i, x in enumerate(COMPOSITIONS):
        stressed_observation = observed[i, :2] + np.array([0.14, 0.27])
        offsets = whitened_residuals(forward[i, :, :2], stressed_observation, FIT_COV)
        yield dict(x=x, site_observed=stressed_observation[0], pair_observed=stressed_observation[1],
                   distance_to_hull_mahalanobis=support_gap_2d(offsets),
                   action="inspect_forward_model_or_expand_support_before_reweighting", synthetic_only="true")


def joint_worlds(rng, worlds, conditional_draws, energy, g, forward, observed, traces):
    """Shared thermal, force-model and structural-calibration variables per world."""
    n_x, size = energy.shape
    freeze_k = rng.uniform(525.0, 825.0, size=worlds)
    model_factor = rng.normal(size=worlds)
    shared_calibration = rng.multivariate_normal(np.zeros(2), SHARED_COV, size=worlds)
    local_observation = rng.multivariate_normal(np.zeros(2), EXP_COV + FORWARD_COV, size=(worlds, n_x))
    family_energy_error = rng.normal(0, 0.019, size=(worlds, n_x, size))
    within_position = np.linspace(-1, 1, size)
    energies = energy + 0.027 * model_factor[:, None, None] * within_position + family_energy_error
    choices = rng.uniform(size=(worlds, conditional_draws, n_x))
    model_loading = 0.09 + 0.16 * np.linspace(-1, 1, n_x)[:, None] + 0.035 * within_position
    sampled_mean = traces.mean(axis=2)
    sampled_se = traces.std(axis=2, ddof=1) / np.sqrt(N_TRAJECTORIES)
    family_scores = (sampled_mean + model_factor[:, None, None] * model_loading
                     + rng.normal(size=(worlds, n_x, size)) * sampled_se)
    thermal = np.empty((worlds, n_x, size))
    posterior = np.empty_like(thermal)
    for w in range(worlds):
        for i in range(n_x):
            thermal[w, i] = boltzmann_prior(energies[w, i], freeze_k[w], g[i])
            z = observed[i, :2] + shared_calibration[w] + local_observation[w, i]
            posterior[w, i] = bme(thermal[w, i], forward[i, :, :2], z, FIT_COV, LAMBDA)
    weights = {"bme": posterior, "thermal_prior": thermal, "uniform": np.full_like(thermal, 1 / size)}
    scores = {}
    for method, weight in weights.items():
        cumulative = np.cumsum(weight, axis=2)[:, None, :, :-1]
        picked = (choices[:, :, :, None] > cumulative).sum(axis=-1)
        scores[method] = family_scores[np.arange(worlds)[:, None, None], np.arange(n_x)[None, None, :], picked]
    return weights, scores, family_scores


def summarize_pairs(scores):
    rows = []
    for method, draw in scores.items():
        for delta in DELTA_GRID:
            world_prob = pair_probabilities(draw, delta)
            point = world_prob.mean(axis=0)
            mcse = world_prob.std(axis=0, ddof=1) / np.sqrt(len(world_prob))
            q05, q95 = np.quantile(world_prob, (0.05, 0.95), axis=0)
            for i, x in enumerate(COMPOSITIONS):
                for j, y in enumerate(COMPOSITIONS):
                    row = dict(method=method, delta_log=delta, primary_delta=str(delta == PRIMARY_DELTA).lower(),
                               x_a=x, x_b=y, p_plus=point[i, j, 0], p_minus=point[i, j, 1], p_tie=point[i, j, 2])
                    for k, label in enumerate(("plus", "minus", "tie")):
                        row[f"p_{label}_mcse"] = mcse[i, j, k]
                        row[f"p_{label}_world_q05"] = q05[i, j, k]
                        row[f"p_{label}_world_q95"] = q95[i, j, k]
                    row["synthetic_only"] = "true"
                    rows.append(row)
    return rows


def summarize_ranks(scores):
    for method, draw in scores.items():
        rank = (np.argsort(np.argsort(-draw, axis=2, kind="stable"), axis=2, kind="stable") + 1)
        for i, x in enumerate(COMPOSITIONS):
            first = (rank[:, :, i] == 1).mean(axis=1)
            top3 = (rank[:, :, i] <= 3).mean(axis=1)
            above = (draw[:, :, i] >= LOG_THRESH).mean(axis=1)
            yield dict(method=method, x=x, p_top1=first.mean(), p_top3=top3.mean(),
                       log_threshold=LOG_THRESH, p_above_intragrain_threshold=above.mean(),
                       p_top1_mcse=first.std(ddof=1) / np.sqrt(len(first)), expected_rank=rank[:, :, i].mean(),
                       synthetic_only="true")


def summarize_weights(records, weights, traces):
    for i, comp in enumerate(records):
        for j, family in enumerate(comp):
            posterior = weights["bme"][:, i, j]
            low, high = np.quantile(posterior, (0.05, 0.95))
            yield {**family, "thermal_prior_mean": weights["thermal_prior"][:, i, j].mean(),
                   "bme_weight_mean": posterior.mean(), "bme_world_q05": low, "bme_world_q95": high,
                   "n_synthetic_trajectories": N_TRAJECTORIES, "transport_log_mean": traces[i, j].mean(),
                   "transport_log_trace_sd": traces[i, j].std(ddof=1)}


def trace_input_rows(records, traces):
    for i, comp in enumerate(records):
        for j, family in enumerate(comp):
            for replicate, value in enumerate(traces[i, j], 1):
                yield dict(x=family["x"], family_id=family["family_id"], toy_replicate=replicate,
                           log_relative_transport=value, source="pseudorandom_not_md", synthetic_only="true")


def des_prior_rows(records, weights):
    for i, comp in enumerate(records):
        prior = weights["thermal_prior"][:, i, :].mean(axis=0)
        for state in STATES:
            select = [row["structure_state"] == state for row in comp]
            yield dict(x=comp[0]["x"], structure_state=state, prior_probability=prior[select].sum(),
                       synthetic_only="true")


def ecdf_rows(weights, family_scores):
    grid = np.linspace(family_scores.min() - 0.1, family_scores.max() + 0.1, 141)
    for method, weight in weights.items():
        for i, x in enumerate(COMPOSITIONS):
            curve = weighted_ecdf(family_scores[:, i].ravel(), weight[:, i].ravel(), grid)
            for location, prob in zip(grid, curve):
                yield dict(method=method, x=x, log_relative_transport=location, ecdf=prob, synthetic_only="true")


def cross_world_independent_rows(weights, scores, family_scores):
    """Diagnostic counterfactual: retain each marginal, remove shared dependence."""
    n_worlds = len(family_scores)
    marginals = []
    for i, _ in enumerate(COMPOSITIONS):
        values = family_scores[:, i].ravel()
        order = np.argsort(values)
        probability = weights["bme"][:, i].ravel()[order] / n_worlds
        marginals.append((values[order], probability, np.r_[0.0, probability.cumsum()]))
    joint_draw = scores["bme"]
    joint = pair_probabilities(joint_draw, PRIMARY_DELTA).mean(axis=0)
    relation = np.corrcoef(joint_draw.reshape(-1, len(COMPOSITIONS)), rowvar=False)
    for i, j in combinations(range(len(COMPOSITIONS)), 2):
        v_a, w_a, cdf_a = marginals[i]
        v_b, w_b, cdf_b = marginals[j]
        independent_a = w_a @ cdf_b[np.searchsorted(v_b, v_a - PRIMARY_DELTA, side="left")]
        independent_b = w_b @ cdf_a[np.searchsorted(v_a, v_b - PRIMARY_DELTA, side="left")]
        yield dict(x_a=COMPOSITIONS[i], x_b=COMPOSITIONS[j], delta_log=PRIMARY_DELTA,
                   joint_p_plus=joint[i, j, 0], joint_p_minus=joint[i, j, 1], joint_p_tie=joint[i, j, 2],
                   independence_p_plus=independent_a, independence_p_minus=independent_b,
                   independence_p_tie=1 - independent_a - independent_b,
                   joint_draw_pearson=relation[i, j], synthetic_only="true")


def historical_directions(benchmark_path, pair_rows):
    """Read historical EIS only after ranking; produce no wet-effect probabilities."""
    with benchmark_path.open(newline="", encoding="utf-8-sig") as stream:
        source = list(csv.DictReader(stream))
    entries = {f"{Decimal(row['x']):.1f}": Decimal(row["sigma_mS_cm"]) for row in source}
    if len(source) != len(COMPOSITIONS) or set(entries) != set(COMPOSITIONS):
        raise ValueError("Mo comparison requires exactly the seven nominal compositions")
    for row in pair_rows:
        x, y = row["x_a"], row["x_b"]
        if x >= y or row["primary_delta"] != "true":
            continue
        gap = entries[x] - entries[y]
        for eps in (Decimal("0"), Decimal("0.1"), Decimal("0.3")):
            historical = "a_higher" if gap > eps else "b_higher" if gap < -eps else "near_threshold"
            pwin, prev, ptie = row["p_plus"], row["p_minus"], row["p_tie"]
            low = row["p_plus_world_q05"] if pwin >= prev else row["p_minus_world_q05"]
            predicted = ("a_higher" if pwin >= 0.67 and low > 0.50 else
                         "b_higher" if prev >= 0.67 and low > 0.50 else
                         "near_tie" if ptie >= 0.50 else "undetermined")
            comparison = ("point_gap_within_margin" if historical == "near_threshold" else
                          "concordant" if historical == predicted else
                          "opposite" if predicted in ("a_higher", "b_higher") else "undetermined")
            direction_probability = pwin if historical == "a_higher" else prev if historical == "b_higher" else ""
            yield dict(method=row["method"], x_a=x, x_b=y, historical_gap_mS_cm=float(gap),
                       historical_margin_mS_cm=float(eps), historic_point_direction=historical,
                       p_plus=pwin, p_minus=prev, p_tie=ptie, p_supporting_historic_point=direction_probability,
                       synthetic_decision=predicted, comparison=comparison,
                       interpretation="synthetic_vs_historical_point_direction_only")


def run(output, benchmark, seed, worlds, repetitions):
    if worlds < 2 or repetitions < 1:
        raise ValueError("require at least two worlds and one conditional draw")
    output.mkdir(parents=True, exist_ok=True)
    rng_input, rng_world = [np.random.default_rng(s) for s in np.random.SeedSequence(seed).spawn(2)]
    records, energy, deg, forward, observed, trajectories = make_synthetic_inputs(rng_input)
    fit = structure_diagnostics(energy, deg, forward, observed)
    weights, scores, family_scores = joint_worlds(rng_world, worlds, repetitions, energy, deg, forward, observed, trajectories)
    pair_rows = summarize_pairs(scores)
    families = list(summarize_weights(records, weights, trajectories))
    ranking_rows = list(summarize_ranks(scores))
    directions = list(historical_directions(benchmark, pair_rows))
    write_csv(output / "integer_cell_options.csv", integer_cell_options())
    write_csv(output / "occupancy_profiles.csv", (p for i in range(len(COMPOSITIONS)) for p in occupancy_profiles(i)))
    write_csv(output / "family_weights.csv", families)
    write_csv(output / "synthetic_trace_inputs.csv", trace_input_rows(records, trajectories))
    write_csv(output / "structure_diagnostics.csv", fit)
    write_csv(output / "structure_support_stress.csv", support_stress_rows(forward, observed))
    write_csv(output / "des_structure_prior.csv", des_prior_rows(records, weights))
    write_csv(output / "pairwise.csv", pair_rows)
    write_csv(output / "weighted_ecdf.csv", ecdf_rows(weights, family_scores))
    write_csv(output / "coupling_sensitivity.csv", cross_world_independent_rows(weights, scores, family_scores))
    write_csv(output / "composition_summary.csv", ranking_rows)
    write_csv(output / "public_direction.csv", directions)
    summary = dict(
        schema="p9.ranking.synthetic.v1", synthetic_only=True, seed=seed,
        worlds=worlds, conditional_draws_per_world=repetitions, trajectories_per_family=N_TRAJECTORIES,
        random_variable="log relative intrinsic transport of one random family, with uncertain latent family mean",
        interval="5th–95th percentiles across shared-parameter scenarios, including inner Monte Carlo error",
        compositions=COMPOSITIONS, main_method="bme", primary_delta_log=PRIMARY_DELTA,
        sensitivity_delta_log=DELTA_GRID, log_threshold=LOG_THRESH, lambda_fixed=LAMBDA,
        lambda_sensitivity=LAMBDAS, freeze_k_range=(525, 825),
        training_observation_covariances=dict(exp=EXP_COV.tolist(), forward=FORWARD_COV.tolist(),
                                              shared_calibration=SHARED_COV.tolist()),
        decision_thresholds=dict(win_point=0.67, win_scenario_q05=0.50, tie_point=0.50),
        source_for_direction_only="Mo et al., J. Alloys Compd. 971, 172727 (2024), Supplement Table S1",
        mo_benchmark_sha256=hashlib.sha256(benchmark.read_bytes()).hexdigest(),
        numpy_version=np.__version__,
        composition_summary=ranking_rows,
        bme_family_weights=[dict(x=r["x"], family_id=r["family_id"], w0=r["thermal_prior_mean"],
                                 weight=r["bme_weight_mean"], q05=r["bme_world_q05"],
                                 q95=r["bme_world_q95"]) for r in families],
    )
    (output / "metadata.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Synthetic ranking completed: {worlds} shared worlds × {repetitions} conditional draws. Outputs at {output}.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--benchmark", type=Path, default=MO_BENCHMARK)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--worlds", type=int, default=128)
    parser.add_argument("--repetitions", type=int, default=256)
    args = parser.parse_args()
    run(args.output, args.benchmark, args.seed, args.worlds, args.repetitions)


if __name__ == "__main__":
    main()
