import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build_snapshot as bs
import events as ev
import freeze
import run_tests_once as rt
from config import MARKER_PURPOSE, SCOPE_OPTIONS, SCOPE_OUTCOMES

SECRET = 987.654


def write_marker(path: Path, scope: str) -> None:
    path.write_text(json.dumps(dict(purpose=MARKER_PURPOSE, scope=scope, approved_by="user", approved_on="2026-11-04")))


def good_series(n=600):
    dates = pd.bdate_range("2021-01-04", periods=n)
    return pd.DataFrame(dict(session_date=dates, atm30=0.6, tier=1))


class Run(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.record, self.result = self.root / "run.json", self.root / "result.json"
        self.options, self.outcomes = self.root / "options.json", self.root / "outcomes.json"
        self.step_a_file = self.root / "step_a.json"
        self.b_calls = []
        self.hash = "frozenhash"

    def run_once(self, series=None, run_b=None, note=None, check=None, save=None, accept=False, accept_stop=False, expected=None):
        series = good_series() if series is None else series

        def default_b(chosen):
            self.b_calls.append(1)
            return dict(decision=dict(outcome="Supported"), line="the verdict line"), pd.DataFrame()

        output = StringIO()
        try:
            with redirect_stdout(output), redirect_stderr(output):
                return rt.run_test(note, self.record, self.result, self.options, self.outcomes, check or (lambda: None), lambda: (series, pd.DataFrame(), dict(sessions=len(series), atm30_days=int(series["atm30"].notna().sum()))), run_b or default_b, save or (lambda panel, terms: None), lambda: self.hash, self.step_a_file, accept, accept_stop, expected)
        finally:
            self.output = output.getvalue()

    def status(self):
        return json.loads(self.record.read_text())["status"]

    def approve_both(self):
        write_marker(self.options, SCOPE_OPTIONS)
        write_marker(self.outcomes, SCOPE_OUTCOMES)

    def test_no_marker_refuses_before_any_read(self):
        with self.assertRaises(rt.RunRefused):
            self.run_once()
        self.assertFalse(self.record.exists())

    def test_empty_marker_refuses(self):
        self.options.write_text("{}")
        with self.assertRaises(rt.RunRefused):
            self.run_once()

    def test_manifest_check_runs_before_the_record_starts(self):
        self.approve_both()

        def fail():
            raise freeze.ManifestMismatch("changed")

        with self.assertRaises(freeze.ManifestMismatch):
            self.run_once(check=fail)
        self.assertFalse(self.record.exists())

    def test_full_run_writes_a_result_and_refuses_a_second_run(self):
        self.approve_both()
        self.run_once()
        self.assertTrue(self.result.exists())
        self.assertEqual(self.status(), "finished")
        with self.assertRaises(rt.RunRefused):
            self.run_once()
        with self.assertRaises(rt.RunRefused):
            self.run_once(note="a fix after the outcome")
        self.assertEqual(len(self.b_calls), 1)

    def test_hash_goes_to_screen_record_and_result(self):
        self.approve_both()
        self.run_once()
        self.assertIn("frozenhash", self.output)
        self.assertEqual(json.loads(self.record.read_text())["attempts"][0]["manifest_sha256"], "frozenhash")
        self.assertEqual(json.loads(self.result.read_text())["manifest_sha256"], "frozenhash")

    def test_floor_failure_is_not_final_until_accepted(self):
        self.approve_both()
        thin = good_series().assign(atm30=np.nan)
        result = self.run_once(thin)
        self.assertIsNone(result["decision"])
        self.assertEqual(self.status(), "floor_failed")
        self.assertFalse(self.result.exists())
        self.assertEqual(self.b_calls, [])
        self.assertTrue(self.step_a_file.exists())
        with self.assertRaises(rt.RunRefused):
            self.run_once(thin)

    def test_accepted_floor_failure_is_final_and_reads_no_outcome(self):
        self.approve_both()
        thin = good_series().assign(atm30=np.nan)
        self.run_once(thin)
        result = self.run_once(thin, accept=True)
        self.assertEqual(result["decision"]["outcome"], rt.rules.NO_FLOOR)
        self.assertEqual(self.b_calls, [])
        self.assertEqual(self.status(), "finished")
        with self.assertRaises(rt.RunRefused):
            self.run_once()

    def test_floor_failure_can_be_fixed_with_a_note(self):
        self.approve_both()
        self.run_once(good_series().assign(atm30=np.nan))
        self.run_once(note="Fixed the rates. Logged in PROTOCOL.md.")
        self.assertEqual(len(self.b_calls), 1)
        self.assertTrue(self.result.exists())

    def test_accept_needs_a_failed_floor(self):
        self.approve_both()
        with self.assertRaises(rt.RunRefused):
            self.run_once(accept=True)

    def test_options_marker_alone_stops_before_outcomes(self):
        write_marker(self.options, SCOPE_OPTIONS)
        result = self.run_once()
        self.assertIsNone(result["decision"])
        self.assertEqual(self.b_calls, [])
        self.assertFalse(self.result.exists())
        self.assertEqual(self.status(), "step_a_done")
        self.assertTrue(self.step_a_file.exists())

    def test_run_continues_after_step_a_stop_without_a_note(self):
        write_marker(self.options, SCOPE_OPTIONS)
        self.run_once()
        write_marker(self.outcomes, SCOPE_OUTCOMES)
        self.run_once()
        self.assertEqual(len(self.b_calls), 1)

    def test_crash_shows_no_value_and_needs_a_logged_fix(self):
        self.approve_both()

        def crash(series):
            raise ValueError(f"close was {SECRET}")

        with self.assertRaises(SystemExit):
            self.run_once(run_b=crash)
        self.assertNotIn(str(SECRET), self.output)
        self.assertNotIn(str(SECRET), self.record.read_text())
        self.assertFalse(self.result.exists())
        with self.assertRaises(rt.RunRefused):
            self.run_once()
        self.run_once(note="Fixed the reader. Logged in PROTOCOL.md.")
        self.assertEqual(len(json.loads(self.record.read_text())["attempts"]), 2)

    def guard_stop(self, series):
        self.b_calls.append(1)
        raise rt.InputGuardFailed("The largest gap of forward and close is above the limit", ["2017-03-01"])

    def stop_on_guard(self):
        self.approve_both()
        with self.assertRaises(SystemExit):
            self.run_once(run_b=self.guard_stop)

    def test_input_stop_keeps_the_dates_and_names_the_check(self):
        self.stop_on_guard()
        self.assertIn("largest gap", self.output)
        self.assertNotIn("2017-03-01", self.output)
        self.assertEqual(self.status(), rt.STATUS_INPUT_STOPPED)
        self.assertFalse(self.result.exists())
        last = json.loads(self.record.read_text())["attempts"][-1]
        self.assertEqual(last["input_stop"]["dates"], ["2017-03-01"])
        self.assertIn("largest gap", last["input_stop"]["check"])

    def test_input_stop_needs_a_changed_file_or_an_acceptance(self):
        self.stop_on_guard()
        with self.assertRaises(rt.RunRefused):
            self.run_once()
        with self.assertRaises(rt.RunRefused):
            self.run_once(note="no change at all")
        self.assertEqual(len(self.b_calls), 1)
        self.hash = "newhash"
        self.run_once(note="Fixed the date map. Logged in PROTOCOL.md.")
        self.assertEqual(self.status(), "finished")

    def test_accepted_input_stop_is_final_and_shows_the_disclosure(self):
        self.stop_on_guard()
        result = self.run_once(accept_stop=True)
        self.assertEqual(result["decision"]["outcome"], rt.INPUTS_FAILED)
        self.assertEqual(result["input_stop"]["dates"], ["2017-03-01"])
        self.assertEqual(len(self.b_calls), 1)
        self.assertEqual(self.status(), "finished")
        self.assertIn(rt.INPUTS_FAILED, self.output)
        self.assertIn(rt.DISCLOSURE, self.output)
        saved = json.loads(self.result.read_text())
        self.assertEqual(saved["manifest_sha256"], "frozenhash")
        self.assertIn(rt.DISCLOSURE, saved["disclosure"])
        self.assertIn("read the failing dates", saved["disclosure"])
        attempt = json.loads(self.record.read_text())["attempts"][-1]
        self.assertTrue(attempt["accepted_input_stop"])
        self.assertEqual(attempt["manifest_sha256"], "frozenhash")
        with self.assertRaises(rt.RunRefused):
            self.run_once(note="another try")

    def test_accept_input_stop_needs_an_input_stop(self):
        self.approve_both()
        with self.assertRaises(rt.RunRefused):
            self.run_once(accept_stop=True)
        self.run_once(good_series().assign(atm30=np.nan))
        with self.assertRaises(rt.RunRefused):
            self.run_once(accept_stop=True)

    def test_accept_input_stop_after_a_change_is_refused(self):
        self.stop_on_guard()
        self.hash = "newhash"
        with self.assertRaises(rt.RunRefused):
            self.run_once(accept_stop=True)

    def test_accepted_floor_failure_keeps_the_audit_fields(self):
        self.approve_both()
        thin = good_series().assign(atm30=np.nan)
        self.run_once(thin)
        result = self.run_once(thin, accept=True, note="Read the counts")
        self.assertIn(rt.DISCLOSURE, self.output)
        self.assertEqual((result["manifest_sha256"], result["disclosure"]), ("frozenhash", rt.DISCLOSURE))
        self.assertFalse(result["floor"]["passed"])
        attempt = json.loads(self.record.read_text())["attempts"][-1]
        self.assertEqual((attempt["manifest_sha256"], attempt["crash_fix_note"]), ("frozenhash", "Read the counts"))
        self.assertTrue(attempt["accepted_floor_failure"])

    def test_accepting_stale_counts_is_refused(self):
        self.approve_both()
        thin = good_series().assign(atm30=np.nan)
        self.run_once(thin)
        self.hash = "newhash"
        with self.assertRaises(rt.RunRefused):
            self.run_once(thin, accept=True)
        self.assertFalse(self.result.exists())

    def test_accepting_a_floor_that_passed_is_refused(self):
        self.approve_both()
        self.run_once(good_series().assign(atm30=np.nan))
        self.step_a_file.write_text(json.dumps(dict(floor=dict(passed=True), counts={})))
        with self.assertRaises(rt.RunRefused):
            self.run_once(accept=True)

    def test_accepting_with_no_step_a_file_is_refused(self):
        self.approve_both()
        self.run_once(good_series().assign(atm30=np.nan))
        self.step_a_file.unlink()
        with self.assertRaises(rt.RunRefused):
            self.run_once(accept=True)

    def test_each_attempt_keeps_its_own_counts(self):
        self.approve_both()
        self.run_once(good_series().assign(atm30=np.nan))
        self.run_once(note="Fixed the rates")
        attempts = json.loads(self.record.read_text())["attempts"]
        self.assertEqual(attempts[0]["step_a"]["counts"]["atm30_days"], 0)
        self.assertFalse(attempts[0]["step_a"]["floor"]["passed"])
        self.assertEqual(attempts[1]["step_a"]["counts"]["atm30_days"], 600)

    def test_a_changed_hash_needs_a_note(self):
        write_marker(self.options, SCOPE_OPTIONS)
        self.run_once()
        self.hash = "newhash"
        with self.assertRaises(rt.RunRefused):
            self.run_once()
        self.run_once(note="Fixed the reader")
        self.assertEqual(self.status(), "step_a_done")

    def test_blank_note_is_no_note(self):
        self.approve_both()

        def crash(series):
            raise ValueError("layout")

        with self.assertRaises(SystemExit):
            self.run_once(run_b=crash)
        with self.assertRaises(rt.RunRefused):
            self.run_once(note="   ")

    def test_history_lists_an_earlier_input_stop(self):
        self.stop_on_guard()
        self.hash = "newhash"
        result = self.run_once(note="Fixed the map")
        past = result["history"]["attempts"]
        self.assertEqual(len(past), 1)
        self.assertEqual(past[0]["input_stop"]["dates"], ["2017-03-01"])
        self.assertIn("read the failing dates", result["disclosure"])
        self.assertIn("read the failing dates", self.output)
        self.assertEqual(json.loads(self.result.read_text())["history"]["attempts"][0]["manifest_sha256"], "frozenhash")

    def test_clean_run_has_an_empty_history(self):
        self.approve_both()
        result = self.run_once()
        self.assertEqual(result["history"], dict(attempts=[], refreezes=[]))
        self.assertEqual(result["disclosure"], rt.DISCLOSURE)

    def test_stale_accept_with_a_note_is_refused(self):
        self.stop_on_guard()
        self.hash = "newhash"
        with self.assertRaises(rt.RunRefused):
            self.run_once(accept_stop=True, note="a note")
        with self.assertRaises(rt.RunRefused):
            self.run_once(accept=True, note="a note")

    def test_accept_floor_needs_the_status_even_with_a_step_a_file(self):
        self.approve_both()
        self.record.write_text(json.dumps(dict(status="crashed", attempts=[dict(manifest_sha256="frozenhash")])))
        self.step_a_file.write_text(json.dumps(dict(floor=dict(passed=False), counts={})))
        with self.assertRaises(rt.RunRefused):
            self.run_once(accept=True)

    def test_result_file_alone_refuses(self):
        self.approve_both()
        self.result.write_text("{}")
        with self.assertRaises(rt.RunRefused):
            self.run_once(note="another try")
        self.assertFalse(self.record.exists())

    def accept_setup(self, kind):
        if kind == "floor":
            self.approve_both()
            self.run_once(good_series().assign(atm30=np.nan))
            return dict(accept=True)
        self.stop_on_guard()
        return dict(accept_stop=True)

    def test_accept_paths_survive_a_failed_rename(self):
        for kind in ("floor", "input"):
            with self.subTest(kind=kind):
                self.setUp()
                flags = self.accept_setup(kind)
                real_replace = Path.replace

                def fail_for_result(path, target):
                    if Path(target) == self.result:
                        raise PermissionError("locked")
                    return real_replace(path, target)

                with mock.patch.object(Path, "replace", fail_for_result), mock.patch.object(rt, "RENAME_WAIT", 0):
                    self.run_once(**flags)
                self.assertEqual(self.status(), freeze.STATUS_FINISHING)
                self.assertIn("Inconclusive", self.output)
                self.assertIn(rt.DISCLOSURE, self.output)
                self.assertTrue(self.result.with_suffix(".partial").exists())

    def test_accept_paths_treat_a_failed_finishing_write_as_a_crash(self):
        for kind in ("floor", "input"):
            with self.subTest(kind=kind):
                self.setUp()
                flags = self.accept_setup(kind)
                real = rt.write_json

                def fail_finishing(path, value):
                    if value.get("status") == freeze.STATUS_FINISHING:
                        raise OSError("disk full")
                    real(path, value)

                with mock.patch.object(rt, "write_json", fail_finishing), self.assertRaises(SystemExit):
                    self.run_once(**flags)
                self.assertEqual(self.status(), "crashed")
                self.assertNotIn("Inconclusive,", self.output)
                self.assertFalse(self.result.exists())

    def test_truncated_partial_is_not_kept(self):
        self.approve_both()
        real = rt.write_text

        def truncate(path, text):
            if path == self.result:
                path.with_suffix(".partial").write_text(text[:10], encoding="utf-8")
                raise OSError("disk full")
            real(path, text)

        with mock.patch.object(rt, "write_text", truncate):
            self.run_once()
        self.assertIn('"line": "the verdict line"', self.output)

    def test_partial_with_bad_bytes_is_not_kept(self):
        self.approve_both()
        real = rt.write_text

        def garble(path, text):
            if path == self.result:
                path.with_suffix(".partial").write_bytes(b"\xff\xfe\x00bad")
                raise OSError("disk full")
            real(path, text)

        with mock.patch.object(rt, "write_text", garble):
            self.run_once()
        self.assertIn('"line": "the verdict line"', self.output)

    def test_interrupt_during_the_result_write_keeps_the_outcome(self):
        self.approve_both()
        real = rt.write_text
        saved = []

        def interrupt(path, text):
            if path == self.result:
                raise KeyboardInterrupt
            real(path, text)

        with mock.patch.object(rt, "write_text", interrupt):
            self.run_once(save=lambda panel, terms: saved.append(1))
        self.assertIn('"line": "the verdict line"', self.output)
        self.assertIn(rt.DISCLOSURE, self.output)
        self.assertEqual(saved, [1])

    def test_failed_print_of_the_line_keeps_the_disclosure_and_the_frames(self):
        self.approve_both()
        saved = []
        seen = []
        real_print = print

        def flaky(text="", **kwargs):
            if text == "the verdict line":
                raise OSError("stdout gone")
            seen.append(text)
            real_print(text, **kwargs)

        with mock.patch("builtins.print", flaky):
            self.run_once(save=lambda panel, terms: saved.append(1))
        self.assertIn(rt.DISCLOSURE, seen)
        self.assertEqual(saved, [1])

    def test_failed_save_does_not_claim_a_safe_result(self):
        self.approve_both()

        def fail_save(panel, terms):
            raise OSError("no space")

        self.run_once(save=fail_save)
        self.assertIn("The frames were not saved", self.output)
        self.assertNotIn("safe", self.output.replace(rt.DISCLOSURE, ""))

    def test_stop_run_hides_the_write_error_and_stops_an_interrupt(self):
        self.approve_both()

        def crash(series):
            raise ValueError(f"close was {SECRET}")

        real = rt.write_json

        def fail_crashed(path, value):
            if value.get("status") == "crashed":
                raise KeyboardInterrupt(f"write {SECRET}")
            real(path, value)

        with mock.patch.object(rt, "write_json", fail_crashed), self.assertRaises(SystemExit) as caught:
            self.run_once(run_b=crash)
        self.assertTrue(caught.exception.__suppress_context__)
        self.assertNotIn(str(SECRET), self.output)

    def test_rename_retry_waits_between_tries(self):
        path = self.root / "file.json"
        with mock.patch.object(Path, "replace", side_effect=[PermissionError("locked"), None]), mock.patch.object(rt.time, "sleep") as sleep:
            rt.write_text(path, "{}")
        sleep.assert_called_once_with(rt.RENAME_WAIT)

    def test_note_of_the_final_attempt_is_in_the_result(self):
        self.stop_on_guard()
        self.hash = "newhash"
        result = self.run_once(note="Fixed the map")
        self.assertEqual(result["crash_fix_note"], "Fixed the map")
        self.assertEqual(json.loads(self.result.read_text())["crash_fix_note"], "Fixed the map")

    def test_clean_run_has_no_note_in_the_result(self):
        self.approve_both()
        self.assertIsNone(self.run_once()["crash_fix_note"])

    def test_note_of_an_accepted_stop_is_in_the_result(self):
        self.stop_on_guard()
        self.assertEqual(self.run_once(accept_stop=True, note="Read the dates")["crash_fix_note"], "Read the dates")

    def test_accepted_stop_result_holds_the_history(self):
        self.stop_on_guard()
        result = self.run_once(accept_stop=True)
        saved = json.loads(self.result.read_text())
        self.assertEqual(saved["history"], rt.to_json(result["history"]))
        self.assertEqual(len(saved["history"]["attempts"]), 1)
        self.assertEqual(saved["history"]["attempts"][0]["input_stop"]["dates"], ["2017-03-01"])
        self.assertIn("See the history", saved["disclosure"])

    def test_history_keeps_exact_keys_and_refreezes(self):
        attempt = dict(started="t", manifest_sha256="h", crash_fix_note="n", error="e", input_stop=dict(check="c", dates=["2017-03-01"]), step_a=dict(counts=dict(sessions=1)), other=1)
        refreezes = [dict(at="t", old_sha256="a", new_sha256="b", changed=["x.py"], note="n")]
        past = rt.history([attempt], refreezes)
        self.assertEqual(set(past["attempts"][0]), {"started", "manifest_sha256", "crash_fix_note", "error", "input_stop"})
        self.assertEqual(past["attempts"][0]["error"], "e")
        self.assertEqual(past["attempts"][0]["crash_fix_note"], "n")
        self.assertEqual(past["refreezes"], refreezes)

    def test_failed_result_write_hides_the_error_message(self):
        self.approve_both()
        with mock.patch.object(rt, "write_text", side_effect=OSError(f"disk at {SECRET}")), mock.patch.object(rt, "write_json"):
            self.run_once()
        self.assertIn("The result write did not finish: OSError", self.output)
        self.assertNotIn(str(SECRET), self.output)
        self.assertIn("the verdict line", self.output)

    def test_second_interrupt_on_the_partial_read_still_prints_the_result(self):
        self.approve_both()
        partial = self.result.with_suffix(".partial")
        real_write = rt.write_text

        def write_partial_then_fail(path, text):
            if path == self.result:
                partial.write_text(text, encoding="utf-8")
                raise KeyboardInterrupt
            real_write(path, text)

        real_read = Path.read_text

        def read(path, *args, **kwargs):
            if path == partial:
                raise KeyboardInterrupt
            return real_read(path, *args, **kwargs)

        with mock.patch.object(rt, "write_text", write_partial_then_fail), mock.patch.object(Path, "read_text", read):
            self.run_once()
        self.assertIn("No file holds the result", self.output)
        self.assertIn("the verdict line", self.output)

    def test_each_open_status_needs_a_note(self):
        self.approve_both()
        for status in ("started", "crashed", "floor_failed", rt.STATUS_INPUT_STOPPED):
            self.record.write_text(json.dumps(dict(status=status, attempts=[])))
            with self.assertRaises(rt.RunRefused):
                self.run_once()

    def test_closed_status_refuses_with_no_result_file(self):
        self.approve_both()
        for status in ("finished", freeze.STATUS_FINISHING):
            self.record.write_text(json.dumps(dict(status=status, attempts=[])))
            with self.assertRaises(rt.RunRefused):
                self.run_once(note="another try")
        self.assertEqual(self.b_calls, [])

    def test_expected_hash_refuses_before_any_read(self):
        self.approve_both()
        with self.assertRaises(rt.RunRefused):
            self.run_once(expected="otherhash")
        self.assertFalse(self.record.exists())
        self.assertEqual(self.b_calls, [])
        self.run_once(expected=" FROZENHASH ")
        self.assertEqual(self.status(), "finished")

    def test_value_that_json_cannot_write_is_an_ordinary_crash(self):
        self.approve_both()

        def bad(series):
            return dict(decision=dict(outcome="Supported"), line="the verdict line", value=object()), pd.DataFrame()

        with self.assertRaises(SystemExit):
            self.run_once(run_b=bad)
        self.assertEqual(self.status(), "crashed")
        self.assertNotIn("the verdict line", self.output)
        self.assertFalse(self.result.with_suffix(".partial").exists())
        self.run_once(note="Fixed the value")
        self.assertEqual(self.status(), "finished")

    def test_nat_is_written_as_null(self):
        self.assertIsNone(rt.to_json(pd.NaT))

    def test_failed_first_finishing_write_shows_nothing_and_permits_a_fix(self):
        self.approve_both()
        real = rt.write_json

        def fail_finishing(path, value):
            if value.get("status") == freeze.STATUS_FINISHING:
                raise OSError("disk full")
            real(path, value)

        with mock.patch.object(rt, "write_json", fail_finishing), self.assertRaises(SystemExit):
            self.run_once()
        self.assertNotIn("the verdict line", self.output)
        self.assertEqual(self.status(), "crashed")
        self.assertFalse(self.result.exists())

    def test_failed_rename_keeps_the_outcome_and_permits_no_second_look(self):
        self.approve_both()
        real_replace = Path.replace
        tries = []
        saved = []

        def fail_for_result(path, target):
            if Path(target) == self.result:
                tries.append(1)
                raise PermissionError("locked")
            return real_replace(path, target)

        with mock.patch.object(Path, "replace", fail_for_result), mock.patch.object(rt, "RENAME_WAIT", 0):
            self.run_once(save=lambda panel, terms: saved.append(1))
        self.assertEqual(len(tries), rt.RENAME_TRIES)
        self.assertEqual(self.status(), freeze.STATUS_FINISHING)
        self.assertEqual(json.loads(self.result.with_suffix(".partial").read_text())["line"], "the verdict line")
        self.assertIn("the verdict line", self.output)
        self.assertIn(rt.DISCLOSURE, self.output)
        self.assertEqual(saved, [1])
        with self.assertRaises(rt.RunRefused):
            self.run_once(note="another try")
        self.assertEqual(len(self.b_calls), 1)

    def test_rename_retry_recovers_from_a_short_lock(self):
        self.approve_both()
        real_replace = Path.replace
        tries = []

        def fail_once(path, target):
            if Path(target) == self.result and not tries:
                tries.append(1)
                raise PermissionError("locked")
            return real_replace(path, target)

        with mock.patch.object(Path, "replace", fail_once), mock.patch.object(rt, "RENAME_WAIT", 0):
            self.run_once()
        self.assertTrue(self.result.exists())
        self.assertEqual(self.status(), "finished")

    def test_result_that_no_file_holds_goes_to_the_screen(self):
        self.approve_both()
        real = rt.write_text

        def fail_for_result(path, text):
            if path == self.result:
                raise OSError("disk full")
            real(path, text)

        with mock.patch.object(rt, "write_text", fail_for_result):
            self.run_once()
        self.assertIn('"line": "the verdict line"', self.output)
        self.assertEqual(self.status(), freeze.STATUS_FINISHING)

    def test_failed_last_record_write_keeps_the_result_and_the_line(self):
        self.approve_both()
        real = rt.write_json

        def fail_finished(path, value):
            if value.get("status") == "finished":
                raise OSError("locked")
            real(path, value)

        with mock.patch.object(rt, "write_json", fail_finished):
            self.run_once()
        self.assertTrue(self.result.exists())
        self.assertIn("the verdict line", self.output)
        self.assertEqual(self.status(), freeze.STATUS_FINISHING)
        with self.assertRaises(rt.RunRefused):
            self.run_once(note="another try")

    def test_double_fault_shows_no_value(self):
        self.approve_both()

        def crash(series):
            raise ValueError(f"close was {SECRET}")

        real = rt.write_json

        def fail_crashed(path, value):
            if value.get("status") == "crashed":
                raise OSError("locked")
            real(path, value)

        script = StringIO()
        with mock.patch.object(rt, "write_json", fail_crashed):
            try:
                self.run_once(run_b=crash)
            except SystemExit as stop:
                self.assertIsNone(stop.__cause__)
                self.assertTrue(stop.__suppress_context__)
                script.write("stopped")
        self.assertEqual(script.getvalue(), "stopped")
        self.assertNotIn(str(SECRET), self.output)
        self.assertIn("The run record was not updated", self.output)
        self.assertIn("The run stopped: ValueError", self.output)
        self.assertEqual(self.status(), "started")
        self.run_once(note="Fixed the reader")
        self.assertEqual(self.status(), "finished")

    def test_input_stop_with_a_failed_record_write_shows_no_date(self):
        self.approve_both()
        real = rt.write_json

        def fail_stopped(path, value):
            if value.get("status") == rt.STATUS_INPUT_STOPPED:
                raise OSError("locked")
            real(path, value)

        with mock.patch.object(rt, "write_json", fail_stopped), self.assertRaises(SystemExit):
            self.run_once(run_b=self.guard_stop)
        self.assertNotIn("2017-03-01", self.output)

    def test_line_and_disclosure_print_before_the_frames_save(self):
        self.approve_both()
        seen = {}

        def save(panel, terms):
            seen["text"] = sys.stdout.getvalue()

        self.run_once(save=save)
        self.assertIn("the verdict line", seen["text"])
        self.assertIn(rt.DISCLOSURE, seen["text"])

    def test_result_holds_the_full_disclosure(self):
        self.approve_both()
        self.run_once()
        self.assertEqual(json.loads(self.result.read_text())["disclosure"], rt.DISCLOSURE)
        for words in ("no contact", "in memory", "condition file", "offering price", "2017-09-26", "depositary", "format break"):
            self.assertIn(words, rt.DISCLOSURE)

    def test_default_wiring_uses_the_locked_dates_markers_rates_and_test_events(self):
        self.approve_both()
        series = good_series()
        result = dict(decision=dict(outcome="Supported"), line="the verdict line")
        with mock.patch.object(rt, "step_a", return_value=(series, pd.DataFrame(), dict(sessions=600, atm30_days=600))) as step_a, mock.patch.object(rt, "step_b", return_value=(result, pd.DataFrame())) as step_b, redirect_stdout(StringIO()):
            rt.run_test(None, self.record, self.result, self.options, self.outcomes, lambda: None, None, None, lambda panel, terms: None, lambda: "frozenhash", self.step_a_file)
        step_a.assert_called_once_with(rt.TEST_START, rt.TEST_END, self.options, rt.TEST_RATES)
        step_b.assert_called_once_with(series, rt.TEST_START, rt.TEST_END, self.outcomes, ev.TEST_EVENTS)

    def test_leftover_partial_file_refuses_a_run(self):
        self.approve_both()
        self.result.with_suffix(".partial").write_text("{}")
        with self.assertRaises(rt.RunRefused):
            self.run_once()

    def test_failed_frame_save_keeps_the_line_and_shows_no_value(self):
        self.approve_both()

        def fail_save(panel, terms):
            raise OSError(f"value {SECRET}")

        self.run_once(save=fail_save)
        self.assertIn("the verdict line", self.output)
        self.assertNotIn(str(SECRET), self.output)
        self.assertEqual(self.status(), "finished")


class CrashPathWithRealManifest(unittest.TestCase):
    """The crash path with the real manifest check, on temporary files."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.code = self.root / "code.py"
        self.code.write_text("x = 1\n")
        self.manifest = self.root / "manifest.json"
        self.record, self.result = self.root / "run.json", self.root / "result.json"
        self.options, self.outcomes = self.root / "options.json", self.root / "outcomes.json"
        write_marker(self.options, SCOPE_OPTIONS)
        write_marker(self.outcomes, SCOPE_OUTCOMES)
        self.first_hash = freeze.write_manifest(self.manifest, [self.code], self.root)

    def run_once(self, run_a, note=None):
        output = StringIO()
        with redirect_stdout(output), redirect_stderr(output):
            return rt.run_test(note, self.record, self.result, self.options, self.outcomes, lambda: freeze.verify_manifest(self.manifest, [self.code], self.root), run_a, lambda series: (dict(decision=dict(outcome="Supported"), line="line"), pd.DataFrame()), lambda panel, terms: None, lambda: freeze.sha256(self.manifest), self.root / "step_a.json")

    def after_crash(self, note="Fixed the reader"):
        return freeze.after_crash(note, self.manifest, self.record, self.result, [self.code], self.root)

    def good_a(self):
        series = good_series()
        return series, pd.DataFrame(), dict(sessions=len(series), atm30_days=len(series))

    def crash_once(self):
        def crash():
            raise ValueError("layout")

        with self.assertRaises(SystemExit):
            self.run_once(crash)

    def test_fix_refreeze_and_rerun_keep_the_audit_trail(self):
        self.crash_once()
        self.code.write_text("x = 2\n")
        with self.assertRaises(freeze.ManifestMismatch):
            self.run_once(self.good_a, note="Fixed the reader")
        new_hash = self.after_crash()
        self.assertNotEqual(new_hash, self.first_hash)
        self.run_once(self.good_a, note="Fixed the reader")
        record = json.loads(self.record.read_text())
        self.assertEqual(record["status"], "finished")
        self.assertEqual(record["refreezes"][0], dict(record["refreezes"][0], old_sha256=self.first_hash, new_sha256=new_hash, note="Fixed the reader"))
        self.assertEqual(json.loads(self.result.read_text())["manifest_sha256"], new_hash)
        self.assertEqual([a["manifest_sha256"] for a in record["attempts"]], [self.first_hash, new_hash])

    def test_no_crash_freeze_without_a_run(self):
        self.code.write_text("x = 2\n")
        with self.assertRaises(freeze.FreezeRefused):
            self.after_crash()

    def test_no_crash_freeze_without_a_note(self):
        self.crash_once()
        self.code.write_text("x = 2\n")
        with self.assertRaises(freeze.FreezeRefused):
            self.after_crash("  ")

    def test_default_inputs_are_protected(self):
        data = self.root / "bars.json"
        data.write_text("[1]")
        files = [self.code, data]
        freeze.write_manifest(self.manifest, files, self.root)
        self.set_status("crashed")
        data.write_text("[2]")
        with mock.patch.object(freeze, "INPUT_FILES", [data]), mock.patch.object(freeze, "frozen_files", return_value=files), self.assertRaises(freeze.FreezeRefused):
            freeze.after_crash("no crash", self.manifest, self.record, self.result, None, self.root)

    def test_failed_manifest_write_leaves_the_old_manifest_whole(self):
        old_text = self.manifest.read_text()
        self.crash_once()
        self.code.write_text("x = 2\n")
        real_write = Path.write_text

        def fail_partial(path, *args, **kwargs):
            if path == self.manifest.with_suffix(".partial"):
                raise OSError("disk full")
            return real_write(path, *args, **kwargs)

        with mock.patch.object(Path, "write_text", fail_partial), self.assertRaises(OSError):
            self.after_crash()
        self.assertEqual(self.manifest.read_text(), old_text)
        self.assertEqual(self.after_crash(), freeze.sha256(self.manifest))

    def test_no_crash_freeze_after_a_result(self):
        self.run_once(self.good_a)
        with self.assertRaises(freeze.FreezeRefused):
            self.after_crash()
        self.assertEqual(freeze.sha256(self.manifest), self.first_hash)

    def test_no_crash_freeze_with_a_partial_result(self):
        self.crash_once()
        self.code.write_text("x = 2\n")
        self.result.with_suffix(".partial").write_text("{}")
        with self.assertRaises(freeze.FreezeRefused):
            self.after_crash()

    def test_no_crash_freeze_with_a_result_file_alone(self):
        self.crash_once()
        self.code.write_text("x = 2\n")
        self.result.write_text("{}")
        with self.assertRaises(freeze.FreezeRefused):
            self.after_crash()

    def set_status(self, status):
        self.record.write_text(json.dumps(dict(status=status, attempts=[])))

    def test_crash_freeze_is_permitted_for_each_open_status(self):
        for number, status in enumerate(freeze.AFTER_CRASH_STATUSES):
            self.set_status(status)
            self.code.write_text(f"x = {number + 10}\n")
            self.assertEqual(self.after_crash(), freeze.sha256(self.manifest))
        self.assertEqual(freeze.AFTER_CRASH_STATUSES, ("started", "crashed", "floor_failed", "step_a_done", rt.STATUS_INPUT_STOPPED))

    def test_crash_freeze_is_refused_for_each_closed_status(self):
        self.code.write_text("x = 2\n")
        for status in ("finished", freeze.STATUS_FINISHING):
            self.set_status(status)
            with self.assertRaises(freeze.FreezeRefused):
                self.after_crash()
        self.assertEqual(freeze.sha256(self.manifest), self.first_hash)

    def test_crash_freeze_with_no_change_is_refused(self):
        self.crash_once()
        with self.assertRaises(freeze.FreezeRefused):
            self.after_crash()

    def test_crash_freeze_records_the_change_and_keeps_the_old_manifest(self):
        old_text = self.manifest.read_text()
        self.crash_once()
        self.code.write_text("x = 2\n")
        self.after_crash()
        entry = json.loads(self.record.read_text())["refreezes"][0]
        self.assertEqual(entry["changed"], ["code.py"])
        self.assertEqual(self.manifest.with_name(f"manifest_{self.first_hash[:12]}.json").read_text(), old_text)

    def test_crash_freeze_refuses_a_changed_input_without_the_flag(self):
        data = self.root / "bars.json"
        data.write_text("[1]")
        files = [self.code, data]
        self.first_hash = freeze.write_manifest(self.manifest, files, self.root)
        self.set_status("crashed")
        data.write_text("[2]")
        with self.assertRaises(freeze.FreezeRefused):
            freeze.after_crash("no crash", self.manifest, self.record, self.result, files, self.root, [data])
        self.assertEqual(freeze.sha256(self.manifest), self.first_hash)
        freeze.after_crash("A logged input fix", self.manifest, self.record, self.result, files, self.root, [data], allow_input_change=True)
        self.assertEqual(json.loads(self.record.read_text())["refreezes"][0]["changed"], ["bars.json"])

    def test_failed_record_write_keeps_the_old_manifest_in_place(self):
        self.crash_once()
        self.code.write_text("x = 2\n")
        with mock.patch.object(Path, "replace", side_effect=PermissionError("locked")), self.assertRaises(PermissionError):
            self.after_crash()
        self.assertEqual(freeze.sha256(self.manifest), self.first_hash)
        new_hash = self.after_crash()
        entry = json.loads(self.record.read_text())["refreezes"][0]
        self.assertEqual((entry["old_sha256"], entry["new_sha256"]), (self.first_hash, new_hash))

    def test_new_hash_in_the_record_matches_the_file(self):
        self.crash_once()
        self.code.write_text("x = 2\n")
        new_hash = self.after_crash()
        self.assertEqual(new_hash, freeze.sha256(self.manifest))

    def test_rerun_after_a_crash_freeze_needs_a_note(self):
        write_marker(self.outcomes, "other")
        self.run_once(self.good_a)
        self.assertEqual(json.loads(self.record.read_text())["status"], "step_a_done")
        self.code.write_text("x = 2\n")
        self.after_crash()
        with self.assertRaises(rt.RunRefused):
            self.run_once(self.good_a)


def panel_for_guard(n=100, gap=0.0):
    close = pd.Series(np.full(n, 50.0))
    return pd.DataFrame(dict(session_date=pd.bdate_range("2021-01-04", periods=n), close=close, near_forward=close * np.exp(gap)))


class NormalFreeze(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        names = dict(OPTIONS_MARKER="options.json", OUTCOMES_MARKER="outcomes.json", RUN_RECORD="run.json", RESULT="result.json")
        self.paths = {key: self.root / name for key, name in names.items()}
        for key, path in self.paths.items():
            patcher = mock.patch.object(freeze, key, path)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = mock.patch.object(freeze, "REPORTS", self.root)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_clean_folder_passes(self):
        freeze.refuse_after_unlock()

    def test_each_trace_of_a_run_refuses(self):
        traces = list(self.paths.values()) + [self.root / "backward_test_unlocked.json", self.root / "result.partial", self.root / "stage5_step_a.json"]
        for path in traces:
            path.write_text("{}")
            with self.assertRaises(SystemExit):
                freeze.refuse_after_unlock()
            path.unlink()

    def test_main_checks_before_it_writes(self):
        (self.root / "run.json").write_text("{}")
        with mock.patch.object(sys, "argv", ["freeze.py"]), mock.patch.object(freeze, "write_manifest") as write, self.assertRaises(SystemExit):
            freeze.main()
        write.assert_not_called()


class CommandLine(unittest.TestCase):
    def setUp(self):
        hook = sys.excepthook
        self.addCleanup(setattr, sys, "excepthook", hook)

    def test_run_passes_every_flag(self):
        argv = ["run_tests_once.py", "--run", "--crash-fix-note", "a note", "--accept-input-stop", "--accept-floor-failure", "--expected-hash", "abc"]
        with mock.patch.object(sys, "argv", argv), mock.patch.object(rt, "run_test") as run:
            rt.main()
        run.assert_called_once_with("a note", accept_floor_failure=True, accept_input_stop=True, expected_hash="abc")
        self.assertIs(sys.excepthook, rt.safe_excepthook)

    def test_freeze_passes_the_input_flag(self):
        argv = ["freeze.py", "--after-crash", "a note", "--allow-input-change"]
        with mock.patch.object(sys, "argv", argv), mock.patch.object(freeze, "after_crash", return_value="hash") as after, redirect_stdout(StringIO()):
            freeze.main()
        after.assert_called_once_with("a note", allow_input_change=True)

    def test_manifest_lists_code_tests_rules_and_inputs(self):
        names = {path.name for path in freeze.frozen_files()}
        self.assertTrue({"run_tests_once.py", "freeze.py", "test_run_once.py", "PROTOCOL.md", "STAGE4_PLAN.md", "fred_rates_test.csv"} <= names)
        self.assertIn(rt.ALPACA_BARS.name, names)
        self.assertIn(freeze.ADR_CASH_EVENTS.name, names)
        self.assertIn(freeze.OPTION_CBBO.name, names)
        self.assertIn(freeze.OPTION_DEFINITIONS.name, names)

    def test_excepthook_keeps_a_refusal_and_hides_other_messages(self):
        stream = StringIO()
        with redirect_stderr(stream):
            rt.safe_excepthook(rt.RunRefused, rt.RunRefused("not permitted"), None)
            rt.safe_excepthook(freeze.ManifestMismatch, freeze.ManifestMismatch("changed file"), None)
            rt.safe_excepthook(ValueError, ValueError(f"close was {SECRET}"), None)
        self.assertIn("not permitted", stream.getvalue())
        self.assertIn("changed file", stream.getvalue())
        self.assertNotIn(str(SECRET), stream.getvalue())


class Say(unittest.TestCase):
    def test_an_interrupt_inside_a_print_does_not_raise(self):
        with mock.patch("builtins.print", side_effect=KeyboardInterrupt):
            rt.say("text")

    def test_a_failure_inside_the_hook_does_not_raise(self):
        with mock.patch.object(rt, "safe_error", side_effect=KeyboardInterrupt):
            rt.safe_excepthook(ValueError, ValueError(f"close was {SECRET}"), None)


CHILD = """
import json, sys
from pathlib import Path
sys.path.insert(0, {project!r})
import pandas as pd
import run_tests_once as rt
from config import MARKER_PURPOSE, SCOPE_OPTIONS, SCOPE_OUTCOMES
root = Path({root!r})
for name, scope in (("options.json", SCOPE_OPTIONS), ("outcomes.json", SCOPE_OUTCOMES)):
    (root / name).write_text(json.dumps(dict(purpose=MARKER_PURPOSE, scope=scope, approved_by="user", approved_on="2026-11-04")))
dates = pd.bdate_range("2021-01-04", periods=600)
series = pd.DataFrame(dict(session_date=dates, atm30=0.6, tier=1))
def crash(chosen):
    raise ValueError("close was 987.654")
real = rt.write_json
def fail(path, value):
    if value.get("status") == "crashed":
        raise {fault}
    real(path, value)
rt.write_json = fail
sys.excepthook = rt.safe_excepthook
rt.run_test(None, root / "run.json", root / "result.json", root / "options.json", root / "outcomes.json", lambda: None, lambda: (series, pd.DataFrame(), dict(sessions=600, atm30_days=600)), crash, lambda panel, terms: None, lambda: "hash", root / "step_a.json")
"""


class ChildProcess(unittest.TestCase):
    """Python prints the context of an error only at the top level, so only a real process can show a leak."""

    def run_child(self, fault):
        with tempfile.TemporaryDirectory() as folder:
            script = Path(folder) / "child.py"
            script.write_text(CHILD.format(project=str(Path(__file__).resolve().parents[1]), root=folder, fault=fault))
            return subprocess.run([sys.executable, "-B", str(script)], capture_output=True, text=True, timeout=120, cwd=folder)

    def test_no_message_reaches_the_screen(self):
        for fault in ("OSError('locked')", "KeyboardInterrupt()"):
            with self.subTest(fault=fault):
                done = self.run_child(fault)
                self.assertNotIn("987.654", done.stderr + done.stdout)
                self.assertIn("The run stopped: ValueError", done.stderr)
                self.assertEqual(done.returncode, 1)


class Wiring(unittest.TestCase):
    def test_step_a_counts_blank_rates(self):
        dates = pd.bdate_range("2021-01-04", periods=3)
        diagnostics = pd.DataFrame(dict(session_date=dates, unmatched_quotes=0, other_roots=0, last_row_null_bids=0, cbbo_rows=10, null_bid_share=0.1, first_bar="09:30", last_bar="16:00"))
        rates = pd.DataFrame(dict(DGS1MO=[0.01, np.nan, np.nan], DGS3MO=[0.01, 0.01, np.nan]), index=dates)
        series = pd.DataFrame(dict(session_date=dates, atm30=np.nan, tier=np.nan, status="no pair", year=2021))
        with mock.patch.object(rt, "snapshot_tables", return_value=(None, None, diagnostics)), mock.patch.object(rt, "session_rates", return_value=rates), mock.patch.object(rt, "series_tables", return_value=(series, pd.DataFrame(), 0)), mock.patch.object(rt, "day_conditions", return_value={}):
            _, _, counts = rt.step_a(dates[0], dates[-1], None, Path("rates.csv"))
        self.assertEqual(counts["blank_rate_sessions"], 2)


class Guard(unittest.TestCase):
    def test_limits_are_the_frozen_values(self):
        self.assertEqual((rt.GUARD_MEDIAN, rt.GUARD_SHARE_GAP, rt.GUARD_SHARE, rt.GUARD_LARGEST, rt.GUARD_NO_FORWARD, rt.GUARD_ONE_SOURCE_SESSIONS), (0.02, 0.05, 0.05, 0.15, 0.15, 3))

    def test_bad_close_on_a_session_with_no_forward_stops(self):
        panel = panel_for_guard()
        panel.loc[panel.index[50], "near_forward"] = np.nan
        panel.loc[panel.index[50], "close"] = 50 * np.exp(0.149)
        rt.input_guard(panel, 0, 0)
        panel.loc[panel.index[50], "close"] = 50 * np.exp(0.151)
        with self.assertRaisesRegex(rt.InputGuardFailed, "no forward") as caught:
            rt.input_guard(panel, 0, 0)
        self.assertEqual(caught.exception.dates, [str(panel["session_date"].iloc[50].date())])
        self.assertNotIn("50", str(caught.exception))

    def test_real_jump_near_one_side_passes(self):
        panel = panel_for_guard()
        panel.loc[panel.index[50:], ["close", "near_forward"]] = 25.0
        panel.loc[panel.index[50], "near_forward"] = np.nan
        rt.input_guard(panel, 0, 0)

    def test_no_forward_at_an_edge_uses_the_one_side(self):
        panel = panel_for_guard()
        panel.loc[panel.index[0], "near_forward"] = np.nan
        panel.loc[panel.index[0], "close"] = 75.0
        with self.assertRaisesRegex(rt.InputGuardFailed, "no forward"):
            rt.input_guard(panel, 0, 0)

    def test_low_bad_close_stops(self):
        panel = panel_for_guard()
        panel.loc[panel.index[50], "near_forward"] = np.nan
        panel.loc[panel.index[50], "close"] = 50 * np.exp(-0.151)
        with self.assertRaisesRegex(rt.InputGuardFailed, "no forward"):
            rt.input_guard(panel, 0, 0)

    def test_stray_on_the_last_row_stops(self):
        panel = panel_for_guard()
        panel.loc[panel.index[-1], "near_forward"] = np.nan
        panel.loc[panel.index[-1], "close"] = 75.0
        with self.assertRaisesRegex(rt.InputGuardFailed, "no forward"):
            rt.input_guard(panel, 0, 0)

    def test_gap_to_forwards_takes_the_nearer_side(self):
        for left, right in ((50.0, 25.0), (25.0, 50.0)):
            with self.subTest(left=left, right=right):
                panel = panel_for_guard()
                panel.loc[panel.index[:50], "near_forward"] = left
                panel.loc[panel.index[51:], "near_forward"] = right
                panel.loc[panel.index[50], "near_forward"] = np.nan
                self.assertAlmostEqual(rt.no_forward_gaps(panel).iloc[0], 0.0)

    def test_dates_list_only_the_stray_among_blank_rows(self):
        panel = panel_for_guard()
        panel.loc[panel.index[[10, 11, 50, 60, 61]], "near_forward"] = np.nan
        panel.loc[panel.index[50], "close"] = 75.0
        with self.assertRaisesRegex(rt.InputGuardFailed, "no forward") as caught:
            rt.input_guard(panel, 0, 0)
        self.assertEqual(caught.exception.dates, [str(panel["session_date"].iloc[50].date())])

    def test_drift_in_a_blank_run_passes(self):
        """The false stop that the condition removes: closes walk away from the forwards, and each stays near an adjacent close."""
        panel = panel_for_guard()
        panel.loc[panel.index[50:56], "near_forward"] = np.nan
        panel.loc[panel.index[50:56], "close"] = 50 * np.exp(np.array([0.08, 0.16, 0.24, 0.24, 0.16, 0.08]))
        self.assertTrue((rt.no_forward_gaps(panel) > rt.GUARD_NO_FORWARD).any())
        rt.input_guard(panel, 0, 0)

    def test_adjacent_close_limit_on_each_side(self):
        for side in (49, 51):
            with self.subTest(side=side):
                panel = panel_for_guard()
                panel.loc[panel.index[49:52], "near_forward"] = np.nan
                panel.loc[panel.index[50], "close"] = 50 * np.exp(0.30)
                panel.loc[panel.index[side], "close"] = 50 * np.exp(0.30 - 0.149)
                rt.input_guard(panel, 0, 0)
                panel.loc[panel.index[side], "close"] = 50 * np.exp(0.30 - 0.151)
                with self.assertRaisesRegex(rt.InputGuardFailed, "adjacent") as caught:
                    rt.input_guard(panel, 0, 0)
                self.assertIn(str(panel["session_date"].iloc[50].date()), caught.exception.dates)

    def test_close_near_a_forward_is_not_listed_even_if_far_from_adjacent_closes(self):
        panel = panel_for_guard()
        panel.loc[panel.index[49:52], "near_forward"] = np.nan
        panel.loc[panel.index[49:52], "close"] = [75.0, 50.0, 75.0]
        self.assertGreater(rt.adjacent_close_gaps(panel).iloc[50], rt.GUARD_NO_FORWARD)
        with self.assertRaisesRegex(rt.InputGuardFailed, "adjacent") as caught:
            rt.input_guard(panel, 0, 0)
        self.assertEqual(caught.exception.dates, [str(panel["session_date"].iloc[49].date()), str(panel["session_date"].iloc[51].date())])

    def test_known_limit_bad_closes_that_agree_pass(self):
        """Stated in PROTOCOL.md: two adjacent bad closes on blank sessions do not stop this check."""
        panel = panel_for_guard()
        panel.loc[panel.index[50:52], "near_forward"] = np.nan
        panel.loc[panel.index[50:52], "close"] = 75.0
        rt.input_guard(panel, 0, 0)

    def test_dates_use_each_check_limit(self):
        panel = panel_for_guard()
        panel.loc[panel.index[10], "near_forward"] = 50 * np.exp(0.10)
        panel.loc[panel.index[20], "near_forward"] = 50 * np.exp(0.20)
        with self.assertRaisesRegex(rt.InputGuardFailed, "largest") as caught:
            rt.input_guard(panel, 0, 0)
        self.assertEqual(caught.exception.dates, [str(panel["session_date"].iloc[20].date())])
        panel = panel_for_guard(gap=0.03)
        panel.loc[panel.index[10], "near_forward"] = 50 * np.exp(0.01)
        with self.assertRaisesRegex(rt.InputGuardFailed, "median") as caught:
            rt.input_guard(panel, 0, 0)
        self.assertEqual(len(caught.exception.dates), 99)

    def test_largest_gap_limit(self):
        panel = panel_for_guard()
        panel.loc[panel.index[50], "near_forward"] = 50 * np.exp(0.149)
        rt.input_guard(panel, 0, 0)
        panel.loc[panel.index[50], "near_forward"] = 50 * np.exp(0.151)
        with self.assertRaisesRegex(rt.InputGuardFailed, "largest") as caught:
            rt.input_guard(panel, 0, 0)
        self.assertEqual(caught.exception.dates, [str(panel["session_date"].iloc[50].date())])

    def test_median_limit_and_dates(self):
        rt.input_guard(panel_for_guard(gap=0.0199), 0, 0)
        with self.assertRaisesRegex(rt.InputGuardFailed, "median") as caught:
            rt.input_guard(panel_for_guard(gap=0.0201), 0, 0)
        self.assertEqual(len(caught.exception.dates), 100)

    def test_share_gap_limit_and_dates(self):
        panel = panel_for_guard()
        panel.loc[panel.index[:6], "near_forward"] = 50 * np.exp(0.049)
        rt.input_guard(panel, 0, 0)
        panel.loc[panel.index[:6], "near_forward"] = 50 * np.exp(0.051)
        with self.assertRaisesRegex(rt.InputGuardFailed, "share") as caught:
            rt.input_guard(panel, 0, 0)
        self.assertEqual(len(caught.exception.dates), 6)

    def test_one_source_stop_keeps_its_dates(self):
        days = pd.to_datetime(["2021-01-05", "2021-01-04"])
        with self.assertRaises(rt.InputGuardFailed) as caught:
            rt.input_guard(panel_for_guard(), 2, 2, days)
        self.assertEqual(caught.exception.dates, ["2021-01-04", "2021-01-05"])

    def test_clean_inputs_pass(self):
        rt.input_guard(panel_for_guard(gap=0.003), 0, 0)

    def test_three_sessions_in_one_source_pass_and_four_stop(self):
        rt.input_guard(panel_for_guard(), 2, 1)
        with self.assertRaises(rt.InputGuardFailed):
            rt.input_guard(panel_for_guard(), 2, 2)

    def test_median_gap_stops(self):
        with self.assertRaisesRegex(rt.InputGuardFailed, "median"):
            rt.input_guard(panel_for_guard(gap=0.021), 0, 0)

    def test_share_of_large_gaps_stops(self):
        panel = panel_for_guard()
        panel.loc[panel.index[:6], "near_forward"] = 50 * np.exp(0.06)
        with self.assertRaisesRegex(rt.InputGuardFailed, "share"):
            rt.input_guard(panel, 0, 0)

    def test_share_at_the_limit_passes(self):
        panel = panel_for_guard()
        panel.loc[panel.index[:5], "near_forward"] = 50 * np.exp(0.06)
        rt.input_guard(panel, 0, 0)

    def test_one_bad_close_stops(self):
        panel = panel_for_guard()
        panel.loc[panel.index[50], "close"] = 75.0
        with self.assertRaisesRegex(rt.InputGuardFailed, "largest"):
            rt.input_guard(panel, 0, 0)

    def test_blank_forwards_on_missing_days_are_ignored(self):
        panel = panel_for_guard()
        panel.loc[panel.index[:50], "near_forward"] = np.nan
        rt.input_guard(panel, 0, 0)

    def test_no_forward_stops(self):
        with self.assertRaises(rt.InputGuardFailed):
            rt.input_guard(panel_for_guard().assign(near_forward=np.nan), 0, 0)
        with self.assertRaises(rt.InputGuardFailed):
            rt.input_guard(panel_for_guard().drop(columns="near_forward"), 0, 0)

    def test_message_holds_no_value(self):
        panel = panel_for_guard()
        panel.loc[panel.index[50], "close"] = SECRET
        with self.assertRaises(rt.InputGuardFailed) as caught:
            rt.input_guard(panel, 0, 0)
        self.assertNotIn(str(SECRET), str(caught.exception))


class StepACounts(unittest.TestCase):
    def test_counts_hold_no_index_value(self):
        series = pd.DataFrame(dict(session_date=pd.bdate_range("2021-01-04", periods=3), atm30=[SECRET, np.nan, SECRET], tier=[1, np.nan, 2], status=["ok", "no bracket", "ok"], year=2021))
        diagnostics = pd.DataFrame(dict(unmatched_quotes=[0, 1, 0], other_roots=[0, 0, 2], last_row_null_bids=[0, 3, 0], cbbo_rows=[10, 20, 30], null_bid_share=[0.1, 0.2, 0.3], first_bar=["09:30"] * 3, last_bar=["16:00"] * 3))
        counts = rt.step_a_counts(series, diagnostics, 4)
        self.assertEqual(counts["status_by_year"]["2021"], dict(ok=2, **{"no bracket": 1}))
        self.assertEqual((counts["unmatched_quotes"], counts["other_roots"], counts["last_row_null_bids"], counts["duplicate_quotes"]), (1, 2, 3, 4))
        self.assertNotIn(str(SECRET), json.dumps(rt.to_json(counts)))

    def test_counts_show_blank_rates(self):
        series = pd.DataFrame(dict(session_date=pd.bdate_range("2021-01-04", periods=1), atm30=[np.nan], tier=[np.nan], status=["no pair"], year=2021))
        diagnostics = pd.DataFrame(dict(unmatched_quotes=[0], other_roots=[0], last_row_null_bids=[0], cbbo_rows=[10], null_bid_share=[0.1], first_bar=["09:30"], last_bar=["16:00"]))
        self.assertEqual(rt.step_a_counts(series, diagnostics, 0, 7)["blank_rate_sessions"], 7)


class LastQuotes(unittest.TestCase):
    def frame(self):
        day = "2021-06-01"
        return pd.DataFrame(dict(instrument_id=[1, 1, 2], ts_recv=pd.to_datetime([f"{day} 14:00", f"{day} 15:00", f"{day} 15:00"]).tz_localize(bs.NY), bid_px_00=[1.0, np.nan, 2.0], ask_px_00=[1.5, 1.6, 2.5])), day

    def test_last_quotes_keeps_the_last_non_null_value(self):
        frame, day = self.frame()
        last = bs.last_quotes(frame, day).set_index("instrument_id")
        self.assertEqual(last.loc[1, "bid_px_00"], 1.0)
        self.assertEqual(last.loc[1, "ask_px_00"], 1.6)
        self.assertEqual(last.loc[1, "age"], 45.0)

    def test_null_bids_in_the_last_row_are_counted(self):
        frame, day = self.frame()
        self.assertEqual(bs.last_row_null_bids(frame, day), 1)


class FloorFromFlags(unittest.TestCase):
    def test_counts_only_rows_with_inputs_and_a_full_window(self):
        series = good_series(100)
        floor = rt.floor_from_flags(series)
        last = series["session_date"].iloc[-1]
        expected = int(((series.index >= rt.HAR_START) & (series["session_date"] + pd.Timedelta(days=30) <= last)).sum())
        self.assertEqual(floor["origins"], expected)
        self.assertLess(floor["origins"], 100 - rt.HAR_START)

    def test_flags_floor_matches_the_panel_floor(self):
        rng = np.random.default_rng(2)
        series = good_series(620)
        series.loc[rng.choice(620, 80, replace=False), "atm30"] = np.nan
        closes = pd.DataFrame(dict(session_date=series["session_date"], close=50 * np.exp(np.cumsum(rng.normal(0, 0.03, 620)))))
        panel = rt.rules.add_inputs(rt.rz.realized_from_closes(closes, pd.DataFrame(dict(ex_date=pd.to_datetime([]), kind=[], usd_per_ads=[]))).merge(series, on="session_date"))
        self.assertEqual(rt.floor_from_flags(series), rt.rules.data_floor(panel["primary"].to_numpy()))


class StepB(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "bars.json"
        rng = np.random.default_rng(4)
        self.dates = pd.bdate_range("2022-01-03", periods=620)
        self.close = 50 * np.exp(np.cumsum(rng.normal(0, 0.03, 620)))
        self.series = pd.DataFrame(dict(session_date=self.dates, atm30=0.6 * np.exp(rng.normal(0, 0.2, 620)), tier=1, near_forward=self.close))

    def write_bars(self, close):
        bars = [dict(t=f"{d.date()}T05:00:00Z", c=float(c)) for d, c in zip(self.dates, close)]
        self.path.write_text(json.dumps(dict(pages=[dict(bars=dict(GGAL=bars))])))

    def run_step(self, series=None):
        return rt.step_b(self.series if series is None else series, self.dates[0], self.dates[-1], None, [("event", "2022-06-05")], 40, "synthetic", self.path)

    def test_synthetic_run_ends_at_the_last_session(self):
        self.write_bars(self.close)
        result, _ = self.run_step()
        self.assertEqual(result["counts"]["alpaca_sessions"], 620)
        self.assertEqual((result["counts"]["only_alpaca"], result["counts"]["only_options"]), (0, 0))
        self.assertLessEqual(pd.Timestamp(result["counts"]["last_window_end"]), self.dates[-1])
        self.assertIn(result["decision"]["outcome"], (rt.rules.SUPPORTED, rt.rules.SMALLER, rt.rules.INCONCLUSIVE))
        self.assertIn("synthetic", result["line"])
        json.dumps(rt.to_json(result))

    def test_data_fault_name_and_dates_reach_the_stop(self):
        days = [pd.Timestamp("2022-03-01")]
        with mock.patch.object(rt, "load_alpaca_closes", side_effect=rt.DataFault("The named fault", days)), self.assertRaises(rt.InputGuardFailed) as caught:
            self.run_step()
        self.assertEqual(str(caught.exception), "The named fault")
        self.assertEqual(caught.exception.dates, ["2022-03-01"])

    def test_bad_close_stops_before_any_result(self):
        bad = self.close.copy()
        bad[300] *= 1.5
        self.write_bars(bad)
        with mock.patch.object(rt.rules, "evaluate") as evaluate, self.assertRaises(rt.InputGuardFailed):
            self.run_step()
        evaluate.assert_not_called()

    def test_wrong_option_map_stops_before_any_result(self):
        self.write_bars(self.close)
        wrong = self.series.assign(near_forward=self.close * 1.5)
        with mock.patch.object(rt.rules, "evaluate") as evaluate, self.assertRaises(rt.InputGuardFailed):
            self.run_step(wrong)
        evaluate.assert_not_called()

    def test_session_mismatch_stops_before_any_result(self):
        self.write_bars(self.close)
        with mock.patch.object(rt.rules, "evaluate") as evaluate, self.assertRaises(rt.InputGuardFailed) as caught:
            self.run_step(self.series.drop(index=[10, 20, 30, 40]))
        evaluate.assert_not_called()
        self.assertEqual(caught.exception.dates, [str(self.dates[i].date()) for i in (10, 20, 30, 40)])

    def test_session_mismatch_lists_days_of_both_sources(self):
        self.write_bars(self.close)
        extra = pd.DataFrame(dict(session_date=[self.dates[-1] + pd.Timedelta(days=1)], atm30=[0.6], tier=[1], near_forward=[50.0]))
        chosen = pd.concat([self.series.drop(index=[10, 20, 30, 40]), extra], ignore_index=True)
        with self.assertRaises(rt.InputGuardFailed) as caught:
            rt.step_b(chosen, self.dates[0], self.dates[-1] + pd.Timedelta(days=1), None, [("event", "2022-06-05")], 40, "synthetic", self.path)
        self.assertEqual(len(caught.exception.dates), 5)

    def fault_dates(self, close):
        with mock.patch.object(rt.rules, "evaluate") as evaluate, self.assertRaises(rt.InputGuardFailed) as caught:
            self.run_step()
        evaluate.assert_not_called()
        return caught.exception

    def test_close_that_is_not_positive_is_an_input_stop(self):
        bad = self.close.copy()
        bad[300] = -SECRET
        self.write_bars(bad)
        stop = self.fault_dates(bad)
        self.assertEqual(stop.dates, [str(self.dates[300].date())])
        self.assertNotIn(str(SECRET), str(stop))

    def test_two_bars_on_one_date_is_an_input_stop(self):
        bars = [dict(t=f"{d.date()}T05:00:00Z", c=float(c)) for d, c in zip(self.dates, self.close)]
        bars.append(dict(t=f"{self.dates[5].date()}T06:00:00Z", c=SECRET))
        self.path.write_text(json.dumps(dict(pages=[dict(bars=dict(GGAL=bars))])))
        stop = self.fault_dates(None)
        self.assertEqual(stop.dates, [str(self.dates[5].date())])
        self.assertNotIn(str(SECRET), str(stop))

    def test_no_bar_is_an_input_stop(self):
        self.path.write_text(json.dumps(dict(pages=[dict(bars=dict(GGAL=[]))])))
        self.assertEqual(self.fault_dates(None).dates, [])

    def test_ex_date_that_is_not_a_session_is_an_input_stop(self):
        self.write_bars(self.close)
        day = pd.Timestamp("2022-01-08")
        events = pd.DataFrame(dict(ex_date=[day], kind=["dividend"], usd_per_ads=[SECRET]))
        with mock.patch.object(rt, "load_cash_events", return_value=events):
            stop = self.fault_dates(None)
        self.assertEqual(stop.dates, ["2022-01-08"])
        self.assertNotIn(str(SECRET), str(stop))

    def test_layout_fault_stays_an_ordinary_crash(self):
        self.path.write_text(json.dumps(dict(pages=[])) .replace("pages", "other"))
        with self.assertRaises(ValueError) as caught:
            self.run_step()
        self.assertNotIsInstance(caught.exception, rt.InputGuardFailed)

    def test_test_events_do_not_enter_the_open_list(self):
        self.assertEqual(len(ev.TEST_EVENTS), 2)
        self.assertFalse({date for _, date in ev.TEST_EVENTS} & {date for _, date in ev.EVENTS})


class Manifest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.file = self.root / "code.py"
        self.file.write_text("x = 1\n")
        self.manifest = self.root / "manifest.json"

    def test_unchanged_files_pass(self):
        freeze.write_manifest(self.manifest, [self.file], self.root)
        freeze.verify_manifest(self.manifest, [self.file], self.root)

    def test_a_change_fails_and_names_the_file(self):
        freeze.write_manifest(self.manifest, [self.file], self.root)
        self.file.write_text("x = 2\n")
        with self.assertRaises(freeze.ManifestMismatch) as caught:
            freeze.verify_manifest(self.manifest, [self.file], self.root)
        self.assertIn("code.py", str(caught.exception))

    def test_failed_rename_keeps_the_old_manifest_whole(self):
        freeze.write_manifest(self.manifest, [self.file], self.root)
        old = self.manifest.read_bytes()
        self.file.write_text("x = 2\n")
        with mock.patch.object(Path, "replace", side_effect=OSError("locked")), self.assertRaises(OSError):
            freeze.write_manifest(self.manifest, [self.file], self.root)
        self.assertEqual(self.manifest.read_bytes(), old)

    def test_manifest_has_no_carriage_return(self):
        freeze.write_manifest(self.manifest, [self.file], self.root)
        self.assertNotIn(b"\r", self.manifest.read_bytes())

    def test_absent_manifest_fails(self):
        with self.assertRaises(freeze.ManifestMismatch):
            freeze.verify_manifest(self.manifest, [self.file], self.root)


if __name__ == "__main__":
    unittest.main()
