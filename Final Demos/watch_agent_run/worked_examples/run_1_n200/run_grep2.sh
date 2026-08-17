#!/bin/zsh
id=$1
paperclip grep -n -i -m 30 \
  -e "bone marrow-derived macrophage" -e "bone marrow derived macrophage" \
  -e "bone marrow macrophage" -e "BMDM" -e "BMM" -e "BMMs" -e "bone-marrow" \
  -e "L-cell" -e "Lcell" -e "conditioned medium" -e "conditioned media" \
  /papers/$id/content.lines 2>&1 | cut -c1-1200 > hits2/$id.txt
