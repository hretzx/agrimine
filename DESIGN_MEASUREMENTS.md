# Design measurements: reference image vs the app

The reference is `AgriMine` dashboard mock-up (1536 x 1024). Everything below was measured from its pixels
(Pillow + NumPy: flat-colour sampling, card-edge detection, text bounding boxes) and then compared with the running app
rendered at the same 1536 x 1024 (headless Chromium + `getBoundingClientRect`). The sidebar landscape is cropped straight from the reference (`assets/sidebar_landscape.jpg`, 242 x 282 px,
its top 34 px faded into the sidebar colour). The other photographs in the mock-up (crop photos, the hero field photo) cannot be
reproduced: the app draws the hero landscape with SVG and uses emoji for crops. Content the mock-up shows but the dataset lacks (farm size, soil type, seasonal curve, planting window,
month-on-month percentages) is not built.

## Colours (measured -> used)
| Element | Measured | In the app |
|---|---|---|
| Sidebar | `#EBF4E9` flat | `#EBF4E9` |
| Page | `#F5F6F4` | `#F5F6F4` (+ a faint radial glow) |
| Active nav pill | `#C9E4C7` | `#C9E4C7`, text `#032D15` |
| Summary cards | `#EDF6EC`, `#F9F3E2`, `#FCECE6` | same |
| Cards | `#FEFEFE`, hairline border | `#FFFFFF`, `#EEF1EE` border |
| Crop row | `#FBFDF9` | `#FBFDF9` |
| Top-3 bars | green `#2FB573`, yellow `#FFC72D`, coral `#FF6971`, track `#EBF3F3` | same |
| Soil bars | green `#29D57B`, orange `#FDB94F`, red `#FD5F6D`, track `#E9F3F5` | `#2FB573`, `#FFC72D`, `#FF6971` (one status palette) |
| Pills | best `#D9F5E3`, good `#FFF3D5`, consider `#FFE1DD` | same fills |
| Status text | `#22A75D`, `#E78E17`, `#FC515D` | `#178A4C`, `#B86E00`, `#D93A48` (darker, so they pass WCAG AA) |
| Headings | near-black navy (`#010720` darkest pixels) | `#061326` |
| Subtitles | `#556D84` | `#556D84` |
| Hero button | `#039563` | `#049564` |

## Geometry at 1536 x 1024 (left, top, right, bottom)
See `measure_rect_report.txt` (card edges) and `measure_compare_report.txt` (colours). Every card edge is within 1 to 3 px of the reference.

## Typography (sizes in design pixels, scaled with the window)
Greeting 24, subtitle 13, summary value 32, card title 16, card subtitle 11.5, crop name 14, nav label 14, brand 25.
