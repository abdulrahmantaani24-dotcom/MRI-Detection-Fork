"""Colab-only acquisition helpers. Importing this module never downloads data."""
from __future__ import annotations

import csv
import hashlib
import gzip
import json
import os
import re
import shutil
import stat
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath


def digest(path, algorithm="sha256"):
    h = hashlib.new(algorithm)
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024**2), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(value, indent=2) + "\n"
    if path.is_symlink():
        raise ValueError(f"Refusing metadata symlink: {path}")
    if path.exists():
        if path.read_text() == content:
            return
        # Retain prior provenance and failure reports on reruns.
        backup = path.with_name(path.name + f".previous.{time.time_ns()}")
        with path.open("rb") as source, backup.open("xb") as output:
            shutil.copyfileobj(source, output)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, prefix=path.name + ".", suffix=".tmp", delete=False) as stream:
        stream.write(content)
        tmp = Path(stream.name)
    tmp.replace(path)


def checked_path(root, relative):
    if Path(root).is_symlink():
        raise ValueError(f"Refusing destination directory symlink: {root}")
    root = Path(root).resolve()
    p = PurePosixPath(relative)
    if not p.parts or p.is_absolute() or ".." in p.parts or "\\" in relative or ":" in relative:
        raise ValueError(f"Unsafe archive/path member: {relative}")
    target = root.joinpath(*p.parts)
    if not target.resolve().is_relative_to(root):
        raise ValueError(f"Path escapes destination: {relative}")
    return target


def require_space(root, needed, reserve=2 * 1024**3):
    free = shutil.disk_usage(root).free
    if free < needed + reserve:
        raise OSError(f"Insufficient filesystem space: need {needed + reserve:,} bytes; free {free:,}")


def assert_colab_drive(root):
    try:
        import google.colab  # noqa: F401
    except ImportError as exc:
        raise RuntimeError("Dataset acquisition is allowed only in Google Colab.") from exc
    mount = Path("/content/drive/MyDrive")
    root = Path(root).resolve()
    if not mount.is_dir() or not root.is_relative_to(mount.resolve()):
        raise RuntimeError("Mount Drive and choose a destination inside /content/drive/MyDrive.")
    # Protect the entire existing IXI tree, not just its Healthy/T2 child.
    protected = Path("/content/drive/MyDrive/BrainMRI/datasets/IXI").resolve()
    if root == protected or root.is_relative_to(protected) or protected.is_relative_to(root):
        raise ValueError("Destination overlaps protected IXI storage.")
    return root


def _request(url, **kwargs):
    if not url.startswith("https://"):
        raise ValueError("Only verified HTTPS sources are allowed.")
    req = urllib.request.Request(url, headers={"User-Agent": "NeuroScope-Acquisition/1.0", "Accept-Encoding": "identity", **kwargs.pop("headers", {})}, **kwargs)
    response = urllib.request.urlopen(req, timeout=90)
    if not response.url.startswith("https://"):
        response.close()
        raise ValueError("Refusing a redirect that downgrades HTTPS.")
    return response


def probe_assets(spec):
    """HEAD only. A failed probe never launches a speculative payload transfer."""
    if not spec.get("eligible"):
        raise RuntimeError(spec["reason"])
    results = []
    for asset in spec["assets"]:
        with _request(asset["url"], method="HEAD") as response:
            if response.status != 200:
                raise RuntimeError(f"HEAD returned {response.status}")
            content_type = response.headers.get("Content-Type", "").lower()
            if any(t in content_type for t in ("text/html", "application/json")):
                raise RuntimeError("HEAD returned a login/error page")
            size = response.headers.get("Content-Length")
            if not size:
                raise RuntimeError("Source did not provide Content-Length; cannot preflight storage")
            size = int(size)
            if asset.get("bytes") is not None and asset["bytes"] != size:
                raise ValueError(f"Source size changed for {asset['path']}")
            asset["bytes"] = size
            results.append({"path": asset["path"], "bytes": size, "accept_ranges": response.headers.get("Accept-Ranges"), "final_url": response.url})
    return results


