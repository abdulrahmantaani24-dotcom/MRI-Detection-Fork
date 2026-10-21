# NeuroScope AI: disease dataset selection

Research date: **2026-10-21**. Scope: clinical 3D brain MRI acquisition for later disease detection; no training. Free access must mean an actual authorized data transfer without registration or case-by-case approval, not merely a public paper, metadata page, or model checkpoint. Licenses below apply to data unless explicitly stated otherwise.

**Three acquisition choices are prepared. Brain metastasis and Alzheimer's remain unresolved under the required verification standard.** This is not a claim that a qualifying dataset cannot exist. Their download switches deliberately fail with the reason rather than silently substituting unverified data.

## Prepared choices and verified direct links

| Disease | Choice | Patient/case count | Download bytes | License and citation |
|---|---|---|---|---|
| Glioma | [MSD Task01 BrainTumour](https://medicaldecathlon.com/), via [MONAI-authorized direct TAR](https://msd-for-monai.s3-us-west-2.amazonaws.com/Task01_BrainTumour.tar) | 750 4D **case volumes**, including 484 annotated cases and 266 without public masks. Independent clinical identities not independently established here. | **7,608,266,240** (7.61 GB / 7.09 GiB) | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/), explicitly stated on the official MSD site. Antonelli et al., *The Medical Segmentation Decathlon*, [doi:10.1038/s41467-022-30695-9](https://doi.org/10.1038/s41467-022-30695-9); also cite source BraTS publications. |
| Meningioma | [OpenNeuro ds007345 v1.0.0](https://openneuro.org/datasets/ds007345/versions/1.0.0): baseline structural MRI plus available tumor/edema masks | **37 independent baseline participants**, **179** selected image/mask files. Postoperative folders are repeat visits and are excluded. | **4,407,701,072** (4.41 GB / 4.10 GiB) for the selected subset | **CC0**, confirmed in the publisher's pinned [dataset_description.json](https://raw.githubusercontent.com/OpenNeuroDatasets/ds007345/fd052d49bfa51677fca817efdb68f237eeda9774/dataset_description.json). Filimonova et al., *Multimodal Brain MRI and Clinical Data in Olfactory Groove Meningioma*, [doi:10.18112/openneuro.ds007345.v1.0.0](https://doi.org/10.18112/openneuro.ds007345.v1.0.0). |
| Post-stroke lesions | [ISLES 2022 public training release](https://zenodo.org/records/7153326), [direct ZIP](https://zenodo.org/api/records/7153326/files/ISLES-2022.zip/content) | **250** expert-annotated stroke cases/patients from three centers. Do not report the full 400-case challenge as 400 downloadable annotated cases. | **1,692,717,470** (1.69 GB / 1.58 GiB) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), open access in the official [Zenodo API record](https://zenodo.org/api/records/7153326). Hernandez Petzsche et al., *Scientific Data* 9, 762 (2022), [doi:10.1038/s41597-022-01875-5](https://doi.org/10.1038/s41597-022-01875-5); dataset DOI 10.5281/zenodo.7153326. |

All **181 selected image/archive endpoints** returned HEAD 200 with matching `Content-Length`; no MRI payload was downloaded. Server Range support was observed. See [download_probes.json](download_probes.json). This verifies endpoint metadata, not the eventual payload hash: Colab must verify every completed file before extraction or inspection. A successful metadata request does not establish Colab execution, full archive integrity, clinical correctness, or GPU readiness.

Meningioma example direct asset: [sub-olf01_T2w.nii.gz](https://s3.amazonaws.com/openneuro.org/ds007345/sub-olf01/anat/sub-olf01_T2w.nii.gz). Every selected file's direct URL, byte size, patient ID and publisher Git-annex SHA-256 is in [dataset_catalog.json](dataset_catalog.json). Metadata is pinned to commit `fd052d49bfa51677fca817efdb68f237eeda9774`, the v1.0.0 tree. Public S3 object names can change; hashes must still match the pinned release. No archive of annex symlinks is mistaken for MRI data.

Publisher archive checksums:

- MSD TAR: MD5 `240a19d752f0d9e9101544901065d872`, from [MONAI 1.5.1](https://raw.githubusercontent.com/Project-MONAI/MONAI/1.5.1/monai/apps/datasets.py).
- ISLES ZIP: MD5 `302ee280373cdd5c190ab763d72a7a50`, from the official Zenodo record.
- OpenNeuro: individual SHA256E digests from publisher Git-annex pointer metadata, recorded per asset in the catalog. Multipart S3 ETags are **not** treated as MD5.

All downloaded files also receive a local SHA-256 for provenance. Local SHA-256 alone is not publisher authenticity verification. TLS verification remains enabled.

## Alternatives compared

### Glioma

| Alternative | Strength | Decision |
|---|---|---|
| MSD Task01 | Direct anonymous HTTPS, multisite/multimodal 3D FLAIR/T1/T1ce/T2, expert masks, documented license and fixed checksum; compatible with the existing project | Select as the practical verified transfer. It is not claimed to be the largest contemporary glioma cohort. |
| [UCSF-PDGM](https://www.cancerimagingarchive.net/collection/ucsf-pdgm/) | Strong pathology/molecular labels and advanced sequences; current TCIA table: **495 subjects / 501 studies**, 142 GB, CC BY 4.0 | Current official primary transfer requires IBM Aspera Connect. A plain authorized HTTP archive and its checksum were not verified. Do not repeat the older 501-independent-subject claim: the current release recognizes follow-ups. |
| BraTS challenge releases | Large expert-annotated 3D cohorts | Current release access/terms must be checked individually; do not use an unofficial Kaggle mirror to evade registration. MSD explicitly derives from BraTS 2016/2017, so combining them does not create independent subjects. |
| TCGA-GBM / TCGA-LGG | Pathology-rich, heterogeneous clinical images | Additional DICOM curation, variable sequences and overlap with BraTS; not selected over the verified direct MSD acquisition in this notebook. Current image access must be checked rather than assumed from historical public availability. |

MSD's archive is **7.61 GB**, not the approximately 2 GB quoted in the older segmentation Colab notebook. That notebook is preserved, not edited. Metadata counts of 750 volumes and 484 training cases are corroborated by the [official MONAI tutorial](https://github.com/Project-MONAI/tutorials/blob/main/3d_segmentation/brats_segmentation_3d.ipynb). Cases, channels, slices and independent patients must not be conflated.

### Meningioma

| Alternative | Evidence | Decision |
|---|---|---|
| OpenNeuro ds007345 | Official CC0 release, [37-row baseline participant table](https://raw.githubusercontent.com/OpenNeuroDatasets/ds007345/fd052d49bfa51677fca817efdb68f237eeda9774/participants.tsv), structural 3D MRI and mask pointers | Select the baseline structural/mask subset. Smaller than gated alternatives but satisfies verified access/permission requirements. |
| [Meningioma-SEG-CLASS](https://www.cancerimagingarchive.net/collection/meningioma-seg-class/) | 96 pathology-confirmed patients; T1/T1ce/FLAIR, RTSTRUCT; 9.39 GB | **Exclude**: current imaging table is labeled **NIH Controlled Data Access Policy**. The separate clinical spreadsheet's CC BY 4.0 does not make the images openly licensed/ungated. |
| [MISGRA, Figshare 33263757](https://api.figshare.com/v2/articles/33263757) | 103 patients, 433 sessions, 1,199 volumes, 22,398,716,158 bytes; grounded report annotations | **Exclude**: metadata explicitly says signed institutional Research Data Access Agreement and manual requests; `is_confidential=true`. Its description mentioning CC BY-NC does not override controlled access. Annotations are points/boxes/lines, not necessarily voxel masks. |
| BraTS-MEN / challenge cohorts | Larger 3D annotated releases | Not accepted without a currently verified authorized no-registration download and research terms for the chosen version. |
| Figshare/Kaggle slice collections; MeniSeg | Some readily available 2D tumor slices; [MeniSeg README](https://github.com/CindyZJT/MeniSeg) says the dataset will be released later | Reject 2D substitutes and unreleased data when a qualified 3D alternative exists. |

Selected OpenNeuro limitations: one center, only olfactory groove meningioma, limited grade diversity, and not all edema masks present. T1 `run-01`/`run-02` alone does not identify contrast administration, so the manifest records contrast as unspecified pending sidecar/clinical review. The entire release also has diffusion/fMRI/processed derivatives; these are excluded from the selected 4.41 GB to keep the structural detection cohort focused. Follow-ups remain grouped with baseline patients if introduced later.

### Brain metastasis — no qualifying transfer selected

| Alternative | Evidence | Outstanding condition |
|---|---|---|
| UCSF-BMSR | [Publisher's official benchmark repository](https://github.com/rachitsaluja/UCSF-BMSR-benchmarks), paper [doi:10.1148/ryai.230126](https://doi.org/10.1148/ryai.230126), [publisher data portal](https://imagingdatasets.ucsf.edu/dataset/1) | The publisher portal was rendered with TLS verification preserved. Version 1.3 advertises **412 patients / 560 exams**, but explicitly says **461 exams** are currently available. Independent patient count within that public subset is not stated. The Download button responds **“Please complete the ReCaptcha challenge”**. No challenge was bypassed; no current direct MRI endpoint or publisher checksum was verified. Dataset-level license still requires confirmation. The official benchmark README explicitly prohibits commercial use; its pretrained-model Drive link is **not** an MRI dataset link. |
| [UCSD-BMETS-Longitudinal](https://www.cancerimagingarchive.net/collection/ucsd-bmets-longitudinal/) | Current official page: **300 subjects**, 163 GB, NIfTI images/segmentations, **CC BY 4.0**, [doi:10.7937/5ejb-9g94](https://doi.org/10.7937/5ejb-9g94) | Strong candidate for a later acquisition adapter, but the published imaging transfer is **Aspera**, not a verified direct HTTP archive. Abstract says 1,065 timepoints; table says 1,066 studies. Neither is 1,066 independent patients. |
| BrainMetShare / Stanford AIMI | [Official source landing page](https://aimi.stanford.edu/datasets/brainmetshare) referenced by downstream work | Current official access/permission and a direct checksum-backed payload were not verified. Do not use third-party Kaggle slices as an authorized replacement. |

The metastasis switch is disabled with an actionable error. No assertion that an ungated dataset does not exist is justified by an unresolved portal. A future change should verify one of these publisher transfers, then add its exact assets and a tested patient-identity adapter.

### Alzheimer's disease — no qualifying clinical cohort selected

| Alternative | Strength | Decision |
|---|---|---|
| [OASIS-1](https://sites.wustl.edu/oasisbrains/) | Historically 416 participants, including a dementia subset; 3D structural scans and clinical tables | A legacy [disc-1 archive](https://download.nrg.wustl.edu/data/oasis_cross-sectional_disc1.tar.gz) answered anonymous HEAD 200, 1,380,527,970 bytes. **This alone is insufficient**: official current OASIS pages/terms returned 503, the full release's checksums/permissions were not verified, and 416 is not an Alzheimer-positive patient count. No acquisition is enabled. |
| OASIS-2 / OASIS-3 | Longitudinal imaging and richer phenotyping | Verify present access conditions and source versions separately; do not assume access to legacy OASIS-1 implies access to later releases or pool repeat visits as new patients. |
| ADNI / AIBL | Strong longitudinal clinical diagnosis/biomarkers | Controlled application/registration workflows do not fit the stated no-registration/no-manual-approval requirement. No credentials are requested. |
| [OpenNeuro ds004767](https://github.com/OpenNeuroDatasets/ds004767) | Official CC0 3D MRI with pathology-related annotations | **Exclude for this clinical detection cohort**: ex-vivo 9.4 T temporal-lobe specimens, not in-vivo whole-brain clinical scans. README describes 55 specimens and maps for 25 donors; specimens must not be counted as independent AD patients. |
| [PEARL-Neuro ds004796](https://github.com/OpenNeuroDatasets/ds004796) | CC0; EEG/fMRI and risk-genotype metadata | **Exclude as an AD-positive cohort**: the official README describes 192 healthy middle-aged participants, with neuroimaging for 79. Genetic risk is not an Alzheimer diagnosis. OpenNeuro ds004504/ds006036 and ds007427 are EEG, not suitable MRI substitutes. |
| [Zenodo 7048297](https://zenodo.org/records/7048297) and common Kaggle dementia slices | Titles can suggest downloadable AD MRI | Record 7048297 actually supplies a **PDF only**, not MRI. Reject 2D slice collections without verifiable patient provenance, research rights and independent identity when evaluating a 3D clinical workflow. |

CDR is a clinical dementia severity measure, not proof of biomarker-confirmed Alzheimer's disease. A cohort can include controls, MCI and other dementia etiologies; diagnosis must come from documented clinical metadata, not a folder title or the dataset's name.

### Post-stroke lesions

| Alternative | Evidence | Decision |
|---|---|---|
| ISLES 2022 | Open official Zenodo release, 250 masks, FLAIR/DWI/ADC, three centers and multiple scanner vendors/field strengths, fixed size/MD5 | Select for verified acquisition of **acute/subacute ischemic** lesions. Clinical target differs from chronic structural lesions. |
| [ATLAS 3.0](https://github.com/npnl/ATLAS) | Official README: **1,453 public training participants**, 362 hidden generalizability cases. [Official S3 listing](https://fcp-indi.s3.amazonaws.com/?list-type=2&prefix=data/Projects/INDI/ATLAS/R3.0/&max-keys=20) confirms raw TAR.GZ **8,244,197,870 bytes** and preprocessed TAR.GZ **14,823,858,360 bytes** | Promising larger **chronic T1** cohort. Do not select automatically: release-specific license and a usable publisher checksum were not verified here. S3 ETags have multipart suffixes and must not be presented as full-file MD5. NITRC landing hostname contains an underscore and was rejected by the environment's DNS allowlist validator. |
| ATLAS 2.0 | Official README: 655 public training images with masks, 300 additional public test images without masks, 316 hidden generalizability cases | Do not add its counts to ATLAS 3.0: the publisher says 3.0 expands/replaces the old public release. |
| ISLES challenge hidden test sets | Additional evaluation cohorts | Hidden masks/test data are not free labeled training data; do not download through a registration path or misrepresent challenge totals. |

If the desired stroke target is specifically chronic residual lesions rather than acute ischemia, leave the switch off and resolve ATLAS 3.0 permissions/checksum before selecting it. ISLES is not silently presented as equivalent.

## Reproducibility and remaining validation

- Notebook: `detection/notebooks/Acquire_Best_5_Disease_Datasets.ipynb`. It embeds `detection/acquisition.py` and the reviewed catalog; it does not fetch executable helpers at runtime. Existing detection setup cells are reused unchanged.
- Five independent user switches default off. Unresolved choices fail explicitly. Colab-only and private-Drive guards prohibit Cloud acquisition. IXI is not scanned or modified.
- Preflight HEADs, Drive-quota input, filesystem space checks, bounded streaming, validated HTTP resumption, publisher checksums, safe ZIP/TAR extraction, and SHA-256 provenance are implemented. All archive files are retained, so storage must cover both compressed and extracted data.
- Public source/evidence metadata is tracked in `source_audit.json`, `download_probes.json` and `dataset_catalog.json`. No MRI data, clinical table values, credentials or notebook outputs are committed.
- Patient/file manifests are generated **in private Drive after acquisition**. They include source patient/case groups, file roles, modality, shape, dtype, spacing, affine, byte size and hashes. They are not fabricated before actual acquisition. Missing masks, diagnosis confidence, image/mask geometry, near duplicates and cross-release identities still require clinical/data review.
- Offline checks use artificial payloads, synthetic NIfTI headers and mocked responses only. Actual Colab transfer, full payload checksums/extraction, Tesla T4 CUDA behavior and acquired clinical data have **not** been executed or verified in Codex Cloud.
- Acquisition/metadata work is on CPU. The notebook reuses strict CUDA checks and has a tiny CUDA/MONAI/AMP self-test and GPU memory report for the future T4 workflow. There is no model, training loop, checkpoint load or training-performance claim. A later approved training task must use patch-based CUDA/AMP, measure VRAM/throughput, and save/resume full training state in private Drive.
- Do not combine IXI T2 controls with disease cohorts without reviewing modality/site/scanner/age confounding. Do not random-split slices, modalities or visits independently. Cross-source identity review is still required; exact file hashing cannot prove absence of near duplicates.

Run offline checks from the repository root with the existing environment:

```bash
.venv/bin/python -m unittest -v detection.test_acquisition
```
