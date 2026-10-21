"""Offline safeguards with artificial bytes only; never downloads an MRI dataset."""
import hashlib
import io
import json
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from detection import acquisition as a


class Response(io.BytesIO):
    def __init__(self, body, status=200, headers=None):
        super().__init__(body)
        self.status = status
        self.headers = headers or {"Content-Length": str(len(body)), "ETag": '"v1"'}
        self.url = "https://publisher.example/file"


class AcquisitionSafety(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.payload = b"artificial test bytes, not MRI data"
        self.asset = {"path": "test.bin", "url": "https://publisher.example/file", "bytes": len(self.payload), "checksum": "sha256:" + hashlib.sha256(self.payload).hexdigest()}

    def test_verified_download_and_repeat_without_request(self):
        with patch.object(a, "_request", return_value=Response(self.payload)):
            self.assertEqual(a.download_verified(self.asset, self.root, max_bytes=100)["status"], "verified")
        with patch.object(a, "_request", side_effect=AssertionError("No network expected")):
            self.assertEqual(a.download_verified(self.asset, self.root, max_bytes=100)["status"], "verified_existing")

    def test_resume_with_validator(self):
        (self.root / "test.bin.part").write_bytes(self.payload[:5])
        a.atomic_json(self.root / "test.bin.resume.json", {"url": self.asset["url"], "validator": '"v1"'})
        with patch.object(a, "_request", return_value=Response(self.payload[5:], 206, {"Content-Range": f"bytes 5-{len(self.payload)-1}/{len(self.payload)}", "ETag": '"v1"'})) as request:
            a.download_verified(self.asset, self.root, max_bytes=100)
            self.assertEqual(request.call_args.kwargs["headers"]["Range"], "bytes=5-")
        self.assertEqual((self.root / "test.bin").read_bytes(), self.payload)

    def test_server_ignoring_range_restarts_partial(self):
        (self.root / "test.bin.part").write_bytes(b"stale")
        a.atomic_json(self.root / "test.bin.resume.json", {"url": self.asset["url"], "validator": '"old"'})
        with patch.object(a, "_request", return_value=Response(self.payload)):
            a.download_verified(self.asset, self.root, max_bytes=100)
        self.assertEqual((self.root / "test.bin").read_bytes(), self.payload)

    def test_bad_range_preserves_partial(self):
        (self.root / "test.bin.part").write_bytes(b"abc")
        a.atomic_json(self.root / "test.bin.resume.json", {"url": self.asset["url"], "validator": '"v1"'})
        with patch.object(a, "_request", return_value=Response(b"def", 206, {"Content-Range": "bytes 0-2/6"})):
            with self.assertRaises(RuntimeError):
                a.download_verified(self.asset, self.root, max_bytes=100)
        self.assertEqual((self.root / "test.bin.part").read_bytes(), b"abc")

    def test_hash_failure_never_promotes(self):
        with patch.object(a, "_request", return_value=Response(b"x" * len(self.payload))):
            with self.assertRaises(ValueError):
                a.download_verified(self.asset, self.root, max_bytes=100)
        self.assertFalse((self.root / "test.bin").exists())

    def test_existing_different_file_preserved(self):
        (self.root / "test.bin").write_bytes(b"user work")
        with self.assertRaises(FileExistsError):
            a.download_verified(self.asset, self.root, max_bytes=100)
        self.assertEqual((self.root / "test.bin").read_bytes(), b"user work")

    def test_truncated_payload_rejected(self):
        with patch.object(a, "_request", return_value=Response(self.payload[:-2], headers={"Content-Length": str(len(self.payload))})):
            with self.assertRaises(ValueError):
                a.download_verified(self.asset, self.root, max_bytes=100)

    def test_budget_enforced(self):
        with patch.object(a, "_request", return_value=Response(self.payload)):
            with self.assertRaises(OSError):
                a.download_verified(self.asset, self.root, max_bytes=2)

    def test_zip_traversal_preflight_before_writing(self):
        p = self.root / "test.zip"
        with zipfile.ZipFile(p, "w") as z:
            z.writestr("good.txt", "good")
            z.writestr("../escape.txt", "bad")
        with self.assertRaises(ValueError):
            a.safe_extract(p, self.root / "out", max_unpacked_bytes=100)
        self.assertFalse((self.root / "out/good.txt").exists())
        self.assertFalse((self.root / "escape.txt").exists())

    def test_tar_symlink_rejected(self):
        p = self.root / "test.tar"
        with tarfile.open(p, "w") as t:
            m = tarfile.TarInfo("link")
            m.type = tarfile.SYMTYPE
            m.linkname = "/tmp/escape"
            t.addfile(m)
        with self.assertRaises(ValueError):
            a.safe_extract(p, self.root / "out", max_unpacked_bytes=100)

    def test_zip_symlink_rejected(self):
        p = self.root / "test.zip"
        with zipfile.ZipFile(p, "w") as z:
            info = zipfile.ZipInfo("link")
            info.create_system = 3
            info.external_attr = 0o120777 << 16
            z.writestr(info, "../escape")
        with self.assertRaises(ValueError):
            a.safe_extract(p, self.root / "out", max_unpacked_bytes=100)

    def test_extract_repeat_preserves_changed_file(self):
        p = self.root / "test.zip"
        with zipfile.ZipFile(p, "w") as z:
            z.writestr("folder/test.txt", "test")
        out = self.root / "out"
        a.safe_extract(p, out, max_unpacked_bytes=100)
        a.safe_extract(p, out, max_unpacked_bytes=100)
        (out / "folder/test.txt").write_text("user change")
        with self.assertRaises(FileExistsError):
            a.safe_extract(p, out, max_unpacked_bytes=100)
        self.assertEqual((out / "folder/test.txt").read_text(), "user change")

    def test_extract_size_limit(self):
        p = self.root / "test.zip"
        with zipfile.ZipFile(p, "w") as z:
            z.writestr("big", "a" * 500)
        with self.assertRaises(OSError):
            a.safe_extract(p, self.root / "out", max_unpacked_bytes=10)

    def test_cloud_download_guard(self):
        with self.assertRaises(RuntimeError):
            a.assert_colab_drive(self.root)

    def test_destination_symlink_rejected(self):
        destination = self.root / "linked"
        destination.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            a.checked_path(destination, "test.bin")

    def test_previous_metadata_preserved(self):
        p = self.root / "report.json"
        a.atomic_json(p, {"status": "old"})
        a.atomic_json(p, {"status": "new"})
        previous = list(self.root.glob("report.json.previous.*"))
        self.assertEqual(len(previous), 1)
        self.assertEqual(json.loads(previous[0].read_text())["status"], "old")

    def test_insufficient_space_rejected(self):
        with patch.object(a.shutil, "disk_usage", return_value=type("Usage", (), {"free": 100})()):
            with self.assertRaises(OSError):
                a.require_space(self.root, 101, reserve=0)

    def test_failure_report_persisted(self):
        spec = {"id": "test", "eligible": True, "disease": "artificial", "assets": [self.asset]}
        with patch.object(a, "assert_colab_drive", return_value=self.root), patch.object(a, "_request", return_value=Response(b"x" * len(self.payload))):
            with self.assertRaises(ValueError):
                a.acquire_one(spec, self.root, download_budget_bytes=100, extraction_budget_bytes=100)
        self.assertEqual(json.loads((self.root / "acquisition_report.json").read_text())["status"], "failed")

    def test_duplicate_archive_member_rejected(self):
        p = self.root / "test.zip"
        with zipfile.ZipFile(p, "w") as z:
            z.writestr("A.txt", "a")
            z.writestr("a.txt", "b")
        with self.assertRaises(ValueError):
            a.safe_extract(p, self.root / "out", max_unpacked_bytes=100)

    def test_manifest_patient_group_and_no_full_volume_load(self):
        import numpy as np
        import nibabel as nib
        for subject in ["sub-olf01", "sub-olf01fu"]:
            p = self.root / subject / "anat" / (subject + "_T2w.nii.gz")
            p.parent.mkdir(parents=True)
            nib.save(nib.Nifti1Image(np.zeros((4, 5, 6), dtype=np.int16), np.eye(4)), p)
        with patch.object(nib.Nifti1Image, "get_fdata", side_effect=AssertionError("No volume load expected")):
            manifest = a.inspect_dataset(self.root, "openneuro_ds007345", "Meningioma")
        self.assertEqual(manifest["patient_count"], 1)
        self.assertEqual(len(manifest["files"]), 2)
        self.assertEqual(manifest["errors"], [])

    def test_catalog_and_notebook_are_synchronized(self):
        root = Path(__file__).parent
        catalog = json.loads((root / "research/dataset_catalog.json").read_text())
        notebook = json.loads((root / "notebooks/Acquire_Best_5_Disease_Datasets.ipynb").read_text())
        cells = {c["id"]: "".join(c["source"]) for c in notebook["cells"]}
        self.assertEqual(cells["acquisition-engine"], (root / "acquisition.py").read_text())
        namespace = {}
        exec(cells["dataset-catalog"], namespace)
        self.assertEqual(namespace["CATALOG"], catalog)
        self.assertEqual(len(catalog), 5)
        self.assertFalse(catalog["alzheimers"]["eligible"])
        self.assertFalse(catalog["brain_metastasis"]["eligible"])
        for c in notebook["cells"]:
            if c["cell_type"] == "code":
                compile("".join(c["source"]), c["id"], "exec")
                self.assertEqual(c["outputs"], [])
                self.assertIsNone(c["execution_count"])


if __name__ == "__main__":
    unittest.main()
