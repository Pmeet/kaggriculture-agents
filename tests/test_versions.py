import json
import os
import tempfile
import unittest
from unittest import mock

from lab import versions

# A stand-in registry with a gap (no v16/v17) and out-of-order keys, because the
# real one has both and ordering by insertion would quietly get it wrong.
REGISTRY = {
    "101": {"label": "v15", "agent": "agents.baseline_j"},
    "104": {"label": "v22", "agent": "agents.baseline_o"},
    "102": {"label": "v18", "agent": "agents.baseline_k"},
    "103": {"label": "v21", "agent": "agents.baseline_n"},
}


class RegistryTest(unittest.TestCase):
    def setUp(self):
        handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump(REGISTRY, handle)
        handle.close()
        self.path = handle.name
        patcher = mock.patch.object(versions, "REGISTRY", self.path)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(os.unlink, self.path)

    def test_orders_numerically_not_by_file_order(self):
        self.assertEqual(list(versions.registry()), ["v15", "v18", "v21", "v22"])

    def test_supplies_the_default_attr(self):
        self.assertEqual(versions.registry()["v21"], "agents.baseline_n:agent")

    def test_missing_file_is_empty_not_fatal(self):
        with mock.patch.object(versions, "REGISTRY", "/nonexistent/submissions.json"):
            self.assertEqual(versions.registry(), {})

    def names(self, spec):
        return [o["name"] if isinstance(o, dict) else o for o in versions.expand(spec)]

    def test_recent_tracks_the_registry(self):
        self.assertEqual(self.names("recent:3"), ["v18", "v21", "v22"])

    def test_recent_clamps_to_what_exists(self):
        self.assertEqual(self.names("recent:99"), ["v15", "v18", "v21", "v22"])

    def test_recent_follows_a_new_submission(self):
        """The whole point: shipping v23 changes the opponent set with no code edit."""
        before = self.names("recent:2")
        with open(self.path) as handle:
            data = json.load(handle)
        data["105"] = {"label": "v23", "agent": "agents.baseline_p"}
        with open(self.path, "w") as handle:
            json.dump(data, handle)
        self.assertEqual(before, ["v21", "v22"])
        self.assertEqual(self.names("recent:2"), ["v22", "v23"])

    def test_range_spans_the_gap(self):
        self.assertEqual(self.names("v18..v22"), ["v18", "v21", "v22"])

    def test_range_accepts_either_order(self):
        self.assertEqual(self.names("v22..v18"), ["v18", "v21", "v22"])

    def test_single_label_resolves_to_its_snapshot(self):
        self.assertEqual(versions.expand("v18"), [
            {"module": "agents.baseline_k", "attr": "agent", "name": "v18"}])

    def test_raw_specs_pass_through_untouched(self):
        self.assertEqual(self.names("agents.v1:agent"), ["agents.v1:agent"])

    def test_tokens_mix_freely(self):
        self.assertEqual(self.names("recent:2,agents.v1:agent"),
                         ["v21", "v22", "agents.v1:agent"])

    def test_unknown_version_names_the_known_ones(self):
        with self.assertRaises(KeyError) as caught:
            versions.expand("v99")
        self.assertIn("v22", str(caught.exception))

    def test_unparsable_count_is_rejected(self):
        with self.assertRaises(KeyError):
            versions.expand("recent:seven")

    def test_zero_count_is_rejected(self):
        with self.assertRaises(ValueError):
            versions.expand("recent:0")

    def test_empty_registry_reports_why_recent_is_empty(self):
        with mock.patch.object(versions, "REGISTRY", "/nonexistent/submissions.json"):
            with self.assertRaises(KeyError) as caught:
                versions.expand("recent")
        self.assertIn("no versions", str(caught.exception))


class LiveRegistryTest(unittest.TestCase):
    """The shipped submissions.json must actually satisfy the workflow."""

    def test_recent_default_resolves_against_real_snapshots(self):
        specs = versions.expand("recent")
        self.assertGreaterEqual(len(specs), 5, "need 5-7 past agents to measure against")
        for spec in specs:
            path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                spec["module"].replace(".", os.sep) + ".py")
            self.assertTrue(os.path.exists(path), f"{spec['name']} has no frozen snapshot")


if __name__ == "__main__":
    unittest.main()
