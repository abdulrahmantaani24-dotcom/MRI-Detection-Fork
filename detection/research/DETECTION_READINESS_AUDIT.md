# Phase 2: dataset validation and detection readiness

This extends existing detection/acquisition work; no segmentation files, acquisition catalogs, checkpoints, MRI or existing splits change. Branch `feature/detection-dataset-readiness` is based on `feature/acquire-five-disease-datasets`. Real readiness has **not** been established in Codex: the actual six Drive trees are only audited when the user runs Colab. Synthetic test outputs are temporary and never committed.

## Run in Colab

Open `detection/notebooks/Detection_Dataset_Readiness_Audit.ipynb` from the new branch:

https://colab.research.google.com/github/abdulrahmantaani24-dotcom/MRI-Detection-Fork/blob/feature/detection-dataset-readiness/detection/notebooks/Detection_Dataset_Readiness_Audit.ipynb

1. CPU runtime is sufficient; T4 is optional. Run cell 2 (`dependencies`) to install only missing nibabel/openpyxl runtime packages. No model or dataset is downloaded. This audit adds no cloud service dependency to future offline inference.
2. Run cell 3 (`mount-and-configure`). Securely authorize your private Drive mount. Retain `/content/drive/MyDrive/BrainMRI`. Leave reviewed-map paths blank unless you have a **separate source-reviewed CSV**. Never use `patient_map_template.csv` as a completed map. Leave optional full-file SHA256 False for the first header audit. No CUDA preflight is required.
3. Run cell 4 (`embedded-audit-engine`), then cell 6 (`metadata-preview`). Check all six locations and acquisition/metadata states before scanning. This first reads existing reports/manifests, dataset.json, templates and available clinical XLSX schemas. It does not assert that raw spreadsheet fields have been diagnostically adjudicated.
4. Set `RUN_READ_ONLY_AUDIT=True` in cell 3 and rerun it, then run cell 7 (`run-audit`). Do not run acquisition/download or segmentation notebooks. The engine reads MRI one at a time, with progress every 25 files. No image array is materialized; no GPU allocation or preprocessing occurs. Retain output privately.
5. Follow the printed report path under `BrainMRI/reports/detection_readiness/run_<unique-id>/`. Each run writes the six requested reports plus private per-file inventories, metadata inventory and cross-dataset byte-duplicate findings. `latest_run.json` identifies the last complete run. The SQLite cache sits in the parent private reports directory. Do not upload reports, notebook outputs or metadata to GitHub.
6. After interruption, reconnect/mount and rerun cells 2, 3, 4, 6, 7. Reuse the same project/reports location. Completed header/hash records are cached by source path, size, mtime, paired-header stats, audit policy and hash mode; errors are retried. Each report run is new and earlier reports remain intact. If source statistics were preserved despite edits, use a fresh subdirectory under private reports to force uncached validation. Cached reads do not constitute a new independent integrity check.
7. For optional exact-file SHA256, change `FULL_FILE_SHA256=True` and rerun configuration and audit. It streams chunks on CPU and may be slow on Drive. It never verifies a diagnosis. Compressed byte equality is narrower than voxel/near-duplicate equality. Header reads and file hashing alone do not prove payload, mask values or clinical validity.

## Evidence and gates

Primary statuses are BLOCKED for missing/unusable trees; NEEDS_FILE_VALIDATION for detected metadata/file/count/reference errors; NEEDS_LABEL_REVIEW for explicit identity/visit/label review queues; otherwise NEEDS_MODALITY_REVIEW. The enum includes READY, but this tool intentionally never awards READY automatically: it cannot resolve clinical acceptance or domain compatibility from file readability. Independent label, modality and payload gates remain visible even when one primary status takes precedence. `training_ready` is always false; acquisition `training_ready=false` is not overridden.

Dataset checks:

