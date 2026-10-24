"""Artificial tiny NIfTI trees only; no research data or network."""
import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import nibabel as nib
import numpy as np
from detection import readiness_audit as a


class ReadinessAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name)
        self.reports = self.project / 'reports' / 'detection_readiness'
        self.roots = {k: self.project / 'datasets' / relative for k, (relative, _) in a.DATASETS.items()}
        for root in self.roots.values(): root.mkdir(parents=True)

    def image(self, key, relative, value=1, shape=(3,4,5)):
        path = self.roots[key] / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        nib.save(nib.Nifti1Image(np.full(shape, value, dtype=np.int16), np.eye(4)), path)
        return path

    def run_audit(self, **kwargs):
        with patch('builtins.print'):
            result = a.audit(self.project, self.reports, **kwargs)
        return result, Path(result['reports_directory'])

    def test_reports_exist_private_and_no_training_or_source_writes(self):
        image = self.image('normal', 'IXI001-Test-T2.nii.gz')
        before = image.read_bytes()
        result, run = self.run_audit()
        self.assertEqual(image.read_bytes(), before)
        self.assertFalse(result['training_ready'])
        for name in ['Detection_Dataset_Readiness_Report.md', 'Detection_Dataset_Summary.csv', 'Detection_Label_Review_Required.csv', 'Detection_Modality_Compatibility.csv', 'Detection_Validation_Errors.json', 'Detection_Training_Readiness.json']:
            self.assertTrue((run / name).is_file())
        normal = next(s for s in result['summary'] if s['dataset'] == 'normal')
        self.assertEqual(normal['source_case_ids'], 1)
        self.assertFalse(normal['IXI_claim_578_matches_actual'])
        self.assertEqual(normal['status'], 'NEEDS_LABEL_REVIEW')
        self.assertTrue(all(s['status'] != 'READY' for s in result['summary']))

    def test_all_six_source_trees_remain_byte_and_mtime_identical(self):
        fixtures = [('normal', 'IXI001-T2.nii.gz'), ('glioma', 'imagesTr/BRATS_001.nii.gz'),
                    ('meningioma', 'data/unknown.nii.gz'), ('brain_metastasis', 'data/P01a/baseline/brats/t2.nii.gz'),
                    ('post_stroke', 'data/sub-strokecase0090/sub-strokecase0090_FLAIR.nii.gz'),
                    ('alzheimers', 'data/OAS2_0001_MR1/T1.nii.gz')]
        for key, relative in fixtures:
            self.image(key, relative)
        def snapshot():
            return {str(p): (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
                    for root in self.roots.values() for p in root.rglob('*') if p.is_file()}
        before = snapshot()
        self.run_audit(full_hash=True)
        self.assertEqual(snapshot(), before)

    def test_malformed_and_missing_metadata_reported_not_invented(self):
        (self.roots['normal'] / 'file_manifest.json').write_text('[]')
        self.image('normal', 'unknown.nii.gz')
        result, run = self.run_audit()
        errors = json.loads((run / 'Detection_Validation_Errors.json').read_text())
        self.assertTrue(any(e['stage'] == 'metadata' for e in errors))
        rows = json.loads((run / 'normal_file_inventory.json').read_text())
        self.assertIsNone(rows[0]['case_id'])

    def test_metadata_first_for_all_sources_before_first_header(self):
        self.image('normal', 'IXI001-T2.nii.gz')
        events = []
        original_meta, original_inspect = a.metadata_first, a.inspect_file
        def meta(*args):
            events.append('metadata'); return original_meta(*args)
        def header(*args):
            events.append('header'); return original_inspect(*args)
        with patch.object(a, 'metadata_first', side_effect=meta), patch.object(a, 'inspect_file', side_effect=header):
            self.run_audit()
        self.assertEqual(events[:6], ['metadata'] * 6)
        self.assertEqual(events[6], 'header')

    def test_resume_uses_cache_and_changed_file_invalidates(self):
        path = self.image('normal', 'IXI001-T2.nii.gz')
        self.run_audit()
        with patch.object(a, 'inspect_file', side_effect=AssertionError('Should use cache')):
            _, run = self.run_audit()
        self.assertEqual(json.loads((run / 'Detection_Validation_Errors.json').read_text())[0]['dataset'], 'glioma')
        path.touch()
        with patch.object(a, 'inspect_file', wraps=a.inspect_file) as inspect:
            self.run_audit()
        self.assertEqual(inspect.call_count, 1)

    def test_interrupted_audit_resumes_without_reloading_completed_headers(self):
        self.image('normal', 'IXI001-T2.nii.gz')
        self.image('normal', 'IXI002-T2.nii.gz', value=2)
        original = a.inspect_file
        calls = 0
        def interrupted(*args):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise KeyboardInterrupt('synthetic disconnect')
            return original(*args)
        with patch.object(a, 'inspect_file', side_effect=interrupted), self.assertRaises(KeyboardInterrupt):
            self.run_audit()
        self.assertFalse((self.reports / 'latest_run.json').exists())
        with patch.object(a, 'inspect_file', wraps=original) as inspect:
            self.run_audit()
        self.assertEqual(inspect.call_count, 1)
        self.assertTrue(json.loads((self.reports / 'latest_run.json').read_text())['complete'])

    def test_clinical_spreadsheet_schema_read_without_label_inference(self):
        import openpyxl
        book = openpyxl.Workbook()
        sheet = book.active
        sheet.append(['patient', 'visit', 'clinical_group'])
        sheet.append(['P01', 'baseline', 'not_adjudicated'])
        downloads = self.roots['brain_metastasis'] / 'downloads'
        downloads.mkdir()
        book.save(downloads / 'clinical.xlsx')
        metadata = a.metadata_first(self.roots['brain_metastasis'], 'brain_metastasis', [])
        self.assertEqual(metadata['clinical_spreadsheets'][0]['sheets'][0]['rows'], 2)
        self.assertIn('Schema inspected only', metadata['clinical_spreadsheets'][0]['interpretation'])

    def test_symlink_mri_and_cache_symlink_rejected(self):
        outside = self.project / 'outside.nii.gz'
        original = self.image('normal', 'IXI001-T2.nii.gz')
        outside.write_bytes(original.read_bytes())
        (self.roots['normal'] / 'IXI002-T2.nii.gz').symlink_to(outside)
        _, run = self.run_audit()
        errors = json.loads((run / 'Detection_Validation_Errors.json').read_text())
        self.assertTrue(any('Symlink' in e['error'] for e in errors))
        (self.reports / 'readiness_cache.sqlite').unlink()
        (self.reports / 'readiness_cache.sqlite').symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'cache symlink'):
            self.run_audit()

    def test_corrupt_file_is_error_not_duplicate(self):
        path = self.roots['normal'] / 'IXI001-T2.nii.gz'
        path.write_bytes(b'not a nifti')
        _, run = self.run_audit(full_hash=True)
        errors = json.loads((run / 'Detection_Validation_Errors.json').read_text())
        self.assertTrue(any(e['dataset'] == 'normal' and e['stage'] == 'file' for e in errors))

    def test_reports_inside_dataset_are_rejected(self):
        with self.assertRaises(ValueError):
            a.audit(self.project, self.roots['normal'] / 'reports')

    def test_missing_manifest_file_fails_validation(self):
        self.image('normal', 'IXI001-T2.nii.gz')
        (self.roots['normal'] / 'file_manifest.json').write_text(json.dumps({'files': [{'relative_path': 'missing.nii.gz'}]}))
        result, run = self.run_audit()
        normal = next(s for s in result['summary'] if s['dataset'] == 'normal')
        self.assertEqual(normal['status'], 'NEEDS_FILE_VALIDATION')

    def test_templates_cannot_become_labels(self):
        self.image('meningioma', 'data/undocumented.nii.gz')
        template = self.roots['meningioma'] / 'patient_map_template.csv'
        template.write_text('relative_path,patient_id,diagnosis,modality,role,visit_id\nundocumented.nii.gz,FAKE,meningioma,T1w,image,v1\n')
        _, run = self.run_audit(reviewed_maps={'meningioma': str(template)})
        row = json.loads((run / 'meningioma_file_inventory.json').read_text())[0]
        self.assertIsNone(row['case_id'])
        self.assertIsNone(row['diagnosis'])
        self.assertEqual(row['role'], 'unresolved')

    def test_oasis_identity_and_diagnosis_not_mci_inference(self):
        identity = a.identify('OAS2_0001_MR2/file.img', 'alzheimers', {}, (3,4,5))
        self.assertEqual(identity['case_id'], 'OAS2_0001')
        self.assertEqual(identity['visit_id'], 'MR2')
        self.assertIsNone(identity['diagnosis'])
        mapping = {'OAS2_0001_MR2/file.img': {'patient_id': 'OAS2_0001', 'visit_id': 'MR2', 'role': 'image', 'modality': 'T1w', 'diagnosis': 'converter_excluded'}}
        self.assertEqual(a.identify('OAS2_0001_MR2/file.img', 'alzheimers', mapping, (3,4,5))['diagnosis'], 'converter_excluded')
        mapping['OAS2_0001_MR2/file.img']['patient_id'] = 'OAS2_9999'
        with self.assertRaises(ValueError):
            a.identify('OAS2_0001_MR2/file.img', 'alzheimers', mapping, (3,4,5))

    def test_proteas_courses_share_patient(self):
        ids = [a.identify(f'{course}/baseline/brats/t2.nii.gz', 'brain_metastasis', {}, (3,4,5)) for course in ['P01a', 'P01b']]
        self.assertEqual(ids[0]['case_id'], ids[1]['case_id'])
        self.assertNotEqual(ids[0]['visit_id'], ids[1]['visit_id'])

    def test_isles_known_link_preserved_without_full_hash(self):
        rows = [{'case_id': case, 'role': 'image'} for case in ['sub-strokecase0090', 'sub-strokecase0169', 'sub-strokecase0200']]
        groups = a.link_duplicates(rows, {})
        self.assertEqual(len(groups), 1)
        self.assertEqual(rows[0]['split_group'], rows[1]['split_group'])
        self.assertNotEqual(rows[0]['split_group'], rows[2]['split_group'])

    def test_transitive_links_and_previous_groups(self):
        rows = [dict(case_id='A', role='image', sha256='x'), dict(case_id='B', role='image', sha256='x', existing_split_group='old'), dict(case_id='C', role='mask', existing_split_group='old')]
        self.assertEqual(a.link_duplicates(rows, {}), [['A','B','C']])
        self.assertEqual(len({r['case_id'] for r in rows}), 3)

    def test_unlabeled_msd_test_not_positive(self):
        identity = a.identify('imagesTs/BRATS_001.nii.gz', 'glioma', {}, (3,4,5,4))
        self.assertEqual(identity['diagnosis'], 'unlabeled_test_not_training_positive')

    def test_msd_pair_references_and_channel_order_checked(self):
        rows = [dict(relative_path='imagesTr/BRATS_001.nii.gz', case_id='BRATS_001', shape=[3,4,5,4], affine=np.eye(4).tolist(), role='image'), dict(relative_path='labelsTr/BRATS_002.nii.gz', case_id='BRATS_002', shape=[3,4,5], affine=np.eye(4).tolist(), role='mask')]
        metadata = {'dataset.json': {'training': [{'image': './imagesTr/BRATS_001.nii.gz', 'label': './labelsTr/BRATS_002.nii.gz'}], 'test': ['../../bad.nii.gz']}}
        errors = []
        a.msd_checks(self.roots['glioma'], rows, metadata, errors)
        self.assertTrue(any('identity/geometry' in e['error'] for e in errors))
        self.assertTrue(any('channel order' in e['error'] for e in errors))
        self.assertTrue(any('test reference' in e['error'] for e in errors))

    def test_same_hash_cross_dataset_is_reviewed(self):
        self.image('normal', 'IXI001-T2.nii.gz')
        path = self.image('glioma', 'imagesTs/BRATS_001.nii.gz')
        source = self.roots['normal'] / 'IXI001-T2.nii.gz'
        path.write_bytes(source.read_bytes())
        _, run = self.run_audit(full_hash=True)
        duplicate = json.loads((run / 'cross_dataset_exact_duplicates.json').read_text())
        self.assertEqual(len(duplicate), 1)

    def test_paired_img_header_cached_and_hashed(self):
        image = nib.Nifti1Pair(np.ones((3,4,5), dtype=np.int16), np.eye(4))
        path = self.roots['alzheimers'] / 'OAS2_0001_MR1.img'
        nib.save(image, path)
        _, run = self.run_audit(full_hash=True)
        row = json.loads((run / 'alzheimers_file_inventory.json').read_text())[0]
        self.assertTrue(row['paired_header_sha256'])


if __name__ == '__main__': unittest.main()
