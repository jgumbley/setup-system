import contextlib
import datetime
import io
import pathlib
import tempfile
import unittest

import backup_status


class BackupStatusTest(unittest.TestCase):
    def test_record_and_status_report_hosts_in_name_order(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = pathlib.Path(temporary_directory)
            hal = root / "hal.smeg"
            hal.mkdir()
            (root / "arnold.smeg").mkdir()

            self.assertEqual(backup_status.record(hal), 0)
            recorded_at = backup_status.format_timestamp(
                (hal / backup_status.MARKER_NAME).stat().st_mtime
            )

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = backup_status.status(root)

            self.assertEqual(result, 0)
            self.assertEqual(
                output.getvalue().splitlines(),
                [
                    "HOST    LAST SUCCESSFUL BACKUP",
                    "arnold  not recorded",
                    f"hal     {recorded_at}",
                ],
            )

    def test_status_rejects_a_missing_backup_root(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            missing = pathlib.Path(temporary_directory) / "missing"
            output = io.StringIO()

            with contextlib.redirect_stderr(output):
                result = backup_status.status(missing)

            self.assertEqual(result, 1)
            self.assertEqual(
                output.getvalue(),
                f"Backup root does not exist: {missing}\n",
            )

    def test_timestamp_includes_the_local_utc_offset(self):
        timestamp = backup_status.format_timestamp(0)

        self.assertEqual(
            timestamp,
            datetime.datetime.fromtimestamp(0).astimezone().isoformat(
                sep=" ", timespec="seconds"
            ),
        )


if __name__ == "__main__":
    unittest.main()
