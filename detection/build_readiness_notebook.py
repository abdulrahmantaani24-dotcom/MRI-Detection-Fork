"""Generate the self-contained audit notebook. No network or real MRI I/O."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parent
cells = []
def md(id, text):
    cells.append(dict(cell_type='markdown', id=id, metadata={}, source=text.splitlines(keepends=True)))
def code(id, text):
    cells.append(dict(cell_type='code', id=id, metadata={}, execution_count=None, outputs=[], source=text.splitlines(keepends=True)))
md('intro', '''# NeuroScope AI — Phase 2 dataset readiness audit

Read-only validation of six existing dataset locations. **No downloads, preprocessing, training, MRI writes or split assignments.** CPU works; CUDA/T4 is optional for this audit. Existing segmentation code, checkpoints and splits are untouched. All findings remain private on Drive. Actual readiness is unknown until you run this notebook on real files; file inventory never establishes clinical validity.

Run cells in order. No GitHub credentials are needed. Helpers are embedded below and never fetched at runtime. This notebook is compatible with a future offline inference system: it introduces no inference service or remote model dependency.
''')
code('dependencies', '''# Colab runtime dependencies only; no MRI data or model download.
import importlib.util, subprocess, sys
missing = [package for package in ['nibabel', 'openpyxl'] if importlib.util.find_spec(package) is None]
if missing:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--quiet', *missing])
import nibabel, openpyxl
print('CPU header audit dependencies ready; no CUDA requirement.')
''')
code('mount-and-configure', '''from pathlib import Path
import json
try:
    from google.colab import drive
except ImportError as exc:
    raise RuntimeError('Real-data auditing belongs in Google Colab; Cloud runs synthetic tests only.') from exc
drive.mount('/content/drive')
PROJECT_ROOT = Path('/content/drive/MyDrive/BrainMRI')
REPORTS_ROOT = PROJECT_ROOT / 'reports' / 'detection_readiness'
# Separate, SOURCE-REVIEWED maps only. Never pass patient_map_template.csv.
MENINGIOMA_REVIEWED_MAP_CSV = ''  # @param {type:"string"}
OASIS2_REVIEWED_MAP_CSV = ''  # @param {type:"string"}
FULL_FILE_SHA256 = False  # @param {type:"boolean"}
RUN_READ_ONLY_AUDIT = False  # @param {type:"boolean"}
PROGRESS_EVERY_FILES = 25  # @param {type:"integer"}
if not PROJECT_ROOT.is_dir() or not PROJECT_ROOT.resolve().is_relative_to(Path('/content/drive/MyDrive').resolve()):
    raise RuntimeError('Mount private Drive and confirm the existing BrainMRI project; do not create replacement datasets.')
for mapping_path in [MENINGIOMA_REVIEWED_MAP_CSV, OASIS2_REVIEWED_MAP_CSV]:
    if mapping_path and (not Path(mapping_path).is_file() or not Path(mapping_path).resolve().is_relative_to(PROJECT_ROOT.resolve())):
        raise ValueError('Reviewed maps must be existing private files within the BrainMRI project.')
print('Reports only:', REPORTS_ROOT)
''')
code('embedded-audit-engine', (ROOT / 'readiness_audit.py').read_text())
md('metadata-help', '''## Metadata first, before scanning MRI

Review location and acquisition status here first. Existing manifests, patient lists, templates, dataset.json and clinical spreadsheet schemas are read before MRI walking. Missing roots/reports remain findings, not fabricated evidence. Template values are provisional. Spreadsheet schema inspection does not validate diagnostic or longitudinal joins.

Header scanning uses one file at a time and loads no image volumes. Optional SHA256 streams files, adding substantial Drive I/O; it detects byte equality, not voxel/near duplicates or patient equivalence. Cache checkpoints each completed file under the private reports folder. It resumes when rerun with the same path/size/mtime/paired-header/mode; errors are retried. Changed file statistics invalidate cache entries. If same-size/same-mtime edits are suspected, use a fresh private reports subdirectory to force uncached scanning. Neither mode proves payload/mask values or replaces publisher-integrity and clinical review.
''')
code('metadata-preview', '''preview_errors = []
for disease, (relative, source_id) in DATASETS.items():
    location = PROJECT_ROOT / 'datasets' / relative
    metadata = metadata_first(location, disease, preview_errors)
    acquisition = metadata.get('acquisition_report.json') or {}
    print(disease, '| exists:', location.is_dir(), '| source:', source_id,
          '| acquisition:', acquisition.get('status', 'not recorded'),
          '| training_ready:', acquisition.get('training_ready', 'not recorded'),
          '| metadata:', ', '.join(metadata))
print('Metadata errors:', len(preview_errors))
# Details stay in this private session; do not commit executed outputs.
''')
code('run-audit', '''if RUN_READ_ONLY_AUDIT:
    audit_result = audit(PROJECT_ROOT, REPORTS_ROOT,
        reviewed_maps={'meningioma': MENINGIOMA_REVIEWED_MAP_CSV, 'alzheimers': OASIS2_REVIEWED_MAP_CSV},
        full_hash=FULL_FILE_SHA256, progress_every=PROGRESS_EVERY_FILES)
    print('Completed private audit:', audit_result['reports_directory'])
    for entry in audit_result['summary']:
        print(entry['dataset'], entry['status'], 'case IDs:', entry['source_case_ids'], 'training_ready:', entry['training_ready'])
else:
    print('Read-only scan disabled. Review metadata, then enable RUN_READ_ONLY_AUDIT and rerun configuration + this cell.')
''')
md('review-gate', '''## Review private results — stop before training

Each run creates a new private `reports/detection_readiness/run_.../` directory with:

- `Detection_Dataset_Readiness_Report.md`
- `Detection_Dataset_Summary.csv`
- `Detection_Label_Review_Required.csv`
- `Detection_Modality_Compatibility.csv`
- `Detection_Validation_Errors.json`
- `Detection_Training_Readiness.json`

Per-file inventories preserve shape, spacing, modality, visit, source case and conservative duplicate-linked components. `latest_run.json` points to the last **completed** run; interruption must not be mistaken for completion. SQLite cache is shared across runs; earlier reports are retained. Keep outputs and clinical metadata private, and clear notebook outputs before sharing.

Statuses are READY, NEEDS_LABEL_REVIEW, NEEDS_MODALITY_REVIEW, NEEDS_FILE_VALIDATION, BLOCKED. This audit deliberately never awards READY automatically: clinical eligibility, voxel/mask checks, modality/domain acceptance, and approval are still required. Review all status dimensions, not just the primary status. IXI file count agreement is not proof of independent healthy patients. Unlabeled MSD test scans are not confirmed-positive training examples. OASIS converters are excluded, and MCI/dementia are not automatically AD. Hwang controls have source-specific cancer-cohort eligibility. PROTEAS courses/visits must remain grouped and its training_ready=false is respected. ISLES is acute/subacute ischemia, not chronic post-stroke disease; the known 0090/0169 duplicate link remains conservative.

T1-only AD versus IXI T2 controls, source/site/scanner, age, skull stripping, and resolution can reveal the binary label without learning disease. Review harmonized modality cohorts and matched/source-balanced controls; do not train merely because files are readable. A proposed grouped 70/15/15 strategy is written, with external site holdout preferred and small-cohort grouped cross-validation considered. All identities, repeat visits, channels, masks and duplicate links must be resolved first. No split is assigned and existing segmentation partitions must be respected.
''')
notebook = dict(cells=cells, metadata={'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'}, 'language_info': {'name': 'python', 'version': '3.11'}}, nbformat=4, nbformat_minor=5)
path = ROOT / 'notebooks' / 'Detection_Dataset_Readiness_Audit.ipynb'
path.write_text(json.dumps(notebook, indent=2) + '\n')
print('Generated', path.name)
