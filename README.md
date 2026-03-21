# fonts I like

## D2Coding + Nerd Fonts + Twemoji

D2Coding v1.3.2 (ligature variant) patched with Nerd Font icons and Twemoji COLRv0 color emoji. Korean (Hangul) stripped to keep the file size reasonable.

| File | Size | Use |
|------|------|-----|
| `D2Coding-ligature-NF-Twemoji-noKR.woff2` | 1.9 MB | Web (`@font-face`) |
| `D2Coding-ligature-NF-Twemoji-noKR.ttf` | 4.2 MB | Desktop / fallback |
| `D2CodingLigature.ttf` | 5.1 MB | Original (nerd fonts only, no emoji, tighter line spacing) |

### Web usage

```css
@font-face {
  font-family: 'D2Coding';
  src: url('/fonts/D2Coding-ligature-NF-Twemoji-noKR.woff2') format('woff2');
}
```

### Tools

- `merge_twemoji.py` — merges a Twemoji COLRv0 font into any TrueType font
- `emoji-test.py` — tests emoji coverage (supports .ttf, .otf, .woff2)

### Rebuild

```sh
# 1. Get a Twemoji COLRv0 font (e.g. from mozilla/twemoji-colr releases)
# 2. Merge into base font
python3 merge_twemoji.py base.ttf twemoji-colr.ttf output.ttf
# 3. Validate
python3 emoji-test.py output.ttf
```
