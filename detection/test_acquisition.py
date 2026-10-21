"""Offline safeguards with artificial bytes only; never downloads an MRI dataset."""
import hashlib
import gzip
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
        self.assertTrue(all(spec["eligible"] for spec in catalog.values()))
        self.assertEqual(catalog["brain_metastasis"]["id"], "proteas_23171182")
        self.assertEqual(len([a for a in catalog["brain_metastasis"]["assets"] if a["archive"]]), 45)
        self.assertEqual(catalog["meningioma"]["alternatives"]["openneuro37"]["independent_patients"], 37)
        for c in notebook["cells"]:
            if c["cell_type"] == "code":
                compile("".join(c["source"]), c["id"], "exec")
                self.assertEqual(c["outputs"], [])
                self.assertIsNone(c["execution_count"])

    def test_proteas_repeat_courses_share_patient_and_visit(self):
        one = a.source_identity("P04a/P04a/BraTS/baseline/t1c.nii.gz", "proteas_23171182")
        two = a.source_identity("P04b/P04b/BraTS/fu2/t1c.nii.gz", "proteas_23171182")
        self.assertEqual(one["patient"], two["patient"])
        self.assertEqual(one["patient"], "P04")
        self.assertEqual(two["visit_id"], "fu2")
        self.assertEqual(one["modalities"], ["T1ce"])

    def test_proteas_ct_and_tissue_labels_are_not_mri_or_tumor(self):
        for path in ["P01/P01_CT.nii.gz", "P01/P01_RTP.nii.gz", "P01/P01_brain_mask.nii.gz"]:
            self.assertEqual(a.source_identity(path, "proteas_23171182")["role"], "ancillary")
        self.assertEqual(a.source_identity("P01/tumor_segmentation/P01_tumor_mask_fu1.nii.gz", "proteas_23171182")["role"], "mask")
        with self.assertRaises(ValueError):
            a.source_identity("P01/mystery.nii.gz", "proteas_23171182")

    def test_oasis_unknown_diagnosis_stays_unknown(self):
        row = a.source_identity("OAS2_0001_MR1/RAW/mpr-1.nii", "oasis2_legacy")
        self.assertEqual(row["patient"], "OAS2_0001")
        self.assertIsNone(row["diagnosis"])
        self.assertEqual(row["modalities"], ["T1w"])

    def test_generic_dementia_and_mci_labels_rejected(self):
        for diagnosis in ["MCI", "Demented", "CDR_0.5", "AD"]:
            p = self.root / "mapping.csv"
            p.write_text("relative_path,patient_id,diagnosis,modality,role,visit_id\nscan.nii,subject," + diagnosis + ",T1w,image,baseline\n")
            with self.assertRaises(ValueError):
                a.load_patient_map(p)

    def test_oasis_mapping_cannot_change_source_patient(self):
        path = "OAS2_0001_MR1/mpr-1.nii"
        mapping = {path: {"patient_id": "OAS2_9999", "diagnosis": "AD_clinical_baseline", "role": "image", "modality": "T1w"}}
        with self.assertRaises(ValueError):
            a.source_identity(path, "oasis2_legacy", mapping)

    def test_paired_nifti_headers_and_clinical_pending_state(self):
        import numpy as np
        import nibabel as nib
        p = self.root / "OAS2_0001_MR1" / "mpr-1.img"
        p.parent.mkdir()
        nib.save(nib.Nifti1Pair(np.zeros((4, 5, 6), dtype=np.int16), np.eye(4)), p)
        manifest = a.inspect_dataset(self.root, "oasis2_legacy", "Alzheimer's Disease")
        self.assertEqual(manifest["patient_count"], 1)
        self.assertTrue(manifest["mapping_required"])
        self.assertIsNone(manifest["patients"][0]["diagnosis"])
        self.assertTrue(manifest["files"][0]["paired_header_sha256"])

    def test_hwang_scan_ids_never_invent_patients_or_controls(self):
        import numpy as np
        import nibabel as nib
        nib.save(nib.Nifti1Image(np.zeros((4, 5, 6), dtype=np.int16), np.eye(4)), self.root / "unmapped_scan.nii")
        manifest = a.inspect_dataset(self.root, "hwang_meningioma_5945963", "Meningioma")
        self.assertIsNone(manifest["patient_count"])
        self.assertEqual(manifest["patients"], [])
        self.assertTrue(manifest["mapping_required"])
        self.assertIsNone(manifest["files"][0]["diagnosis"])

    def test_explicit_meningioma_map_groups_visits(self):
        import numpy as np
        import nibabel as nib
        mapping = {}
        for visit in ["baseline", "followup"]:
            name = visit + ".nii"
            nib.save(nib.Nifti1Image(np.zeros((4, 5, 6), dtype=np.int16), np.eye(4)), self.root / name)
            mapping[name] = {"patient_id": "source_patient", "diagnosis": "meningioma", "modality": "T1ce", "role": "image", "visit_id": visit}
        manifest = a.inspect_dataset(self.root, "hwang_meningioma_5945963", "Meningioma", mapping)
        self.assertEqual(manifest["patient_count"], 1)
        self.assertFalse(manifest["mapping_required"])

    def legacy_asset(self, payload):
        return {"path": "OAS2_RAW_PART1.tar.gz", "url": "https://download.nrg.wustl.edu/data/OAS2_RAW_PART1.tar.gz", "bytes": len(payload), "checksum": None, "integrity_policy": "https_size_gzip_crc32_local_sha256"}

    def test_legacy_integrity_crc_and_repeat_sha256_are_explicit(self):
        payload = gzip.compress(b"artificial gzip test content")
        asset = self.legacy_asset(payload)
        with patch.object(a, "_request", return_value=Response(payload)):
            result = a.download_verified(asset, self.root, max_bytes=1000)
        self.assertIsNone(result["publisher_checksum"])
        ledger = json.loads((self.root / (asset["path"] + ".integrity.json")).read_text())
        self.assertIsNone(ledger["publisher_cryptographic_checksum"])
        self.assertEqual(ledger["gzip_crc32"], "passed")
        with patch.object(a, "_request", side_effect=AssertionError("No network expected")):
            self.assertEqual(a.download_verified(asset, self.root, max_bytes=1000)["status"], "verified_existing")

    def test_legacy_integrity_rejects_crc_damage(self):
        payload = bytearray(gzip.compress(b"artificial gzip test content"))
        payload[-8] ^= 1
        asset = self.legacy_asset(payload)
        with patch.object(a, "_request", return_value=Response(bytes(payload))):
            with self.assertRaises(gzip.BadGzipFile):
                a.download_verified(asset, self.root, max_bytes=1000)
        self.assertFalse((self.root / asset["path"]).exists())

    def test_legacy_policy_cannot_bypass_other_source_hash_requirements(self):
        asset = self.legacy_asset(b"bytes")
        asset["url"] = "https://other.example/scan.tar.gz"
        with self.assertRaises(ValueError):
            a.download_verified(asset, self.root, max_bytes=1000)
        asset = dict(self.asset)
        asset["checksum"] = None
        with self.assertRaises(ValueError):
            a.download_verified(asset, self.root, max_bytes=1000)

    def test_legacy_policy_never_overrides_a_supplied_hash(self):
        payload = gzip.compress(b"artificial gzip test content")
        asset = self.legacy_asset(payload)
        asset["checksum"] = "md5:" + "0" * 32
        with patch.object(a, "_request", return_value=Response(payload)):
            with self.assertRaises(ValueError):
                a.download_verified(asset, self.root, max_bytes=1000)

    def test_shared_multi_archive_extraction_budget(self):
        assets = []
        for index in [1, 2]:
            path = self.root / f"{index}.zip"
            with zipfile.ZipFile(path, "w") as z:
                z.writestr("test.txt", "x" * 60)
            assets.append({"path": path.name, "url": "https://publisher.example/" + path.name, "bytes": path.stat().st_size, "checksum": "sha256:" + a.digest(path), "archive": True, "extract_subdir": str(index)})
        spec = {"id": "test", "eligible": True, "disease": "artificial", "assets": assets}
        def fake_download(asset, root, **kwargs):
            return {"path": str(self.root / asset["path"]), "status": "verified"}
        with patch.object(a, "assert_colab_drive", return_value=self.root), patch.object(a, "download_verified", side_effect=fake_download):
            with self.assertRaisesRegex(OSError, "extraction budget"):
                a.acquire_one(spec, self.root, download_budget_bytes=1000, extraction_budget_bytes=100)
        self.assertFalse((self.root / "data/2/test.txt").exists())

    def test_pending_acquisition_then_reviewed_map_completes_manifest(self):
        import numpy as np
        import nibabel as nib
        source = self.root / "synthetic.nii"
        nib.save(nib.Nifti1Image(np.zeros((4, 5, 6), dtype=np.int16), np.eye(4)), source)
        payload_stream = io.BytesIO()
        with zipfile.ZipFile(payload_stream, "w") as z:
            z.writestr("visit1.nii", source.read_bytes())
        payload = payload_stream.getvalue()
        asset = {"path": "synthetic.zip", "url": "https://publisher.example/test.zip", "bytes": len(payload), "checksum": "sha256:" + hashlib.sha256(payload).hexdigest(), "archive": True}
        spec = {"id": "hwang_meningioma_5945963", "eligible": True, "disease": "Meningioma", "assets": [asset], "expected_diagnosis_groups": {"meningioma": 1}}
        destination = self.root / "acquisition"
        with patch.object(a, "assert_colab_drive", side_effect=lambda p: Path(p)), patch.object(a, "_request", return_value=Response(payload)):
            pending = a.acquire_one(spec, destination, download_budget_bytes=10000, extraction_budget_bytes=10000)
        self.assertEqual(pending["status"], "download_verified_inventory_pending_patient_map")
        self.assertIsNone(pending["patient_or_case_groups"])
        self.assertEqual(json.loads((destination / "patient_manifest.json").read_text()), [])
        self.assertTrue((destination / "patient_map_template.csv").is_file())
        reviewed = self.root / "reviewed.csv"
        reviewed.write_text("relative_path,patient_id,diagnosis,modality,role,visit_id\nvisit1.nii,documented_patient,meningioma,T1ce,image,baseline\n")
        with patch.object(a, "assert_colab_drive", side_effect=lambda p: Path(p)), patch.object(a, "_request", side_effect=AssertionError("Verified archive must be reused")):
            completed = a.acquire_one(spec, destination, download_budget_bytes=10000, extraction_budget_bytes=10000, patient_map_path=reviewed)
        self.assertEqual(completed["status"], "acquired_and_inspected_not_approved_for_training")
        self.assertEqual(completed["patient_or_case_groups"], 1)

    def test_completed_legacy_partial_is_verified_without_http_416(self):
        payload = gzip.compress(b"artificial gzip test content")
        asset = self.legacy_asset(payload)
        (self.root / (asset["path"] + ".part")).write_bytes(payload)
        a.atomic_json(self.root / (asset["path"] + ".resume.json"), {"url": asset["url"], "validator": '"v1"'})
        with patch.object(a, "_request", side_effect=AssertionError("No new HTTP range needed")):
            result = a.download_verified(asset, self.root, max_bytes=1000)
        self.assertEqual(result["status"], "verified_completed_partial")

    def test_original_detection_setup_cells_preserved(self):
        root = Path(__file__).parent
        original = json.loads((root / "notebooks/Brain_MRI_Detection_Colab.ipynb").read_text())
        acquisition = json.loads((root / "notebooks/Acquire_Best_5_Disease_Datasets.ipynb").read_text())
        by_id = {c["id"]: c for c in acquisition["cells"]}
        for cell in original["cells"]:
            if cell["id"] in {"configuration", "runtime-check", "dependency-setup", "compatibility-check", "drive-mount"}:
                self.assertEqual(cell, by_id[cell["id"]])


if __name__ == "__main__":
    unittest.main()
