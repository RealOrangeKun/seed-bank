# Seed Bank — Graduation Deck

Two built decks generated from the content guide [`presentation.md`](./presentation.md),
so you can present from whichever fits the venue. Both share **one design system**:
environmental light theme (soft greens on warm-white), **Inter**, on-brand **Lucide**
icons (no emoji), a leaf watermark + slide number on every slide, and a diagram-focus
entrance animation per slide.

| | Slidev (`slidev/`) | Editable PPTX (`pptx/`) |
|---|---|---|
| Best for | presenting from your own laptop, in a browser | a shared/PowerPoint machine, or last-minute edits |
| Edit by | editing `slidev/slides.md` (Markdown) | opening `seed-bank.pptx` in PowerPoint / Canva |
| Animations | native (Vue `v-motion`) | injected auto-fade (verify playback in PowerPoint) |
| 39 logical slides | ✓ | ✓ |

## Run the Slidev deck

```bash
cd slidev
npm install
bash ../tools/sync_media.sh   # populate slidev/media/ from ../assets (one-time)
npm run dev        # → http://localhost:3030  (present here)
```

Export to PDF/PPTX needs a headless browser (one-time, needs network):

```bash
npx playwright install chromium
npm run export     # → slidev-exports/  (PDF; add --format pptx for PowerPoint)
```

## Build / open the PPTX deck

```bash
cd pptx
python3 -m venv .venv && .venv/bin/pip install python-pptx Pillow
.venv/bin/python build_pptx.py     # → seed-bank.pptx
```

Open `pptx/seed-bank.pptx` in PowerPoint or Canva. Animations are **auto-fade
entrances** injected as OOXML timing — they render in PowerPoint; **confirm playback
there** (LibreOffice ignores animation timing, so the `render/` previews are static).

## Assets (shared by both decks)

Generated into [`assets/`](./assets/) and mirrored into `slidev/media/`:

- **`assets/diagrams/`** — the curated C4 / architecture PDFs from
  `docs/report/figures/*.pdf`, rasterised at 200 dpi (`pdftoppm`).
- **`assets/screenshots/`, `assets/heatmaps/`, `assets/logos/`** — copied from the report.
- **`assets/icons/`** — 79 leaf-green Lucide PNGs from
  [`tools/gen_icons.sh`](./tools/gen_icons.sh) (edit + rerun to add icons).
- **`assets/fonts/`** — Inter TTFs (installed to `~/.fonts` so LibreOffice renders in Inter).

To regenerate all assets: rerun the `pdftoppm`/copy pipeline for diagrams+screenshots
and `bash tools/gen_icons.sh` for icons.

## Notes

- The deck keeps **one physical slide per logical slide** (39 total), so footer numbers
  and cross-references ("Slide 32", "Slide 33") stay aligned.
- Content is faithful to `presentation.md`; the decks render it, they don't restate it.
- No emoji anywhere — icons are Lucide (the same family the app UI uses, `lucide-react`).
