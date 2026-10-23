# Colab Drive storage preflight correction

The old `require_space` used `shutil.disk_usage(root).free` for every destination. Preflight first compared its archive + extraction reservation against the user's Drive quota, but then compared the same reservation against mounted Drive statvfs. Download and extraction repeated that filesystem check. DriveFS's approximately 63.44 GiB figure is not an authoritative account quota; changing only the first preflight comparison would leave later false rejections.

All Drive-path checks now require a positive current user-confirmed `DRIVE_AVAILABLE_GIB`. They never use mounted Drive statvfs to decide account capacity. Local paths continue to use actual filesystem free space. Preflight and acquisition separately check real `/content` capacity, retaining 2 GiB for runtime/cache overhead. Downloads stream directly into Drive `.part` files and extraction streams into Drive `.extracting` files; this implementation creates no MRI-sized local staging copies. Any future local staging must declare simultaneous peak bytes to `check_storage_plan`. DriveFS cache/provider errors remain real I/O failures and propagate; the local reserve is not a guarantee about undocumented DriveFS caching.

Reservation is the sum of all retained selected downloads plus the shared extraction budget for each selected archived disease, plus **max(5 GiB, 10% of that combined footprint)**. Download and extraction limits, archive member size checks, per-disease total budgets, resume, checksums, and preservation of existing files remain enforced. Reservation is intentionally conservative: it does not credit existing archives or extracted outputs toward required free quota. Confirm current free account space before every run, including any data acquired since the previous run. It is a preflight estimate, not an account-space lock against other writers.

For Hwang alone: 19.42 GiB + 45 GiB = 64.42 GiB footprint, with approximately 6.44 GiB headroom, or **70.86 GiB free required**. Recommend rounding up to **at least 75 GiB free Drive quota**, and preferably 80 GiB if other writes are ongoing; retain at least 2 GiB free on local `/content`. The confirmed 350 GiB is ample. Keep the user's 25 GiB download and 45 GiB unpacked limits: extraction must stop if actual unpacked content exceeds 45 GiB, even with more account quota. Reassess that limit from source inventory rather than automatically expanding it. Account GB and notebook GiB differ (1 GiB = 1,073,741,824 bytes); use the free amount, not the total account allocation.

## Exact rerun on the same connected Colab runtime

Open the updated `detection/notebooks/Acquire_Best_5_Disease_Datasets.ipynb` from `feature/acquire-five-disease-datasets`; merely rerunning an old saved notebook will retain the old helper.

Rerun these cells **in this order** (numbers refer to the updated 24-cell notebook):

1. Cell 13, `download-configuration`: select only Meningioma, source `hwang91`; restore `DRIVE_AVAILABLE_GIB = 350`, `MAX_DOWNLOAD_GIB_PER_DISEASE = 25`, `MAX_UNPACKED_GIB_PER_DISEASE = 45`. Preserve original `PROJECT_ROOT` and any reviewed-map path. All other disease switches remain False.
2. Cell 14, `dataset-catalog`.
3. Cell 15, `acquisition-engine` (loads corrected helpers into the live runtime).
4. Cell 19, `acquisition-preflight` (must pass again; inspect `storage_plan` in the private preflight report).
5. Cell 21, `execute-acquisition`, only after preflight passes. Existing verified archives are reused and different existing files remain protected; no deletion is required. Existing partial downloads follow the established validator-based resume rules.

On a fresh/disconnected runtime first run setup cells 4 (`configuration`, using the original project path), 6 (`runtime-check`), 8 (`dependency-setup`), 9 (`compatibility-check`), 11 (`drive-mount`), then the sequence above. The acquisition preflight retains the existing Colab/CUDA requirement; this storage fix performs no GPU preprocessing or training. Cell 17 (`cuda-acquisition-readiness`) is the optional existing GPU report. Do not run the ISLES revalidation cell for this Meningioma job.

No MRI files, IXI storage or segmentation code are changed by this fix. Synthetic storage tests reproduce the 63.44-versus-350 GiB mismatch and reject inadequate quota/local space, undeclared Drive-as-local staging, and aggregate archive/extraction overcommit.
