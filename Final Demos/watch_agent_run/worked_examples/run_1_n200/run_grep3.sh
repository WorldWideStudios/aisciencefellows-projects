#!/bin/zsh
id=$1
paperclip grep -n -i -m 60 \
  -e "L929" -e "L-929" -e "L-cell" -e "M-CSF" -e "MCSF" -e "CSF-1" -e "CSF1" \
  -e "femur" -e "femora" -e "tibia" -e "bone marrow" -e "BMDM" -e "BMM" \
  /papers/$id/content.lines 2>&1 > full/$id.txt
