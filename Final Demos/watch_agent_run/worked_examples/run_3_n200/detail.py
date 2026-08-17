import re,os,sys
FACT=re.compile(r"(M-?CSF|MCSF|CSF-?1\b|CSF1\b|L-?929|L-cell|LCCM|GM-?CSF|colony[- ]stimulating|conditioned)",re.I)
MAR=re.compile(r"(bone marrow|femur|femora|tibia|marrow cell|BM cell|BMDM|BMM|BM-M|marrow-derived|marrow derived)",re.I)
Q=re.compile(r"(ng/m|µg/m|ug/m|U/m|%|\bday|\bd\b|hour)",re.I)
ids=sys.argv[1:]
for pid in ids:
    p=f"raw/{pid}.txt"
    print(f"######## {pid}  [{open('strain2/'+pid+'.txt').read().strip() if os.path.exists('strain2/'+pid+'.txt') else ''}]")
    if not os.path.exists(p): print("(no raw)"); continue
    out=[];seen=set()
    for line in open(p,encoding="utf-8",errors="replace"):
        line=line.rstrip("\n")
        m=re.match(r"^(L\d+):(.*)$",line)
        if not m: continue
        ln,txt=m.groups()
        if not (FACT.search(txt) and MAR.search(txt) and Q.search(txt)): continue
        if len(txt)>2200: 
            # keep windows around factor mentions
            keep=[]
            for mm in FACT.finditer(txt):
                keep.append(txt[max(0,mm.start()-400):mm.start()+400])
            txt=" ... ".join(keep[:3])
        k=txt[:100]
        if k in seen: continue
        seen.add(k)
        out.append(f"{ln}|{txt}")
    txt="\n".join(out)
    print(txt[:4500] if txt else "(no detail lines)")
