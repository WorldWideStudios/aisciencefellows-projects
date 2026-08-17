== run_1  (59 calls)
   17  ids.txt                    fetched      written by command, no file input
   19  triage.txt                 fetched      written by command, no file input
   20  empties.txt                parsed       reads content.lines, id.txt, triage.txt  [saved script]
   22  have.txt                   parsed       reads triage.txt
   25  followup.txt               fetched      written by command, no file input
   25  rows_aa.tsv                fetched      written by command, no file input
   28  followup.txt               fetched      written by command, no file input
   28  rows_ab.tsv                fetched      written by command, no file input
   31  followup.txt               fetched      written by command, no file input
   31  rows_ac.tsv                fetched      written by command, no file input
   34  followup.txt               fetched      written by command, no file input
   34  rows_ad.tsv                fetched      written by command, no file input
   37  followup.txt               fetched      written by command, no file input
   37  rows_ae.tsv                fetched      written by command, no file input
   40  followup.txt               fetched      written by command, no file input
   40  rows_af.tsv                fetched      written by command, no file input
   41  fu.txt                     parsed       reads content.lines, followup.txt, id.txt  [saved script]
   42  fu1.txt                    parsed       reads fu.txt, id.txt
   42  fu2.txt                    parsed       reads fu.txt, id.txt
   42  fu3.txt                    parsed       reads fu.txt, id.txt
   48  fu4.txt                    parsed       reads content.lines, id.txt  [saved script]
   54  rows_fu.tsv                fetched      written by command, no file input
   55  rows_extra.tsv             parsed       reads rows_ab.tsv, rows_fu.tsv
   56  results.tsv                fetched      written by command, no file input
   57  included.txt               parsed       reads fu.txt, have.txt, results.tsv
   57  reviewed.txt               parsed       reads fu.txt, have.txt, results.tsv
   transform: run1.sh, run2.sh, run3.sh, run4.sh

