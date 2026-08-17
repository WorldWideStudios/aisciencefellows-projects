#!/bin/zsh
id=$1
paperclip grep -i -n -h -e "M-CSF" -e "MCSF" -e "CSF-1" -e "CSF1" -e "L929" -e "L-929" -e "GM-CSF" -e "colony.stimulating" -e "bone marrow" -e "femur" -e "femora" -e "tibia" -e "BMDM" -e "BMM" -e "marrow-derived" -e "marrow derived" /papers/$id/content.lines > raw/$id.txt 2>&1
