"""Quota mismatch regression tests: no MRI, downloads or mounted Drive required."""
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from detection import acquisition as a

GIB = 2**30
DRIVE = '/content/drive/MyDrive/BrainMRI/datasets/DiseaseAcquisition'


class StorageAccounting(unittest.TestCase):
    def test_reported_meningioma_quota_mismatch_passes(self):
        # Mounted Drive says 63.44 GiB; real account has a confirmed 350 GiB.
        calls = []
        def usage(path):
            calls.append(str(path))
            return SimpleNamespace(free=int((63.44 if str(path).startswith('/content/drive') else 10) * GIB))
        with patch.object(a.shutil, 'disk_usage', side_effect=usage):
            plan = a.check_storage_plan(DRIVE, int(19.42 * GIB), 45 * GIB,
                drive_available_bytes=350 * GIB, local_root='/content')
        self.assertGreater(plan['reserved_bytes'], 63.44 * GIB)
        self.assertAlmostEqual(plan['reserved_bytes'] / GIB, 70.862, places=3)
        self.assertEqual(calls, ['/content'])
        self.assertEqual(plan['local_staging_bytes'], 0)

    def test_large_mounted_capacity_cannot_override_insufficient_quota(self):
        with patch.object(a.shutil, 'disk_usage', return_value=SimpleNamespace(free=1000 * GIB)) as usage:
            with self.assertRaisesRegex(OSError, 'Google Drive quota'):
                a.check_storage_plan(DRIVE, 20 * GIB, 45 * GIB, drive_available_bytes=65 * GIB)
            usage.assert_not_called()

    def test_missing_confirmed_quota_fails_closed(self):
        for available in [None, 0, -1]:
            with self.subTest(available=available), self.assertRaises(ValueError):
                a.require_space(DRIVE, GIB, drive_available_bytes=available)

    def test_local_disk_not_overridden_by_drive_quota(self):
        with patch.object(a.shutil, 'disk_usage', return_value=SimpleNamespace(free=GIB)):
            with self.assertRaisesRegex(OSError, 'local filesystem'):
                a.check_storage_plan(DRIVE, 20 * GIB, 45 * GIB,
                    drive_available_bytes=350 * GIB, local_root='/content')

    def test_declared_local_staging_is_accounted_for(self):
        with patch.object(a.shutil, 'disk_usage', return_value=SimpleNamespace(free=10 * GIB)):
            with self.assertRaises(OSError):
                a.check_storage_plan(DRIVE, GIB, GIB, drive_available_bytes=350 * GIB,
                    local_root='/content', local_staging_bytes=9 * GIB)

    def test_aggregate_reservation_keeps_archives_and_extraction(self):
        plan = a.check_storage_plan(DRIVE, 40 * GIB, 90 * GIB, drive_available_bytes=150 * GIB)
        self.assertEqual(plan['reserved_bytes'], 143 * GIB)
        with self.assertRaises(OSError):
            a.check_storage_plan(DRIVE, 40 * GIB, 90 * GIB, drive_available_bytes=140 * GIB)
        self.assertEqual(a.storage_reservation(GIB, GIB), 7 * GIB)

    def test_drive_cannot_be_used_as_local_storage(self):
        with self.assertRaises(ValueError):
            a.check_storage_plan(DRIVE, GIB, GIB, drive_available_bytes=350 * GIB, local_root=DRIVE)

    def test_stage_checks_never_consult_drive_statvfs(self):
        with patch.object(a.shutil, 'disk_usage', side_effect=AssertionError('Not a Drive quota API')):
            a.require_space(DRIVE, 20 * GIB, drive_available_bytes=350 * GIB)
            a.require_space(DRIVE + '/data', 45 * GIB, drive_available_bytes=350 * GIB)


if __name__ == '__main__':
    unittest.main()
