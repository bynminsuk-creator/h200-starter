import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile


RUNNER = Path(__file__).resolve().parents[1] / "scripts" / "runner.py"


class RunnerTests(unittest.TestCase):
    def run_job(self, code, *, idle=4, maximum=6, executable=None):
        with tempfile.TemporaryDirectory() as temp:
            env = dict(os.environ, OUTPUT_ROOT=temp, PYTHONIOENCODING="utf-8")
            command = [executable] if executable else [sys.executable, "-u", "-c", code]
            result = subprocess.run(
                [sys.executable, str(RUNNER), "--idle-seconds", str(idle),
                 "--max-seconds", str(maximum), "--", *command],
                env=env, capture_output=True, text=True, encoding="utf-8", timeout=12,
            )
            output, = Path(temp).iterdir()
            summary = json.loads((output / "summary.json").read_text())
            with zipfile.ZipFile(output / "results.zip") as archive:
                self.assertIsNone(archive.testzip())
                self.assertEqual(json.loads(archive.read("summary.json")), summary)
            log = (output / "run.log").read_bytes() if (output / "run.log").exists() else b""
            return result, summary, log

    def test_success_and_result_directory(self):
        result, summary, log = self.run_job(
            "import os; from pathlib import Path; "
            "Path(os.environ['RUN_OUTPUT_DIR'], 'metric.txt').write_text('0.5'); "
            "print('job OK')"
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(summary["status"], "passed")
        self.assertIn(b"job OK", log)

    def test_failure_keeps_exit_code_and_log(self):
        result, summary, log = self.run_job("import sys; print('failed step'); sys.exit(7)")
        self.assertEqual(result.returncode, 7)
        self.assertEqual(summary["reason"], "command_failed")
        self.assertIn(b"failed step", log)

    def test_missing_command_still_saves_summary(self):
        result, summary, _ = self.run_job("", executable="h200-command-that-does-not-exist")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(summary["status"], "failed")
        self.assertIn("FileNotFoundError", summary["reason"])

    def test_silent_job_is_terminated(self):
        result, summary, _ = self.run_job("import time; time.sleep(8)", idle=0.6)
        self.assertEqual(result.returncode, 124)
        self.assertEqual(summary["reason"], "idle_timeout")
        self.assertLess(summary["elapsed_seconds"], 4)

    def test_deadline_applies_even_when_logs_continue(self):
        result, summary, _ = self.run_job(
            "import time\nfor _ in range(80):\n print('progress', flush=True); time.sleep(0.05)",
            idle=2, maximum=0.8,
        )
        self.assertEqual(result.returncode, 124)
        self.assertEqual(summary["reason"], "deadline")

    @unittest.skipUnless(os.name == "posix", "POSIX descriptor semantics")
    def test_process_that_closes_output_before_exit(self):
        result, summary, _ = self.run_job(
            "import os,time; os.close(1); os.close(2); time.sleep(0.3)", idle=2,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(summary["reason"], "completed")

    def test_full_log_and_comment_output_are_bounded(self):
        result, summary, log = self.run_job("print('x' * (9 * 1024**2))")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(summary["status"], "passed")
        self.assertEqual(len(log), 8 * 1024**2)
        self.assertLess(len(result.stdout.encode("utf-8")), 14000)


if __name__ == "__main__":
    unittest.main()
