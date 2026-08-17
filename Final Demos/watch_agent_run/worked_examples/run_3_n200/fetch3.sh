#!/bin/zsh
id=$1
paperclip head -1 /papers/$id/content.lines 2>/dev/null | head -1 > title/$id.txt
