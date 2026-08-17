import re, os
CAND="cand"
FACT = re.compile(r"(M-?CSF|CSF-?1\b|L-?929|L929|GM-?CSF|colony[- ]stimulating|conditioned med|conditioned sup)", re.I)
QUANT = re.compile(r"(\d+\s*(ng|µg|ug|U|IU)\s*/\s*m[lL]|\d+\s*%|\d+\s*(-|\s|to\s)?\d*\s*days?|overnight|for \d+ ?d\b)", re.I)
MARROW = re.compile(r"(bone marrow|femur|femora|tibia|marrow cell|BM cells|BMDM|BMM)", re.I)
tot=0
for fn in sorted(os.listdir(CAND)):
    pid=fn[:-4]
    lines=[l.rstrip("\n") for l in open(os.path.join(CAND,fn),encoding="utf-8")]
    hi=[l for l in lines if FACT.search(l) and QUANT.search(l)]
    if not hi:
        hi=[l for l in lines if FACT.search(l)][:6]
    if not hi:
        hi=[l for l in lines if MARROW.search(l)][:4]
    open(f"focus/{pid}.txt","w",encoding="utf-8").write("\n".join(hi))
    tot+=sum(len(x) for x in hi)
    print(pid, len(hi))
print("TOTAL BYTES", tot)
