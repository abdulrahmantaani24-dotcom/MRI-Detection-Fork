# Brain MRI detection: Colab setup

This separate workspace prepares Google Colab for future detection work. Training belongs in Colab on a Tesla T4; Codex Cloud is for coding, review, and lightweight CPU checks. No detection model or training pipeline is included.

## Open and run

1. Download [Brain_MRI_Detection_Colab.ipynb](notebooks/Brain_MRI_Detection_Colab.ipynb), open [Google Colab](https://colab.research.google.com/), and choose **File → Upload notebook**.
2. Select **Runtime → Change runtime type → T4 GPU**, then connect.
3. Edit the first code cell: set your private `PROJECT_ROOT`, and optionally override dataset/checkpoint paths. Enable Drive mounting if needed. Authorize access only through Colab's prompt.
4. Run the cells in order. They check CUDA/PyTorch with a tiny device tensor, install pinned MONAI/NiBabel without replacing Colab's PyTorch, verify package requirements and in-memory transforms, and prepare paths.
5. Missing data or checkpoints are reported and are acceptable for setup. Output directory creation is opt-in. The notebook does not download data, read MRI files, load weights, or start training.

For a CPU-only check in an environment with the dependencies already installed, disable `REQUIRE_GPU`, `INSTALL_COLAB_DEPENDENCIES`, and `MOUNT_GOOGLE_DRIVE`; set `PROJECT_ROOT` to an absolute local path. Otherwise, JSON structure and code syntax can be checked without any ML packages or dataset.

## Existing segmentation files

The existing workflow stays at the repository root: `segmentation_baseline.py`, `monai_preprocessing_pipeline.py`, `finetune_segresnet.py`, `generate_segmentation_visualizations.py`, `test_segmentation_readiness.py`, `run_smoke_test.py`, and `verify_model_training_7checks.py`. Its Colab notebook is `notebooks/NeuroScope_Glioma_FineTuning_Colab.ipynb`; associated weights and results are in `models/`, `reports/`, and `outputs/`. The existing `detection_experiment.py` is also left unchanged.

Keep datasets and checkpoints outside the Git checkout, in private Drive storage. Do not commit patient data, weights, credentials, or sensitive notebook outputs. Clear outputs before committing the notebook. This setup requires no upstream changes.

## Disease dataset acquisition

Use [Acquire_Best_5_Disease_Datasets.ipynb](notebooks/Acquire_Best_5_Disease_Datasets.ipynb)
for opt-in, checksum-verified acquisition into private Google Drive **from Colab only**.
It reuses this setup notebook's runtime/dependency/Drive cells. All five disease switches
default off. The updated choices include PROTEAS brain metastasis, a larger 91-patient
meningioma cohort, and official legacy OASIS-2; the original 37-patient meningioma option
is retained. Download readiness is separate from clinical-label readiness: the larger
meningioma and OASIS-2 choices need reviewed mapping, and OASIS-2 has no publisher
cryptographic digest (its explicit policy uses HTTPS/size/gzip CRC32 and a local SHA-256
ledger). Existing IXI files are not scanned or changed.

Read the [dataset comparison and evidence](research/DATASET_SELECTION.md) before selecting
downloads. No training is included. The helper's offline safety tests use artificial data:
`python -m unittest -v detection.test_acquisition` from the repository root.
After editing the helpers/catalog, refresh the embedded notebook with
`python detection/sync_acquisition_notebook.py`; this performs no network or MRI I/O.

ISLES duplicate FLAIR: use the notebook's **Revalidate existing ISLES without downloading or extracting** section rather than rerunning downloads. See [root cause, safeguards and exact Colab instructions](research/ISLES_VALIDATION_REVIEW.md). Exact duplicates require manual review and shared split groups; they are reported separately from file errors. Acquisition integrity never implies clinical/training approval. Run synthetic regression checks with `python -m unittest detection.test_acquisition detection.test_isles_duplicates -q`.

Drive storage checks use current user-confirmed free account quota, with independent real local-disk checks. See [storage reservation, headroom and exact Colab cell rerun order](research/COLAB_STORAGE_PREFLIGHT.md). Test with `python -m unittest detection.test_acquisition detection.test_isles_duplicates detection.test_storage -q`.

For stalled/interrupted Hwang transfers, see [findings, streaming/resume policy and exact rerun instructions](research/MENINGIOMA_INTERRUPTED_DOWNLOAD.md). Progress snapshots are informational, never integrity evidence. Additional synthetic tests: `python -m unittest detection.test_streaming -q`.

Phase 2: [Detection_Dataset_Readiness_Audit.ipynb](notebooks/Detection_Dataset_Readiness_Audit.ipynb) audits six existing Drive trees read-only on CPU, with resumable private reports and no training or preprocessing. See [run instructions and evidence limits](research/DETECTION_READINESS_AUDIT.md). Run synthetic checks with `python -m unittest detection.test_readiness_audit -q`. Real dataset readiness remains unestablished until the Colab audit and subsequent clinical/domain review.
