# Run 1a — spec

Date: 2026-08-11T01:50:13-04:00

## Prompt(s)

Initial prompt:

Extract every mouse BMDM differentiation protocol from these 8 papers. Don't search
for others.

PMC3003694 PMC3574850 PMC7047825 PMC11144798
PMC11302253 PMC11417223 PMC12041772 PMC12234436

Emit a table with each unique mouse BMDM differentiation protocol that these papers
describe.

Write ./results.tsv, tab-separated, with this header exactly:

paper_id	species	strain	cell_source	growth_factor	conc_value	conc_unit	culture_days	base_medium	line

Work only in the current directory.

---

Additional prompts:

