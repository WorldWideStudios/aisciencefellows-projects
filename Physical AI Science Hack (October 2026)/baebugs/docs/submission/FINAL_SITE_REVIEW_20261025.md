# Baebugs final published website — verifiable handoff

## Intent
Restore parity between the latest GitHub main and the public Baebugs workcell
without silently including unreviewed team photographs or overstating physical
proof. This is a derived web projection, not a new Merkle/MMR commitment.

## Review routes (same production origin)
- / — workflow-first, source-addressed evidence homepage.
- /review/ — source revision, graph root, research claims and gate status.
- /story/ — seven-stage source-backed story, regenerated from current source
  data in the output directory (the prior committed story bytes are preserved).
- /demo/ — four repo-source videos, explicitly classified as software
  walkthrough, CAD animation, robot simulation, and noncompliant music reel.
- /protocols/ — source-verified catalog, BYO/remix and private local review.
- /board/ — workflow planner and source references pinned to the deployed
  source commit, rather than a mutable integration branch.
- /lab/ — printable CAD viewer.
- /detection/ — recorded YOLOE/OWLv2 toy-photo bounding boxes and source hashes.
- /deployment-manifest.json — source SHA, files and exact-byte digests.

## Critical assertions
- Source-hash reproducibility and the published exact-byte manifest are
  independently testable. Hashes identify data; they do not validate science.
- Do not treat unedited bench footage, verified plate recovery or taxonomic
  identification as present: none is established by the available video files.
- A 14-slide team deck and PR #34's 32-slide autoplay presentation do not
  satisfy the five-slide event limit without a separate five-slide
  Google Slides deck.
- Submitted/unlisted YouTube and Google Slides URLs remain NOT_VERIFIED until
  independently read back in signed-out browsing.
- PR #34's face-bearing photos are deliberately excluded from this public
  site; the PR must receive publication-rights review before merging.
- The old per-source custody gaps and any model-weight failures remain recorded.

## Deploy procedure
Fetch and pin main, regenerate the repo's AoK and MVP snapshot, and execute:
  python site/mvp/build_public_site.py --out /tmp/baebugs-site-release --ref FULL_COMMIT_SHA
  vercel deploy --prod --yes --scope biobitworks

Do not assume a deploy is accepted until production deployment-manifest.json
and all listed files read back at the expected SHA-256.
