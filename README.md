# fonts I like

## Clanker Mono: D2Coding + Nerd Fonts + Twemoji

Clanker Mono is [D2Coding](https://github.com/naver/d2-coding-font) 1.4.0, NAVER's monospaced Korean and Latin coding font with ligatures. D2Coding's license reserves the name "D2Coding", so these modified builds are renamed. They carry D2Coding 1.4.0's credits and version.

### What Clanker Mono changes in D2Coding

- Tighter line spacing in Regular and Bold: the line gap in the `hhea` table is removed, which takes the line height that browsers and macOS apps use from 1.16 em to 1.08 em. Windows line height and every glyph advance are unchanged.
- Nerd Fonts icons (NF and Emoji builds): the 10,400 glyphs of [Nerd Fonts](https://www.nerdfonts.com/) 3.5.1 for the codepoints D2Coding does not map, so icons work without a separate symbols font.
- Color emoji (Emoji build): [Twemoji](https://github.com/jdecked/twemoji) 17.0.3 as a COLRv0 font merged in. Hangul syllables are removed from this build to keep it small.
- A website subset and a chart subset, which are small files cut from the base Regular build.

Everything else is D2Coding as released: the outlines, glyph widths, hinting, coding ligatures and Hangul are not redrawn or edited. A rebuild is checked against the upstream fonts to show that.

| File | Family | Size | Use |
|------|--------|------|-----|
| `ClankerMono-Regular.ttf` | Clanker Mono | 4.1 MB | Base build with Hangul, without icons or emoji |
| `ClankerMono-Bold.ttf` | Clanker Mono | 4.4 MB | Bold of the base build |
| `ClankerMono-web.woff2` | Clanker Mono | 91 KB | Website subset without Hangul, Nerd Fonts private-use glyphs, or emoji |
| `ClankerMono-Emoji.woff2` | Clanker Mono Emoji | 2.5 MB | Web (`@font-face`) |
| `ClankerMono-Emoji.ttf` | Clanker Mono Emoji | 5.9 MB | Desktop / fallback |
| `ClankerMono-NF.ttf` | Clanker Mono NF | 6.1 MB | Regular with Nerd Fonts icons and Hangul, no emoji |
| `ClankerTwemoji.ttf` | Clanker Twemoji | 1.8 MB | Color emoji font alone, for desktop use |
| `ClankerTwemoji.woff2` | Clanker Twemoji | 0.6 MB | Color emoji font alone, for the web |

Clanker Twemoji is the Twemoji 17.0.3 graphics as a COLRv0 font, with every emoji one em wide, and it is what the Emoji build merges. It supports 100% of the fully qualified sequences of Emoji 15.0 and 99.5% of those in the current Unicode list; Twemoji 17 has no artwork for the 19 added since. Twemoji draws every family sequence with one generic family icon.

The Nerd Fonts icons are from Nerd Fonts 3.5.1, whose Material Design icons sit at U+F0001 to U+F1AF0. The earlier builds had the 2.3.0-RC icons, where those icons were at U+F500 to U+FD46, and that range is no longer mapped. D2Coding's own glyphs are kept wherever the patcher overwrote them, such as the Powerline symbols.

### Dotted zero

The zero is slashed by default. Turning on the `cv01` OpenType feature, also registered as `ss01`, selects D2Coding's dotted zero, for example with `font-feature-settings: 'cv01' 1;` in CSS.

### Web usage

```css
@font-face {
  font-family: 'Clanker Mono';
  src: url('/ClankerMono-web.woff2') format('woff2');
}
```

`ClankerMono-web.woff2` is built from `ClankerMono-Regular.ttf`, so it has the same tighter vertical metrics. It covers Latin, Greek, punctuation, currency, arrows, mathematical operators, box drawing, and common technical symbols. The website uses the browser's fallback fonts for emoji.

### Tools

- `patch_nerd_fonts.sh` - patches D2Coding Regular with the Nerd Fonts icons; `build_fonts.py` takes the icon glyphs from its output
- `build_fonts.py` - builds the base, NF, and Emoji fonts from D2Coding's ligature Regular and Bold releases
- `rename_font.py` - renames a modified D2Coding build and gives it the family, style, version, and description records, keeping the credits and license records of the font it came from
- `build_chart_font.sh` - builds `ClankerMono.ttf`, a 101 KB TTF for matplotlib charts from `ClankerMono-Regular.ttf`, covering Latin-1, punctuation, currency, arrows, and math, since matplotlib cannot read WOFF2
- `build_twemoji.py` - builds the Clanker Twemoji fonts from the SVG graphics of a Twemoji release with [nanoemoji](https://github.com/googlefonts/nanoemoji)
- `merge_twemoji.py` - merges a Twemoji COLRv0 font into any TrueType font
- `emoji-test.py` - tests emoji coverage (supports .ttf, .otf, .woff2)
- `font-density.py` - measures information density of all fonts in [programmingfonts](https://github.com/braver/programmingfonts)
- `audit_d2coding_hints.py` - scans every Unicode glyph for an isolated baseline lift associated with a missing TrueType delta and writes a self-contained HTML specimen report

### Rebuild

```sh
# Build the Twemoji font from the SVG graphics of a Twemoji release (jdecked/twemoji 17.0.3)
uv run --with fonttools --with brotli --with nanoemoji python build_twemoji.py \
  --svg twemoji/assets/svg --emoji-test emoji-test.txt

# Patch D2Coding Regular with the icons of a Nerd Fonts release (FontPatcher.zip, unpacked),
# then build the other fonts. The ligature fonts are in the D2Coding release archive
./patch_nerd_fonts.sh FontPatcher D2Codingligature-Regular.ttf patched
uv run --with fonttools --with brotli python build_fonts.py \
  --regular D2Codingligature-Regular.ttf --bold D2Codingligature-Bold.ttf \
  --icons patched/D2KodingLigatureNerdFont-Regular.ttf --twemoji ClankerTwemoji.ttf

# Website and chart subsets
./build_web_font.sh
./build_chart_font.sh

# Validate emoji coverage
python3 emoji-test.py ClankerMono-Emoji.ttf

# Audit a font and create a screenshot-ready report
uv run --with fonttools --with freetype-py python audit_d2coding_hints.py FONT.ttf --output hint-audit.html
```

## Information density (chars per 1000×1000px at 16px, 1.4 line spacing)

Higher = more code on screen. **Bold** = fonts I use.

| # | Font | Width | Height | Density |
|---|------|-------|--------|---------|
| 1 | Proggy Clean | 7.0px | 18.6px | 7,665 |
| 2 | Effects Eighty | 7.2px | 18.1px | 7,664 |
| 3 | VT323 | 6.6px | 22.4px | 6,718 |
| 4 | Sudo | 7.0px | 22.4px | 6,377 |
| 5 | Scientifica | 7.3px | 22.4px | 6,138 |
| 6 | Bront Ubuntu Mono | 8.0px | 22.4px | 5,580 |
| 7 | Fairfax | 8.0px | 22.4px | 5,580 |
| 8 | Fairfax HD | 8.0px | 22.4px | 5,580 |
| 9 | Fairfax Hax HD | 8.0px | 22.4px | 5,580 |
| 10 | Fairfax Serif | 8.0px | 22.4px | 5,580 |
| 11 | Fixedsys with Ligatures | 8.0px | 22.4px | 5,580 |
| 12 | Lekton | 8.0px | 22.4px | 5,580 |
| 13 | Nanum Gothic Coding | 8.0px | 22.4px | 5,580 |
| 14 | Spleen | 8.0px | 22.4px | 5,580 |
| 15 | Ubuntu Mono | 8.0px | 22.4px | 5,580 |
| 16 | GNU Unifont | 8.0px | 22.4px | 5,580 |
| 17 | UnifontEX | 8.0px | 22.4px | 5,580 |
| 18 | Inconsolata OTF | 8.0px | 22.6px | 5,525 |
| 19 | Comic Shanns | 8.2px | 22.4px | 5,470 |
| 20 | Monofur | 8.0px | 22.9px | 5,462 |
| 21 | Fifteen | 6.0px | 30.8px | 5,411 |
| 22 | Quinze | 6.0px | 30.8px | 5,411 |
| 23 | Terminus (TTF) | 8.0px | 23.1px | 5,407 |
| 24 | Envy Code B | 8.6px | 21.8px | 5,348 |
| 25 | Inconsolata | 8.0px | 23.5px | 5,319 |
| 26 | InconsolataGo | 8.0px | 23.5px | 5,319 |
| 27 | Fantasque Sans Mono | 8.3px | 22.9px | 5,262 |
| 28 | **D2Coding** | **8.0px** | **24.2px** | **5,166** |
| 29 | 3270 | 8.6px | 22.4px | 5,166 |
| 30 | Cozette | 8.0px | 24.3px | 5,152 |
| 31 | Gohufont 11 | 8.7px | 22.4px | 5,115 |
| 32 | Anonymous Pro | 8.7px | 22.4px | 5,111 |
| 33 | AudioLink Mono | 9.2px | 21.3px | 5,107 |
| 34 | Code New Roman | 8.8px | 22.4px | 5,074 |
| 35 | Computer Modern Unicode Typewriter | 8.4px | 23.7px | 5,013 |
| 36 | IBM VGA 9x16 | 9.0px | 22.4px | 4,960 |
| 37 | Eirian | 8.0px | 25.5px | 4,919 |
| 38 | Gohufont 14 | 9.1px | 22.4px | 4,884 |
| 39 | Agave | 8.0px | 25.9px | 4,826 |
| 40 | Iosevka | 8.0px | 26.4px | 4,729 |
| 41 | Bedstead | 9.6px | 22.4px | 4,650 |
| 42 | DPSDbeyond | 9.6px | 22.4px | 4,650 |
| 43 | Nimbus Mono | 9.6px | 22.4px | 4,650 |
| 44 | Old Timey Code | 9.6px | 22.4px | 4,650 |
| 45 | APL2741 | 9.6px | 22.6px | 4,631 |
| 46 | Courier Prime | 9.6px | 22.6px | 4,617 |
| 47 | Courier Prime Code | 9.6px | 22.6px | 4,617 |
| 48 | Courier Prime Sans | 9.6px | 22.6px | 4,617 |
| 49 | Serious Shanns | 8.7px | 24.9px | 4,616 |
| 50 | Atkinson Hyperlegible Mono | 10.1px | 21.4px | 4,613 |
| 51 | Fixedsys | 8.8px | 24.7px | 4,607 |
| 52 | Comic Mono | 8.7px | 24.9px | 4,599 |
| 53 | Share Tech Mono | 8.6px | 25.2px | 4,584 |
| 54 | Myna | 7.8px | 28.2px | 4,567 |
| 55 | GNU Freefont | 9.6px | 22.8px | 4,564 |
| 56 | DaddyTimeMono | 9.2px | 23.9px | 4,552 |
| 57 | M PLUS Code | 8.0px | 27.7px | 4,518 |
| 58 | Aporetic Sans Mono | 8.4px | 26.4px | 4,503 |
| 59 | Aporetic Serif Mono | 8.4px | 26.4px | 4,503 |
| 60 | Monaspace Argon | 9.9px | 22.4px | 4,500 |
| 61 | Monaspace Krypton | 9.9px | 22.4px | 4,500 |
| 62 | Monaspace Neon | 9.9px | 22.4px | 4,500 |
| 63 | Monaspace Radon | 9.9px | 22.4px | 4,500 |
| 64 | Monaspace Xenon | 9.9px | 22.4px | 4,500 |
| 65 | Envy Code R | 8.6px | 25.9px | 4,489 |
| 66 | Mononoki | 9.0px | 25.2px | 4,424 |
| 67 | Lotion | 8.5px | 26.9px | 4,387 |
| 68 | Average Mono | 9.7px | 23.7px | 4,369 |
| 69 | Commit Mono | 9.6px | 24.6px | 4,227 |
| 70 | BigBlue Terminal | 10.7px | 22.4px | 4,185 |
| 71 | Cutive Mono | 9.7px | 24.7px | 4,185 |
| 72 | BPmono | 9.6px | 24.9px | 4,178 |
| 73 | Victor Mono | 8.7px | 27.5px | 4,168 |
| 74 | PT Mono | 9.6px | 25.1px | 4,152 |
| 75 | Monofoki | 9.0px | 26.9px | 4,136 |
| 76 | Lyth Mono | 9.7px | 25.1px | 4,124 |
| 77 | IBM Courier | 9.6px | 25.3px | 4,118 |
| 78 | IBM Courier (dot) | 9.6px | 25.3px | 4,118 |
| 79 | IBM Courier (slash) | 9.6px | 25.3px | 4,118 |
| 80 | Cousine | 9.6px | 25.4px | 4,104 |
| 81 | Cascadia Code | 9.4px | 26.0px | 4,097 |
| 82 | Ioskeley Mono | 9.6px | 25.4px | 4,097 |
| 83 | Luculent | 8.8px | 28.0px | 4,081 |
| 84 | Geist | 9.6px | 25.5px | 4,079 |
| 85 | APL385 | 9.6px | 25.6px | 4,075 |
| 86 | Liberation Mono | 9.6px | 25.8px | 4,034 |
| 87 | Go Mono | 9.6px | 25.9px | 4,022 |
| 88 | Borg Sans Mono | 9.6px | 26.1px | 3,994 |
| 89 | SK Modernist Mono | 10.0px | 25.1px | 3,982 |
| 90 | Bront DejaVu Sans Mono | 9.6px | 26.1px | 3,981 |
| 91 | DejaVu Markup | 9.6px | 26.1px | 3,981 |
| 92 | Hack | 9.6px | 26.1px | 3,981 |
| 93 | Hack Ligatured | 9.6px | 26.1px | 3,981 |
| 94 | Mensch | 9.6px | 26.1px | 3,981 |
| 95 | Inconsolata-g | 9.6px | 26.3px | 3,967 |
| 96 | Heterodox Mono | 9.1px | 27.9px | 3,956 |
| 97 | Anka/Coder | 9.6px | 26.4px | 3,947 |
| 98 | Adwaita Mono | 9.6px | 26.4px | 3,940 |
| 99 | ZhiMa Mono | 9.6px | 26.4px | 3,940 |
| 100 | Latin Modern Mono | 8.4px | 30.3px | 3,930 |
| 101 | Bitstream Vera Sans Mono | 9.6px | 26.5px | 3,915 |
| 102 | Verily Serif Mono | 9.6px | 26.5px | 3,914 |
| 103 | Chivo Mono | 9.6px | 26.7px | 3,907 |
| 104 | JuliaMono | 9.6px | 26.7px | 3,907 |
| 105 | CamingoCode | 8.8px | 29.1px | 3,902 |
| 106 | Fira Mono | 9.6px | 26.9px | 3,875 |
| 107 | Indicate Mono | 9.6px | 26.9px | 3,875 |
| 108 | League Mono | 9.6px | 26.9px | 3,875 |
| 109 | MD IO | 9.6px | 26.9px | 3,875 |
| 110 | Recursive | 9.6px | 26.9px | 3,875 |
| 111 | Sligoil | 9.6px | 26.9px | 3,875 |
| 112 | Binchotan Sharp | 8.0px | 32.4px | 3,861 |
| 113 | saxMono | 8.8px | 29.6px | 3,855 |
| 114 | Sometype Mono | 9.3px | 28.0px | 3,848 |
| 115 | Aurulent Sans Mono | 9.6px | 27.1px | 3,836 |
| 116 | Edlo | 9.6px | 27.1px | 3,836 |
| 117 | Twilio Sans Mono | 9.6px | 27.2px | 3,824 |
| 118 | Reddit Sans Mono | 9.0px | 29.1px | 3,819 |
| 119 | Luxi Mono | 9.6px | 27.4px | 3,801 |
| 120 | Drafting* Mono | 9.6px | 27.4px | 3,799 |
| 121 | Cartograph | 9.8px | 26.9px | 3,780 |
| 122 | Ellograph | 9.8px | 26.9px | 3,780 |
| 123 | Fragment Mono | 9.9px | 26.9px | 3,762 |
| 124 | Sono | 9.9px | 26.9px | 3,756 |
| 125 | 0xProto | 9.9px | 26.9px | 3,750 |
| 126 | Paper Mono | 9.9px | 26.9px | 3,750 |
| 127 | TeX Gyre Cursor | 9.6px | 27.9px | 3,735 |
| 128 | Google Sans Code | 9.6px | 28.0px | 3,714 |
| 129 | NotCourierSans | 9.6px | 28.1px | 3,711 |
| 130 | Proggy Vector | 9.6px | 28.0px | 3,710 |
| 131 | Hasklig | 9.6px | 28.2px | 3,699 |
| 132 | Office Code Pro | 9.6px | 28.2px | 3,699 |
| 133 | Source Code Pro | 9.6px | 28.2px | 3,699 |
| 134 | Fira Code | 9.8px | 27.6px | 3,683 |
| 135 | Azeret Mono | 10.4px | 26.1px | 3,678 |
| 136 | Generic Mono | 10.2px | 26.9px | 3,633 |
| 137 | psudoFont Liga Mono | 9.6px | 29.1px | 3,580 |
| 138 | iA Writer Mono | 9.6px | 29.1px | 3,577 |
| 139 | Lilex | 9.6px | 29.1px | 3,577 |
| 140 | Maple | 9.6px | 29.1px | 3,577 |
| 141 | Overpass Mono | 9.9px | 28.4px | 3,577 |
| 142 | IBM Plex Mono | 9.6px | 29.1px | 3,577 |
| 143 | Annotation Mono | 10.0px | 28.0px | 3,571 |
| 144 | DM Mono | 9.6px | 29.2px | 3,571 |
| 145 | Nova Mono | 9.0px | 31.2px | 3,565 |
| 146 | B612 Mono | 10.4px | 27.2px | 3,532 |
| 147 | JetBrains Mono | 9.6px | 29.6px | 3,522 |
| 148 | Red Hat Mono | 9.6px | 29.6px | 3,514 |
| 149 | Gintronic | 10.6px | 26.9px | 3,507 |
| 150 | Consolamono | 9.4px | 30.7px | 3,478 |
| 151 | Droid Sans | 9.6px | 30.2px | 3,452 |
| 152 | Roboto Mono | 9.6px | 30.2px | 3,452 |
| 153 | Departure Mono | 10.2px | 28.5px | 3,445 |
| 154 | NK57 Monospace | 10.8px | 26.9px | 3,434 |
| 155 | Oxygen Mono | 9.6px | 30.4px | 3,428 |
| 156 | Noto Mono | 9.6px | 30.5px | 3,414 |
| 157 | Profont | 10.7px | 28.1px | 3,341 |
| 158 | Martian Mono | 11.2px | 26.9px | 3,321 |
| 159 | Intel One Mono | 9.8px | 30.9px | 3,292 |
| 160 | DejaVu Mono | 9.6px | 32.2px | 3,228 |
| 161 | Meslo | 9.6px | 32.2px | 3,228 |
| 162 | Monoflow | 10.1px | 30.7px | 3,222 |
| 163 | Hermit | 9.9px | 31.7px | 3,192 |
| 164 | MonoLisa | 10.2px | 30.9px | 3,159 |
| 165 | Monocraft | 10.7px | 29.9px | 3,138 |
| 166 | Monoid | 10.7px | 29.9px | 3,138 |
| 167 | Space Mono | 9.8px | 33.2px | 3,078 |
| 168 | Miracode | 10.7px | 31.7px | 2,954 |
| 169 | Press Start 2P | 16.0px | 22.4px | 2,790 |
| 170 | OpenDyslexic Mono | 11.7px | 39.2px | 2,178 |

## License

The fonts are licensed under the [SIL Open Font License 1.1](OFL.txt), as modified versions of D2Coding, copyright (c) 2015 NAVER Corporation. The Nerd Fonts icons come from the [Nerd Fonts](https://github.com/ryanoasis/nerd-fonts) project, whose icon sets keep their own licenses, listed in its [license audit](https://github.com/ryanoasis/nerd-fonts/blob/master/license-audit.md). The color emoji are [Twemoji](https://github.com/jdecked/twemoji) graphics, copyright Twitter, Inc. and other contributors, licensed under [CC-BY 4.0](https://creativecommons.org/licenses/by/4.0/). The scripts are licensed under the MIT license in [LICENSE](LICENSE).