- **IXI:** observe actual files and source IXI IDs, shapes, spacing, formats and duplicate byte evidence when enabled. Compare observed count with 578 without declaring independent healthy patients. Individual clinical eligibility is unresolved; filenames do not verify health.
- **MSD:** expected 484 imagesTr, 484 labelsTr, 266 imagesTs; validate headers, channel declaration/order, dataset.json references and coverage, training image/label source IDs and geometry. Every unlabeled test scan remains explicitly excluded from confirmed-positive training. This is not a tumor-mask-value or clinical diagnosis audit.
- **Hwang:** templates are provisional; absent a separate reviewed map, case/diagnosis/visit/channel/role remain unresolved rather than invented from filenames or absent masks. The original published 91 meningioma patients/171 scans do not resolve the additional control-count discrepancy. Map rows require path, patient_id, diagnosis, modality, role and visit_id. Diagnoses are only `meningioma` or `brain_lesion_negative_lung_cancer`. Missing MRI references and incomplete/duplicate rows are errors. Supplying a map is an explicit assertion that its source metadata has been reviewed; the audit cannot independently authenticate a user's adjudication.
- **OASIS-2:** preserve OAS2 patient/MR-visit IDs; diagnosis stays unknown until a reviewed map is supplied. Permitted classes are `AD_clinical_baseline`, `control_stable`, `converter_excluded`, with published 64/72/14 patient-group checks and contradictory-visit-label detection. Generic dementia, MCI and missing data never become AD. Converters must be excluded across all visits. Paired IMG/HDR is supported and optional hashing includes the header.
- **PROTEAS:** source patient P01–P40, a/b treatment-course grouping and visits, MRI versus tumor masks versus ancillary CT/RTP/tissue data, missing clinical spreadsheet/schema inspection, prior acquisition state. A source-reviewed clinical join and image/mask coverage/space review remain required; spreadsheets are not silently turned into diagnoses.
- **ISLES:** exactly 250 source case IDs and one each FLAIR/ADC/DWI/mask per case, preserve prior duplicate-linked components and the known 0090/0169 conservative link even in header-only mode. No case is merged or removed. Acute/subacute ischemia is not a chronic post-stroke cohort. Native-space multimodal registration is not assumed.

Existing acquisition file-manifest references are compared with the source tree. Optional new file SHA256 is compared with prior manifest SHA256 when present; mismatches remain hard findings. Existing manifests are supporting evidence, not permission to relabel images. Segmentation masks are inventoried without editing or loading full arrays; lesion content and value/clinical assessment remain subsequent explicitly authorized work.

## Cross-dataset compatibility and proposed split policy

IXI T2 versus OASIS T1-only cohorts cannot become a defensible modality-balanced detector simply by pooling. Even within T2-capable sources, scanner/site, age, resolution, native space, skull stripping, treatment and disease prevalence can reveal source/label. Compatibility reports explicitly leave these fields unadjudicated rather than inferring them from shapes. Review published protocols and private clinical metadata; seek matched/source-balanced controls and external-site evaluation. No harmonization/preprocessing runs here.

After all identity/label/domain checks, build a global patient/source-overlap connected-component graph, including repeated visits/courses, channels, masks and exact/near-duplicate links across releases. Reconcile existing segmentation patient partitions without changing them. Exclude unknown labels, unlabeled MSD test cases and converters. Prefer an external site-held-out test cohort, then consider 70/15/15 by verified component with disease/site/age/sex balance where metadata supports it. Small cohorts may require grouped cross-validation. This tool recommends only: no split assignments or patient IDs are fabricated.

Source/citation details remain in the existing `DATASET_SELECTION.md` and pinned acquisition catalog; no new data or unauthorized copies are introduced. No model training, clinical performance claim or readiness approval is produced.

## Verification

`python -m unittest detection.test_readiness_audit -q` runs only tiny synthetic NIfTI/IMG and XLSX fixtures in temporary directories. Tests cover metadata-first ordering, corruption/missing manifests, templates and unknown identities, MSD pairing/channel references, OASIS diagnosis/visit handling, PROTEAS courses, ISLES link preservation, transitive and cross-source byte duplicates, cache reuse/invalidation/resumption after interruption, safe report placement, source preservation and symlink rejection.
