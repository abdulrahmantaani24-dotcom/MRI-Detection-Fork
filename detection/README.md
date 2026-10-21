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
default off; three choices are prepared, while brain metastasis and Alzheimer's remain
disabled pending verified qualifying access. Existing IXI files are not scanned or changed.

Read the [dataset comparison and evidence](research/DATASET_SELECTION.md) before selecting
downloads. No training is included. The helper's offline safety tests use artificial data:
`python -m unittest -v detection.test_acquisition` from the repository root.
