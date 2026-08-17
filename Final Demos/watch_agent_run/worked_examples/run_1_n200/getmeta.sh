#!/bin/zsh
paperclip cat /papers/$1/meta.json 2>/dev/null | jq -c --arg id "$1" '{id:$id,t:.title,a:(.authors//[]),j:.journal,y:.pub_year,d:.doi}' 2>/dev/null
