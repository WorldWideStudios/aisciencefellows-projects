#!/bin/zsh
id=$1
paperclip grep -i -h -o -e "C57BL/6[A-Za-z]*" -e "C57Bl/6[A-Za-z]*" -e "BALB/c[A-Za-z]*" -e "129S[0-9A-Za-z/]*" -e "FVB[/A-Za-z]*" -e "CD-1 mice" -e "ICR mice" -e "Sprague.Dawley" -e "Wistar" -e "Lewis rat" -e "Fischer 344" -e "C3H/He[A-Za-z]*" -e "NOD/[A-Za-z]*" -e "mouse" -e "mice" -e "rats" -e "\brat\b" -e "Peromyscus [a-z]*" -e "deer mice" -e "deer mouse" -e "human" -e "porcine" -e "bovine" -e "chicken" -e "equine" -e "feline" /papers/$id/content.lines 2>/dev/null | tr 'A-Z' 'a-z' | sort | uniq -c | sort -rn | head -18 > strain/$id.txt
