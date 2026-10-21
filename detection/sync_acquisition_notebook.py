"""Refresh embedded, reviewed helpers/catalog and acquisition instructions; no network or MRI I/O."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PATH = ROOT / 'notebooks/Acquire_Best_5_Disease_Datasets.ipynb'
notebook = json.loads(PATH.read_text())
by_id = {c['id']: c for c in notebook['cells']}

def replace(cell_id, text):
    by_id[cell_id]['source'] = text.splitlines(keepends=True)
    if by_id[cell_id]['cell_type'] == 'code':
        by_id[cell_id]['execution_count'] = None
        by_id[cell_id]['outputs'] = []

replace('acquisition-intro', '''# NeuroScope AI — Acquire qualifying disease datasets

Run actual transfers only in Google Colab with private Google Drive storage. Do not run downloads or training in Codex Cloud. Every disease switch defaults to **False**. No model training is included.

This continues the existing notebook and reuses the runtime, dependency and Drive setup from `Brain_MRI_Detection_Colab.ipynb` on `feature/detection-setup`. That original notebook and all segmentation files are unchanged. The helpers and pinned catalog are embedded; no executable helper is fetched at runtime.

Five sources are prepared for download, with different readiness levels. Glioma, PROTEAS brain metastasis and ISLES have publisher checksums and documented identity conventions. The preferred larger meningioma source needs a reviewed identity/diagnostic map after file inventory. OASIS-2 has an explicit weaker integrity policy and needs clinical-group mapping. Download completion never means approval for training.

The existing **578 IXI-T2 files** at `/content/drive/MyDrive/BrainMRI/datasets/IXI/Healthy/IXI-T2/` are not read, scanned, modified, moved or downloaded. Keep MRI data, clinical metadata and notebook outputs out of GitHub.
''')
replace('choices', '''## Five-disease comparison, updated 2026-10-22

| Disease | Source prepared for download | Independent people / counts | Compressed download | Readiness / research terms |
|---|---|---|---|---|
| Glioma | MSD Task01, authorized MONAI S3 mirror | 750 case volumes; 484 annotated; clinical patient identity not independently proven | 7.61 GB | Publisher MD5; CC BY-SA 4.0; BraTS overlap |
| Meningioma | Preferred: Hwang/SNUBH, Zenodo 5945963 | 91 meningioma patients, 171 scans. Additional lesion-negative lung-cancer controls: body says 10, supplement says 12. | 20.86 GB | Publisher MD5; CC BY 4.0; file inventory then explicit patient/diagnosis mapping |
| Brain metastasis | PROTEAS, latest pinned Zenodo 23171182 | 40 patients; 185 studies; 65 metastases; 45 course archives | 15.13 GB including clinical XLSX | Publisher MD5; CC BY 4.0; a/b courses share patient identity |
| Alzheimer's | Official OASIS-2 legacy raw archives | 150 people: 64 AD at baseline, 72 stable controls, 14 converters; 373 sessions | 19.32 GB | Custom OASIS terms; **no publisher hash**; full gzip CRC32 + local SHA-256; clinical-group map required |
| Post-stroke | ISLES 2022 public training release | 250 annotated cases from three centers | 1.69 GB | Publisher MD5; CC BY 4.0; acute/subacute ischemic lesions |

The original OpenNeuro 37-person meningioma baseline subset remains selectable below (4.41 GB, CC0). It is an olfactory-groove-only, single-center cohort, not representative of all meningiomas. The larger SNUBH cohort covers more anatomical sites, but is still single-center and has repeat scans and unresolved control-count reporting.

OASIS terms are published by the project's maintainers at https://www.nitrc.org/projects/oasis/. The official NrgXnat README explicitly distinguishes direct OASIS-1/2 access from signed-DUA/project access for later releases. This notebook uses only the official Washington University legacy server, not third-party MRI copies. Local SHA-256 is a repeat-use integrity baseline, **not publisher-hash verification**. If publisher-hash verification is essential to your use, leave the Alzheimer's switch off.

The full report with source comparisons, citations, exact links, count semantics and unresolved issues is `detection/research/DATASET_SELECTION.md`.
''')
replace('download-configuration-help', '''## Select diseases, meningioma source and storage budgets

All transfers go to private `Drive/datasets/DiseaseAcquisition/<dataset_id>/`. Different existing data are never overwritten. Archives remain on Drive, so reserve space for both compressed and extracted data. HTTP Range/If-Range enables resume where supported.

**Drive quota is not reliably reported by `shutil.disk_usage`.** Enter the free space shown in Google Drive as `DRIVE_AVAILABLE_GIB`. Zero blocks transfers. Filesystem free space is also checked. `MAX_UNPACKED_GIB_PER_DISEASE` is one shared extraction budget across a disease's archives, not multiplied by PROTEAS's 45 course archives.

For the larger meningioma source and OASIS-2, the first run may end with `download_verified_inventory_pending_patient_map`. This is an explicit review state, not a successful clinical-label validation. Headers, hashes and known identities are inventoried, while missing identities/diagnoses stay null. A private `patient_map_template.csv` is generated. Use verified source metadata and review to fill a **separate** CSV, enter its Drive path below, then rerun. Never invent new patients from scan counts or infer a control label from an absent mask.

Mapping columns: `relative_path,patient_id,diagnosis,modality,role,visit_id`. Meningioma diagnoses are `meningioma` or `brain_lesion_negative_lung_cancer`; do not call these controls population-healthy. OASIS diagnoses are `AD_clinical_baseline`, `control_stable`, or `converter_excluded`. All visits of a converter must remain excluded from a binary AD/control training cohort. Missing information is not AD, MCI is not automatically AD, and generic CDR thresholds are not used to assign labels. Full reviewed OASIS mapping is checked against the published 64/72/14 patient groups.
''')
replace('download-configuration', '''DOWNLOAD_GLIOMA = False  # @param {type:"boolean"}
DOWNLOAD_MENINGIOMA = False  # @param {type:"boolean"}
DOWNLOAD_BRAIN_METASTASIS = False  # @param {type:"boolean"}
DOWNLOAD_ALZHEIMERS = False  # @param {type:"boolean"}
DOWNLOAD_POST_STROKE = False  # @param {type:"boolean"}
MENINGIOMA_SOURCE = "hwang91"  # @param ["hwang91", "openneuro37"]
MENINGIOMA_REVIEWED_MAP_CSV = ""  # @param {type:"string"}
OASIS2_REVIEWED_MAP_CSV = ""  # @param {type:"string"}
DRIVE_AVAILABLE_GIB = 0.0  # @param {type:"number"}
MAX_DOWNLOAD_GIB_PER_DISEASE = 25.0  # @param {type:"number"}
MAX_UNPACKED_GIB_PER_DISEASE = 60.0  # @param {type:"number"}
ACQUISITION_ROOT = str(Path(PROJECT_ROOT) / "datasets" / "DiseaseAcquisition")
SWITCHES = {
    "glioma": DOWNLOAD_GLIOMA, "meningioma": DOWNLOAD_MENINGIOMA,
    "brain_metastasis": DOWNLOAD_BRAIN_METASTASIS, "alzheimers": DOWNLOAD_ALZHEIMERS,
    "post_stroke": DOWNLOAD_POST_STROKE,
}
''')
catalog = json.loads((ROOT / 'research/dataset_catalog.json').read_text())
replace('dataset-catalog', 'import json\nCATALOG = json.loads(' + repr(json.dumps(catalog, ensure_ascii=False)) + ')\n')
replace('acquisition-engine', (ROOT / 'acquisition.py').read_text())
replace('preflight-help', '''## Preflight without MRI transfer

HEAD requests check all selected endpoints, current byte sizes and available storage. A missing Drive mount, login/error page, changed size or insufficient budget stops preflight before MRI transfer. Publisher digests remain pinned; multipart ETags are not MD5.

OASIS-2 is a separately disclosed legacy policy: authenticated HTTPS + exact byte size + full gzip CRC32, with a local SHA-256 ledger for repeat verification. It has no publisher cryptographic digest. Other sources still require their published MD5/SHA-256; this policy does not bypass a known checksum mismatch.
''')
replace('acquisition-preflight', '''import copy
if MENINGIOMA_SOURCE not in {"hwang91", "openneuro37"}:
    raise ValueError("Choose a reviewed meningioma source.")
selected = []
for key, enabled in SWITCHES.items():
    if enabled:
        spec = CATALOG[key]
        if key == "meningioma" and MENINGIOMA_SOURCE == "openneuro37":
            spec = spec["alternatives"]["openneuro37"]
        selected.append(copy.deepcopy(spec))
reviewed_maps = {"hwang_meningioma_5945963": MENINGIOMA_REVIEWED_MAP_CSV,
                 "oasis2_legacy": OASIS2_REVIEWED_MAP_CSV}
preflight_ok = False
if not selected:
    print("No diseases selected. No MRI files read or downloaded; IXI is untouched.")
else:
    if not IN_COLAB or not DRIVE_MOUNTED or not torch.cuda.is_available():
        raise RuntimeError("Colab CUDA runtime and mounted private Drive are required.")
    for spec in selected:
        if not spec["eligible"]:
            raise RuntimeError(f"{spec['disease']}: {spec['reason']}")
        if spec["id"] == "oasis2_legacy":
            print("OASIS-2: NO PUBLISHER CHECKSUM. HTTPS/size/gzip CRC32 + local SHA-256 ledger; clinical mapping remains required.")
    if min(DRIVE_AVAILABLE_GIB, MAX_DOWNLOAD_GIB_PER_DISEASE, MAX_UNPACKED_GIB_PER_DISEASE) <= 0:
        raise ValueError("Enter available Drive quota and positive storage budgets before download.")
    acquisition_root = assert_colab_drive(ACQUISITION_ROOT)
    acquisition_root.mkdir(parents=True, exist_ok=True)
    probes = {}
    try:
        for spec in selected:
            probes[spec["id"]] = probe_assets(spec)
        total_download = sum(asset["bytes"] for spec in selected for asset in spec["assets"])
        archive_diseases = sum(any(asset.get("archive") for asset in spec["assets"]) for spec in selected)
        reserve = total_download + int(archive_diseases * MAX_UNPACKED_GIB_PER_DISEASE * 2**30) + 2 * 2**30
        if reserve > DRIVE_AVAILABLE_GIB * 2**30:
            raise OSError(f"Conservative storage reservation is {reserve / 2**30:.2f} GiB; available quota is lower.")
        for spec in selected:
            if sum(asset["bytes"] for asset in spec["assets"]) > MAX_DOWNLOAD_GIB_PER_DISEASE * 2**30:
                raise OSError(f"{spec['id']} exceeds the per-disease download budget.")
        require_space(acquisition_root, reserve - 2 * 2**30)
        preflight_ok = True
        atomic_json(acquisition_root / "preflight_report.json", {"status": "passed", "probes": probes, "reserved_bytes": reserve})
        print(f"Preflight passed: {total_download / 2**30:.2f} GiB download; reserve {reserve / 2**30:.2f} GiB including shared extraction budgets.")
    except Exception as exc:
        atomic_json(acquisition_root / "preflight_report.json", {"status": "failed", "probes": probes, "error": f"{type(exc).__name__}: {exc}"})
        raise
''')
replace('download-help', '''## Download, inspect and report readiness accurately

Only in Colab, stream the enabled files to Drive, verify the source's declared integrity policy, then extract with path/type/size checks. PROTEAS course archives have separate extraction directories; a/b courses retain a shared patient ID. CT, radiation plans and brain-tissue labels are ancillary, not MRI sequences or metastasis masks. Raw DICOM is retained without conversion.

Headers are inspected one file at a time without loading full MRI volumes. NIfTI-1 paired IMG/HDR is supported, including a separate header hash. Source IDs group OASIS visits; undocumented meningioma identities remain unknown until a reviewed mapping is supplied. No incomplete identity/diagnosis mapping is reported as training ready.

Failures are persisted per disease while other independent selections continue. Different existing files are preserved. Interrupted extraction files require inspection; existing reports are retained on rerun. No code in this notebook trains or loads a model.
''')
replace('execute-acquisition', '''results = []
if selected and not preflight_ok:
    raise RuntimeError("Rerun and pass preflight before transferring any MRI data.")
for spec in selected:
    try:
        result = acquire_one(spec, str(Path(ACQUISITION_ROOT) / spec["id"]),
                             download_budget_bytes=int(MAX_DOWNLOAD_GIB_PER_DISEASE * 2**30),
                             extraction_budget_bytes=int(MAX_UNPACKED_GIB_PER_DISEASE * 2**30),
                             patient_map_path=reviewed_maps.get(spec["id"]) or None)
        results.append(result)
        print(spec["id"], result["status"], result.get("patient_or_case_groups"))
        if result.get("mapping_template"):
            print("Private mapping template:", result["mapping_template"])
            print(result["limitation"])
    except Exception as exc:
        results.append({"dataset_id": spec["id"], "status": "failed", "error": f"{type(exc).__name__}: {exc}"})
        print(spec["id"], "FAILED:", type(exc).__name__, str(exc))
if selected:
    atomic_json(Path(ACQUISITION_ROOT) / "acquisition_summary.json", results)
    if any(r["status"] == "failed" for r in results):
        raise RuntimeError("At least one acquisition failed. Review private Drive reports; no training is authorized.")
    pending = [r["dataset_id"] for r in results if r["status"] == "download_verified_inventory_pending_patient_map"]
    if pending:
        print("Downloaded/inventoried, but patient/clinical review still pending:", pending)
print("Acquisition stage ended. No models trained; verification and user approval remain prerequisites for training.")
''')
replace('review-gate', '''## Stop before training

Review every private source/license record, acquisition report and file/patient manifest. For OASIS-2, finish the clinical-group join and exclude all converter visits from the binary AD/control cohort. For the larger meningioma source, resolve longitudinal patient IDs and source-specific control labels; the paper/supplement disagree about the control count. Missing masks or labels must not become healthy labels.

The original 37-patient meningioma choice remains an alternative; do not download both just to inflate sample counts. PROTEAS versions overlap and are never independent cohorts. Keep every patient's repeated visits, channels and slices in one split. Review exact/near duplicates, mask geometry and source provenance before creating splits.

IXI T2 controls differ in scanner, modality, age and site from these disease cohorts; this notebook does not read or combine IXI. No GPU MRI preprocessing, validation experiment or training has been performed. Those belong to a later, approved Colab T4 task with CUDA, memory-efficient patches, AMP and complete Drive checkpoint/resume state.
''')
PATH.write_text(json.dumps(notebook, indent=2, ensure_ascii=False) + '\n')
print(f'Refreshed {PATH.name}; {len(notebook["cells"])} cells; outputs cleared for refreshed code cells')
