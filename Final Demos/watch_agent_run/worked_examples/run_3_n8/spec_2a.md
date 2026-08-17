# Run 2a — spec

Date: 2026-08-11T01:50:26-04:00

## Prompt(s)

Initial prompt:

Extract every mouse BMDM differentiation protocol from these 8 papers. Don't search
for others.

PMC3003694 PMC3574850 PMC7047825 PMC11144798
PMC11302253 PMC11417223 PMC12041772 PMC12234436

Emit a table with each unique mouse BMDM differentiation protocol that these papers
describe.

A protocol needs a stated differentiating agent, and rodent bone marrow as the starting
material. Anything else — human cells, spleen, peritoneum, lavage, DC protocols,
polarization reagents — gets a row with verdict=excluded and a one-line reason.

One row per distinct cell_source x growth_factor x concentration x duration.

Write ./results.tsv, tab-separated, with this header exactly:

paper_id	verdict	reason	species	strain	cell_source	growth_factor	conc_value	conc_unit	culture_days	base_medium	line

Work only in the current directory.

---

Additional prompts:

