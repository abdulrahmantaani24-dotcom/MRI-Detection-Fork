# ISLES duplicate-FLAIR validation review

## Root cause and evidentiary limit

The former `acquire_one` rejected `manifest['errors'] OR manifest['exact_duplicate_image_groups']` with the same generic “Manifest inspection failed” exception. `inspect_dataset` populated the duplicate list whenever image-file SHA256 matched across distinct case IDs. Thus identical FLAIR bytes for sub-strokecase0090 and sub-strokecase0169 alone trigger rejection, even with readable files, distinct ADC/DWI/masks and correct counts. This is a content-review finding, not evidence that a file is corrupted, and does not establish that these IDs are one patient.

The user reported 250 groups, 1,000 entries, 250 each FLAIR/ADC/DWI/mask and no reading errors. Those satisfy the former count/read conditions; on that evidence the duplicate predicate explains the rejection. Cloud has no access to the private Drive manifests or archives, so it cannot independently establish that this is the only actual finding. The offline rerun enumerates every detected duplicate and every hard manifest failure. It additionally checks per-case channel completeness (global counts alone are insufficient). No MRI data were downloaded or inspected in Cloud.

## Behavior and safeguards

- No image, mask, archive or case ID is removed, renamed, replaced or merged.
- Exact cross-case image byte duplicates have a separate SHA256/path/modality report and explicit manual-review flags. This is not voxel-wise/near-duplicate detection; differently compressed identical voxels need further review.
- All modalities and masks of every connected duplicate-linked component share a deterministic `split_group`. Connections are transitive. Original `patient_id` and `case_id` remain unchanged; source case counts do not become independent-person claims.
- No training/splitting occurs. Future split consumers must enforce `validate_split_assignments`; it rejects incomplete assignments and any train/validation/test disagreement inside a component. Review must not bypass this guard.
- Hard failures remain fatal: unreadable/invalid headers, unknown identities where disallowed, conflicting labels, missing groups/masks, and ISLES missing/extra channels. `validation_failures` lists all manifest checks rather than failing at the first one. File inspection errors remain separate from duplicate findings; an inspection error does not automatically prove physical corruption.
- Offline revalidation first verifies the retained archive's pinned publisher MD5/size, reads every member to EOF (ZIP CRC), and compares every extracted member's full SHA256/size with the archive. This detects truncated or changed payloads even when NIfTI headers remain readable. Unsafe paths/links/encrypted/duplicate archive entries fail. Missing archive or files fail without repair or network access.
- `download_integrity_verified_review_required` is emitted only after archive and file checks pass. It means acquisition integrity passed while duplicate/clinical review remains open; `training_ready` stays false. Other hard failures yield `failed`. Reports retain previous versions through the existing metadata backup mechanism.

## Exact Colab rerun

1. Open `detection/notebooks/Acquire_Best_5_Disease_Datasets.ipynb` from `feature/acquire-five-disease-datasets` (not an older saved notebook). Run the existing Colab runtime/dependency and Drive-mount setup. Keep the original `PROJECT_ROOT` so the retained ISLES location is used. T4 remains the intended future training runtime; this audit runs on CPU.
2. Leave **all five DOWNLOAD switches False**. Run configuration, embedded `dataset-catalog` and `acquisition-engine` cells. Do not run the acquisition preflight or download/extraction execution cells. Storage download budgets are irrelevant to this read-only audit.
3. In **Revalidate existing ISLES without downloading or extracting**, set `REVALIDATE_EXISTING_ISLES = True` and run that cell only. It resolves `Path(ACQUISITION_ROOT) / CATALOG['post_stroke']['id']`, normally `/content/drive/MyDrive/BrainMRI/datasets/DiseaseAcquisition/isles2022/`. Adjust the original PROJECT_ROOT if your initial acquisition used another project directory.
4. Retain `downloads/ISLES-2022.zip` and the original `data/` tree. If either is unavailable, stop and review the error; this path never redownloads or reextracts anything. It streams existing archive/data and may take time on Drive.
5. Review private `acquisition_report.json`, `file_manifest.json`, `patient_manifest.json`, and `duplicate_image_report.json`. Require passing archive/file checks and empty `validation_failures`. Check whether the only duplicate SHA group is the two reported FLAIR files. Review both cases clinically; do not assume patient equivalence. Confirm every file/mask for both shares a split_group, distinct from unrelated cases. Keep all clinical/training approval pending.

The existing 578 IXI files and all segmentation code are outside this audit. No training is authorized.