def record_oasis_integrity(part, ledger_path, asset):
    if not asset.get("bytes") or Path(part).stat().st_size != asset["bytes"]:
        raise ValueError("OASIS archive must match the official HEAD byte size")
    # Exhaust every gzip member to verify CRC32 and uncompressed-size trailers.
    with gzip.open(part, "rb") as stream:
        for _ in iter(lambda: stream.read(4 * 1024**2), b""):
            pass
    atomic_json(ledger_path, {"source_url": asset["url"], "bytes": asset["bytes"], "sha256": digest(part),
                             "gzip_crc32": "passed", "publisher_cryptographic_checksum": None,
                             "limitation": "Local SHA-256 is a repeat-use integrity baseline, not a publisher hash comparison"})


def download_verified(asset, root, *, max_bytes):
    """Resume only with a server validator and matching Content-Range; never trust ETag as MD5."""
    target = checked_path(root, asset["path"])
    checksum = asset.get("checksum")
    # This legacy publisher supplies no cryptographic digest. Keep this weaker,
    # explicit policy restricted to its two authenticated HTTPS archive URLs.
    legacy_oasis = asset.get("integrity_policy") == "https_size_gzip_crc32_local_sha256"
    if legacy_oasis and asset["url"] not in {
        "https://download.nrg.wustl.edu/data/OAS2_RAW_PART1.tar.gz",
        "https://download.nrg.wustl.edu/data/OAS2_RAW_PART2.tar.gz",
    }:
        raise ValueError("Legacy integrity policy is restricted to the two official OASIS-2 archives")
    if checksum:
        algorithm, expected = checksum.split(":", 1)
    elif legacy_oasis:
        algorithm, expected = "sha256", None
    else:
        raise ValueError("Missing publisher checksum; no explicit authorized alternative integrity policy")
    expected_size = asset.get("bytes")
    length = {"md5": 32, "sha256": 64}.get(algorithm)
    if length is None or (expected is not None and not re.fullmatch(r"[0-9a-f]{" + str(length) + r"}", expected)):
        raise ValueError("Missing/invalid publisher checksum")
    ledger_path = target.with_name(target.name + ".integrity.json")
    if target.exists():
        previous = json.loads(ledger_path.read_text()) if legacy_oasis and ledger_path.exists() else {}
        reference = expected or (previous.get("sha256") if previous.get("source_url") == asset["url"] else None)
        if reference and (expected_size is None or target.stat().st_size == expected_size) and digest(target, algorithm) == reference:
            return {"path": str(target), "sha256": digest(target), "status": "verified_existing"}
        raise FileExistsError(f"Existing file differs from publisher checksum; preserve and inspect: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_name(target.name + ".part")
    state_path = target.with_name(target.name + ".resume.json")
    if expected is not None and part.exists() and (expected_size is None or part.stat().st_size == expected_size) and digest(part, algorithm) == expected:
        part.replace(target)
        state_path.unlink(missing_ok=True)
        return {"path": str(target), "sha256": digest(target), "status": "verified_completed_partial"}
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    headers = {}
    offset = part.stat().st_size if part.exists() else 0
    if legacy_oasis and offset == expected_size and state.get("url") == asset["url"]:
        record_oasis_integrity(part, ledger_path, asset)
        part.replace(target)
        state_path.unlink(missing_ok=True)
        return {"path": str(target), "sha256": digest(target), "publisher_checksum": None,
                "integrity_policy": asset["integrity_policy"], "status": "verified_completed_partial"}
    validator = state.get("validator") if state.get("url") == asset["url"] else None
    if offset and validator:
        headers = {"Range": f"bytes={offset}-", "If-Range": validator}
    elif offset:
        raise RuntimeError(f"Partial file has no trusted resume validator; preserve it and inspect: {part}")
    with _request(asset["url"], headers=headers) as response:
        if response.status not in (200, 206):
            raise RuntimeError(f"Unexpected HTTP status {response.status}")
        if any(x in response.headers.get("Content-Type", "").lower() for x in ["text/html", "application/json"]):
            raise RuntimeError("Source returned a web page/API error instead of the MRI asset")
        if offset and response.status == 206:
            content_range = response.headers.get("Content-Range", "")
            match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", content_range)
            if not match or int(match[1]) != offset:
                raise RuntimeError("Server returned an invalid resume Content-Range")
            total = int(match[3])
            mode = "ab"
        else:
            if response.status == 206:
                raise RuntimeError("Unexpected partial response for a fresh download")
            # If-Range mismatch/server ignores Range: explicitly restart the partial file.
            offset = 0
            mode = "wb"
            total = int(response.headers["Content-Length"]) if response.headers.get("Content-Length") else None
        if expected_size is not None and total is not None and total != expected_size:
            raise ValueError(f"Publisher size differs: expected {expected_size}, server {total}")
        if total is not None and total > max_bytes:
            raise OSError("Asset exceeds the configured download budget")
        limit = expected_size or total or max_bytes
        if limit > max_bytes:
            raise OSError("Asset exceeds the configured download budget")
        require_space(root, max(0, limit - offset))
        etag = response.headers.get("ETag", "")
        validator = etag if etag and not etag.startswith("W/") else response.headers.get("Last-Modified")
        atomic_json(state_path, {"url": asset["url"], "validator": validator, "total": total})
        count = offset
        with part.open(mode) as stream:
            for chunk in iter(lambda: response.read(4 * 1024**2), b""):
                count += len(chunk)
                if count > limit:
                    raise OSError("Download exceeded expected size/budget")
                stream.write(chunk)
        for size in (total, expected_size):
            if size is not None and count != size:
                raise ValueError(f"Incomplete download: {count} != {size}")
    if expected is not None and digest(part, algorithm) != expected:
        raise ValueError(f"Publisher {algorithm} mismatch; file kept as .part for investigation")
    if legacy_oasis:
        record_oasis_integrity(part, ledger_path, asset)
    part.replace(target)
    state_path.unlink(missing_ok=True)
    return {"path": str(target), "bytes": count, "publisher_checksum": checksum, "sha256": digest(target),
            "integrity_policy": asset.get("integrity_policy", "publisher_checksum"), "status": "verified"}


def safe_extract(archive, destination, *, max_unpacked_bytes):
    """Preflight all members; reject links, devices, traversal, duplicates and archive bombs."""
    archive, destination = Path(archive), Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    if zipfile.is_zipfile(archive):
        container = zipfile.ZipFile(archive)
        members = container.infolist()
        records = []
        for m in members:
            mode = m.external_attr >> 16
            if (stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR)) or m.flag_bits & 1:
                container.close()
                raise ValueError("ZIP contains a link, special file or encrypted entry")
            records.append((m.filename, m.file_size, m.is_dir(), m))
        opener = container.open
    else:
        container = tarfile.open(archive, "r:*")
        records = []
        for m in container.getmembers():
            if not (m.isfile() or m.isdir()):
                container.close()
                raise ValueError("TAR contains a link or special file")
            records.append((m.name, m.size, m.isdir(), m))
        opener = container.extractfile
    try:
        total = 0
        seen = set()
        for name, size, is_dir, _ in records:
            if name.rstrip("/") in (".", "") and is_dir:
                continue
            target = checked_path(destination, name)
            key = str(target.resolve()).casefold()
            if key in seen:
                raise ValueError(f"Duplicate archive member: {name}")
            seen.add(key)
            total += size
            if total > max_unpacked_bytes:
                raise OSError("Archive exceeds extraction budget")
        require_space(destination, total)
        for name, size, is_dir, member in records:
            if name.rstrip("/") in (".", "") and is_dir:
                continue
            target = checked_path(destination, name)
            if is_dir:
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                # Rerun/resume extraction without blindly overwriting existing data.
                with opener(member) as source:
                    h = hashlib.sha256()
                    for chunk in iter(lambda: source.read(4 * 1024**2), b""):
                        h.update(chunk)
                if target.stat().st_size == size and digest(target) == h.hexdigest():
                    continue
                raise FileExistsError(f"Extraction would replace different existing data: {target}")
            partial = target.with_name(target.name + ".extracting")
            if partial.exists():
                raise FileExistsError(f"Previous interrupted extraction requires inspection: {partial}")
            with opener(member) as source, partial.open("xb") as output:
                shutil.copyfileobj(source, output, length=4 * 1024**2)
            if partial.stat().st_size != size:
                raise ValueError(f"Extracted size mismatch: {name}")
            partial.replace(target)
        return {"members": len(records), "unpacked_bytes": total}
    finally:
        container.close()


