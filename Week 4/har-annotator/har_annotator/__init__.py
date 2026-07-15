"""har_annotator — a reproducible pipeline that filters human accelerated
regions (HARs) to constrained, neurodevelopment-adjacent, disease-overlapping
elements and assembles per-element evidence into a ranked shortlist.

Pipeline stages (see the driver script ``run_pipeline.py``):
    download   -- cached, hashed, provenance-logged data fetches
    filters    -- Phase 1 funnel: constraint ∩ neurodev-gene proximity ∩ GWAS
    evidence   -- Phase 2 per-element evidence spine
    temporal   -- Phase 2b developmental-timing axis (BrainSpan mid-fetal window)
    acceleration -- Phase 2c human–chimp substitution rate (panTro5 ortholog alignment)
    motif      -- Phase 2c JASPAR TF-motif gain/loss between human and chimp alleles
    score      -- Phase 3 transparent additive evidence score
"""
__version__ = "1.0.0"
