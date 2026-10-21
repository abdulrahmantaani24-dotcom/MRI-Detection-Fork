# NeuroScope AI: five-disease acquisition comparison

Updated **2026-10-22**; continues the October 21 research and draft PR. The notebook prepares downloads in **Google Colab/private Drive only**. No MRI dataset was downloaded, no MRI preprocessing experiment was run, and no model was trained in Codex. Scientific papers, publication supplements and non-image source metadata were inspected for research.

Brain metastasis now has an author-authorized direct source. A larger meningioma source is preferred, with the original 37-patient option retained. OASIS-2 has a verified official direct-download route and clinical cohort definitions, but a weaker integrity policy and a clinical-label join that must remain explicit. **Download readiness, publisher-hash verification, completed patient manifests and training readiness are different states.**

## Updated comparison and download readiness

| Disease | Prepared source | Independent people versus scans | Compressed download | Data permission | What is ready for Colab? |
|---|---|---|---|---|---|
| Glioma | [MSD Task01](https://medicaldecathlon.com/), [direct TAR](https://msd-for-monai.s3-us-west-2.amazonaws.com/Task01_BrainTumour.tar) | 750 case volumes: 484 annotated, 266 without public masks. Independent clinical identity across cases/releases is not independently proven. | **7,608,266,240 bytes / 7.61 GB** | **CC BY-SA 4.0**, official MSD site | Download with publisher MD5; documented case-ID inventory. BraTS overlap still needs review. |
| Meningioma | **Preferred:** Hwang/SNUBH, [Zenodo 5945963](https://zenodo.org/records/5945963), [direct TAR.GZ](https://zenodo.org/api/records/5945963/files/Nii_data.tar.gz/content) | **91 meningioma patients**, 171 scans. Additional lesion-negative lung-cancer controls: paper body says 10; supplementary Table S1 says 12. Do not claim 171 patients or a resolved total/control count. | **20,855,300,096 bytes / 20.86 GB** | **CC BY 4.0**, author-deposited Zenodo record | Publisher-MD5 download and file/header inventory. **Patient linking, exact released modalities/masks, and diagnosis/control mapping remain review steps** after acquisition. |
| Brain metastasis | **PROTEAS**, latest pinned [Zenodo 23171182](https://zenodo.org/records/23171182); [example direct P01 ZIP](https://zenodo.org/api/records/23171182/files/P01.zip/content) | **40 patients**, 185 imaging studies, 65 metastases; **45 course ZIPs**, not 45 independent patients | **15,131,636,697 bytes / 15.13 GB**, including clinical XLSX; radiomics XLSX excluded | **CC BY 4.0**, author-deposited Zenodo release | Publisher-MD5 downloads and documented patient/course/visit/MRI-versus-ancillary parsing. Clinical/mask review still precedes training. |
| Alzheimer's disease | **Official OASIS-2 legacy raw release**, [part 1](https://download.nrg.wustl.edu/data/OAS2_RAW_PART1.tar.gz), [part 2](https://download.nrg.wustl.edu/data/OAS2_RAW_PART2.tar.gz) | **150 people / 373 sessions**: **64 clinical AD at baseline**, **72 stable nondemented controls**, **14 converters**. Three/four T1 acquisitions per visit are repeats, not new people. | **19,323,750,662 bytes / 19.32 GB** | **Custom OASIS Data Use Terms**, published on the [maintainer's NITRC page](https://www.nitrc.org/projects/oasis/); **not CC0/CC BY** | Direct anonymous download and source-ID/header inventory, **with disclosed weaker integrity**: no publisher cryptographic digest; HTTPS + exact size + full gzip CRC32 + local SHA-256 ledger. **Clinical-group join remains mandatory.** |
| Post-stroke lesions | [ISLES 2022 public training release](https://zenodo.org/records/7153326), [direct ZIP](https://zenodo.org/api/records/7153326/files/ISLES-2022.zip/content) | **250 annotated cases/patients**, three centers; not the full 400-case challenge | **1,692,717,470 bytes / 1.69 GB** | **CC BY 4.0**, official Zenodo record | Publisher-MD5 download and documented patient inventory. Acute/subacute ischemic lesions, not chronic ATLAS-type lesions. |

All **51 primary selected endpoints** returned anonymous HEAD 200 with expected byte sizes on October 22; no payload/range bytes from MRI archives were fetched. [download_probes.json](download_probes.json) records the observations. HEAD proves endpoint metadata/access, **not full payload integrity, archive contents, diagnostic correctness or successful Colab execution**. Every asset URL and available publisher digest is pinned in [dataset_catalog.json](dataset_catalog.json).

The primary choices total **64,611,671,165 compressed bytes** before extraction. Choose diseases independently and check private Drive quota; the notebook defaults every switch off. The 578 existing IXI-T2 files are not read, scanned, moved, modified or downloaded.

## Brain metastasis: resolving record 17253793 and its latest version

The official [latest-version endpoint](https://zenodo.org/api/records/17253793/versions/latest) resolves to **23171182**, published **2026-10-05**. The concept record is **15499111**. Record 17253793 is an earlier version, not an independent cohort. The current metadata has `access_right=open`, `license=cc-by-4.0`, and institutional authors from the University of Cyprus and Bank of Cyprus Oncology Center.

The data descriptor, [Flouri et al., Scientific Data 12, 1828 (2025), doi:10.1038/s41597-025-06131-0](https://doi.org/10.1038/s41597-025-06131-0), was inspected through [Europe PMC full-text XML](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC12630624/fullTextXML). It describes confirmed brain metastases with pathologically/clinically confirmed primary tumors and neuroradiologist-refined segmentations. MRI sequences are **T1w, contrast-enhanced T1, T2w and FLAIR**. The release includes raw **DICOM**, processed **NIfTI (.nii.gz)** in BraTS space, CT, radiotherapy data and clinical spreadsheets.

The documented layout supports a concrete acquisition adapter:

- Patients use `P01`–`P40`. `P04a/b`, `P07a/b`, `P17a/b`, `P20a/b` and `P23a/b` are separate treatment courses in the **same five patients**. They share a patient/split group. Multiple lesion rows such as P31/P33 entries in the updated clinical spreadsheet are not additional people.
- `BraTS/baseline`, `BraTS/fu1`, etc. contain `t1.nii.gz`, `t1c.nii.gz`, `t2.nii.gz`, `fla.nii.gz`. Visits remain within the patient.
- `tumor_segmentation/P??_tumor_mask_baseline.nii.gz` and follow-up masks are lesion annotations: necrotic core **1**, enhancing tumor **2**, edema **3**. Brain tissue labels **10/30/40/50**, CT and radiation plans are **ancillary**, not tumor masks or MRI channels.
- The original archives are retained and extracted into separate course directories. Raw DICOM is not converted or treated as an additional independent MRI cohort.

Publisher MD5 and byte size exist for every selected ZIP and the clinical spreadsheet. Compared with 17253793, **six ZIPs changed**: `P04b`, `P06`, `P07a`, `P07b`, `P09`, `P10`. The clinical XLSX also changed. The notebook pins latest URLs/checksums and never merges versions into one destination. The optional radiomics spreadsheet is omitted from the selected transfer.

Limitations: single-center, treatment-enriched longitudinal cohort; small lesions **under 3 mm were excluded**. Clinical protocol/response labels and mask geometry still require data review in Colab. The repository metadata's journal/year fields are inconsistent with the published paper; the citation above uses the actual 2025 descriptor, not the deposit's journal-year text.

Compared alternatives remain useful but are not required for this qualified transfer: UCSF-BMSR's official portal requires reCAPTCHA before its actual endpoint/hash can be verified; UCSD-BMETS-Longitudinal has 300 subjects, 163 GB and CC BY 4.0, but its advertised imaging transfer is Aspera. The notebook does not bypass challenges or replace data with pretrained weights/third-party Kaggle slices.

## Alzheimer's: qualifying access versus correct clinical labels

### Why OASIS-2 can now be prepared

Two independent authorized sources resolve the earlier access/terms gap:

1. The [official NrgXnat/oasis-scripts README](https://github.com/NrgXnat/oasis-scripts#oasis-scripts-overview), maintained by the OASIS/XNAT team, explicitly states that its signed-DUA/project-access download scripts for **OASIS-3/4** are **not needed for OASIS-1/2**, whose data download directly. Do not incorrectly generalize later-release registration requirements to these legacy releases.
2. The [OASIS NITRC resource](https://www.nitrc.org/projects/oasis/), maintained by Daniel Marcus/OASIS administrators at Washington University, publishes the custom OASIS terms and identifies OASIS-1/2 as public scientific resources. The official [Washington University download directory](https://download.nrg.wustl.edu/data/) lists both `OAS2_RAW_PART1.tar.gz` (**10,874,461,059 bytes**) and `OAS2_RAW_PART2.tar.gz` (**8,449,289,603 bytes**); both answer anonymous HEAD 200 with Range support.

The terms prohibit reidentification/contact, facial recognition/3D facial rendering, require source-specific acknowledgment/citation and usage information to the Knight ADRC on request. The separate Avid review condition concerns specified PET tracers, not these T1 MRI archives. No registration, application, approval bypass, credentials or unauthorized MRI mirror is used. The central OASIS website still returns 503; the authorized NITRC resource, maintainer documentation and official server supply the evidence used here. Terms are custom: do not relabel the data CC0 or CC BY.

### Clinical AD is not a generic dementia/MCI label

[Marcus et al., Journal of Cognitive Neuroscience 22(12), 2677–2684 (2010), doi:10.1162/jocn.2009.21407](https://doi.org/10.1162/jocn.2009.21407), available as [PMC2895005](https://pmc.ncbi.nlm.nih.gov/articles/PMC2895005/), defines **150 people aged 60–96**: 64 clinically AD at baseline, 72 nondemented throughout observation and 14 initially nondemented people who later converted. There are **373 sessions**, each with three/four **3D T1w MP-RAGE** acquisitions on one **1.5 T scanner**. The descriptor specifies NIfTI-1 distribution; the inspector supports both single-file NIfTI and paired IMG/HDR, and hashes the paired header too. Exact package inventory is verified only after Colab acquisition.

The paper describes cohort-specific clinical AD assessment, including collateral history, progression and exclusion of alternative contributors. Its very-mild AD cases may have CDR 0.5, but **this does not justify calling arbitrary CDR 0.5/MCI records AD in other datasets**. No biomarker-confirmation claim is made.

The notebook **does not infer diagnosis from the filename, absent metadata, missing mask, generic dementia label or CDR threshold**. It groups all `OAS2_####` visits under one patient and leaves clinical diagnosis null until a reviewed per-file clinical-group CSV is supplied. The allowed groups are:

- `AD_clinical_baseline`: 64 independent baseline-AD patients.
- `control_stable`: 72 stable controls.
- `converter_excluded`: all visits of the 14 converters, kept out of a binary AD/control cohort.

Conflicting within-patient labels, changed source IDs, generic `MCI`/`Demented`/CDR labels and incorrect final group counts are rejected. The first download can finish with **clinical mapping pending**, not a falsely completed labeled dataset. A private template is produced; missing clinical metadata must be obtained/reviewed from authorized source material, never fabricated.

### OASIS-2 integrity limitation

The official directory and response metadata publish **no cryptographic checksum**. The notebook does **not** invent an MD5, treat Apache ETags as MD5, or claim a newly computed SHA-256 is publisher verification. Only these two exact official legacy URLs are allowed to use the explicitly named `https_size_gzip_crc32_local_sha256` policy:

- HTTPS and exact HEAD byte size during transfer.
- Full gzip-stream CRC32/uncompressed-size verification before promotion.
- A private local SHA-256 ledger, compared on subsequent use; different existing files are preserved.

This is **weaker than comparison with a publisher cryptographic digest**. The notebook prints that fact before transfer and records it in source/asset reports. If publisher-hash verification is essential, leave Alzheimer's disabled. All other sources retain mandatory publisher MD5/SHA-256; this policy cannot override a provided checksum or be used for another host/file.

### Other AD alternatives investigated

| Repository/source | Verified finding | Decision |
|---|---|---|
| [MIRIAD, NITRC](https://www.nitrc.org/projects/miriad/); [Malone et al. descriptor](https://doi.org/10.1016/j.neuroimage.2012.12.044) | 46 mild/moderate AD patients + 23 controls; 708 3D T1 scans. NITRC publishes a **“By registering and downloading”** agreement, prohibits redistribution without agreement; its file page has no data packages. | Clinically useful, but does not meet the requested verified no-registration route. Do not use an unauthorized mirror. |
| OASIS-1 | Maintainer resource reports 416 participants, 100 clinically AD; official legacy archive index is public. | Credible alternative; OASIS-2 has a more clearly documented stable-control/AD/converter grouping and is chosen here. Neither all 416 people nor all demented/MCI subjects may be labeled AD. |
| OASIS-3/4, ADNI, AIBL | Richer clinical/imaging data; documented registration/DUA/project-access or application workflows. | Do not substitute gated releases under the no-registration requirement. |
| [Zenodo 20426271](https://zenodo.org/records/20426271) | Restricted; description counts 24,000 **JPG images** in Demented/NonDemented categories, without independent clinical-patient provenance. | Not a 3D clinically AD-labeled replacement. |
| [Zenodo 8113922](https://zenodo.org/records/8113922) | 16 AD / 10 controls / 7 FTD, but restricted derived connectivity matrices/time series, not the requested whole-brain MRI transfer. | Exclude. |
| [Zenodo 1247911](https://zenodo.org/records/1247911) | Public PET/fMRI paper describes mixed aMCI/AD patients, but deposit supplies the paper PDF, not raw MRI. | Do not treat a paper or combined MCI/AD group as a labeled AD MRI dataset. |
| OpenNeuro | ds004504/ds006036/ds007427 are EEG; ds004796 is healthy/risk-genotype imaging; ds004767 is ex-vivo temporal-lobe specimens. | Not clinically diagnosed in-vivo whole-brain AD/control substitutes. |
| Figshare, Dryad and GIN searches | Additional hits included publications, clinical/radiomic tables, model files, derived matrices or other diseases; GIN was unavailable (503). | No additional independently verified clinical whole-brain MRI transfer selected; no adverse conclusion about the entire repositories is implied. |

## Meningioma: why the 37-patient cohort is not representative enough

The retained [OpenNeuro ds007345 v1.0.0](https://openneuro.org/datasets/ds007345/versions/1.0.0) option remains useful: **37 baseline patients**, 179 selected structural/mask files, **4,407,701,072 bytes**, **CC0**. It is a single-center **olfactory-groove meningioma** cohort. Its restricted anatomy and small sample do not represent meningioma generally. Follow-up folders were excluded, not counted as additional people.

A stronger accessible alternative is now verified:

- **Source/access:** author-deposited, open [Zenodo 5945963](https://zenodo.org/api/records/5945963), latest version verified, CC BY 4.0, direct TAR.GZ with publisher MD5 **`c3b2ce5fbad44e1885ac73a03be9d38b`**. HEAD confirms **20,855,300,096 bytes** without MRI transfer.
- **Independent count:** [Hwang et al., Journal of Imaging 8(12), 327 (2022), doi:10.3390/jimaging8120327](https://doi.org/10.3390/jimaging8120327), checked in [PMC9782766 full text](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC9782766/fullTextXML), reports **91 meningioma patients**. Of these, 35 account for 115 longitudinal scans and 56 have one scan each: **171 scans, not 171 people**.
- **Anatomical coverage:** supplementary Table S2 lists convexity **48**, parasagittal **10**, falx **10**, sphenoid wing **10**, tentorial **6**, olfactory groove **3**, tuberculum sellae **2**, clinoidal **1**, intraventricular **1**. Skull-base attachment is present in **22/91**. This is materially broader than an exclusively olfactory-groove sample.
- **Imaging/labels:** clinical protocol includes T1w, 3D contrast-enhanced T1 (1 mm acquisition), T2w and FLAIR on 1.5/3 T systems. Two radiologists manually labeled meningioma ROIs on preprocessed T1ce. The release states NIfTI image files; **exact released channel/mask inventory and file-to-patient linkage have not been inspected in Cloud** and remain Colab review steps.
- **Limitations:** one tertiary hospital, supratentorial selection and follow-up enrichment; not a population-representative multicenter cohort. Paper body says **10** lesion-negative controls, while supplement Table S1 says **12**. These subjects have lung cancer with no brain/extrapulmonary metastases; they are not equivalent to healthy IXI controls. Do not silently resolve the discrepancy or report a definitive 101/103 total.

The notebook prefers this larger source for acquisition, retains `MENINGIOMA_SOURCE="openneuro37"` for the original fully documented baseline layout, and does not download both by default. For the larger source, undocumented scan filenames are **not invented as patient IDs**: the first run returns a file/header inventory with null identities/diagnoses plus a private mapping template. A reviewed source-based mapping is required before a complete patient manifest is reported; it must establish **91 distinct meningioma patients**. Unknown diagnoses and missing masks do not become negative controls.

Other larger candidates remain unsuitable under these access requirements: Meningioma-SEG-CLASS currently labels imaging controlled access (96 patients); MISGRA (103 patients, 433 sessions) explicitly requires a signed institutional data-access agreement; Zenodo 6939897 is restricted and has no MRI files; Zenodo 5148138 describes 46 patients but releases a small spreadsheet, not their scans. Existing BraTS-MEN access conditions must be verified per version rather than evaded with slice mirrors. A larger advertised study count alone is not a downloadable dataset.

## Preserved glioma and stroke decisions

- **Glioma:** MSD Task01 remains the practical anonymous, authorized, checksum-backed 3D choice. Publisher MD5 **`240a19d752f0d9e9101544901065d872`** comes from [MONAI 1.5.1](https://raw.githubusercontent.com/Project-MONAI/MONAI/1.5.1/monai/apps/datasets.py); modalities are FLAIR/T1w/T1ce/T2w. Cite [Antonelli et al., doi:10.1038/s41467-022-30695-9](https://doi.org/10.1038/s41467-022-30695-9) and source BraTS work. MSD overlaps BraTS 2016/17 and cannot be pooled as an independent cohort. UCSF-PDGM has stronger molecular/pathology context, but the current 495-subject/501-study, 142 GB release advertises Aspera rather than the verified plain archive used here.
- **Stroke:** ISLES 2022 provides FLAIR/DWI/ADC and expert masks; MD5 **`302ee280373cdd5c190ab763d72a7a50`** is published in the [Zenodo record](https://zenodo.org/api/records/7153326). Cite [Hernandez Petzsche et al., doi:10.1038/s41597-022-01875-5](https://doi.org/10.1038/s41597-022-01875-5). Native-space sequences are not assumed aligned. ATLAS 3.0 is a larger chronic T1 alternative (1,453 public training participants), but release-specific license/checksum was not fully verified; its counts overlap/replenish ATLAS 2.0, so they are not additive.

## Implementation, validation and remaining work

Notebook: `detection/notebooks/Acquire_Best_5_Disease_Datasets.ipynb`. Existing branch/PR and the original detection/segmentation work are preserved. `sync_acquisition_notebook.py` updates embedded reviewed helpers/catalog without network or MRI I/O.

- Five independent switches default off; meningioma has a source selector. Download/extraction/hashing/header inspection are CPU acquisition work in Colab, not model preprocessing/training.
- Colab/Drive and IXI-protection guards remain. HTTPS is verified; publisher hashes for existing sources are unchanged. OASIS's narrow legacy policy is prominently disclosed, not presented as publisher hashing.
- Resume uses validated HTTP Range/If-Range. Extraction rejects traversal, links, special files, duplicate paths and oversized archives. One **shared extraction budget per disease** covers all its archives; 45 PROTEAS ZIPs do not multiply the quota reservation 45-fold. Different existing files and previous reports are preserved.
- PROTEAS patient/case/visit parsing, MRI-versus-CT/RTP/tissue roles, NIfTI IMG/HDR support, explicit identity/clinical CSV mapping and pending-review states are implemented. Private manifests contain shape, dtype, spacing, affine, byte counts and hashes. **Pending review never becomes training-ready.**
- No MRI, clinical spreadsheet rows, credentials or notebook outputs are committed. [source_audit.json](source_audit.json) and [download_probes.json](download_probes.json) retain metadata provenance and observations.
- Offline tests use artificial bytes/archives and synthetic NIfTI headers only. Actual full payload integrity, extraction/package layout, Colab Drive behavior, T4 CUDA/AMP operation and clinical correctness remain **unexecuted** until an opt-in Colab run. The notebook retains a tiny CUDA/MONAI/AMP readiness self-test; it is not a model benchmark.
- No model training starts. Later training requires verified/approved datasets, correct patient-level splits, CUDA on Colab T4, efficient 3D patches/AMP and full Drive checkpoint/resume state. IXI T2 controls must not be pooled with unmatched disease modalities/scanners/ages without reviewing confounding.

Validation commands from the checkout root:

```bash
python detection/sync_acquisition_notebook.py
.venv/bin/python -m unittest -v detection.test_acquisition
```