def load_patient_map(path):
    """Explicit reviewed file-to-patient mapping; never infer diagnosis from a mask."""
    required = {"relative_path", "patient_id", "diagnosis", "modality", "role", "visit_id"}
    allowed_diagnoses = {"meningioma", "brain_lesion_negative_lung_cancer", "AD_clinical_baseline", "control_stable", "converter_excluded"}
    rows = {}
    with Path(path).open(newline="") as stream:
        reader = csv.DictReader(stream)
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"Patient map must contain {sorted(required)}")
        for row in reader:
            relative = row["relative_path"]
            if relative in rows:
                raise ValueError(f"Duplicate patient-map path: {relative}")
            if any(not row[k].strip() for k in required):
                raise ValueError(f"Incomplete reviewed identity/label mapping: {relative}")
            if row["diagnosis"] not in allowed_diagnoses or row["role"] not in {"image", "mask"}:
                raise ValueError(f"Unrecognized source diagnosis/role: {relative}")
            rows[relative] = row
    return rows


def source_identity(relative, dataset_id, patient_map=None):
    """Interpret only publisher-documented conventions; unknown identity stays unknown."""
    path = PurePosixPath(relative)
    if dataset_id == "oasis2_legacy":
        match = re.search(r"OAS2_\d{4}", relative, re.I)
        visit = re.search(r"MR\d+", relative, re.I)
        if not match or not visit:
            raise ValueError("Cannot establish OASIS-2 patient and visit from documented identifiers")
        mapping = (patient_map or {}).get(relative)
        if mapping and (mapping["patient_id"] != match[0].upper() or mapping["diagnosis"] not in {"AD_clinical_baseline", "control_stable", "converter_excluded"}):
            raise ValueError("OASIS patient map must preserve source identity and use explicit clinical cohort groups")
        if mapping and (mapping["role"] != "image" or mapping["modality"] != "T1w"):
            raise ValueError("OASIS-2 source contains T1w images, not tumor masks or other sequences")
        return {"patient": match[0].upper(), "role": "image", "modalities": ["T1w"],
                "visit_id": visit[0].upper(), "diagnosis": mapping["diagnosis"] if mapping else None,
                "diagnosis_source": "OASIS-2 clinical cohort, doi:10.1162/jocn.2009.21407; reviewed clinical mapping required; never infer AD from missing data or generic CDR/MCI"}
    if dataset_id == "proteas_23171182":
        match = re.search(r"(?:^|/)(P\d{2}[ab]?)(?:/|_)", relative)
        if not match or not 1 <= int(match[1][1:3]) <= 40:
            raise ValueError("Cannot establish PROTEAS patient from the published P01-P40 layout")
        source_case = match[1]
        patient = source_case[:3]  # a/b are separate treatment courses, not new patients.
        visit_match = re.search(r"(?:^|[/_])(baseline|fu\d+)(?:[/_.]|$)", relative, re.I)
        visit = visit_match[1].lower() if visit_match else "unspecified"
        name = path.name.lower()
        if name in {"t1.nii.gz", "t2.nii.gz", "t1c.nii.gz", "fla.nii.gz"} and "brats" in {p.lower() for p in path.parts}:
            role = "image"
            modality = {"t1.nii.gz": "T1w", "t2.nii.gz": "T2w", "t1c.nii.gz": "T1ce", "fla.nii.gz": "FLAIR"}[name]
        elif "_tumor_mask_" in name:
            role, modality = "mask", "tumor_edema_necrosis"
        elif "_brain_mask" in name:
            role, modality = "ancillary", "brain_tissue_labels"
        elif name.endswith("_ct.nii.gz"):
            role, modality = "ancillary", "CT"
        elif name.endswith("_rtp.nii.gz"):
            role, modality = "ancillary", "radiotherapy_plan"
        else:
            raise ValueError(f"Undocumented PROTEAS NIfTI file; review rather than assume MRI: {relative}")
        return {"patient": patient, "source_case": source_case, "visit_id": visit,
                "role": role, "modalities": [modality], "diagnosis": "brain_metastasis",
                "diagnosis_source": "Flouri et al. confirmed-BM cohort, doi:10.1038/s41597-025-06131-0"}
    if dataset_id == "hwang_meningioma_5945963":
        mapping = (patient_map or {}).get(relative)
        if not mapping:
            return {"patient": None, "role": "unresolved", "modalities": ["unresolved"],
                    "diagnosis": None, "visit_id": None,
                    "diagnosis_source": "Explicit source identity/diagnosis map required; absence of a mask is not a control label"}
        if mapping["diagnosis"] not in {"meningioma", "brain_lesion_negative_lung_cancer"}:
            raise ValueError("Hwang cohort requires meningioma or its source-specific lesion-negative control label")
        return {"patient": mapping["patient_id"], "role": mapping["role"], "modalities": [mapping["modality"]],
                "diagnosis": mapping["diagnosis"], "visit_id": mapping["visit_id"],
                "diagnosis_source": "Reviewed source patient map; Hwang et al. doi:10.3390/jimaging8120327"}
    return None


