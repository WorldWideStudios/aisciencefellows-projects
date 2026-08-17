#!/bin/zsh
s=$1; e=$2
for f in $(sed -n "${s},${e}p" ids.txt); do
  echo "######## $f"
  if [ -s focus/$f.txt ]; then head -c 3000 focus/$f.txt; echo; else echo "(none)"; fi
done
