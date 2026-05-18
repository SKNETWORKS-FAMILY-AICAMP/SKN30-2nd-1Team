import csv
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import batch
import main as cli_main
from src.fetcher import fetch_comments
from src.parser import FIELDNAMES, parse_directory, parse_info_json, write_csv, _to_mysql_dt


class TimestampTests(unittest.TestCase):
    def test_to_mysql_dt_converts_unix_to_utc_string(self):
        result = _to_mysql_dt(0)
        self.assertEqual(result, "1970-01-01 00:00:00")

    def test_to_mysql_dt_returns_none_for_none_input(self):
        self.assertIsNone(_to_mysql_dt(None))

    def test_parse_info_json_timestamps_are_datetime_strings(self):
        sample = {
            "id": "vid1",
            "timestamp": 1000000,
            "comments": [
                {
                    "id": "c1",
                    "parent": "root",
                    "text": "hello",
                    "like_count": 0,
                    "author_id": "auth1",
                    "author_is_uploader": False,
                    "author_is_verified": False,
                    "timestamp": 2000000,
                    "is_favorited": False,
                    "is_pinned": False,
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            json_path = Path(tmp) / "video.info.json"
            json_path.write_text(json.dumps(sample), encoding="utf-8")
            rows = parse_info_json(json_path)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["video_published_at"], "1970-01-12 13:46:40")
        self.assertEqual(rows[0]["timestamp"], "1970-01-24 03:33:20")

    def test_parse_info_json_none_timestamp_handled_safely(self):
        sample = {"id": "vid1", "timestamp": None, "comments": []}
        with tempfile.TemporaryDirectory() as tmp:
            json_path = Path(tmp) / "video.info.json"
            json_path.write_text(json.dumps(sample), encoding="utf-8")
            rows = parse_info_json(json_path)
        self.assertEqual(rows, [])


class ParserTests(unittest.TestCase):
    def test_write_csv_writes_header_for_empty_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "comments.csv"

            write_csv([], output_path)

            with open(output_path, encoding="utf-8-sig", newline="") as f:
                header = next(csv.reader(f))

        self.assertEqual(header, FIELDNAMES)

    def test_parse_directory_writes_header_only_csv_for_zero_comments(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "raw"
            input_dir.mkdir()
            output_path = Path(tmp) / "comments.csv"
            with open(input_dir / "video.info.json", "w", encoding="utf-8") as f:
                json.dump({"id": "video", "timestamp": 1, "comments": []}, f)

            with redirect_stdout(io.StringIO()):
                count = parse_directory(input_dir, output_path)

            self.assertEqual(count, 0)
            with open(output_path, encoding="utf-8-sig", newline="") as f:
                rows = list(csv.reader(f))
        self.assertEqual(rows, [FIELDNAMES])


class MainTests(unittest.TestCase):
    def test_no_save_json_deletes_raw_file_after_csv_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            json_path = tmp_path / "channel_video.info.json"
            json_path.write_text("{}", encoding="utf-8")

            def write_csv_asserts_raw_still_exists(rows, output_path):
                self.assertTrue(json_path.exists())

            argv = ["main.py", "video", "--no-save-json", "--output", "out.csv"]
            with patch.object(sys, "argv", argv), \
                patch.object(cli_main, "fetch_comments", return_value=json_path), \
                patch.object(cli_main, "parse_info_json", return_value=[]), \
                patch.object(cli_main, "write_csv", side_effect=write_csv_asserts_raw_still_exists), \
                redirect_stdout(io.StringIO()):
                cli_main.main()

            self.assertFalse(json_path.exists())


class FetcherTests(unittest.TestCase):
    def test_remote_components_are_opt_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw_dir = Path(tmp)
            (raw_dir / "abc.info.json").write_text('{"channel_id": "channel"}', encoding="utf-8")

            with patch("src.fetcher.shutil.which", return_value="/usr/bin/deno"), \
                patch("subprocess.run") as run:
                fetch_comments("abc", raw_dir)

            command = run.call_args.args[0]
        self.assertNotIn("--remote-components", command)

    def test_remote_components_flag_adds_yt_dlp_option(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw_dir = Path(tmp)
            (raw_dir / "abc.info.json").write_text('{"channel_id": "channel"}', encoding="utf-8")

            with patch("src.fetcher.shutil.which", return_value="/usr/bin/deno"), \
                patch("subprocess.run") as run:
                fetch_comments("abc", raw_dir, remote_components=True)

            command = run.call_args.args[0]
        self.assertIn("--remote-components", command)
        self.assertIn("ejs:github", command)

    def test_missing_deno_fails_with_clear_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("src.fetcher.shutil.which", return_value=None):
                with self.assertRaisesRegex(RuntimeError, "Deno is required"):
                    fetch_comments("abc", Path(tmp))

    def test_youtube_extractor_args_include_top_sort_and_comment_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw_dir = Path(tmp)
            (raw_dir / "abc.info.json").write_text('{"channel_id": "channel"}', encoding="utf-8")

            with patch("src.fetcher.shutil.which", return_value="/usr/bin/deno"), \
                patch("subprocess.run") as run:
                fetch_comments("abc", raw_dir, comment_limit="120,120,0")

            command = run.call_args.args[0]
        self.assertIn("--extractor-args", command)
        self.assertIn("youtube:comment_sort=top;max_comments=120,120,0", command)


class BatchTests(unittest.TestCase):
    def test_dry_run_reports_skipped_instead_of_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            videos_dir = tmp_path / "videos"
            videos_dir.mkdir()
            input_tsv = tmp_path / "input.tsv"
            input_tsv.write_text("channel_number\tchannel_id\n1\tchannel\n", encoding="utf-8")
            (videos_dir / "videos.csv").write_text(
                "channel_id,video_id,published_at\nchannel,video,2025-01-01T00:00:00Z\n",
                encoding="utf-8",
            )

            output = io.StringIO()
            with patch.object(batch, "VIDEOS_CSV_DIR", videos_dir), redirect_stdout(output):
                batch.run_batch(
                    input_tsv,
                    tmp_path / "raw",
                    tmp_path / "csv",
                    no_save_json=False,
                    dry_run=True,
                )

        summary = output.getvalue()
        self.assertIn("Skipped: 1", summary)
        self.assertNotIn("Success: 1", summary)


class BatchPolicyTests(unittest.TestCase):
    def _make_videos_csv(self, videos_dir: Path, rows: list[tuple[str, str, str]]) -> None:
        content = "channel_id,video_id,published_at\n"
        content += "".join(f"{ch},{vid},{pub}\n" for ch, vid, pub in rows)
        (videos_dir / "videos.csv").write_text(content, encoding="utf-8")

    def test_load_videos_returns_newest_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            videos_dir = Path(tmp)
            self._make_videos_csv(videos_dir, [
                ("ch", "old", "2024-01-01T00:00:00Z"),
                ("ch", "new", "2025-06-01T00:00:00Z"),
                ("ch", "mid", "2024-12-01T00:00:00Z"),
            ])
            with patch.object(batch, "VIDEOS_CSV_DIR", videos_dir):
                result = batch.load_videos_for_channel("ch")
        self.assertEqual(result, ["new", "mid", "old"])

    def test_load_videos_caps_at_max_videos_per_channel(self):
        with tempfile.TemporaryDirectory() as tmp:
            videos_dir = Path(tmp)
            rows = [("ch", f"v{i:02d}", f"2025-{i:02d}-01T00:00:00Z") for i in range(1, 25)]
            self._make_videos_csv(videos_dir, rows)
            with patch.object(batch, "VIDEOS_CSV_DIR", videos_dir):
                result = batch.load_videos_for_channel("ch")
        self.assertEqual(len(result), batch.MAX_VIDEOS_PER_CHANNEL)
        self.assertEqual(result[0], "v24")

    def test_policy_constants_have_expected_values(self):
        self.assertEqual(batch.MAX_VIDEOS_PER_CHANNEL, 10)
        self.assertEqual(batch.COMMENT_FETCH_LIMIT, "60,60,0")
        self.assertEqual(batch.MAX_VIEWER_COMMENTS, 50)

    def test_run_batch_passes_comment_limit_and_parse_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            videos_dir = tmp_path / "videos"
            videos_dir.mkdir()
            input_tsv = tmp_path / "input.tsv"
            input_tsv.write_text("channel_number\tchannel_id\n1\tchannel\n", encoding="utf-8")
            self._make_videos_csv(videos_dir, [("channel", "vid1", "2025-01-01T00:00:00Z")])

            fake_json = tmp_path / "fake.info.json"
            fake_json.write_text("{}", encoding="utf-8")

            with patch.object(batch, "VIDEOS_CSV_DIR", videos_dir), \
                 patch.object(batch, "fetch_comments", return_value=fake_json) as mock_fetch, \
                 patch.object(batch, "parse_info_json", return_value=[]) as mock_parse, \
                 patch.object(batch, "write_csv"), \
                 redirect_stdout(io.StringIO()):
                batch.run_batch(
                    input_tsv,
                    tmp_path / "raw",
                    tmp_path / "csv",
                    no_save_json=False,
                )

            fetch_kwargs = mock_fetch.call_args.kwargs
            self.assertEqual(fetch_kwargs.get("comment_limit"), batch.COMMENT_FETCH_LIMIT)

            parse_kwargs = mock_parse.call_args.kwargs
            self.assertEqual(parse_kwargs.get("max_comments"), batch.MAX_VIEWER_COMMENTS)
            self.assertTrue(parse_kwargs.get("exclude_uploader"))
            self.assertTrue(parse_kwargs.get("root_only"))


class ChannelFailureTests(unittest.TestCase):
    def _make_videos_csv(self, videos_dir: Path) -> None:
        (videos_dir / "videos.csv").write_text(
            "channel_id,video_id,published_at\n", encoding="utf-8"
        )

    def test_video_list_fetch_failure_does_not_abort_batch(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cwd = Path.cwd()
            videos_dir = tmp_path / "videos"
            videos_dir.mkdir()
            self._make_videos_csv(videos_dir)
            input_tsv = tmp_path / "input.tsv"
            input_tsv.write_text(
                "CH001\tchannel_a\nCH002\tchannel_b\n",
                encoding="utf-8",
            )

            try:
                os.chdir(tmp_path)
                with patch.object(batch, "VIDEOS_CSV_DIR", videos_dir), \
                     patch.object(batch, "_fetch_video_ids_from_youtube",
                                  side_effect=RuntimeError("network error")), \
                     redirect_stdout(io.StringIO()):
                    batch.run_batch(
                        input_tsv, tmp_path / "raw", tmp_path / "csv", no_save_json=False,
                    )

                failed_ch_files = list(tmp_path.glob("failed_channels_*.tsv"))
                self.assertTrue(len(failed_ch_files) > 0, "failed_channels_*.tsv not created")
            finally:
                os.chdir(cwd)

    def test_failed_channels_tsv_contains_correct_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cwd = Path.cwd()
            videos_dir = tmp_path / "videos"
            videos_dir.mkdir()
            self._make_videos_csv(videos_dir)
            input_tsv = tmp_path / "input.tsv"
            input_tsv.write_text(
                "channel_number\tchannel_id\nCH001\tchannel_a\n",
                encoding="utf-8",
            )

            try:
                os.chdir(tmp_path)
                with patch.object(batch, "VIDEOS_CSV_DIR", videos_dir), \
                     patch.object(batch, "_fetch_video_ids_from_youtube",
                                  side_effect=RuntimeError("dns error")), \
                     redirect_stdout(io.StringIO()):
                    batch.run_batch(
                        input_tsv, tmp_path / "raw", tmp_path / "csv", no_save_json=False,
                    )

                failed_ch_files = list(tmp_path.glob("failed_channels_*.tsv"))
                self.assertTrue(len(failed_ch_files) > 0)
                with open(failed_ch_files[-1], encoding="utf-8", newline="") as f:
                    rows = list(csv.DictReader(f, delimiter="\t"))
            finally:
                os.chdir(cwd)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["channel_number"], "CH001")
        self.assertEqual(rows[0]["channel_id"], "channel_a")
        self.assertEqual(rows[0]["reason"], "video_list_fetch_failed")
        self.assertIn("dns error", rows[0]["error_message"])

    def test_channel_failure_does_not_create_video_failed_tsv(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cwd = Path.cwd()
            videos_dir = tmp_path / "videos"
            videos_dir.mkdir()
            self._make_videos_csv(videos_dir)
            input_tsv = tmp_path / "input.tsv"
            input_tsv.write_text(
                "channel_number\tchannel_id\nCH001\tchannel_a\n",
                encoding="utf-8",
            )

            try:
                os.chdir(tmp_path)
                with patch.object(batch, "VIDEOS_CSV_DIR", videos_dir), \
                     patch.object(batch, "_fetch_video_ids_from_youtube",
                                  side_effect=RuntimeError("error")), \
                     redirect_stdout(io.StringIO()):
                    batch.run_batch(
                        input_tsv, tmp_path / "raw", tmp_path / "csv", no_save_json=False,
                    )

                video_failed_files = list(tmp_path.glob("failed_[0-9]*.tsv"))
                self.assertEqual(len(video_failed_files), 0)
            finally:
                os.chdir(cwd)


if __name__ == "__main__":
    unittest.main()