def inspect_dataset(root, dataset_id, disease, patient_map=None):
    """CPU headers only; one file at a time, no full volume load or GPU preprocessing."""
    import nibabel as nib
    rows, errors = [], []
    for path in sorted(Path(root).rglob("*")):
        if any(p.startswith(".") or p == "__MACOSX" for p in path.relative_to(root).parts):
            continue
        if not path.is_file() or not path.name.endswith((".nii", ".nii.gz", ".img", ".img.gz")):
            continue
        relative = path.relative_to(root).as_posix()
        try:
            image = nib.load(path)
            if len(image.shape) < 3 or min(image.shape[:3]) < 2:
                raise ValueError(f"Not a 3D MRI/mask: {image.shape}")
            identity = source_identity(relative, dataset_id, patient_map)
            if identity is not None:
                patient, role, modality = identity["patient"], identity["role"], identity["modalities"]
            elif dataset_id == "msd_task01":
                match = re.search(r"BRATS_\d+", path.name)
                patient = match[0] if match else None
                modality = ["FLAIR", "T1w", "T1ce", "T2w"] if len(image.shape) == 4 else ["mask"]
                role = "mask" if "labelsTr" in path.parts else "image"
            elif dataset_id == "openneuro_ds007345":
                match = re.search(r"sub-olf\d{2}", relative)
                patient = match[0] if match else None  # 'fu' never becomes a new patient
                role = "mask" if "segmentation" in path.parts else "image"
                modality = ["mask" if role == "mask" else ("T2w" if "_T2w" in path.name else "T1w_contrast_unspecified")]
            else:
                match = re.search(r"sub-strokecase\d+", relative)
                patient = match[0] if match else None
                role = "mask" if "_msk" in path.name else "image"
                modality = [next((m for m in ["FLAIR", "ADC", "dwi"] if m.lower() in path.name.lower()), "mask" if role == "mask" else "unknown")]
            if not patient and dataset_id != "hwang_meningioma_5945963":
                raise ValueError("Cannot establish patient/case identity from the documented layout")
            zooms = [float(v) for v in image.header.get_zooms()[:3]]
            if any(not (0 < z < 100) for z in zooms):
                raise ValueError(f"Invalid voxel spacing: {zooms}")
            header = image.file_map.get("header")
            paired_header_hash = digest(header.filename) if header and header.filename else None
            rows.append({"dataset_id": dataset_id, "patient_id": f"{dataset_id}:{patient}" if patient else None, "case_id": patient,
                         "disease": disease, "role": role, "modalities": modality, "relative_path": relative,
                         "shape": list(image.shape), "spacing_mm": zooms, "dtype": str(image.get_data_dtype()),
                         "affine": image.affine.tolist(), "bytes": path.stat().st_size,
                         "paired_header_sha256": paired_header_hash,
                         "sha256": digest(path), "diagnosis_source": identity["diagnosis_source"] if identity else "dataset-level cohort; review clinical metadata before training",
                         "diagnosis": identity["diagnosis"] if identity else disease,
                         "visit_id": identity.get("visit_id") if identity else None,
                         "source_case": identity.get("source_case") if identity else None,
                         "split_group": f"{dataset_id}:{patient}" if patient else None, "split": "unassigned"})
        except Exception as exc:
            errors.append({"path": relative, "error": f"{type(exc).__name__}: {exc}"})
    if not rows:
        errors.append({"error": "No valid 3D NIfTI files found"})
    groups = {}
    for row in rows:
        if row["patient_id"] is None:
            continue
        g = groups.setdefault(row["patient_id"], {"patient_id": row["patient_id"], "diagnosis": row["diagnosis"], "images": [], "masks": [], "ancillary": [], "split": "unassigned"})
        if g["diagnosis"] != row["diagnosis"]:
            errors.append({"error": f"Conflicting diagnoses for {row['patient_id']}"})
        g[{"image": "images", "mask": "masks"}.get(row["role"], "ancillary")].append(row["relative_path"])
    if any(not g["images"] for g in groups.values()):
        errors.append({"error": "Mask-only patient/case group found"})
    hashes = {}
    for row in rows:
        if row["role"] == "image":
            hashes.setdefault(row["sha256"], set()).add(row["patient_id"])
    duplicates = [sorted(v) for v in hashes.values() if len(v) > 1]
    pending = [row["relative_path"] for row in rows if row["patient_id"] is None or row["diagnosis"] is None]
    return {"files": rows, "patients": list(groups.values()), "errors": errors,
            "pending_identity_files": pending, "mapping_required": bool(pending),
            "exact_duplicate_image_groups": duplicates, "patient_count": None if any(row["patient_id"] is None for row in rows) else len(groups),
            "count_note": "MSD IDs are case groups; independent clinical identity is not proven. No cross-release deduplication is claimed."}


