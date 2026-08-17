== run_0  (67 calls)
    5  ids.txt                    fetched      written by command, no file input
    6  PMC11976235.txt            parsed       reads content.lines
    8  candidates.txt             fetched      written by command, no file input  [saved script]
   11  nocand.txt                 parsed       reads content.lines, id.txt  [saved script]
   12  candidates2.txt            parsed       reads nocand.txt  [inline (not saved)]
   15  covered.txt                parsed       reads cand1.txt, cand2.txt, ids.txt
   15  uncovered.txt              parsed       reads cand1.txt, cand2.txt, ids.txt
   20  cand3.txt                  parsed       reads covered.txt, ids.txt  [inline (not saved)]
   22  list2.txt                  parsed       reads content.lines, id.txt  [saved script]
   23  full_extract.txt           parsed       reads list2.txt  [inline (not saved)]
   32  final_extract.txt          parsed       reads ids.txt  [inline (not saved)]
   32  nohit.txt                  parsed       reads ids.txt  [inline (not saved)]
   33  new_extract.txt            fetched      written by command, no file input  [inline (not saved)]
   36  nohit_check.txt            parsed       reads nohit.txt  [inline (not saved)]
   61  incl.txt                   parsed       reads meta.json  [saved script]
   62  refs.txt                   parsed       reads meta.jsonl  [inline (not saved)]
   64  refs.txt                   parsed       reads incl.txt, meta.json  [saved script]
   66  bmdm_protocols.md          parsed       reads refs.txt
   67  bmdm_protocols.md          parsed       reads refs.txt  [inline (not saved)]
   transform: getmeta.sh, run_grep.sh, run_grep2.sh, run_grep3.sh, select.py

