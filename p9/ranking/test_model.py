import csv
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import numpy as np

from model import (COMPOSITIONS, bme, boltzmann_prior, equilibrium_frequencies,
                   occupancy_profiles, pair_probabilities, support_gap_2d, weighted_ecdf)
from run_demo import HERE, MO_BENCHMARK, cross_world_independent_rows, integer_cell_options, run


class RankingTests(unittest.TestCase):
    def test_integer_composition_and_ideal_charge_balance(self):
        for i, x in enumerate(COMPOSITIONS):
            rows = list(occupancy_profiles(i))
            self.assertEqual(len(rows), 21 - 2 * i)
            for r in rows:
                self.assertEqual(r['P'], 20)
                self.assertEqual(r['Li'], 120 - 2 * i)
                self.assertEqual(r['atoms'], 260 - 2 * i)
                self.assertEqual(r['x'], x)
                self.assertEqual(r['Li'] + 5 * r['P'] - 2 * r['S'] - r['Cl'], 0)
                self.assertEqual(r['S_A'] + r['Cl_A'], 20)
                self.assertEqual(r['S_B'] + r['Cl_B'], 20)
                self.assertEqual(r['S_framework'] + r['S_A'] + r['S_B'], r['S'])
        self.assertTrue(all(r['determinant'] == 20 for r in integer_cell_options()))

    def test_prior_shift_and_importance_correction(self):
        prior = boltzmann_prior([0, 0.05, 0.2], 675, [1, 3, 2])
        increased = boltzmann_prior([100_000, 100_000.05, 100_000.2], 675, [1, 3, 2])
        np.testing.assert_allclose(prior, increased, rtol=1e-8)
        np.testing.assert_allclose(boltzmann_prior([0, 0], 600, [1, 2], [0.2, 0.8]), [2 / 3, 1 / 3])
        self.assertDictEqual(equilibrium_frequencies(['a', 'a', 'b']), {'a': 2 / 3, 'b': 1 / 3})
        with self.assertRaises(ValueError):
            boltzmann_prior([0, 1], 600, proposal_probability=[0, 1])

    def test_bme_fit_retains_support_and_prior_ratio_in_null_direction(self):
        f = [[0.0, 0.0], [0.0, 0.0], [1.0, 0.0], [0.5, 1.0]]
        p = np.array([0.2, 0.3, 0.5, 0.0])
        observed = [0.77, 0.0]
        covariance = [[0.01, 0.003], [0.003, 0.02]]
        loose = bme(p, f, observed, covariance, 0.5)
        tight = bme(p, f, observed, covariance, 5)
        self.assertAlmostEqual(loose.sum(), 1)
        self.assertEqual(loose[3], 0)
        self.assertAlmostEqual(loose[0] / loose[1], 2 / 3)
        self.assertLess(abs(loose[2] - 0.77), abs(tight[2] - 0.77))

    def test_exact_2d_support_gap(self):
        self.assertEqual(support_gap_2d([[-1, -1], [1, -1], [0, 1]]), 0)
        self.assertAlmostEqual(support_gap_2d([[3, 0], [3, 4], [6, 4]]), 3)
        self.assertAlmostEqual(support_gap_2d([[-2, 1], [2, 1]]), 1)

    def test_shared_worlds_are_not_crossed_and_triples_close(self):
        joint = np.array([[[5.0, 4.0], [5.0, 5.0]], [[-4.0, -5.0], [-5.0, -5.0]]])
        p = pair_probabilities(joint, 0.5)
        np.testing.assert_allclose(p[0, 0, 1], [0.5, 0.0, 0.5])
        np.testing.assert_allclose(p[1, 1, 0], [0.0, 0.5, 0.5])
        np.testing.assert_allclose(p.sum(axis=-1), 1)
        np.testing.assert_allclose(p[..., 0], p[..., 1].transpose(0, 2, 1))
        self.assertTrue(np.all(p[:, (0, 1), (0, 1), 2] == 1))

    def test_weighted_ecdf_with_duplicate_locations(self):
        result = weighted_ecdf([2, 0, 2, 1], [1, 2, 2, 5], [-1, 0, 1, 2, 3])
        np.testing.assert_allclose(result, [0, 0.2, 0.7, 1, 1])

    def test_coupling_diagnostic_keeps_marginals_and_changes_difference(self):
        family_scores = np.broadcast_to(np.array([0.0, 1.0])[:, None, None], (2, 7, 1))
        draws = {'bme': family_scores.transpose(0, 2, 1)}
        weights = {'bme': np.ones_like(family_scores)}
        rows = list(cross_world_independent_rows(weights, draws, family_scores))
        self.assertEqual(len(rows), 21)
        self.assertEqual(rows[0]['joint_p_tie'], 1)
        self.assertEqual(rows[0]['independence_p_plus'], 0.25)
        self.assertEqual(rows[0]['independence_p_minus'], 0.25)

    def test_demo_reproducible_and_des_schema_normalized(self):
        with TemporaryDirectory(dir=HERE) as directory:
            a, b = [Path(directory) / name for name in ('a', 'b')]
            run(a, MO_BENCHMARK, seed=123, worlds=4, repetitions=8)
            run(b, MO_BENCHMARK, seed=123, worlds=4, repetitions=8)
            for path in a.iterdir():
                self.assertEqual(path.read_bytes(), (b / path.name).read_bytes())
            with (a / 'des_structure_prior.csv').open(encoding='utf-8', newline='') as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 21)
            self.assertTrue(all(r['synthetic_only'] == 'true' for r in rows))
            for x in COMPOSITIONS:
                row = [r for r in rows if r['x'] == x]
                self.assertSetEqual({r['structure_state'] for r in row}, {'low', 'mid', 'high'})
                self.assertAlmostEqual(sum(float(r['prior_probability']) for r in row), 1)
            with (a / 'pairwise.csv').open(encoding='utf-8', newline='') as stream:
                primary = [r for r in csv.DictReader(stream) if r['method'] == 'bme' and r['primary_delta'] == 'true']
            self.assertEqual(len(primary), 49)
            for r in primary:
                self.assertAlmostEqual(sum(float(r[k]) for k in ('p_plus', 'p_minus', 'p_tie')), 1)


if __name__ == '__main__':
    unittest.main()
