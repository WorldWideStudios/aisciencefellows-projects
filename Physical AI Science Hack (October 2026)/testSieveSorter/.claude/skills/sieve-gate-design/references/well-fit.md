# Does it fit a 96-well plate well?

The first cut the team wants is to remove anything that cannot go into a 96-well plate well. This page gives:
- the verified well geometry;
- the fit rules, as `gatecalc.py` applies them (spec `[well]` table, or `item --plate`);
- what gates can and cannot do about it.

## 1. Which plate? (open question)

**Source status:**
- **verified**: read in a primary source; the reader is named.
- **unverified**: not confirmed.

**What we know:**
- BugPicker places "the next numbered well of a 96-well plate (A1…H12)" at "9 mm well pitch". It names no plate model and doesn't say standard, deep-well or PCR (github.com/BioKEA/BugPicker README; read by a research subagent, 2026-10-24).
- biokea.ai gives the BugPicker picking range as "2-6 mm", without saying which dimension.
- Precedents use standard 96-well plates:
  - DiversityScanner moves "specimens below 3 mm body length" into "a standard 96-well microplate" ([Wührl et al. 2022](https://www.biorxiv.org/content/10.1101/2021.05.17.444523v4.full)).
  - BIOSCAN UK puts one insect per well in ethanol, 100 µL crude lysate ([protocol](https://www.protocols.io/view/high-throughput-dna-barcoding-library-construction-chj5t4q6.pdf)).
  - Neither names a plate model.
- **Ask the team which plate BugPicker fills.** Until then the default is `std96_flat`.

## 2. Well geometry

**The standards.**
- **ANSI/SLAS 4-2004 fixes only the well positions**: first column 14.38 mm from the left edge, first row 11.24 mm from the top, 9 mm pitch.
- **It sets no diameter, depth or shape.** Its figure is "for illustration only" ([SLAS 4](https://www.slas.org/SLAS/assets/File/public/standards/ANSI_SLAS_4-2004_WellPositions.pdf)).
- The footprint is 127.76 x 85.48 mm ([SLAS 1](https://www.slas.org/SLAS/assets/File/public/standards/ANSI_SLAS_1-2004_FootprintDimensions.pdf)).
- **Well size is therefore the manufacturer's choice, so check the actual plate.** The 9 mm pitch caps every 96 well at about 8.2 mm across.

Inner dimensions in mm (Ø = diameter, side = square well):

| gatecalc name | Model | Top | Bottom | Depth | Volume | Bottom shape | Source | Status |
|---|---|---|---|---|---|---|---|---|
| `std96_flat` | Greiner 655101/655161 | Ø6.96 | Ø6.39 | 10.9 | 382 µL | flat | [Greiner guide](https://www.gbo.com/fileadmin/media/GBO-International/01_Downloads_BioScience/SALES_Brochures/F073027_Microplate_Dimensions_Guide.pdf), table p. 15 | verified (read myself) |
| (alternative) | Greiner 655180 chimney | Ø6.69 | Ø6.58 | 10.9 | 392 µL | flat | same | verified (read myself) |
| (alternative) | Corning 3595/3596/3599 | Ø6.86 | Ø6.35 | 10.67 | 360 µL | flat | Corning dimension sheet, read via a third-party copy | verified by subagent |
| `std96_round` | Greiner 650101 | Ø6.94 | (5.5 assumed) | 10.3 | 323 µL | U | Greiner guide p. 15 | top and depth verified; the bottom value is an assumed allowance for the hemisphere |
| `pcr96` | Bio-Rad HSP96 skirted | Ø5.46 | Ø2.64 (cone tip) | 14.81 | 200 µL | conical | [Bio-Rad](https://www.bio-rad.com/en-us/sku/hsp9601b-hard-shell-thin-wall-96-well-skirted-pcr-plates?ID=hsp9601b) | verified by subagent |
| `deep96_round_1ml` | Greiner 780261 MASTERBLOCK 1 mL | Ø7.0 | Ø5.97 | 38.2 | 1220 µL | U | Greiner guide p. 15 | verified (read myself) |
| `deep96_square_2ml` | Greiner 780270 MASTERBLOCK 2 mL | side 8.2 | side 7.37 | 41.0 | 2420 µL | V (pyramid) | Greiner guide p. 15 | verified (read myself) |
| (alternative) | Corning 3960 2 mL square | side 8.15 | — | 42.03 | 2000 µL | V | Corning sheet, via a copy | verified by subagent |

**Typical ranges:**
- standard 96: top Ø 6.7-7.0 mm, depth 10.3-11.3 mm;
- round deep-well 1 mL: Ø about 7.0 mm at the top, 38-40 mm deep;
- square deep-well 2 mL: side 8.15-8.2 mm at the top, 41-42 mm deep;
- PCR: Ø about 5.5 mm, conical.

**Different models of a plate type** differ by up to about 0.3 mm in diameter. The default 0.3 mm margin covers that; measure the real plate if a cut sits near the limit. Any other plate goes in the spec as `[well] shape`, `top_mm`, `bottom_mm`, `depth_mm`.

## 3. Fit rules

All rules are derived geometry on the rigid body, L >= W >= T, minus the margin m (default 0.3 mm). Appendages are ignored: legs and antennae of preserved specimens usually fold or bend when a specimen is placed. Long-legged specimens are a known risk (section 5).

1. **Through the mouth (end-first)**
   - round well: W <= top - m
   - square well: min(W, √((W² + T²)/2)) <= top - m (the diagonal)
   - If this fails, the item is **"no"**: no orientation gets it in.
2. **Lies flat on the bottom**, using the bottom size, which is the narrower one in tapered wells:
   - round well: L² + W² <= (bottom - m)² (a W-wide body along a diameter)
   - square well: L <= bottom - m, or L <= √2 (bottom - m) - W (along the diagonal)
   - plus T <= the allowed height.
   - If this holds, the item is **"flat"**.
3. **Leans in the well** (a long, skinny item standing tilted against the wall). For some tilt angle α:
   - L cos α + T sin α <= reach, where reach = bottom - m (round) or √2 (bottom - m) (square);
   - and L sin α + T cos α <= the allowed height.
   - If this holds, the item is **"leans"**.
4. **Allowed height**:
   - `require = "below_rim"`: the well depth, so the plate can be sealed;
   - `require = "submerged"`: the liquid height, fill_ul / bottom area. Use this when the specimen must sit in lysis buffer or ethanol (BIOSCAN uses 100 µL).
5. **"fits"** = flat, or leans if `accept_lean = true` (the default).

**Placement risk:** an item longer than the well mouth bridges the opening when dropped flat. BugPicker has to set it in end-first, or it must be nudged. Treat "leans" as fits-with-risk until the picker is tested with long specimens.

**Approximations:**
- Wall taper is ignored (the bottom size is used, which is conservative).
- U, V and conical bottoms are treated as a flat floor at the bottom size, which is optimistic for V/U and very conservative for PCR cones.
- The fill height ignores the bottom's shape.

**Rule of thumb for a standard well**: about 6.6 mm mouth less margin, 6.1 mm usable floor, 10.9 mm deep.
- Fits flat up to about 6 mm long.
- Leans up to about 12 mm long if under about 1 mm thick.
- Nothing wider than about 6.6 mm enters.
- With 100 µL of liquid (about 3.1 mm deep at Ø6.39), anything longer than about 6 mm sticks out of the buffer.

## 4. Worked examples

All are `gatecalc.py item` output (executed 2026-10-24). Sizes are body L x W x T in mm.

| Item | std96_flat | pcr96 | deep96_round_1ml | deep96_square_2ml |
|---|---|---|---|---|
| small fly 3 x 1 x 0.8 | flat | leans | flat | flat |
| fly 6 x 1.8 x 1.5 | leans | leans | leans | flat |
| wasp 9 x 3 x 2.5 | leans | no | leans | leans |
| crane fly body 12 x 1.5 x 1.2 | **no** (too long even leaning) | leans | leans | leans |
| crane fly body 15 x 1.5 x 1.2 | no | no | leans | leans |
| flat beetle 7 x 6.8 x 3 | no (too wide) | no | no | flat |

## 5. What gates can and cannot do about it

- **Width** is the only fit dimension a gate can cut, and **a round hole is the exact filter for a round well's mouth**. `o<d>` with d = top - m passes exactly the items whose cross-section enters the well.
- **For a square deep well**, a square window of side = top - m is the exact filter: the same diagonal rule applies.
- **A tall width gap (w) is a poor well-fit filter.** A wide, flat item rolls on edge and passes whenever T < s. In the example above, the flat beetle passes w6.0 on edge and also passes win6.0x5.8 at an intermediate angle; only o6.0 blocks it. `gatecalc plan` reports this and says whether a height cap can help.
- **Length and depth cannot be cut by gates.** Items pass end-first. In the sim's insect population (`templates/malaise-spec.toml`), every specimen that fails a standard well fails on length, not width (long-legged and elongate bodies). A width gate keeps none of them, and `plan` says so.
- **Options for length:**
  1. **Choose a deeper plate.** Every example above except the flat beetle fits a 1 mL round or 2 mL square deep well, at least by leaning.
  2. **Reject at the picker by vision.** BugPicker already images each specimen with OpenCV.
  3. **Use an indented-cylinder length grader** before the tower.
  4. **Hand-pick the few long specimens.** Malaise: 2.9-5.5% are longer than 5 mm (EntoSieve, below).

**Malaise size mix.** [Ascenzi et al. 2025, EntoSieve](https://pmc.ncbi.nlm.nih.gov/articles/PMC12225705/) gives these shares for two Malaise samples: "56%-58% of specimens measured less than 1.5 mm, 27%-31% measured between 1.5 and 3.0 mm", "8%-12% measured between 3.0 and 5.0 mm and 2.9%-5.5% were longer than 5.0 mm".
- The classes are "defined based on insect body lengths".
- But the sorting used perforated plates of 1.5 / 3 / 5 mm, which cut by cross-section. The paper says "perforation diameters", so probably round holes; the shape is inferred.
- So these shares are a length distribution, measured with a width-type filter. Don't read them as "the share that fits a well": most specimens over 5 mm long are narrow and pass a 5-6 mm hole.
