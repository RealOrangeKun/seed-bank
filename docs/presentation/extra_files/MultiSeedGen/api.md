# Web API reference

The FastAPI backend (`multiseedgen/web/app.py`) is a **thin, sandboxed wrapper over the same
CLI/pipeline**: it launches `python -m multiseedgen --config <json>` as a subprocess and streams
its log. This is the **internal contract for the bundled SPA**, not a stable public API — it has
intentionally **no auth, CORS, or rate-limiting** and is meant for a single local user. Don't
expose it to an untrusted network.

Request bodies are the Pydantic models in `multiseedgen/web/schemas.py`; the `config` field is a
free dict that round-trips to the CLI (the single source of truth for validating individual keys).

## Sandbox

Every path parameter (`path`, `out`, `dest`, `root`) is resolved and required to live at or under
an **allowed base**, else the route returns **403**. The allowed bases are:

- the **project root**,
- **`MULTISEEDGEN_DATA_ROOT`** (falls back to the project root if unset or not a directory),
- the **system temp dir**.

Dotfiles/dotdirs (e.g. `.seg_cache`) are hidden from listings and excluded from downloads.

## Schema & config

| Method | Path | Params | Returns |
|--------|------|--------|---------|
| `GET` | `/api/schema` | — | The form descriptor from `services.build_schema()` plus `data_root` and `project_root`. Drives the web form; its shape is pinned by `tests/golden/api_schema.json`. |
| `GET` | `/api/config/load` | `?path=` | The flat config dict from a YAML/JSON file (keys validated, `format`→`fmt` mapped). `400` on a `ConfigError`. |
| `POST` | `/api/config/save` | body `{path, config}` | Writes `{config: …}` as YAML (`.yaml`/`.yml`) or JSON. `400` if YAML is requested but PyYAML isn't installed. Returns `{saved, format}`. |

## Runs (subprocess + live log)

| Method | Path | Params | Returns |
|--------|------|--------|---------|
| `POST` | `/api/runs` | body `{config}` (`StartRunRequest`) | Launches a generation subprocess. `{run_id, out}`. `400` if `sources`/`out` are missing. |
| `GET` | `/api/runs` | — | `{runs: [{id, status, out, returncode}]}` (retains up to 40 runs; oldest finished are evicted). |
| `GET` | `/api/runs/{rid}` | — | `{id, status, returncode, out, log}` (last 400 lines). `404` if unknown. |
| `POST` | `/api/runs/{rid}/stop` | — | Signals the whole process group `SIGTERM`, escalating to `SIGKILL` after 5 s. `{stopped}` (or `{stopped, already_exited}`). `404` if unknown. |
| `WS` | `/ws/runs/{rid}` | — | Replays the backlog, then streams `{type:"line", line}` messages and finally `{type:"done", returncode, status}`. `{type:"error"}` for an unknown run id. |

`status` is one of `running` / `done` / `error`.

## Segmentation tuner

| Method | Path | Params | Returns |
|--------|------|--------|---------|
| `POST` | `/api/seg/check` | body `{config, n=24, out?}` (`SegCheckRequest`) | Starts a tracked, **stoppable** segmentation check — a tuner run that produces no dataset (`num_images=0`, `check_seeds=n`, `scan_limit=n`, so report counts and gallery both reflect exactly `n`). Returns `{run_id, out}`. Progress streams over `/ws/runs/{run_id}`; cancel via `/api/runs/{run_id}/stop`. |
| `GET` | `/api/seg/result` | `?out=` | The finished/stopped check's report + per-seed manifest: `{report, out, seeds: [{url, source, status, confidence, method, reason}]}`. Tolerates a missing/corrupt report or manifest by falling back to a glob of the rendered cut-outs. |

`seeds[].status` distinguishes **kept** vs **skipped** cut-outs, and `confidence`/`reason` back the
tuner's kept/skipped gallery.

## Dataset browser

| Method | Path | Params | Returns |
|--------|------|--------|---------|
| `GET` | `/api/datasets` | `?root=` | `{root, datasets:[paths]}`. Bounded directory walk (depth ≤ 6, cap 200) — a dataset is a dir with `data.yaml`, `annotations_*.json`, or `train/images`. |
| `GET` | `/api/datasets/info` | `?path=` | `{path, splits:{train,val counts}, classes, qa:[image urls], seg_report, run_config?}`. |
| `GET` | `/api/datasets/image` | `?path=&split=train&idx=0` | A PNG of the image with boxes/polygons drawn from the **exported** labels on disk (same read-back as `qa.make_previews`). Headers `X-Total` (image count) and `X-Name`. |
| `GET` | `/api/datasets/download` | `?path=&split=?` | Streams the dataset (or one split) as a `.zip`. `split` must be `train`/`val` if given. |

## Filesystem picker & seed upload

| Method | Path | Params | Returns |
|--------|------|--------|---------|
| `GET` | `/api/fs/list` | `?path=&kind=dir` | Sandboxed directory listing for the path picker: `{path, parent, entries:[{name, path, is_dir}], data_root}`. `kind=dir` shows folders only; `kind=file` also lists files (for `segment_map`/`sam_checkpoint`). `parent` is `null` at a sandbox boundary so the UI can't navigate above it. |
| `GET` | `/api/file` | `?path=` | Serves a single sandboxed file with content-type sniffing (png/jpg/json/txt/yaml/md). Backs the gallery and QA image URLs. |
| `POST` | `/api/seeds/upload` | multipart: `dest` (Form), `files` (File[]) | Saves uploaded seed images into a sandboxed folder usable as `sources`. **All-or-nothing**: the whole batch is validated (extension in png/jpg/jpeg, ≤ 25 MB each, must actually decode via OpenCV) **before any file is written**, so a single bad file can't leave a half-written upload. Returns `{saved_dir, files, count}` (`UploadResponse`). |

> There are two ways to point `sources` at seeds: **upload** local files (above), or **browse an
> existing server folder** with the picker (`/api/fs/list`) and set `sources` directly — no upload.

## Static SPA

`GET /` serves the built `index.html`; the bundle is mounted at `/static`.

---

This page is derived from `multiseedgen/web/app.py` and `multiseedgen/web/schemas.py` — treat those
as authoritative if they ever diverge from this table.
