---
name: jd-read-html-bookshelf
description: Optimize JD Read exported ebook folders into polished local HTML document sites and maintain the output bookshelf homepage. Use when working in export_jd_read_py/output with book folders that contain index.html, index.json, index.txt, and Data/*.html, especially when the user asks to optimize a newly added book, follow the previous three-book workflow, fix ugly exported layouts, preserve chapter anchors, or add the book to the bookshelf index.
---

# JD Read HTML Bookshelf

## Goal

Turn each exported JD Read book folder into a readable, searchable, single-page document site, then add the book to `output/index.html` as a bookshelf card.

The source export usually looks like:

```text
output/<book-title>/
├── index.html
├── index.json
├── index.txt
└── Data/
    ├── cover.xhtml.html
    ├── copyright.xhtml.html
    ├── preface-*.xhtml.html
    └── Section*.xhtml.html or chapter*.html
```

## Workflow

1. Inspect `output/` and identify the newly added or target book folder.
2. Read `index.json` to understand chapter order, `level`, `chapter_item`, `chapter_name`, and `nav_point`.
3. Inspect representative source files in `Data/`, including cover/copyright/preface and one content chapter.
4. Generate or update the book folder's `index.html` as a single-page document site.
5. Update `output/index.html` with a bookshelf card, filter tags, book spine, metrics, and links.
6. Run static validation before replying.

Use `rg`, `jq`, `sed`, `find`, and small scripts for inspection. Use `apply_patch` for hand edits to existing files. Large generated HTML rewrites may be produced by a script when the transform is mechanical.

## Book Page Requirements

Build the optimized book `index.html` as a real document site, not an iframe wrapper.

Include:

- Sticky topbar with book title, bookshelf link, dark mode, and reader mode.
- Side navigation generated from every `index.json` row.
- Search over TOC and sections.
- Filters suited to the book, such as `基础`, `特效`, `案例`, `正文`, `资料`, or domain-specific groups.
- Hero with book-specific value proposition, cover image, author, publisher, and publish date when available.
- Stats from source data, such as core chapters,细分目录, image count, or case chapters.
- Chapter cards for `level == 0` core chapters.
- Full merged body content from every unique `chapter_item`, in original order.
- Responsive mobile behavior with a menu/drawer for the TOC.
- No fixed-height horizontal-reader remnants.

Avoid:

- `iframe`.
- `horizontal-read-container`.
- `height: 912px`.
- `user-scalable=no`.
- External JD CSS such as `storage.360buyimg.com/ebooks/*.css`.
- Duplicate IDs after merging chapters.
- Empty anchor placeholders such as `<a></a>`.
- Duplicate attributes such as `href="..." href="..."`.

## Content Merge Rules

Use `index.json` as the source of truth for order and anchors.

Build a unique ordered list of `chapter_item` values. For each file:

1. Read `Data/<chapter_item>`.
2. Extract the old reader body from `#horizontal-read-container` when present; otherwise extract `<body>`.
3. Remove old reader attributes and inline layout styles:
   - `isfree`
   - `style`
   - local image `href="./image/..."`
4. Prefix every `id` with the file stem to avoid collisions:
   - `sigil_toc_id_1` in `Section0001.xhtml.html` becomes `Section0001-sigil_toc_id_1`.
   - `TAGchapter40008` in `chapter4.html` becomes `chapter4-TAGchapter40008`.
5. Generate TOC links:
   - If `nav_point` exists, link to `#{stem(chapter_item)}-{nav_point}`.
   - Otherwise link to the section wrapper `#doc-{chapter_index}`.
6. Add `loading="lazy"` and `decoding="async"` to images when missing.
7. Preserve remote image `src` URLs unless the user asks to localize assets.
8. Convert useful bold classes to a local style class if needed.

For `data-original-href`, do not blindly convert it when an `href` already exists. After generation, check for duplicate `href` attributes.

## Book-Specific Design

Tailor the copy and filters to the book. Do not reuse Seedance wording for a剪映/文案/other book.

Examples:

- Seedance quick-start book: emphasize AI video prompts, scenes, editing, monetization.
- Seedance director-practice book: emphasize director workflow, character consistency, camera motion, local edits, audio-video sync.
- 文案 book: emphasize titles, social media, ecommerce, brand stories, proposals.
- 剪映专业版 book: emphasize desktop editing workflow, audio, transitions, effects, subtitles, color, and practical short-video cases.

Choose a restrained multi-color palette. Avoid a one-note single-hue page. Keep cards at `8px` radius or less unless the existing page already uses another radius.

## Bookshelf Update

Update `output/index.html` after the book page is generated.

Checklist:

- Increase book count in title/subtitle/hero copy.
- Add or adjust filter buttons only when useful, such as `剪辑` for editing books.
- Add one shelf spine if the hero has a shelf visual.
- Add one `.book-card` with:
  - Cover image.
  - Short title and author.
  - One-paragraph positioning.
  - Tags.
  - Metrics from `index.json` and metadata.
  - Main link to `./<book-title>/index.html`.
  - Raw link to a stable source page, usually `./<book-title>/Data/cover.xhtml.html` or `Data/chapter00.html`.
- Set `data-type` and `data-title` so filtering and search work.
- Check responsive grid after adding the new card. Prefer `repeat(auto-fit, minmax(330px, 1fr))` for a growing shelf.

## Inspection Commands

Use these shapes and adapt paths:

```bash
find output -maxdepth 2 -name index.json -print
jq -r '.[] | [.chapter_index,.level,.chapter_item,.chapter_name,.nav_point] | @tsv' 'output/<book>/index.json' | sed -n '1,220p'
find 'output/<book>/Data' -maxdepth 1 -type f | sort
sed -n '1,220p' 'output/<book>/Data/cover.xhtml.html'
sed -n '1,260p' 'output/<book>/Data/Section0001.xhtml.html'
rg -o 'id="[^"]+"|src="[^"]+"|<h[123][^>]*>[^<]+' 'output/<book>/Data' | sed -n '1,180p'
```

## Validation

Run validation every time before final response.

HTML parser and JS syntax:

```bash
python3 - <<'PY'
from html.parser import HTMLParser
from pathlib import Path
for p in [Path('output/index.html'), Path('output/<book>/index.html')]:
    s = p.read_text(encoding='utf-8')
    HTMLParser().feed(s)
    print(p, 'html_ok', len(s))
PY

python3 - <<'PY'
from pathlib import Path
import re, subprocess, tempfile
for p in [Path('output/index.html'), Path('output/<book>/index.html')]:
    s = p.read_text(encoding='utf-8')
    for i, code in enumerate(re.findall(r'<script>(.*?)</script>', s, flags=re.S), 1):
        tmp = Path(tempfile.gettempdir()) / f'check_{p.parent.name}_{i}.js'
        tmp.write_text(code, encoding='utf-8')
        r = subprocess.run(['node', '--check', str(tmp)], text=True, capture_output=True)
        print(p, 'script', i, 'node_check', r.returncode)
        if r.returncode:
            print(r.stderr or r.stdout)
PY
```

Anchor and bookshelf link checks:

```bash
python3 - <<'PY'
from pathlib import Path
import re
p = Path('output/<book>/index.html')
s = p.read_text(encoding='utf-8')
hrefs = set(re.findall(r'href="#([^"]+)"', s))
ids = set(re.findall(r'id="([^"]+)"', s))
ignore = {'top', 'chapter-index'}
missing = sorted(h for h in hrefs if h not in ids and h not in ignore and not h.startswith('${'))
print('book_hash_hrefs', len(hrefs), 'ids', len(ids), 'missing', len(missing))
if missing:
    print('\n'.join(missing[:40]))

idx = Path('output/index.html')
text = idx.read_text(encoding='utf-8')
local_hrefs = re.findall(r'href="(\./[^"]+|\.\./[^"]+)"', text)
bad = []
for h in local_hrefs:
    if not (idx.parent / h).resolve().exists():
        bad.append(h)
print('shelf_local_hrefs', len(local_hrefs), 'missing', len(bad))
if bad:
    print('\n'.join(bad))
PY
```

Forbidden remnants:

```bash
rg -n 'iframe|horizontal-read-container|height: 912px|user-scalable=no|storage.360buyimg.com/ebooks|<a></a>|data-original-href|href="[^"]+" href="' 'output/<book>/index.html' 'output/index.html' || true
```

The expected result is:

- HTML parser succeeds.
- `node --check` returns `0`.
- Anchor missing count is `0`.
- Bookshelf local-link missing count is `0`.
- Forbidden-remnant search returns no output.

## Final Response

Reply in Chinese. Include:

- The optimized book page path.
- The bookshelf homepage path.
- A compact verification summary.
- Any known limitation, such as not running a live browser screenshot if browser access to `file://` is blocked.
