# Interrupted Hwang download: findings and safe rerun

## Evidence and limits

The observed 129-byte resume JSON with validator=null and total=20855300096 is not a download-completion marker. Without an archive or `.part` file there are no observable reusable payload bytes. The old downloader wrote resume metadata before opening the partial file. It read at most 4 MiB at once; it did **not** accumulate the 20 GB archive in RAM or stage it on local disk. However, `HTTPResponse.read(4 MiB)` could wait for that amount, there was no transfer progress, buffered file writes were not explicitly flushed/fsynced during transfer, and transport failures were not retried. Its single socket timeout was 90 seconds.

The exact disconnect cause is not established. Slow/stalled source reads, DriveFS open/write/cache stalls, delayed Drive visibility/sync, or runtime disconnection are hypotheses. Cloud has not inspected the private Drive or fetched the archive. Metadata with no partial could reflect stopping before the file opened or delayed/lost DriveFS visibility; it does not establish an HTTP buffering failure.

## Corrected behavior

- Bounded `read1` chunks (default 1 MiB; maximum 4 MiB) write unbuffered directly to the Drive `.part` path. No full-volume RAM buffer or local archive staging. File writes handle short writes. First chunk, every configured sync interval, and stream exit call fsync. This requests filesystem persistence; DriveFS remote durability/visibility cannot be guaranteed after abrupt runtime loss.
- Print before connection and at status changes, plus every 10 seconds **when reads are making progress**. Read timeout bounds a stalled network read (default 60s); connection timeout defaults to 30s. DriveFS operations themselves are outside socket timeout control. Checksum verification is explicitly announced and can take time without intermediate chunk messages.
- `.download_status.json` records bytes saved, bytes transferred this run, expected total, elapsed seconds, attempt, status and errors. It is a small replaced snapshot, never proof of checksum success. Resume metadata is separate. Progress is not a keep-alive guarantee for Colab.
- Up to two retries after the first attempt, with bounded backoff, for timeouts, disconnects, premature EOF and HTTP 408/429/500/502/503/504. Permanent HTTP errors, integrity failures, bad Range responses and filesystem failures are not retried. A nonempty partial without a validator stops with explicit resume-unavailable status.
- Resume requires a saved strong ETag or Last-Modified, matching URL/expected total, Range + If-Range, HTTP 206, matching Content-Range offset/end/total and any returned validator. HTTP 200 after a Range request stops and preserves the partial. Accept-Ranges alone is not evidence of safe resume. A server without validators cannot reliably resume under this policy; no automatic unsafe append or destructive restart is attempted.
- Orphan resume metadata with no partial is explicitly reported as stale and starts a fresh download. A partial with malformed/untrusted metadata is preserved and rejected. Existing verified archives are rechecked/reused; mismatches are preserved. Final size and publisher digest must pass before promotion to the final archive path and extraction.
- Confirmed Drive quota and separate actual `/content` space checks remain, along with shared extraction/download limits and headroom. No existing datasets are deleted. Source URLs, catalog checksums, ISLES audit logic, IXI and segmentation files are unchanged.

## Exact Colab rerun

Use the updated branch notebook `detection/notebooks/Acquire_Best_5_Disease_Datasets.ipynb`, not an older saved copy. Avoid two simultaneous notebook sessions writing the same download. Wait for Drive synchronization and check both the Colab downloads listing and Drive web interface before concluding no partial exists. Never rename metadata to an archive.

On a still-connected configured runtime rerun:

1. **Cell 13 `download-configuration`**: only Meningioma=True; source `hwang91`; other four disease switches=False. Retain original project location and map path. Keep current confirmed free Drive quota (350 GiB if still accurate), max download=25 GiB and max unpacked=45 GiB. New default options: connect=30s, read=60s, retries=2, chunk=1 MiB, progress=10s, sync=5s. These configurable options are passed explicitly to the Hwang acquisition.
2. **Cell 14 `dataset-catalog`** and **cell 15 `acquisition-engine`**, in order. This reloads the corrected embedded code; rerunning only preflight does not update live helpers.
3. **Cell 19 `acquisition-preflight`**. It must pass before transfers.
4. **Cell 21 `execute-acquisition`**. Watch connecting/streaming/byte counts. The orphan resume JSON needs no manual deletion; absent `.part` bytes cause a clearly reported fresh transfer. It never assumes metadata means complete. Keep the runtime connected and let Drive sync before closing.

For a fresh runtime first run setup cells **4, 6, 8, 9, 11**, preserving the original PROJECT_ROOT, then follow the sequence above. No ISLES revalidation cell is needed.

If an actual `.part` exists, let verified Range resume handle it. If the server lacks a validator, returns an incompatible Range, or changes identity, stop and inspect the status/error. Preserve the partial. An explicit fresh restart requires deciding where to retain that partial and updating free-space accounting for both copies; the notebook does not do this automatically. Do not delete datasets or increase budgets merely to suppress errors. If the connection fails again, preserve the status JSON and last printed exception for diagnosis. Size/checksum verification must finish before extraction; acquisition still does not authorize training.