def acquire_one(spec, destination, *, download_budget_bytes, extraction_budget_bytes, patient_map_path=None):
    root = assert_colab_drive(destination)
    if not spec.get("eligible"):
        raise RuntimeError(f"{spec['disease']}: acquisition disabled: {spec['reason']}")
    root.mkdir(parents=True, exist_ok=True)
    atomic_json(root / "source_and_license.json", spec)
    report = {"dataset_id": spec["id"], "status": "running", "assets": [], "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    try:
        known_total = sum(a.get("bytes") or 0 for a in spec["assets"])
        if known_total > download_budget_bytes:
            raise OSError("Selected assets exceed the total download budget")
        require_space(root, known_total)
        used = 0
        unpacked = 0
        for asset in spec["assets"]:
            result = download_verified(asset, root / "downloads", max_bytes=download_budget_bytes - used)
            report["assets"].append(result)
            used += Path(result["path"]).stat().st_size
            if asset.get("archive"):
                data_destination = checked_path(root / "data", asset["extract_subdir"]) if asset.get("extract_subdir") else root / "data"
                extraction = safe_extract(result["path"], data_destination, max_unpacked_bytes=extraction_budget_bytes - unpacked)
                unpacked += extraction["unpacked_bytes"]
                report.setdefault("extraction", []).append(extraction)
        data_root = root / ("data" if any(a.get("archive") for a in spec["assets"]) else "downloads")
        if spec["id"] == "msd_task01":
            descriptions = list(data_root.rglob("dataset.json"))
            if len(descriptions) != 1:
                raise ValueError("Expected one MSD dataset.json to confirm source license and modalities")
            description = json.loads(descriptions[0].read_text())
            license_text = str(description.get("licence", description.get("license", ""))).lower()
            if not ("cc-by-sa" in license_text or "by-sa/4.0" in license_text):
                raise ValueError(f"Unexpected MSD license declaration: {license_text!r}; review before reuse")
        if patient_map_path:
            assert_colab_drive(Path(patient_map_path).parent)
        patient_map = load_patient_map(patient_map_path) if patient_map_path else None
        manifest = inspect_dataset(data_root, spec["id"], spec["disease"], patient_map=patient_map)
        atomic_json(root / "file_manifest.json", manifest)
        atomic_json(root / "patient_manifest.json", manifest["patients"])
        if manifest["errors"]:
            raise ValueError("NIfTI/identity inspection failed; review file_manifest.json")
        expected = spec.get("expected_groups")
        if expected and manifest["patient_count"] is not None and manifest["patient_count"] != expected:
            raise ValueError(f"Expected {expected} patient/case groups; found {manifest['patient_count']}")
        if manifest["mapping_required"]:
            # No invented patient IDs or disease/control labels for undocumented filenames.
            template = root / "patient_map_template.csv"
            if not template.exists():
                with template.open("x", newline="") as stream:
                    writer = csv.DictWriter(stream, fieldnames=["relative_path", "patient_id", "diagnosis", "modality", "role", "visit_id"])
                    writer.writeheader()
                    for row in manifest["files"]:
                        if row["relative_path"] in manifest["pending_identity_files"]:
                            writer.writerow({"relative_path": row["relative_path"], "patient_id": row["case_id"] or "",
                                             "diagnosis": row["diagnosis"] or "", "modality": row["modalities"][0] if row["role"] != "unresolved" else "",
                                             "role": row["role"] if row["role"] != "unresolved" else "", "visit_id": row["visit_id"] or ""})
            report["status"] = "download_verified_inventory_pending_patient_map"
            report["patient_or_case_groups"] = manifest["patient_count"]
            report["mapping_template"] = str(template)
            report["limitation"] = "Identity and/or diagnostic-label review is incomplete. Review source identities, repeated visits and disease/control labels; fill a separate reviewed CSV and rerun. No training is authorized."
            return report
        expected = spec.get("expected_groups")
        if expected and manifest["patient_count"] != expected:
            raise ValueError(f"Expected {expected} patient/case groups; found {manifest['patient_count']}")
        for diagnosis, count in spec.get("expected_diagnosis_groups", {}).items():
            actual = sum(p["diagnosis"] == diagnosis for p in manifest["patients"])
            if actual != count:
                raise ValueError(f"Expected {count} independent groups for {diagnosis}; found {actual}")
        minimum_masks = spec.get("expected_min_masks", 0)
        if sum(row["role"] == "mask" for row in manifest["files"]) < minimum_masks:
            raise ValueError(f"Expected at least {minimum_masks} lesion masks")
        if manifest["errors"] or manifest["exact_duplicate_image_groups"]:
            raise ValueError("Manifest inspection failed; review file_manifest.json")
        report["status"] = "acquired_and_inspected_not_approved_for_training"
        report["patient_or_case_groups"] = manifest["patient_count"]
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        atomic_json(root / "acquisition_report.json", report)
    return report
