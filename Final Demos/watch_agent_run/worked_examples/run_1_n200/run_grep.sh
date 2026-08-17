#!/bin/zsh
id=$1
paperclip grep -n -i -m 40 \
  -e "L929" -e "L-929" -e "L 929" -e "M-CSF" -e "MCSF" -e "CSF-1" -e "CSF1" \
  -e "femur" -e "femora" -e "tibia" -e "bone marrow" \
  /papers/$id/content.lines 2>&1 | cut -c1-1600 > hits/$id.txt
