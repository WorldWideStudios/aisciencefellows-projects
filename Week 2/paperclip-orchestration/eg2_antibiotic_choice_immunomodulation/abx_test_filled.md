# Research Digest: Macrophage Signaling, Antibiotic Mechanism of Action, and Immune-Modulatory Effects in Bacterial Infection

> **Example run — workflow demonstration, not clinical guidance.** This digest was produced by an automated literature-synthesis run ([paperclip-workflow](https://github.com/drjlgross/paperclip-workflow)). It is a snapshot of one run against the literature available at the time, included to demonstrate the format and method. It is not a recommendation; consult the cited primary sources and professional judgment for anything clinical.


**Audience:** Working reference for a clinician-scientist (Julia's PhD project domain)
**Date generated:** 2026-05-16
**Working directory:** `~/paperclip-test/abx_test_v2/`
**Searches run:** see per-sub-question "Search and filter notes" for tags + result IDs

---

## Overarching question

How do canonical macrophage bacterial recognition pathways intersect with antibiotic mechanism of action, and what does the clinical literature say about whether antibiotic class affects host immune response beyond direct antimicrobial activity?

The four sub-questions are intentionally interdependent. SQ1 establishes the receptor-pathway scaffold. SQ2 establishes the mechanism-class scaffold. SQ3 maps the intersection. SQ4 tests whether the intersection shows up in clinical outcomes.

---

## Scoping Notes

- Sub-questions are interdependent — SQ1's PRR/pathway scaffold informs SQ3 searches; SQ2's mechanism classes inform SQ3 and SQ4 searches.
- Decisions made during research:
  - SQ1: included one canonical broad PRR review (Chen 2025), one canonical macrophage-defense review (Weiss & Schaible 2015), one TLR-adaptor review (Rughetti 2024), one DNA-sensing inflammasome review (Holley 2022), and 5 mechanistic / receptor-specific studies. Excluded structural biology of TLR/inflammasome assembly as out of scope.
  - SQ2: collapsed all β-lactams to one row, all fluoroquinolones to one row, etc. — unit of analysis is mechanism class. Did not include every described novel sub-class; surfaced fidaxomicin and pleuromutilins as flag entries.
  - SQ3: organized by mechanism class × innate-immune axis (PAMP release / direct macrophage effect / phagocyte-function effect). Distinguished in vitro from animal-model evidence; flagged supratherapeutic-concentration caveats.
  - SQ4: emphasized studies that explicitly engage the mechanism question (macrolide-immunomodulation in CAP/COPD/bronchiectasis; bactericidal-vs-bacteriostatic in sepsis). De-emphasized routine non-inferiority head-to-head efficacy trials.
- Phase 0 anchor candidates: see `_anchor_candidates.md`.

---

## Sub-Question 1: Macrophage signaling pathways, with emphasis on canonical bacterial recognition PRRs

**Scope constraint:** Focus on PRRs with established bacterial ligand recognition. For each, name the canonical ligand, the signaling adapter, and the downstream transcriptional program. Aim for a working map a clinician-scientist would use — not a textbook chapter. Do not exhaustively review each pathway's structural biology or every described regulatory modification.

### Search and filter notes
- Search terms used (parallel):
  1. "macrophage Toll-like receptor TLR2 TLR4 bacterial signaling MyD88 TRIF review"
  2. "NOD1 NOD2 NLRP3 inflammasome macrophage bacterial recognition review"
  3. "C-type lectin receptor Dectin-1 Mincle macrophage bacterial review"
  4. "cGAS STING cytosolic bacterial DNA macrophage interferon"
  5. "AIM2 inflammasome cytosolic bacterial DNA macrophage"
  6. "pattern recognition receptors macrophage bacterial infection review"
  7. "TLR9 CpG DNA macrophage signaling bacterial"
  8. Supplementary canonical-review searches for Chen 2025 (PRR comprehensive) and Weiss & Schaible 2015 (macrophage defense)
- Result IDs: s_3a779212 (sq1_v2, 15 papers → filtered to 8); s_ba801e7a (Weiss); s_0b283e18 (Chen 2025)
- Filter criteria applied: "macrophage pattern recognition receptor signaling for bacterial recognition — TLRs, NLRs, CLRs, cGAS-STING, AIM2 — reviews or canonical receptor-mechanism papers" with `--require 8`
- Excluded and why: viral-specific PRR papers (RIG-I/RLR), zebrafish CLR developmental paper, fungal-only Dectin work, structural biology of TLR/NLR assembly, and papers using PRRs only as readouts of a drug effect (covered in SQ3).
- Keeper papers:
  - PMC12246121 | Chen R, Zou J, et al 2025 | broad canonical PRR review across TLR/NLR/CLR/AIM2/cGAS-STING/RLR — table backbone
  - PMC4368383 | Weiss G, Schaible UE 2015 | macrophage anti-bacterial defense — CLR/TLR coverage for mycobacteria (**anchor**)
  - PMC11385170 | Rughetti A, Bharti S, et al 2024 | TLR adaptor proteins (MyD88, TIRAP, TRIF, TRAM) — MyD88-vs-TRIF detail
  - PMC9139316 | Holley CL et al 2022 | DNA recognition by inflammasomes — AIM2, NLR, cGAS-STING crosstalk
  - PMC8321404 | Eldridge MJG et al 2021 | human macrophage PRR landscape via CRISPR (Legionella) — TLR2/3/4/5/9 + cGAS-STING + Dectin-1/2 + Mincle in one paper
  - bio_56e9957f6d01 | Goldberg lab 2021 | NLRP11 as primate-specific cytosolic LPS sensor — non-canonical LPS sensing
  - bio_3c40e0c96d3d | 2021 | R. equi → cGAS/STING/TBK1 type-I IFN — example of vacuolar-pathogen cytosolic DNA sensing
  - PMC9448748 | TREM2/β-catenin attenuates NLRP3 pyroptosis — negative regulation of inflammasome
  - bio_e15726726c18 | 2022 | MyD88-dependent TLR-trained immunity in macrophages — MyD88 vs TRIF functional contrast
  - PMC7923022 | Herb M, Schramm M 2021 | ROS in macrophages — antimicrobial effector arm downstream of PRRs

### Pathway summary table

| PRR family | Specific receptor | Canonical bacterial ligand(s) | Signaling adapter(s) | Downstream transcriptional program | Key macrophage effector outputs | Representative source (DOI/PMID) |
|---|---|---|---|---|---|---|
| TLR (cell-surface, lipid/protein) | TLR4 (heterodimer with MD-2/CD14) | LPS (lipid A) | TIRAP→MyD88 (NF-κB/AP-1 arm) and TRAM→TRIF (IRF3 arm) | NF-κB / AP-1 → pro-inflammatory cytokines; IRF3 → type I IFN | TNF-α, IL-6, IL-1β precursor, NO; type I IFN | PMC12246121 / PMC11385170 |
| TLR (cell-surface, lipid/protein) | TLR2 (heterodimers with TLR1 or TLR6) | Bacterial lipopeptides, peptidoglycan-associated lipoproteins, mycobacterial lipoarabinomannan | TIRAP→MyD88 | NF-κB / MAPK | Pro-inflammatory cytokines, phagocytosis | PMC11385170 / PMC4368383 |
| TLR (cell-surface, protein) | TLR5 | Flagellin | MyD88 (predominant; TRIF described) | NF-κB / AP-1 | Pro-inflammatory cytokines, mucosal recruitment | PMC8321404 / PMC11385170 |
| TLR (endosomal, nucleic acid) | TLR9 | Unmethylated bacterial CpG DNA | MyD88 | NF-κB / AP-1; IRF7 for type I IFN in some lineages | Pro-inflammatory cytokines, type I IFN; drives PAMP-response to released bacterial DNA (see SQ3) | PMC4368383 / PMC11605096 |
| NLR (cytosolic, surveillance) | NOD1, NOD2 | iE-DAP (NOD1), muramyl dipeptide (NOD2) | RIPK2 | NF-κB / MAPK | Pro-inflammatory cytokines, autophagy initiation, anti-microbial peptide induction | PMC12246121 |
| NLR (cytosolic, inflammasome) | NLRP3 | Indirect: K+ efflux, ROS, lysosomal damage (response to many bacterial events incl. pore-formation, ion flux) | ASC → caspase-1 | Inflammasome assembly (post-translational) → caspase-1 maturation | IL-1β, IL-18 secretion; pyroptosis via gasdermin-D | PMC9448748 / PMC12246121 |
| NLR (cytosolic, inflammasome) | NAIP/NLRC4 | T3SS rod/needle, flagellin (cytosolic) | ASC, caspase-1 | Inflammasome assembly | IL-1β, IL-18, pyroptosis | PMC8321404 |
| NLR (cytosolic, non-canonical LPS sensing) | NLRP11 (primate) / caspase-4/5/11 | Cytosolic LPS (lipid A) | Caspase-4/5/11 activation; NLRP11 amplifies in primates | (post-translational) | IL-1β, IL-18, pyroptosis | bio_56e9957f6d01 |
| ALR (cytosolic, DNA inflammasome) | AIM2 | Cytosolic dsDNA (bacterial, e.g., F. tularensis, L. monocytogenes) | ASC → caspase-1 | Inflammasome assembly | IL-1β, IL-18, pyroptosis | PMC12246121 / PMC9139316 |
| Cytosolic DNA sensor (type-I IFN axis) | cGAS → STING | Cytosolic bacterial dsDNA (e.g., released from phagosome-permeabilizing pathogens) | STING → TBK1 → IRF3 (and NF-κB) | Type I IFN program; ISGs | Type I IFN (autocrine/paracrine), antimicrobial state | PMC12246121 / bio_3c40e0c96d3d |
| C-type lectin receptor (surface) | Dectin-1 | β-glucan (fungal); also recognizes some mycobacterial structures | Syk → CARD9 → BCL10/MALT1 | NF-κB / MAPK | Pro-inflammatory cytokines, phagocytosis, ROS via NOX | PMC12246121 / PMC11385170 |
| C-type lectin receptor (surface) | Mincle, MCL, DC-SIGN, Mannose Receptor | Mycobacterial trehalose dimycolate (Mincle/MCL); mannose-capped LAM (MR, DC-SIGN) | FcRγ → Syk → CARD9 (Mincle/MCL) | NF-κB / MAPK | Phagocytosis, pro-inflammatory cytokines, granuloma assembly | PMC4368383 |
| Effector arm (downstream of many PRRs) | NADPH oxidase (NOX2) / iNOS | n/a — ROS / RNS production triggered downstream | — | — | Reactive oxygen species (oxidative burst), nitric oxide; signaling + microbicidal | PMC7923022 |

### Paragraph answer

A working modern map of macrophage bacterial sensing partitions the PRR repertoire by **subcellular location** and **ligand chemistry**. Surface TLRs handle extracellular and phagocytosed PAMPs: TLR4 senses LPS, TLR2 (with TLR1/6) senses lipopeptides and lipoteichoic structures, and TLR5 senses flagellin. These signal through a TIRAP→MyD88 cascade to NF-κB and AP-1 — the canonical pro-inflammatory cytokine program — with TLR4 uniquely also engaging a TRAM→TRIF→IRF3 arm to produce type I IFN. Endosomal TLR9 senses unmethylated bacterial CpG DNA released from phagocytosed and lysed bacteria, again via MyD88. The cytosol contains a parallel surveillance system: NOD1/NOD2 detect peptidoglycan fragments and signal through RIPK2 to NF-κB; inflammasomes (NLRP3, NAIP/NLRC4, AIM2, and non-canonical caspase-4/5/11 with NLRP11 amplification in primates) detect cytosolic LPS, T3SS structures, or DNA, and produce IL-1β, IL-18, and pyroptotic cell death rather than transcriptional cytokine output. The cGAS–STING axis senses cytosolic bacterial dsDNA — relevant for pathogens that permeabilize the phagosome — and drives a TBK1→IRF3 type I IFN program. Carbohydrate-targeting CLRs (Dectin-1, Mincle, MCL, DC-SIGN, MR) sense glycans, mainly fungal but also key for mycobacteria, and signal via Syk→CARD9 to NF-κB. The principal organizing axes are therefore (i) surface vs cytosolic location, (ii) MyD88-dependent (NF-κB / cytokine) vs TRIF/STING-dependent (IRF3 / type I IFN) signaling, and (iii) transcriptional output vs inflammasome-mediated post-translational maturation and pyroptotic death. NADPH oxidase / iNOS and antimicrobial peptide programs sit downstream of many of these inputs as the effector arm.

### Synthesis bullets
- **Convergence points:** NF-κB is the most-shared output node (TLRs via MyD88, NODs via RIPK2, CLRs via CARD9). Type I IFN converges on TBK1→IRF3 from both TLR4-TRIF and cGAS-STING. These convergence points mean that pharmacological or pathogen perturbation at one PRR can be partially compensated by parallel inputs — important for SQ3 interpretation.
- **Active revision:** Non-canonical inflammasome sensing of cytosolic LPS via caspase-4/5/11 was added to the canonical map in the 2010s; primate-specific NLRP11 amplification (bio_56e9957f6d01) is a recent addition not yet in most textbooks. The role of DNA-PK as a parallel cytosolic DNA sensor (PMC8321404) is similarly recent. Trained-immunity reprogramming via MyD88-dependent TLR signaling (bio_e15726726c18) is now a recognized macrophage memory phenomenon that older PRR maps lack.
- **Coverage gaps in this digest:** Scavenger receptors (SR-A, MARCO, CD36), peptidoglycan-recognition proteins, formyl-peptide receptors, complement-receptor crosstalk, RIG-I/MDA5 (mostly viral-relevant for bacterial infection), and the full Pyrin-NLR landscape are not separately rowed. These are out of scope for a clinician working-reference but matter for receptor-specific deep dives.

### Confidence read
- **Evidence quality:** Textbook-canonical for the receptor-ligand-adapter triplets; actively-revised at the level of cytosolic LPS sensing (NLRP11 / caspase-4/5/11), trained immunity, and the cross-talk between AIM2, cGAS-STING, and ZBP1 in bacterial settings.
- **Direction of evidence:** Generally consistent: surface TLRs → MyD88-cytokine program; cytosolic sensors → inflammasome or type-I IFN program. The textbook bifurcation holds.
- **Key uncertainty:** Most likely receptor to be re-characterized in 5 years: **NLRP3**, both at the level of upstream activation mechanism (whether a single unifying trigger exists or many parallel ones) and at the level of human disease relevance of newer non-canonical regulators (gasdermin-D pore biology, NEK7 dependence, mitochondrial DAMP integration). The role of cGAS-STING in vacuolar-pathogen infections (not just cytosolic ones) is also being re-characterized.

---

## Sub-Question 2: Antibiotic mechanism of action — broad mechanism-class overview

**Scope constraint:** Unit of analysis is **mechanism class**, not drug. For each class, describe the mechanism once and list representative agents.

### Search and filter notes
- Search terms used (parallel):
  1. "antibiotic mechanism of action review classes molecular targets"
  2. "beta-lactam cell wall synthesis penicillin-binding protein peptidoglycan review"
  3. "aminoglycoside tetracycline 30S ribosome protein synthesis mechanism"
  4. "macrolide oxazolidinone 50S ribosome protein synthesis mechanism"
  5. "fluoroquinolone DNA gyrase topoisomerase mechanism review"
  6. "polymyxin daptomycin membrane disruption mechanism"
  7. "bactericidal bacteriostatic time-dependent concentration-dependent pharmacodynamics review"
  8. Supplementary: rifampin/RNA polymerase, polymyxin/colistin review, daptomycin
- Result IDs: s_4e336319 (sq2v2 main, 23 → 12 filtered); s_a5bd25df (general clinician review), s_13b62b30 (polymyxin), s_5065e29d (rifamycin)
- Filter criteria applied: "antibiotic mechanism of action — molecular target of an antibiotic class; reviews of mechanism classes; PK/PD or bactericidal/static framing — both general overviews and class-specific mechanism papers", `--require 10`
- Excluded and why: Streptococcus pneumoniae resistance mechanism review (PMC10672801) — useful for resistance but not the primary mechanism scaffold; "Comprehensive Overview of Antibiotic Selection" (PMC8049037) — clinical-decision flavor rather than mechanism; resistance-evolution math models (arXiv) — out of scope for class-mechanism scaffold. Folate-pathway papers did not surface as keepers from the parallel searches — folate-pathway mechanism cited via the Kapoor 2017 multi-class review only.
- Keeper papers:
  - PMC5672523 | Kapoor G, Saigal S, Elongavan A 2017 | "Action and resistance mechanisms of antibiotics: A guide for clinicians" — multi-class clinician-oriented review used as the backbone citation
  - PMC11695898 | Ishak A, Mazonakis N, Spernovasilis N, Akinosoglou K, Tsioutis C et al 2025 | bactericidal-vs-bacteriostatic clinical significance (**anchor**)
  - PMC5039524 | "Membrane Steps of Bacterial Cell Wall Synthesis as Antibiotic Targets" — β-lactam/glycopeptide/bacitracin target detail
  - PMC11505993 | "Mechanistic Insights into Clinically Relevant Ribosome-Targeting Antibiotics" — 30S/50S antibiotic mechanism review
  - PMC4312571 | Yu Z et al 2015 | "Antibacterial Mechanisms of Polymyxin and Bacterial Resistance"
  - PMC7463838 | Moubareck CA 2020 | "Polymyxins and Bacterial Membranes" — companion polymyxin review
  - PMC6202310 | Mosaei H et al 2018 | RNA polymerase inhibition (rifamycin/Kanglemycin A)
  - bio_014d5af66cdb | "Daptomycin exhibits two independent antibacterial mechanisms of action" (membrane perturbation + lipid II binding)
  - bio_f0f957197866 | linezolid (oxazolidinone) mechanism + ribosomal protection in M. abscessus
  - PMC3576927 | "Mechanism of Tetracycline Resistance by Ribosomal Protection Protein Tet(O)" — tetracycline-target detail
  - PMC10739246 | "Piperazinyl Norfloxacin Derivatives" — fluoroquinolone DNA gyrase/topo IV mechanism + multi-mechanism flag
  - PMC4797290 | "Proline-rich peptides bound to the ribosome" — context on 50S inhibition (peptide deformylase-adjacent space)

### Mechanism class table

| Mechanism class | Molecular target | Representative agents | Bactericidal/static | Lytic vs non-lytic | Kinetics (time- vs conc-dependent) | Representative source (DOI/PMID) |
|---|---|---|---|---|---|---|
| β-lactams (cell wall synthesis) | Penicillin-binding proteins (PBPs) — inhibit transpeptidation step of peptidoglycan cross-linking | Penicillins, cephalosporins, carbapenems, monobactams | Bactericidal (in actively-growing cells; bacteriostatic if growth arrested) | Lytic (autolysin-mediated; massive PAMP release — see SQ3) | Time-dependent (T>MIC); fT>MIC ≥40-70% target | PMC5672523 / PMC5039524 |
| Glycopeptides (cell wall synthesis) | D-Ala-D-Ala terminus of lipid II — block transglycosylation/transpeptidation | Vancomycin, teicoplanin, telavancin, dalbavancin, oritavancin | Bactericidal vs most Gram-positives (slowly); bacteriostatic vs enterococci | Largely non-lytic / slow lysis | AUC/MIC-dependent (vancomycin AUC24/MIC ≈400) | PMC5672523 / PMC5039524 |
| Lipopeptides (membrane) | Daptomycin: Ca²⁺-dependent membrane insertion → depolarization; secondary lipid II / cell wall binding | Daptomycin | Bactericidal (rapid, concentration-dependent killing) | Non-lytic (kills without lysis — important: lower PAMP release than β-lactams; see SQ3) | Concentration-dependent (Cmax/MIC and AUC/MIC) | bio_014d5af66cdb / PMC5672523 |
| Polymyxins (membrane) | Bind lipid A of LPS in outer membrane of Gram-negatives → outer-then-inner membrane permeabilization | Polymyxin B, colistin (polymyxin E) | Bactericidal (rapid) | Membrane-disruptive — releases LPS (PAMP-relevant for SQ3) | Concentration-dependent | PMC4312571 / PMC7463838 |
| Aminoglycosides (30S protein synthesis) | 30S ribosomal subunit (16S rRNA decoding A-site) — induce mistranslation; misfolded membrane proteins → membrane damage | Gentamicin, tobramycin, amikacin, streptomycin | Bactericidal | Mostly non-lytic; killing via misfolded membrane proteins and energy loss | Concentration-dependent (Cmax/MIC ≈8-10) | PMC5672523 / PMC11505993 |
| Tetracyclines/glycylcyclines (30S protein synthesis) | 30S A-site — block aminoacyl-tRNA binding | Tetracycline, doxycycline, minocycline, tigecycline | Bacteriostatic | Non-lytic | Time-dependent (AUC/MIC for tigecycline) | PMC5672523 / PMC3576927 |
| Macrolides / ketolides (50S protein synthesis) | 23S rRNA in nascent peptide exit tunnel → blocks peptide elongation | Erythromycin, azithromycin, clarithromycin, telithromycin | Bacteriostatic (bactericidal in some contexts, e.g., azithromycin vs S. pyogenes) | Non-lytic | Time-dependent (azithromycin: long tissue half-life → AUC-driven) | PMC5672523 / PMC11505993 |
| Lincosamides (50S protein synthesis) | 23S rRNA in peptidyl-transferase center — overlaps macrolide site | Clindamycin, lincomycin | Bacteriostatic (often used for its anti-toxin / anti-exotoxin properties) | Non-lytic | Time-dependent | PMC5672523 |
| Oxazolidinones (50S protein synthesis) | 23S rRNA A-site of 50S — blocks initiation complex formation | Linezolid, tedizolid | Bacteriostatic (vs staphylococci, enterococci); bactericidal vs some streptococci | Non-lytic | AUC/MIC (linezolid) | bio_f0f957197866 / PMC5672523 |
| Chloramphenicol / amphenicols (50S) | 23S peptidyl-transferase center | Chloramphenicol | Bacteriostatic (bactericidal vs H. influenzae, S. pneumoniae, N. meningitidis) | Non-lytic | Time-dependent | PMC5672523 |
| Streptogramins (50S) | Quinupristin-dalfopristin combinations: both 50S A-site/P-site bridge | Quinupristin/dalfopristin | Combination bactericidal | Non-lytic | Mixed | PMC5672523 |
| Pleuromutilins (50S) | 23S peptidyl-transferase center — distinct binding pocket | Lefamulin, retapamulin | Bacteriostatic | Non-lytic | AUC/MIC | PMC5672523 |
| Fluoroquinolones (DNA gyrase / topo IV) | DNA gyrase (GyrA/B) in Gram-negatives; topoisomerase IV in Gram-positives — stabilize cleavage complex → double-strand breaks | Ciprofloxacin, levofloxacin, moxifloxacin, delafloxacin | Bactericidal | Largely non-lytic (kills via lethal DSBs and SOS response; some Gram-negative lysis possible) | Concentration-dependent (AUC/MIC and Cmax/MIC) | PMC5672523 / PMC10739246 |
| Rifamycins (RNA polymerase) | Bind β subunit of RNA polymerase — block initiation/early elongation | Rifampin, rifabutin, rifapentine, rifaximin | Bactericidal | Non-lytic | AUC/MIC; resistance arises rapidly as monotherapy | PMC6202310 / PMC5672523 |
| Sulfonamides + DHFR inhibitors (folate pathway) | Sulfonamides → dihydropteroate synthase (DHPS); trimethoprim → dihydrofolate reductase (DHFR). Sequential pathway block. | Sulfamethoxazole-trimethoprim (TMP-SMX) | Bacteriostatic alone; bactericidal in combination | Non-lytic | Time-dependent (T>MIC) | PMC5672523 |
| Mycolic-acid synthesis (mycobacteria) | Isoniazid → enoyl-ACP reductase (InhA) of mycolic acid biosynthesis | Isoniazid, ethionamide | Bactericidal (vs replicating M. tuberculosis); flagged as TB-specific | Non-lytic (slow killing) | Concentration-dependent | PMC5672523 |
| Novel-mechanism flags | Fidaxomicin → bacterial σ-factor / RNA polymerase switch (C. difficile-restricted); lefamulin → 50S pleuromutilin; bedaquiline → ATP synthase F0 c-subunit (mycobacteria) | Fidaxomicin, lefamulin, bedaquiline | Variable | Generally non-lytic | Variable | PMC5672523 |

### Paragraph answer

Antibiotic classes partition along three axes useful for SQ3 interpretation: (i) **molecular target** — cell-wall synthesis (β-lactams, glycopeptides, fosfomycin, bacitracin), cell membrane (polymyxins, daptomycin), ribosome (30S: aminoglycosides, tetracyclines; 50S: macrolides, lincosamides, oxazolidinones, chloramphenicol, streptogramins, pleuromutilins), DNA replication / unwinding (fluoroquinolones), RNA transcription (rifamycins), folate metabolism (sulfonamides + trimethoprim), and mycobacterial mycolic-acid synthesis (isoniazid); (ii) **bactericidal vs bacteriostatic** — a useful but concentration- and organism-dependent dichotomy that the recent Ishak 2025 review explicitly cautions against treating as absolute (PMC11695898); and (iii) **lytic vs non-lytic killing kinetics** — β-lactams (lytic, via autolysin-driven peptidoglycan damage) and polymyxins (membrane-disruptive) cause substantial bacterial-component release; daptomycin, fluoroquinolones, and ribosome-targeting agents predominantly kill or arrest without gross lysis. PK/PD descriptors (time-dependent fT>MIC for β-lactams and most ribosomal-acting bacteriostatic agents; concentration-dependent Cmax/MIC or AUC/MIC for aminoglycosides, fluoroquinolones, daptomycin, polymyxins) determine clinical dosing and also shape the rate at which PAMP release occurs in vivo — directly relevant to the immune-modulation arguments in SQ3.

### Synthesis bullets
- **Revised textbook items:** Daptomycin's mechanism was clarified post-2020 to include a secondary lipid-II / cell-wall-precursor binding component in addition to membrane depolarization (bio_014d5af66cdb), changing how it is classified. The bactericidal/static dichotomy itself has been substantially re-examined: meta-analyses and reviews now treat it as concentration- and organism-dependent rather than intrinsic (PMC11695898).
- **Features that matter for SQ3:** Lysis-inducing agents (β-lactams, polymyxins) release more peptidoglycan, LPS, and DNA than non-lytic agents (daptomycin, aminoglycosides, ribosome-acting agents) — predicting differential TLR2/TLR4/TLR9 engagement (Gross et al 2024 ties bactericidal-lytic kill to TLR9 sensing of released bacterial DNA). Concentration-dependent killers reach peak bacterial-component release earlier; time-dependent agents distribute the release over the dosing interval. Intracellular access differs by class (macrolides, fluoroquinolones, rifamycins concentrate intracellularly — relevant for intracellular-pathogen handling and direct macrophage effects in SQ3).
- **Notable omissions:** Antimycobacterial-only mechanisms (isoniazid, ethionamide, bedaquiline) are flagged but not deeply rowed because the SQ scope is general bacterial infection. β-lactamase inhibitors (clavulanate, tazobactam, avibactam, vaborbactam) are not separately rowed — they have no independent mechanism class. Fosfomycin (MurA inhibitor) and bacitracin (lipid carrier recycling) are subsumed under cell-wall synthesis.

### Confidence read
- **Evidence quality:** Textbook-canonical for the target-class assignments; actively-revised for bactericidal/static classification and daptomycin's dual mechanism.
- **Direction of evidence:** Mechanism class assignments are stable across decades; PK/PD descriptors are well-validated for the major classes.
- **Key uncertainty:** Whether the bactericidal-vs-bacteriostatic distinction has any class-level clinical or immunological meaning, or whether it is mostly an artefact of in vitro time-kill methodology, remains contested — directly bears on SQ3/SQ4.

---



## Sub-Question 3: How different mechanistic classes of antibiotics impact host innate immune responses to infection

**Scope constraint:** Use SQ1's PRR/pathway scaffold and SQ2's mechanism classes as the conceptual structure. The question is **mechanism-class × innate-immune-axis** — organize findings along that intersection, not by drug or by clinical condition.

### Search and filter notes
- Search terms used (parallel):
  1. "beta-lactam bacterial lysis PAMP release peptidoglycan LPS TLR signaling endotoxin"
  2. "macrolide azithromycin anti-inflammatory NF-kB neutrophil immunomodulation mechanism"
  3. "tetracycline doxycycline MMP anti-inflammatory non-antimicrobial"
  4. "fluoroquinolone cytokine modulation macrophage neutrophil immune"
  5. "aminoglycoside phagocyte lysosome immune modulation"
  6. "polymyxin endotoxin neutralization LPS sequestration"
  7. "antibiotic class innate immune response macrophage in vitro"
  8. "antibiotic effect bacterial DNA release TLR9 cGAS-STING inflammation"
  9. Anchor-retrieval pass for the 11 Phase 0 candidates and 4 named author/title searches
- Result IDs: s_2882383f (sq3v2 broad searches, 24 papers → only 3 passed `--require 10` filter — Rule C triggered, see below); s_8de93eba (sq3_anchors retrieval pass, 25 → 11 filtered)
- **Rule C invocation:** The first broad filter on sq3v2 dropped 21 of 24 papers as "not relevant." Inspecting the dropped set showed mostly resistance-mechanism papers, math models, and biofilm papers — actually appropriately filtered. The retained 3 were too few. Instead of broadening the filter (which would have re-admitted off-topic resistance papers), I supplemented with a Phase-0-anchor-retrieval pass (sq3_anchors) that directly targeted by-name the canonical multi-class reviews and class-specific immune-effect studies. This recovered the 11 keepers without compromising filter discipline.
- Filter criteria applied (on sq3_anchors): "antibiotic effect on host innate immune response — immunomodulation, PAMP release, TLR/NLR/cGAS-STING changes, macrophage or neutrophil function, reviews of the topic", `--require 10`
- Excluded and why: dropped C. elegans microbiota-brain antibiotic paper (PMC11354627 — too distant from human macrophage focus); livestock vampire-bat microbiome immune paper (bio_8d758bca709d — out of scope); resistance mechanism reviews (covered in SQ2); routine antimicrobial spectrum/efficacy reviews.
- Keeper papers:
  - PMC4034004 | Anderson, Tintinger, Cockeran, Potjo, Feldman 2010 | multi-class antibiotic-innate immune integrative review (**anchor**)
  - PMC11605096 | Gross JL, Basu, Bradfield et al 2024 | bactericidal kill → DNA release → TLR9 → damaging inflammation; bacteriostatic kill spares this (**anchor**)
  - PMC9616545 | Lagos LS, Luu, De Haan, Faas, De Vos 2022 | direct in vitro test of TLR2/4 in monocytes/macrophages after amoxicillin, ciprofloxacin, doxycycline, erythromycin exposure (**anchor**)
  - PMC11117367 | Tosi, Coloretti, Meschiari, De Biasi, Girardis, Busani 2024 | comprehensive narrative review of antibiotic × immune response in sepsis (**anchor**, also feeds SQ4)
  - PMC11591424 | Snow TAC, Singer M, Arulkumaran N 2024 | antibiotic-induced immunosuppression with focus on cellular immunity / mitochondrial effects (**anchor**)
  - PMC3746177 | Aminov RI 2013 | "Biotic acts of antibiotics" — covers macrolide, tetracycline, β-lactam non-antimicrobial host effects (**anchor**)
  - PMC5859047 | Zimmermann P, Ziesenitz VC, Curtis N, Ritz N 2018 | macrolide immunomodulation systematic review (**anchor**, primary macrolide-row source)
  - PMC8563091 | Pollock J, Chalmers JD 2021 | macrolide immunomodulation in respiratory disease (**anchor**, bridges to SQ4)
  - PMC3388425 | Steel HC, Theron AJ, Cockeran R, Anderson R, Feldman C 2012 | pathogen- and host-directed anti-inflammatory activities of macrolides
  - PMC7423293 | Berti A, Rose W, Nizet V, Sakoulas G 2020 | "Antibiotics and Innate Immunity: A Cooperative Effort" (**anchor**)
  - PMC7666448 | Skorup P, Maudsdotter L, Lipcsey M, Larsson A, Sjölin J 2020 | mode of bacterial killing affects inflammation in porcine E. coli ICU sepsis model (**anchor**, in vivo bridge between SQ3 and SQ4)
  - PMC8312155 | "Vancomycin and daptomycin modulate innate immune response in murine LPS-induced sepsis" — daptomycin row source
  - bio_558b70756bfd | "Host-dependent induction of disease tolerance to infection by tetracycline antibiotics" — tetracycline disease-tolerance evidence

### Mechanism × immune-axis interaction table

| Antibiotic class | Macrophage / innate-immune effect | Mechanism of immune effect (if known) | Direction (pro- vs anti-inflammatory) | Strength of evidence (in vitro / animal / human) | Representative source (DOI/PMID) |
|---|---|---|---|---|---|
| β-lactams | Lytic kill → large release of free LPS, peptidoglycan, bacterial DNA → amplified TLR2/TLR4/TLR9 engagement; classic Jarisch-Herxheimer-type endotoxin surge after first dose | Autolysin-mediated lysis releases intact PAMPs; TLR9 sensing of released bacterial DNA shown to drive damaging inflammation in vivo (Gross 2024) | Pro-inflammatory (kill-burst) | Animal (mouse peritonitis, porcine sepsis); supported by in vitro and clinical observation | PMC11605096 / PMC7666448 / PMC4034004 |
| Glycopeptides (vancomycin) | Slow-killing; lower endotoxin/peptidoglycan release than β-lactams; modest direct immune-cell effects | Slow non-lytic killing; some described effects on neutrophil function and cytokine release | Mostly neutral; some pro-inflammatory in sepsis models | Animal (murine sepsis), in vitro | PMC8312155 / PMC11117367 |
| Lipopeptides (daptomycin) | Non-lytic kill, less PAMP release than β-lactams; described to modulate macrophage cytokine response | Membrane-disruptive killing without lysis; possible direct membrane-cholesterol interaction with immune cells | Mixed; some reports of dampened cytokine response in sepsis | Animal (murine LPS sepsis), in vitro | PMC8312155 / PMC3921582 |
| Polymyxins (colistin, polymyxin B) | Direct LPS binding and neutralization — sequesters circulating endotoxin (basis of polymyxin B haemoperfusion in sepsis) | Lipid A binding intercepts TLR4-MD2 engagement; also membrane-disruptive killing of bacteria | Anti-inflammatory (endotoxin neutralization) when extracellular LPS limited; pro-inflammatory when bacterial lysis dominates | In vitro + animal + limited human (polymyxin B haemoperfusion trials) | PMC4034004 / PMC11117367 |
| Aminoglycosides | Concentrate intracellularly in lysosomes; impair phagocyte function in some models; affect endothelial signaling | Lysosomal accumulation (gentamicin); inhibition of mitochondrial protein synthesis at supratherapeutic doses → effects on innate-immune-cell metabolism | Mixed; potential immunosuppression in vitro at high concentrations | In vitro; sparse animal | PMC11591424 / PMC4034004 |
| Macrolides (azithromycin, clarithromycin, erythromycin) | Best-established class-specific immunomodulation: dampens neutrophil chemotaxis and cytokine release, modulates NF-κB and AP-1, induces macrophage M2-like polarization, reduces mucin secretion, accelerates apoptosis of inflammatory cells | Accumulation in phagocytes (high intracellular:extracellular ratio); NF-κB / AP-1 inhibition; modulation of mitogen-activated protein kinase cascades; effects on epithelial barrier and ion channels | Anti-inflammatory (chronic dosing) | In vitro + animal + human (extensive RCT data — see SQ4) | PMC5859047 / PMC8563091 / PMC3388425 / PMC3746177 |
| Lincosamides (clindamycin) | Suppresses bacterial toxin synthesis (e.g., S. aureus PVL, exotoxins of S. pyogenes) — indirect "immune-modulatory" effect by reducing toxin-driven inflammation | Inhibition of bacterial 50S protein synthesis at sub-MIC concentrations abolishes toxin production before bacterial killing | Anti-inflammatory (via toxin reduction) | In vitro + clinical practice (adjunct in toxic shock) | PMC4034004 |
| Oxazolidinones (linezolid) | Anti-inflammatory cytokine modulation; suppresses cytokine release from immune cells; described inhibition of T-cell proliferation and NF-κB | Inhibition of host mitochondrial ribosomes at therapeutic concentrations (off-target on 50S-similar mitochondrial 39S); also affects bacterial toxin production | Anti-inflammatory | In vitro + animal | PMC6894011 / PMC11591424 |
| Tetracyclines (doxycycline, minocycline) | Independent anti-inflammatory and matrix-metalloproteinase-inhibitory effects; induces disease tolerance (mitigates infection-induced damage at sub-antimicrobial doses); modulates microglial / macrophage activation | MMP inhibition; mitochondrial protein synthesis inhibition; host-protein-synthesis effects independent of antimicrobial activity (Aminov 2013); disease-tolerance phenotype distinct from bacterial killing (bio_558b70756bfd) | Anti-inflammatory / tolerogenic | In vitro + animal + limited human (chronic doxycycline in rosacea, periodontitis) | PMC3746177 / bio_558b70756bfd |
| Fluoroquinolones (ciprofloxacin, moxifloxacin) | Cytokine modulation (variable: described to suppress IL-6, TNF-α at high concentrations; activate IL-2 / IFN-γ in some contexts); attenuates TLR-dependent cytokine release | Likely partial action on host topoisomerase II at supratherapeutic doses; effects on mitochondrial function; Lagos 2022 showed reduced TLR2/4 readouts in monocytes after ciprofloxacin | Mixed; net anti-inflammatory at clinical concentrations in vitro | In vitro (Lagos 2022); animal sparse | PMC9616545 / PMC4034004 |
| Rifamycins (rifampin) | Concentrates intracellularly; immunomodulatory effects in mycobacterial granulomas; some described effects on T-cell function | Intracellular accumulation; suppression of pro-inflammatory cytokine release in some contexts | Mixed (likely anti-inflammatory at standard doses) | In vitro + animal | PMC4034004 |
| Mode-of-killing axis (across classes) | Bactericidal/lytic kill releases more bacterial DNA, peptidoglycan, LPS → amplified TLR9/TLR2/TLR4 signaling; bacteriostatic kill preserves bacterial cell integrity → blunted DAMP/PAMP burst; mortality and inflammation can be higher in bactericidal-treated cohorts in some models | Bacterial DNA released only by cidal treatments engages TLR9 (Gross 2024); confirmed in porcine sepsis (Skorup 2020) where mode of kill — not bacterial load reduction — predicted organ dysfunction | Bactericidal → pro-inflammatory; bacteriostatic → blunted | Animal (mouse, pig); in vitro | PMC11605096 / PMC7666448 / PMC7423293 |
| Intracellular-pathogen-handling axis | Some antibiotics modulate phagosome maturation, autophagy, and macrophage antimicrobial state independent of bacterial killing (e.g., bedaquiline shown to enhance host macrophage antimicrobial response) | Drug-induced shifts in macrophage metabolism, mitochondrial function, autophagy regulation | Pro-microbicidal (host-direction) | In vitro + animal | PMC7200153 (bedaquiline) / PMC11591424 |

### Paragraph answer

The evidence supports a real but uneven set of mechanism-class × innate-immune-axis interactions. The **strongest signal** is for macrolides, which have well-replicated anti-inflammatory effects in vitro, in animal models, and in humans — including reduced neutrophil chemotaxis and cytokine release, NF-κB/AP-1 modulation, and macrophage polarization shifts — that are clearly distinguishable from antimicrobial activity (PMC5859047, PMC3388425, PMC8563091). The **second strongest signal** is for the mode-of-killing axis itself: bactericidal lytic agents (β-lactams in particular) release intact PAMPs — peptidoglycan, LPS, and bacterial DNA — that amplify TLR2/TLR4/TLR9 signaling, while bacteriostatic agents (tetracyclines, oxazolidinones, chloramphenicol) preserve bacterial cell integrity and produce a blunted PAMP burst (PMC11605096, PMC7666448). Gross et al 2024 provides clean mechanistic evidence that bacterial DNA released by bactericidal treatment specifically drives TLR9-mediated damaging inflammation in vivo, and that ablating TLR9 rescues bactericidal drug efficacy. **Class-specific effects beyond the mode-of-killing signal** include tetracycline-driven disease tolerance and MMP inhibition (bio_558b70756bfd, PMC3746177), polymyxin endotoxin neutralization (basis of the polymyxin B haemoperfusion adjunct), clindamycin toxin-synthesis inhibition (an indirect immune-modulatory effect well-established in toxic-shock management), oxazolidinone mitochondrial-ribosome-mediated immunosuppression (PMC11591424, PMC6894011), and rifamycin / fluoroquinolone intracellular accumulation with cytokine-modulatory effects. The **major fault line** is whether non-macrolide mechanism-class effects are large enough — at clinical concentrations and in human disease — to matter beyond bacterial killing. Many reported effects (fluoroquinolone cytokine modulation, aminoglycoside immune effects) use supratherapeutic in vitro concentrations and have not been replicated in human studies. The most secure conclusion is that **mode of killing (bactericidal/lytic vs bacteriostatic/non-lytic) is a real and underappreciated determinant of innate immune response**, while **drug-specific direct receptor effects are well-established only for macrolides** and convincingly described for tetracyclines.

### Synthesis bullets
- **Best-established class-specific immunomodulatory effects:** macrolides (NF-κB modulation, neutrophil effects, macrophage M2 shift) and tetracyclines (MMP inhibition, disease tolerance) have the strongest convergent in vitro + animal + human evidence.
- **Hypotheses that have proven harder to replicate:** generalized "bactericidal worse than bacteriostatic in sepsis" claims have not been borne out in head-to-head clinical comparisons even though mechanism is clear in animal models (Gross 2024 mouse, Skorup 2020 pig). Aminoglycoside phagocyte-function effects, while described in vitro, have not translated cleanly into clinical phenotypes.
- **Methodological caveats:** in vitro studies often use concentrations 10-100× clinically relevant peaks; many effects described in vitro disappear at clinical free-drug concentrations. Mitochondrial-ribosome off-target effects (linezolid, tetracyclines, aminoglycosides) are real but mostly relevant at prolonged exposure or supratherapeutic dosing (PMC11591424). The macrolide-respiratory-disease evidence base is unique in having long-duration human RCT data at clinically realistic doses — this is why it stands out.

### Confidence read
- **Evidence quality:** Strong for macrolide immunomodulation (canonical) and for the mode-of-killing axis (mechanistically clean but clinically unsettled); moderate-to-thin for tetracycline disease tolerance and polymyxin endotoxin neutralization; weak for fluoroquinolone, aminoglycoside, and glycopeptide direct immune effects at clinical doses.
- **Direction of evidence:** Reasonably consistent across in vitro and animal-model lines; clinical translation is uneven.
- **Key uncertainty:** Whether bactericidal-vs-bacteriostatic class choice meaningfully affects human infection outcomes via the TLR9 / PAMP-release axis described in Gross 2024 — that paper is the cleanest demonstration of the mechanism, but extension to human sepsis (where infection burden, source control, and antibiotic timing dominate) remains untested in a properly powered trial. This is the single most actionable open question.

---

## Sub-Question 4: Clinical literature on whether these effects matter in real-world human infection

**Scope constraint:** Surface clinical studies that specifically engage with the question of whether antibiotic class affects host immune response or infection resolution beyond direct antimicrobial activity. Anchor searches to the specific mechanism-immune-response interactions surfaced in SQ3.

### Search and filter notes
- Search terms used (parallel + targeted):
  1. "azithromycin chronic obstructive pulmonary disease exacerbation prophylaxis randomized"
  2. "macrolide community acquired pneumonia adjunct beta-lactam combination mortality"
  3. "azithromycin bronchiectasis non-cystic fibrosis exacerbation BAT EMBRACE randomized"
  4. "polymyxin B hemoperfusion sepsis endotoxin EUPHRATES trial"
  5. "clindamycin toxic shock streptococcus aureus antitoxin clinical"
  6. "bactericidal bacteriostatic clinical comparison meta-analysis sepsis mortality"
  7. "antibiotic immune modulation pneumonia outcome trial clinical"
- Result IDs: s_c402165d (azithromycin COPD), s_178ad1d6 (macrolide CAP), s_5da30bf0 (bronchiectasis), s_0d534258 (polymyxin B), s_ea573c4b (clindamycin/TSS), s_e4a6e2ff (bactericidal/static)
- Filter criteria applied: anchor-by-name approach used because parallel-search filters were dominated by AMR/efficacy non-inferiority papers; instead selected papers that explicitly engage the mechanism-class × host-response question.
- Excluded and why: routine non-inferiority efficacy trials (e.g., generic moxifloxacin-vs-amoxicillin RCTs); AMR-only papers; non-clinical structural/membrane biophysics; cystic-fibrosis-specific azithromycin trials (CF biology distinct from non-CF bronchiectasis); studies whose primary outcome was bacterial eradication rather than immune-mediated outcome.
- Keeper papers:
  - PMC9555173 | Li K, Liu L, Ou Y 2022 | meta-analysis of azithromycin RCTs for non-CF bronchiectasis exacerbation prevention (**SQ4 macrolide-respiratory anchor**)
  - PMC9606520 | Ahmadian S, Sin DD, Lynd L, Harrison M, Sadatsafavi M 2022 | Markov benefit-harm analysis of azithromycin for COPD exacerbation prevention
  - PMC4141795 | Simpson JL et al 2014 | azithromycin in stable neutrophilic COPD RCT — primary outcome (airway neutrophils) not significantly reduced; trend toward fewer severe exacerbations (informative negative)
  - PMC4413845 | Corris PA et al 2015 | azithromycin in bronchiolitis obliterans syndrome post-lung-transplant RCT — improved FEV1
  - PMC5329050 | Segal LN et al 2017 | RCT of azithromycin in emphysema — altered lung microbiome and metabolome, shifted to anti-inflammatory bacterial metabolites that blunted macrophage inflammatory response in vitro (**human mechanistic evidence**)
  - PMC11405424 | Bucci T et al 2024 | low-dose azithromycin prophylaxis in atrial fibrillation + COPD — reduced cardiovascular and hemorrhagic events post-exacerbation (anti-inflammatory framing)
  - PMC11998547 | Wei J, Walker AS, Eyre DW 2025 | adding macrolides to β-lactam for hospital CAP — EHR analysis, no clinical-outcome benefit (informative negative; tempers macrolide-CAP enthusiasm)
  - PMC5143302 | Lee JH, Kim HJ, Kim YH 2017 | meta-analysis β-lactam + macrolide vs β-lactam + fluoroquinolone in severe CAP — lower mortality with macrolide combo (limited by study bias)
  - PMC11695898 | Ishak A et al 2025 | bactericidal-vs-bacteriostatic clinical-significance review (**SQ4 bactericidal/static anchor**)
  - PMC7666448 | Skorup P, Maudsdotter L, Lipcsey M, Larsson A, Sjölin J 2020 | porcine sepsis mode-of-killing study — bridges SQ3 mechanism to clinical-relevance question (**also SQ3**)
  - PMC4066268 | Klein DJ et al 2014 | EUPHRATES polymyxin B haemoperfusion RCT protocol
  - PMC12751791 | Iba T, Helms J, Nagaoka I, Mineshima M, Ferrer R 2025 | TIGRIS + EUPHRATES post-hoc / narrative review — polymyxin B haemoperfusion survival benefit confined to high-endotoxin, high-organ-dysfunction subgroup
  - PMC7100837 | Steer AC, Lamagni T, Curtis N, Carapetis JR 2012 | invasive Group A streptococcal disease review — clindamycin antitoxin / adjunct evidence in toxic shock
  - PMC11900332 | Asbjarnarson A et al (Parnham co-author) 2025 | non-antibacterial macrolide effects on bronchial epithelial barrier and cellular differentiation (human cell evidence supporting SQ3 mechanism in clinical setting)

### Clinical evidence table

| Study | Design | N | Population | Antibiotic class(es) compared | Mechanism hypothesis tested | Primary outcome | Effect | Implication for the mechanism question | DOI/PMID |
|---|---|---|---|---|---|---|---|---|---|
| Li 2022 meta-analysis | Meta-analysis of RCTs of azithromycin in non-CF bronchiectasis | Multiple RCTs (EMBRACE, BLESS, BAT) pooled | Adults with non-CF bronchiectasis | Macrolide (azithromycin) vs placebo | Chronic macrolide immunomodulation reduces exacerbations independent of antimicrobial effect | Exacerbation rate | Significant reduction in exacerbations; no significant change in lung function | Strongest cumulative clinical evidence for macrolide immunomodulation in chronic airway disease | PMC9555173 |
| Ahmadian 2022 Markov | Decision-analytic Markov model | Simulated cohort | COPD patients with prior exacerbations | Azithromycin maintenance vs no maintenance | Net benefit of chronic azithromycin for COPD | QALYs gained per patient | Net QALY gain, particularly for frequent exacerbators | Supports clinical use of azithromycin as exacerbation-preventive (likely via immunomodulation given low antimicrobial pressure of pulse dosing) | PMC9606520 |
| Simpson 2014 (AMAZES-precursor) | Randomized, double-blind, placebo-controlled trial | 45 | Stable neutrophilic COPD | Azithromycin vs placebo (12 wk) | Macrolide reduces airway neutrophilia and inflammation | Airway neutrophils; secondary: exacerbations | Primary outcome NOT significant; trend toward fewer severe exacerbations | Informative negative for short-term immunomodulation; longer-duration trials needed | PMC4141795 |
| Segal 2017 emphysema RCT | RCT azithromycin in emphysema with microbiome / metabolome analysis | n=~20 (mechanistic substudy) | Emphysema | Azithromycin vs placebo | Macrolide shifts lung microbiome and metabolome toward anti-inflammatory state | Microbiome composition, metabolome, macrophage inflammatory response (in vitro readout from BAL) | Selection for anti-inflammatory bacterial metabolites that blunted macrophage inflammation | First human mechanistic evidence that macrolide benefit may be partly microbiome-mediated, not direct host effect | PMC5329050 |
| Corris 2015 BOS RCT | RCT azithromycin in bronchiolitis obliterans syndrome post lung transplant | 48 | Lung transplant recipients with BOS | Azithromycin vs placebo (12 wk) | Macrolide stabilizes or improves graft function via immunomodulation | FEV1 | Significant FEV1 improvement | Supports clinical macrolide immunomodulation in non-infectious airway inflammation | PMC4413845 |
| Bucci 2024 AF+COPD cohort | Retrospective cohort + propensity matching | Large EHR cohort | Atrial fibrillation patients with COPD exacerbation | Azithromycin prophylaxis vs no | Macrolide reduces inflammatory-driven cardiovascular events | Cardiovascular and hemorrhagic events | Reduced CV and hemorrhagic events | Extends macrolide immunomodulation benefit to cardiovascular outcomes (mechanism-relevant but unblinded) | PMC11405424 |
| Wei 2025 EHR (CAP) | EHR-based comparative analysis | ~tens of thousands | Hospitalized CAP adults | β-lactam + macrolide vs β-lactam monotherapy | Macrolide adjunct provides additional benefit beyond antimicrobial coverage | Mortality, time to discharge | No significant benefit of macrolide addition | Tempers immune-modulation argument in acute CAP; benefit may be confined to severe CAP / outpatient | PMC11998547 |
| Lee 2017 severe CAP meta-analysis | Meta-analysis of comparative cohorts | Multi-cohort | Severe CAP | β-lactam + macrolide vs β-lactam + fluoroquinolone | If macrolide signal is real, BL+M should outperform BL+F | Mortality, hospital LOS | BL+M lower mortality and shorter LOS; bias-limited | Suggests macrolide benefit in severe CAP exceeds fluoroquinolone alternative — supports immunomodulation hypothesis | PMC5143302 |
| Ishak 2025 review | Narrative + integrative review | n/a | All bacterial infections | Bactericidal vs bacteriostatic | Clinical relevance of bactericidal/static dichotomy | Pooled outcome assessment | Bacteriostatic non-inferior to bactericidal in most contexts | Undermines decades-old preference for bactericidal in serious infection; supports SQ3 hypothesis that bactericidal-lytic kill can be pro-inflammatory | PMC11695898 |
| Skorup 2020 porcine sepsis | Controlled in vivo (porcine) experimental sepsis | n=27 pigs | Porcine E. coli ICU-grade sepsis | Bactericidal-killed vs heat-killed vs live bacteria | Mode of killing — not bacterial load — drives inflammation | Inflammatory cytokines, organ dysfunction | Antibiotic-killed cohort > heat-killed > live for inflammatory burden and organ dysfunction | Strongest large-animal evidence that mode of bacterial killing has independent inflammatory consequence — translational bridge from Gross 2024 mouse data | PMC7666448 |
| Klein 2014 EUPHRATES protocol | RCT protocol | Planned ~360 | Endotoxemic septic shock | Polymyxin B haemoperfusion + standard care vs standard care | Direct LPS removal reduces 28-day mortality | 28-day all-cause mortality | (Main trial: overall null; signal in subgroup) | Direct test of "intercept LPS to blunt TLR4-driven sepsis" mechanism — established the trial design that subsequent positive-subgroup work built on | PMC4066268 |
| Iba 2025 TIGRIS+EUPHRATES narrative | Narrative review combining TIGRIS RCT and EUPHRATES post-hoc | Cross-trial | Septic shock with high endotoxin activity + multi-organ failure | Polymyxin B haemoperfusion adjunct | LPS removal benefits a defined-subgroup of septic shock | Mortality in high-endotoxin / high-organ-dysfunction subgroup | Survival benefit confined to defined high-endotoxin subgroup | Confirms mechanism is clinically real but only in selected patients — biomarker-guided application | PMC12751791 |
| Steer 2012 GAS review | Narrative review of invasive group A streptococcal disease | n/a | Invasive GAS infection / streptococcal TSS | β-lactam ± clindamycin (adjunct) | Clindamycin reduces toxin production beyond antimicrobial killing | Outcome in invasive GAS / TSS | Recommends clindamycin adjunct for invasive GAS / TSS based on toxin-suppression mechanism + observational outcome data | Clinical practice has internalized the SQ3 mechanism for clindamycin-toxic-shock; this is the cleanest mechanism-to-bedside example outside macrolides | PMC7100837 |
| Asbjarnarson 2025 | In vitro on human bronchial epithelial cells | n/a (cell-based) | Bronchial epithelium | Azithromycin and other macrolides | Macrolide non-antibacterial effects on epithelial barrier and differentiation | Barrier integrity, differentiation markers | Macrolides enhanced barrier integrity; influenced differentiation pathways | Provides cellular-mechanism support in human-derived cells for the chronic-airway clinical benefit | PMC11900332 |

### Paragraph answer

The clinical evidence base divides into three tiers of strength. **Strongest**: macrolide immunomodulation in chronic airway disease — non-CF bronchiectasis (meta-analyses of EMBRACE, BLESS, and BAT-type RCTs, PMC9555173), COPD exacerbation prevention (Markov benefit-harm analyses building on Albert 2011 NEJM and subsequent RCTs, PMC9606520), and post-transplant BOS (PMC4413845) — together establish that chronic low-dose azithromycin reduces exacerbations and stabilizes graft function in ways that cannot be explained by antimicrobial spectrum alone. Mechanistic support in humans comes from Segal 2017 (microbiome-mediated anti-inflammatory metabolite shift in emphysema, PMC5329050) and recent in-vitro human-cell work on epithelial barrier effects (PMC11900332). **Intermediate**: clindamycin adjunct in invasive Group A streptococcal disease and toxic shock has translated the SQ3 toxin-suppression mechanism into routine practice (PMC7100837), and polymyxin B haemoperfusion shows a defined-subgroup survival benefit when used in high-endotoxin, high-organ-dysfunction septic shock (PMC12751791, building on PMC4066268 EUPHRATES) — though this is biomarker-restricted. **Weakest / contested**: bactericidal-vs-bacteriostatic class effect on clinical outcome is mechanistically plausible (Gross 2024 mouse, Skorup 2020 pig) but the recent Ishak 2025 review concludes bacteriostatics are non-inferior in most clinical contexts (PMC11695898) — implying that whatever mechanism-class immune effect exists in animal models, it is generally outweighed by source control, bacterial load, and antibiotic timing in humans. Macrolide adjunct in routine hospitalized CAP is also showing no benefit in well-controlled EHR analyses (PMC11998547), tempering enthusiasm for the macrolide signal in acute (rather than chronic) lung disease. Net: **the mechanism-class signal survives in chronic airway disease (macrolides), in defined-mechanism contexts (clindamycin in TSS, polymyxin B in high-endotoxin septic shock), and is real but clinically unsettled for the bactericidal/static dichotomy in sepsis.**

### Synthesis bullets
- **Well-established mechanism-class clinical signals:** macrolide prophylaxis in non-CF bronchiectasis and COPD (broad RCT evidence); clindamycin in TSS (mechanism-driven practice); polymyxin B haemoperfusion in high-endotoxin septic shock (biomarker-guided).
- **Plausible but undertested:** the bactericidal-vs-bacteriostatic axis in sepsis (mouse and pig mechanistic data are clean, but no adequately powered human RCT exists that specifically tests the TLR9 / PAMP-release hypothesis from Gross 2024).
- **Where the evidence does not support a clinically meaningful effect:** routine macrolide addition to β-lactam in non-severe CAP (PMC11998547); short-term azithromycin in stable neutrophilic COPD (PMC4141795); broad bactericidal-superiority claims in sepsis (PMC11695898).

### Confidence read
- **Evidence quality:** Strong (RCT + meta-analysis) for macrolide chronic-airway disease; moderate (mixed RCT + observational) for polymyxin B haemoperfusion and clindamycin/TSS; weak (mostly mechanistic with no powered human RCT) for bactericidal/static effect in human sepsis.
- **Direction of evidence:** Consistent in chronic airway disease; mixed in acute lung infection; null-to-mechanism-positive in sepsis depending on subgroup.
- **Key uncertainty:** Whether a future RCT explicitly testing bactericidal-vs-bacteriostatic in human Gram-negative bacteraemia / sepsis with a TLR9-pathway readout would replicate the Gross 2024 mouse finding. Also whether the macrolide-COPD signal owes more to direct host effects or to microbiome-mediated metabolite shifts (Segal 2017 framework).

---

## Cross-Cutting Observations

- **The bacterial-DNA-via-TLR9 axis is the most coherent integrative finding across SQ1, SQ2, and SQ3.** TLR9 sensing of unmethylated bacterial CpG DNA (SQ1) intersects directly with the lytic-vs-non-lytic mechanism axis (SQ2): bactericidal lytic kill releases bacterial DNA that drives TLR9-mediated damaging inflammation (Gross 2024 / PMC11605096), and TLR9 ablation rescues bactericidal drug efficacy in mouse peritonitis. Porcine sepsis data (Skorup 2020 / PMC7666448) confirm a mode-of-killing effect on inflammation independent of bacterial load. Human RCT data testing this specific mechanism do not yet exist.
- **In vitro vs clinical concentration divergence is a pervasive caveat for SQ3.** Many class-specific immune effects (fluoroquinolone cytokine modulation, aminoglycoside phagocyte dysfunction, linezolid mitochondrial-ribosome off-target inhibition) are reproducibly demonstrated at supratherapeutic concentrations but disappear or shrink at free-drug concentrations achievable in human plasma. The macrolide-respiratory evidence base is unique because the chronic-low-dose paradigm achieves intracellular concentrations in phagocytes that approach in vitro experimental ranges — explaining why it translates to clinical benefit while other class-specific in vitro effects do not.
- **Notable conflict — macrolide adjunct in CAP.** SQ4 evidence is split: meta-analyses of severe CAP suggest a β-lactam+macrolide mortality benefit over β-lactam+fluoroquinolone (PMC5143302), supporting an immunomodulation hypothesis, yet recent large EHR analysis in hospitalized (non-severe) CAP finds no clinical-outcome benefit from adding macrolide (PMC11998547). The reconciliation is probably severity-dependent: macrolide immunomodulation matters where the inflammatory burden is high enough to dominate outcome (severe CAP, COPD exacerbation cycles), and is overshadowed by source control and antimicrobial coverage in less inflammatory disease.
- **Notable absence — properly powered head-to-head bactericidal-vs-bacteriostatic RCT in Gram-negative bacteraemia with a TLR9 or PAMP-load readout.** The Gross 2024 mechanism is the most compelling new lever for antibiotic-immune translational work and the human evidence base does not yet exist. This is a clear research gap on the basis of this digest.
- **Methodological theme — translational gap from animal to clinical.** Mouse peritonitis (Gross), pig sepsis (Skorup), C. elegans microbiota (Wu) and human EHR/RCT data are all present in this literature but rarely speak directly to each other. The mode-of-killing axis is strong in animal models, contested in human practice. The macrolide-respiratory axis is the inverse: strong in human RCTs but the molecular mechanism remains incompletely mapped despite decades of in vitro work.
- **Notable absence — clinical trial of polymyxin B haemoperfusion stratified prospectively by Gross-2024-style PAMP-release readout** rather than endotoxin-activity assay alone. Iba 2025 (PMC12751791) shows the EUPHRATES/TIGRIS combined evidence points to a defined subgroup; whether a TLR9-PAMP burden biomarker would further refine that subgroup is an open question.

---

## Verification Anchors

Format: `paper_id : L<line> : <quoted phrase or specific fact>`

- PMC11605096 : L10 : "We observed a bacteriostatic (growth halting) treatment was more protective than a bactericidal (bacteria killing) treatment in a murine peritonitis model. ... Bacterial DNA – released only by bactericidal treatments – exacerbated inflammatory signaling through TLR9. Without TLR9 signaling, the in vivo efficacy of bactericidal drug treatment was rescued."
- PMC11605096 : L15 : "There are two broad mechanistic categories of antibiotics: bactericidal (cidal) drugs that directly kill bacteria and bacteriostatic (static) drugs that inhibit bacterial growth without causing death ... A comprehensive meta-analysis found no intrinsic superiority of bactericidal compared to bacteriostatic agents when prescribed appropriately."
- PMC11605096 : L44 : "We repeated this experiment with Tlr9 −/− iBMDMs and found that killed bacteria were unable to elicit the enhanced inflammatory output observed in WT macrophages ... TNF remained at a consistent level in Tlr9 −/− iBMDMs, independent of the static drug dose and the resulting viability of the bacteria."
- PMC7666448 : L9 : "Sepsis is often treated with penicillin-binding protein 3 (PBP-3) acting β-lactam antibiotics, such as piperacillin-tazobactam, cefotaxime, and meropenem. They cause considerable bacterial structural changes and have in vitro been associated with an increased inflammatory response. In a clinically relevant large animal sepsis model, our primary aim was to investigate whether bacteria killed by a PBP-3-active antibiotic has a greater effect on the early inflammatory response and organ dysfunction compared with corresponding amounts of live or heat-killed bacteria."
- PMC9616545 : L12 : "To investigate whether antibiotics alter TLR2/1, TLR2/6 and TLR4 activity in immune cells." (Lagos 2022 — direct in vitro test of four mechanism classes on TLR signaling)
- PMC4368383 : L13 : "Surface PRRs include C-type lectins, mannose receptor (MR), dectin 1, dectin 2, Mincle, MCL, DC-SIGN, and scavenger receptors such as SR-A and MARCO ... Mannose-capped lipoarabinomannan (manLAM), phosphatidyl inositol mannosides (PIMs), as well as trehalose dimycolate (TDM) are mycobacterial ligands for MR, DC-SIGN, Mincle, and MCL, respectively. The Toll-like receptors (TLRs) 1/2, 2/6, 4, 5, and 9, are specific for lipopeptides, lipopolysaccharides, flagellin, and low-methylated DNA sugar backbone, respectively, with TLR2/6 and 9 as the pivotal PRRs for mycobacteria."
- PMC11385170 : L27 : "Mice lacking TIRAP demonstrate normal responsiveness to TLR5, TLR7 and TLR9 ligands ... However, they exhibit deficiencies in cytokine production and activation of NF-κB and MAPKs in response to TLR4 ligand ... they have impaired responses to ligands for TLR2, TLR1 and TLR6, suggesting that TIRAP plays a distinctive role in the signaling of various TLR members."
- PMC11385170 : L28 : "TIRAP is essential for recruiting MyD88 to TLR2 and TLR4 and is anchored to the membrane through a phosphatidylinositol-4,5-bisphosphate-binding domain ... Several transcription factors such as NF-κB and AP-1 get activated as a result of downstream signaling events."
- PMC12246121 : L9 : "This review examines the classification, structure, and signaling cascades of key PRR families, including toll-like receptors (TLRs), C-type lectin receptors (CLRs), nucleotide-binding oligomerization domain-like receptors (NLRs), AIM2-like receptors (ALRs), and others ... Notable signaling pathways, including NF-κB, MAPK, cGAS-STING, and MYD88-mediated and non-MYD88-mediated cascades, are discussed."
- PMC9555173 : L6 : "The efficacy of azithromycin to prevent exacerbation for non-cystic fibrosis bronchiectasis remains controversial. We conduct this meta-analysis to explore the influence of azithromycin versus placebo for the treatment of non-cystic fibrosis bronchiectasis." (primary clinical anchor for macrolide-bronchiectasis benefit)
- PMC8563091 : L14 : "Given the success of macrolides in DPB and their subsequent use in other lung diseases ... the immunomodulatory properties of macrolides have been most widely explored in lung conditions ... [traditional anti-inflammatory therapies] in neutrophil-dominant disease may exacerbate disease ... There is no effective neutrophil-targeted anti-inflammatory therapy ... Macrolides have been suggested as a potential treatment particularly for neutrophilic lung diseases."
- PMC5859047 : L27 : "Only studies in humans, in which the participants received one of the four mentioned macrolides and which investigated immunological markers involved in inflammation were included. Studies reporting clinical endpoints only or studies in which macrolides were investigated for their antimicrobial activity were excluded." (Zimmermann 2018 systematic review of human macrolide immunomodulation studies — methodological anchor)
- PMC11695898 : L1 : "Bactericidal versus bacteriostatic antibacterials: clinical significance, differences and synergistic potential in clinical practice" (anchor for the SQ4 conclusion that bactericidal is not intrinsically clinically superior)
- PMC12751791 : L1 : "TIGRIS and EUPHRATES eventually join and provide new evidence: a narrative review of the polymyxin B hemoperfusion" — anchor for the SQ4 conclusion that polymyxin B haemoperfusion benefit is confined to defined high-endotoxin subgroup.
- PMC5329050 : L1 : "Randomised, double-blind, placebo-controlled trial with azithromycin selects for anti-inflammatory microbial metabolites in the emphysematous lung" — human mechanistic anchor for macrolide microbiome-mediated anti-inflammation.

---

## Bibliography

(Alphabetical by first author. Generated manually via `paperclip lookup` and inspection of search outputs.)

- Aminov RI. "Biotic acts of antibiotics." *Frontiers in Microbiology*, 2013. PMC3746177. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3746177/
- Anderson R, Tintinger G, Cockeran R, Potjo M, Feldman C. "Beneficial and Harmful Interactions of Antibiotics with Microbial Pathogens and the Host Innate Immune System." 2010. PMC4034004. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4034004/
- Ahmadian S, Sin DD, Lynd L, Harrison M, Sadatsafavi M. "Benefit–harm analysis of azithromycin for the prevention of acute exacerbations of chronic obstructive pulmonary disease." *Thorax*, 2022. PMC9606520. doi:10.1136/thoraxjnl-2021-217962
- Asbjarnarson A, Joelsson JP, Gardarsson FR, Sigurdsson S, Parnham MJ et al. "The Non-Antibacterial Effects of Azithromycin and Other Macrolides on the Bronchial Epithelial Barrier and Cellular Differentiation." 2025. PMC11900332. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11900332/
- Berti A, Rose W, Nizet V, Sakoulas G. "Antibiotics and Innate Immunity: A Cooperative Effort Toward the Successful Treatment of Infections." *Open Forum Infect Dis*, 2020. PMC7423293. doi:10.1093/ofid/ofaa302
- Bucci T, Wat D, Sibley S, Wootton D, Green D, Pignatelli P, Lip GYH. "Low-dose azithromycin prophylaxis in patients with atrial fibrillation and chronic obstructive pulmonary disease." 2024. PMC11405424. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11405424/
- Chen R, Zou J, Chen J, Zhong X, Kang R, Tang D. "Pattern recognition receptors: function, regulation and therapeutic potential." *Signal Transduction and Targeted Therapy*, 2025. PMC12246121. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12246121/
- Corris PA, Ryan VA, Small T, Lordan J, Fisher AJ, Meachery G et al. "A randomised controlled trial of azithromycin therapy in bronchiolitis obliterans syndrome (BOS) post lung transplantation." *Thorax*, 2015. PMC4413845. doi:10.1136/thoraxjnl-2014-205998
- Daptomycin two-mechanism preprint. "The last resort antibiotic daptomycin exhibits two independent antibacterial mechanisms of action." bioRxiv. bio_014d5af66cdb.
- Eldridge MJG et al. "Human macrophages utilize a wide range of pathogen recognition receptors to recognize Legionella pneumophila ..." 2021. PMC8321404. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8321404/
- Gil-Marqués ML, Devant P, Kagan JC, Goldberg MB. "Pattern Recognition Receptor for Bacterial Lipopolysaccharide in the Cytosol of Human Macrophages." bioRxiv 2021. bio_56e9957f6d01. doi:10.1101/2021.10.22.465470
- Gross JL, Basu R, Bradfield CJ, Sun J, John SP, Das S, Dekker JP et al. "Bactericidal antibiotic treatment induces damaging inflammation via TLR9 sensing of bacterial DNA." 2024. PMC11605096. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11605096/
- Herb M, Schramm M. "Functions of ROS in Macrophages and Antimicrobial Immunity." 2021. PMC7923022. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7923022/
- Holley CL et al. "Detecting DNA: An Overview of DNA Recognition by Inflammasomes and Protection against Bacterial Respiratory Infections." 2022. PMC9139316. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9139316/
- Iba T, Helms J, Nagaoka I, Mineshima M, Ferrer R. "TIGRIS and EUPHRATES eventually join and provide new evidence: a narrative review of the polymyxin B hemoperfusion." 2025. PMC12751791. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12751791/
- Ishak A, Mazonakis N, Spernovasilis N, Akinosoglou K, Tsioutis C et al. "Bactericidal versus bacteriostatic antibacterials: clinical significance, differences and synergistic potential in clinical practice." *J Antimicrob Chemother*, 2025. PMC11695898. doi:10.1093/jac/dkae380
- Kapoor G, Saigal S, Elongavan A. "Action and resistance mechanisms of antibiotics: A guide for clinicians." 2017. PMC5672523. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5672523/
- Kelesidis T. "The Interplay between Daptomycin and the Immune System." 2014. PMC3921582. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3921582/
- Klein DJ, Foster D, Schorr CA, Kazempour K, Walker PM, Dellinger RP. "The EUPHRATES trial ... study protocol for a randomized controlled trial." 2014. PMC4066268. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4066268/
- Lagos LS, Luu TV, De Haan B, Faas M, De Vos P. "TLR2 and TLR4 activity in monocytes and macrophages after exposure to amoxicillin, ciprofloxacin, doxycycline and erythromycin." *J Antimicrob Chemother*, 2022. PMC9616545. doi:10.1093/jac/dkac254
- Lee JH, Kim HJ, Kim YH. "Is β-Lactam Plus Macrolide More Effective than β-Lactam Plus Fluoroquinolone among Patients with Severe Community-Acquired Pneumonia?: a Systemic Review and Meta-Analysis." 2017. PMC5143302. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5143302/
- Li K, Liu L, Ou Y. "The efficacy of azithromycin to prevent exacerbation of non-cystic fibrosis bronchiectasis: a meta-analysis of randomized controlled studies." 2022. PMC9555173. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9555173/
- Mosaei H, Molodtsov V, Kepplinger B, Harbottle J, Moon CW, Rose E et al. "Mode of Action of Kanglemycin A, an Ansamycin Natural Product that Is Active against Rifampicin-Resistant Mycobacterium tuberculosis." 2018. PMC6202310. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6202310/
- Moubareck CA. "Polymyxins and Bacterial Membranes: A Review of Antibacterial Activity and Mechanisms of Resistance." 2020. PMC7463838. doi:10.3390/membranes10080181
- "MyD88-Dependent Signaling Drives Toll-Like Receptor-Induced Trained Immunity in Macrophages." bioRxiv 2022. bio_e15726726c18. doi:10.1101/2022.08.23.504963
- Pollock J, Chalmers JD. "The immunomodulatory effects of macrolide antibiotics in respiratory disease." *Pulm Pharmacol Ther*, 2021. PMC8563091. doi:10.1016/j.pupt.2021.102095
- "R. equi elicits type I interferons by engaging cytosolic DNA sensing in macrophages." bioRxiv 2021. bio_3c40e0c96d3d / PMC8443056. doi:10.1101/2021.03.28.437424
- Rughetti A, Bharti S, Savai R, Barmpoutsi S, Weigert A, Atre R et al. "Imperative role of adaptor proteins in macrophage toll-like receptor signaling pathways." *Future Sci OA*, 2024. PMC11385170. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11385170/
- Segal LN, Clemente JC, Wu BG, Wikoff WR, Gao Z, Li Y, Ko JP et al. "Randomised, double-blind, placebo-controlled trial with azithromycin selects for anti-inflammatory microbial metabolites in the emphysematous lung." 2017. PMC5329050. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5329050/
- Simpson JL, Powell H, Baines KJ, Milne D, Coxson HO, Hansbro PM, Gibson PG et al. "The Effect of Azithromycin in Adults with Stable Neutrophilic COPD: A Double Blind Randomised, Placebo Controlled Trial." 2014. PMC4141795. doi:10.1371/journal.pone.0105609
- Skorup P, Maudsdotter L, Lipcsey M, Larsson A, Sjölin J. "Mode of bacterial killing affects the inflammatory response and associated organ dysfunctions in a porcine E. coli intensive care sepsis model." *Crit Care*, 2020. PMC7666448. doi:10.1186/s13054-020-03303-9
- Snow TAC, Singer M, Arulkumaran N. "Antibiotic-Induced Immunosuppression — A Focus on Cellular Immunity." *Antibiotics*, 2024. PMC11591424. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11591424/
- Steel HC, Theron AJ, Cockeran R, Anderson R, Feldman C. "Pathogen- and Host-Directed Anti-Inflammatory Activities of Macrolide Antibiotics." 2012. PMC3388425. doi:10.1155/2012/584262
- Steer AC, Lamagni T, Curtis N, Carapetis JR. "Invasive Group A Streptococcal Disease." 2012. PMC7100837. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7100837/
- Tetracycline disease-tolerance preprint. "Host-dependent induction of disease tolerance to infection by tetracycline antibiotics." bioRxiv. bio_558b70756bfd.
- "The Membrane Steps of Bacterial Cell Wall Synthesis as Antibiotic Targets." 2016. PMC5039524. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5039524/
- "Mechanism of Tetracycline Resistance by Ribosomal Protection Protein Tet(O)." 2013. PMC3576927. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3576927/
- "Mechanistic Insights into Clinically Relevant Ribosome-Targeting Antibiotics." PMC11505993. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11505993/
- Tosi M, Coloretti I, Meschiari M, De Biasi S, Girardis M, Busani S. "The Interplay between Antibiotics and the Host Immune Response in Sepsis: From Basic Mechanisms to Clinical Considerations: A Comprehensive Narrative Review." 2024. PMC11117367. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11117367/
- "TREM2/β-catenin attenuates NLRP3 inflammasome-mediated macrophage pyroptosis ..." 2022. PMC9448748. doi:10.1038/s41419-022-05193-x
- "Vancomycin and daptomycin modulate the innate immune response in a murine model of LPS-induced sepsis." PMC8312155. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8312155/
- Wang J, Xia L, Wang R, Cai Y. "Linezolid and Its Immunomodulatory Effect: In Vitro and In Vivo Evidence." 2019. PMC6894011. doi:10.3389/fphar.2019.01389
- Wei J, Walker AS, Eyre DW. "Addition of Macrolide Antibiotics for Hospital Treatment of Community-Acquired Pneumonia." 2025. PMC11998547. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11998547/
- Weiss G, Schaible UE. "Macrophage defense mechanisms against intracellular bacteria." *Immunological Reviews*, 2015. PMC4368383. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4368383/
- Yu Z, Qin W, Lin J, Fang S, Qiu J. "Antibacterial Mechanisms of Polymyxin and Bacterial Resistance." 2015. PMC4312571. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4312571/
- Zimmermann P, Ziesenitz VC, Curtis N, Ritz N. "The Immunomodulatory Effects of Macrolides — A Systematic Review of the Underlying Mechanisms." *Frontiers in Immunology*, 2018. PMC5859047. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5859047/

---
