"""Public repo trust boundary and callback lifecycle contract."""
from pathlib import Path
import re
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]


class Workflows(unittest.TestCase):
    def test_self_hosted_jobs_use_installed_entrypoint_only(self):
        for filename in ("crcr.yml", "_crcr-schedule.yml", "_crcr-run.yml", "reconcile-run.yml"):
            workflow = yaml.safe_load(
                (ROOT / ".github/workflows" / filename).read_text()
            )
            for job in workflow["jobs"].values():
                if "runs-on" not in job:
                    continue
                self.assertIn("self-hosted", job["runs-on"])
                for step in job["steps"]:
                    if "run" in step:
                        self.assertRegex(
                            step["run"], r"^/opt/crcr/bin/crcrctl [a-z-]+$"
                        )
                    if "uses" in step:
                        self.assertEqual(step["uses"], "./.crcr-actions/callback")

    def test_matrix_is_dynamic_and_has_independent_callback_names(self):
        doc = yaml.safe_load((ROOT / ".github/workflows/_crcr-run.yml").read_text())
        job = doc["jobs"]["monitor"]
        self.assertFalse(job["strategy"]["fail-fast"])
        self.assertIn("fromJSON", job["strategy"]["matrix"]["job"])
        callback = [s for s in job["steps"] if "uses" in s]
        self.assertEqual(
            [s["with"]["status"] for s in callback], ["in_progress", "completed"]
        )
        self.assertTrue(
            all(s["with"]["job-name"] == "${{ matrix.job.id }}" for s in callback)
        )
        terminal = next(s for s in job["steps"] if s.get("id") == "terminal")
        self.assertNotIn("steps.start.outcome == 'success'", terminal["if"])
        self.assertEqual(job["permissions"]["id-token"], "write")
        self.assertEqual(job["steps"][0]["env"]["GITHUB_CHECK_RUN_ID"], "${{ job.check_run_id }}")

    def test_concurrency_is_after_admission(self):
        text = (ROOT / ".github/workflows/crcr.yml").read_text()
        doc = yaml.safe_load(text)
        self.assertNotIn("concurrency", doc)
        self.assertTrue(doc["jobs"]["execute"]["concurrency"]["cancel-in-progress"])
        self.assertIn(
            "outputs.generation", doc["jobs"]["execute"]["concurrency"]["group"]
        )
        self.assertEqual(doc["jobs"]["execute"]["uses"], "./.github/workflows/_crcr-schedule.yml")

    def test_scheduler_orders_layers_and_does_not_treat_reporting_failure_as_business_failure(self):
        doc = yaml.safe_load((ROOT / '.github/workflows/_crcr-schedule.yml').read_text())
        self.assertIn('${{ inputs.planning_label }}', doc['jobs']['plan']['runs-on'])
        stages = ('prepare', 'build', 'test')
        self.assertEqual(set(doc['jobs']), {'plan', *stages, 'whole_plan'})
        self.assertEqual(
            {key for key in doc['jobs']['plan']['outputs'] if key.startswith('layer_')},
            {'layer_0', 'layer_1', 'layer_2'},
        )
        for index, stage in enumerate(stages):
            job = doc['jobs'][stage]
            self.assertEqual(job['name'], stage.title())
            self.assertEqual(job['needs'], ['plan'] if index == 0 else ['plan', stages[index-1]])
            self.assertIn('always()', job['if'])
            self.assertIn('!cancelled()', job['if'])
            self.assertNotIn('.result', job['if'].replace('needs.plan.result', ''))
            self.assertIn("schedule_mode == 'layered'", job['if'])
            self.assertIn('needs.plan.outputs.layer_' + str(index) + " != '[]'", job['if'])
            self.assertEqual(job['uses'], './.github/workflows/_crcr-run.yml')
            self.assertEqual(job['with']['jobs_json'], '${{ needs.plan.outputs.layer_' + str(index) + ' }}')
        fallback = doc['jobs']['whole_plan']
        self.assertIn("schedule_mode == 'whole_plan'", fallback['if'])
        self.assertEqual(fallback['with']['jobs_json'], '${{ needs.plan.outputs.jobs_json }}')

    def test_no_unpinned_remote_actions(self):
        for p in (ROOT / ".github/workflows").glob("*.yml"):
            for action in re.findall(r"uses: ([^\s]+)", p.read_text()):
                if not action.startswith("./"):
                    self.assertRegex(action, r"@[0-9a-f]{40}$")


if __name__ == "__main__":
    unittest.main()
