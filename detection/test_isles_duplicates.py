"""Synthetic 3D files only: no research MRI or network access."""
import hashlib
import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
import nibabel as nib
import numpy as np
from detection import acquisition as a


class IslesDuplicateRegression(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = self.root / 'data'
        self.ids = ['sub-strokecase0090', 'sub-strokecase0169', 'sub-strokecase0200']
        for i, case in enumerate(self.ids):
            folder = self.data / case
            folder.mkdir(parents=True)
            for j, channel in enumerate(['FLAIR', 'ADC', 'dwi', 'msk']):
                image = nib.Nifti1Image(np.full((3, 4, 5), i * 10 + j, dtype=np.int16), np.eye(4))
                nib.save(image, folder / f'{case}_{channel}.nii.gz')
        shutil.copyfile(self.file(0, 'FLAIR'), self.file(1, 'FLAIR'))
        self.spec = {'id': 'isles2022', 'disease': 'Post-stroke Lesions', 'expected_groups': 3, 'expected_min_masks': 3}

    def file(self, i, channel):
        return self.data / self.ids[i] / f'{self.ids[i]}_{channel}.nii.gz'

    def inspect(self):
        return a.inspect_dataset(self.data, 'isles2022', self.spec['disease'])

    def archive(self):
        downloads = self.root / 'downloads'
        downloads.mkdir()
        archive = downloads / 'synthetic.zip'
        with zipfile.ZipFile(archive, 'w') as z:
            for path in self.data.rglob('*.gz'):
                z.write(path, path.relative_to(self.data).as_posix())
        self.spec['assets'] = [{'path': archive.name, 'archive': True, 'bytes': archive.stat().st_size, 'checksum': 'md5:' + a.digest(archive, 'md5')}]
        return archive

    def test_duplicate_is_review_not_corruption_and_all_channels_grouped(self):
        before = {str(p): a.digest(p) for p in self.data.rglob('*.gz')}
        manifest = self.inspect()
        self.assertEqual(manifest['errors'], [])
        self.assertEqual(a.manifest_failures(self.spec, manifest), [])
        self.assertEqual(manifest['patient_count'], 3)
        self.assertEqual(len(manifest['exact_duplicate_images']), 1)
        self.assertEqual(manifest['exact_duplicate_images'][0]['files'][0]['modalities'], ['FLAIR'])
        linked = [p for p in manifest['patients'] if p['manual_review_required']]
        self.assertEqual(len(linked), 2)
        self.assertEqual(len({p['split_group'] for p in linked}), 1)
        self.assertEqual(len({r['split_group'] for r in manifest['files'] if r['manual_review_required']}), 1)
        self.assertEqual(before, {str(p): a.digest(p) for p in self.data.rglob('*.gz')})
        assignments = {p['patient_id']: 'train' for p in manifest['patients']}
        self.assertTrue(a.validate_split_assignments(manifest, assignments))
        assignments[linked[1]['patient_id']] = 'test'
        with self.assertRaisesRegex(ValueError, 'cannot cross splits'):
            a.validate_split_assignments(manifest, assignments)

    def test_transitive_links_do_not_merge_patients(self):
        shutil.copyfile(self.file(1, 'ADC'), self.file(2, 'ADC'))
        manifest = self.inspect()
        self.assertEqual(len({p['split_group'] for p in manifest['patients']}), 1)
        self.assertEqual(len({p['patient_id'] for p in manifest['patients']}), 3)

    def test_missing_modality_and_corruption_remain_hard_failures(self):
        self.file(2, 'ADC').unlink()
        self.assertTrue(a.manifest_failures(self.spec, self.inspect()))
        self.file(2, 'dwi').write_bytes(b'corrupt synthetic NIfTI')
        manifest = self.inspect()
        self.assertTrue(manifest['errors'])
        self.assertEqual(len(manifest['exact_duplicate_images']), 1)
        self.assertTrue(a.manifest_failures(self.spec, manifest))

    def test_offline_rerun_verifies_and_preserves_every_file(self):
        archive = self.archive()
        before = {str(p): a.digest(p) for p in [archive, *self.data.rglob('*.gz')]}
        with patch.object(a, 'assert_colab_drive', side_effect=Path), patch.object(a, '_request', side_effect=AssertionError('Network forbidden')):
            report = a.revalidate_existing_isles(self.spec, self.root)
        self.assertEqual(report['status'], 'download_integrity_verified_review_required')
        self.assertFalse(report['training_ready'])
        self.assertEqual(before, {p: a.digest(p) for p in before})
        self.assertEqual(report['validation_failures'], [])

    def test_changed_extracted_payload_fails_without_replacement(self):
        self.archive()
        target = self.file(0, 'ADC')
        target.write_bytes(b'corrupted')
        with patch.object(a, 'assert_colab_drive', side_effect=Path):
            with self.assertRaisesRegex(ValueError, 'differs from verified archive'):
                a.revalidate_existing_isles(self.spec, self.root)
        self.assertEqual(target.read_bytes(), b'corrupted')
        self.assertEqual(json.loads((self.root / 'acquisition_report.json').read_text())['status'], 'failed')

    def test_global_counts_cannot_hide_per_case_channel_errors(self):
        # Keep all 12 entries but move one ADC to the wrong case.
        self.file(2, 'ADC').rename(self.data / self.ids[1] / (self.ids[1] + '_extra_ADC.nii.gz'))
        manifest = self.inspect()
        self.assertEqual(len(manifest['files']), 12)
        failures = a.manifest_failures(self.spec, manifest)
        self.assertEqual(len(failures), 2)

    def test_unlinked_case_can_use_another_split_and_missing_assignments_fail(self):
        manifest = self.inspect()
        assignments = {p['patient_id']: ('train' if p['manual_review_required'] else 'test') for p in manifest['patients']}
        self.assertTrue(a.validate_split_assignments(manifest, assignments))
        assignments.pop(next(iter(assignments)))
        with self.assertRaises(ValueError):
            a.validate_split_assignments(manifest, assignments)

    def test_bad_archive_and_missing_archive_fail_closed(self):
        archive = self.archive()
        archive.write_bytes(b'invalid archive')
        with patch.object(a, 'assert_colab_drive', side_effect=Path):
            with self.assertRaisesRegex(ValueError, 'checksum/size'):
                a.revalidate_existing_isles(self.spec, self.root)
            archive.unlink()
            with self.assertRaises(FileNotFoundError):
                a.revalidate_existing_isles(self.spec, self.root)


if __name__ == '__main__':
    unittest.main()
