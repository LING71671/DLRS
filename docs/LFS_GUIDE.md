# Git LFS in DLRS

> Audience: contributors and self-hosters of the DLRS reference repository.
>
> Status: **defensive** layer only. Pointer files (`.pointer.json`) referencing object
> storage are the **primary** mechanism for handling large media in DLRS. Git LFS
> exists so that an accidentally committed binary is routed to LFS instead of
> bloating the pack file.

## 1. Why both pointers *and* LFS?

DLRS is pointer-first by design (see `docs/OBJECT_STORAGE_POINTERS.md`). Original
audio, video, image, and 3D assets MUST live in regional object storage, with the
repository only holding a `.pointer.json` plus checksums. That keeps the
repository:

- small enough to clone in seconds
- safe to mirror across regions without unintentional cross-border data transfer
- compatible with subject-data-erasure: deleting a pointer does not strand bytes
  inside Git history

Despite that, contributors sometimes commit a binary by mistake (a sample frame
exported from a notebook, a screenshot, a test recording). The role of `.gitattributes`
+ Git LFS is to:

1. divert those bytes to an LFS server instead of the pack file (so `git push` does
   not balloon), and
2. make the mistake **visible** in the diff (the worktree shows an LFS pointer text
   blob, not the binary), so reviewers can ask the contributor to move it to object
   storage and replace it with a `.pointer.json`.

CI (`tools/check_sensitive_files.py` and `validate_media.py`) remains the primary
gate. Git LFS is the secondary gate.

## 2. What's tracked

`.gitattributes` at the repository root marks the following extensions as LFS:

| Category | Extensions |
|---|---|
| Audio | `.wav` `.flac` `.mp3` `.ogg` `.m4a` `.aac` `.opus` |
| Video | `.mp4` `.mov` `.mkv` `.webm` `.avi` |
| Raw images | `.tif` `.tiff` `.dng` `.cr2` `.arw` `.nef` `.exr` `.hdr` `.psd` |
| 3D assets | `.vrm` `.glb` `.gltf` `.fbx` `.obj` `.usd` `.usdz` `.usda` `.usdc` `.blend` |
| Model weights | `.bin` `.safetensors` `.onnx` `.pt` `.pth` `.ckpt` `.gguf` |
| Archives | `.zip` `.tar` `.tar.gz` `.7z` |

> Small `.png` / `.jpg` previews (e.g. in `humans/_TEMPLATE/artifacts/samples/`) are
> intentionally *not* tracked by LFS, because they are small enough to live as plain
> blobs without bloating history. If you find yourself wanting to commit a `.png`
> larger than ~512 KiB, treat it as a real artifact and route it through a pointer.

## 3. Setting up LFS locally

```bash
# Install once per machine (macOS via brew, Debian/Ubuntu via apt, see https://git-lfs.com/)
git lfs install

# After cloning, fetch any LFS-managed blobs the maintainers approved
git lfs pull
```

Most contributors do **not** need to push LFS blobs: in DLRS you should be uploading
to object storage and committing a `.pointer.json` instead.

## 4. Migrating an accidentally committed binary

If you committed a `*.mp4` or similar in error and want to clean it up before merge:

```bash
# 1. Move the bytes out of the repo entirely. Upload to your object storage.
python tools/upload_to_storage.py \
    --source ./bad_commit.mp4 \
    --target s3://your-bucket/key/bad_commit.mp4 \
    --artifact-type video \
    --out humans/<region>/<record>/artifacts/raw_pointers/video/bad_commit.pointer.json

# 2. Remove the file from the working tree and re-commit.
git rm bad_commit.mp4
git commit -m "Replace raw binary with object storage pointer"

# 3. (Optional) If the binary is already in repository history and you have
#    permission to rewrite it, use `git filter-repo` or BFG. Coordinate with
#    maintainers because force-pushing requires a release.
```

If a binary slipped into a long-lived branch that has already been pushed publicly,
do **not** rewrite history without consensus. Instead, file an `.github/ISSUE_TEMPLATE/takedown-request.yml`
issue and let maintainers decide whether to redact via `git filter-repo` and reissue
release tags.

## 5. CI behaviour

- `.github/workflows/validate.yml` runs `tools/check_sensitive_files.py` first;
  the workflow fails immediately if a disallowed binary appears in the working
  tree, regardless of whether LFS captured it.
- The job does **not** require LFS bandwidth: validators only inspect text and
  pointer files. Forks and contributor PRs without LFS access will still pass CI
  for normal pointer-only changes.
