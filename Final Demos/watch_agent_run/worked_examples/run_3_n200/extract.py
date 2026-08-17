import re, os, sys

RAW="raw"
KEY = re.compile(r"(M-?CSF|CSF-?1\b|L-?929|GM-?CSF|colony[- ]stimulating|conditioned m|BMDM|BMM\b|BMMs\b|bone[- ]marrow[- ]derived|marrow-derived macrophage)", re.I)
MARROW = re.compile(r"(bone marrow|femur|femora|tibia|marrow cell)", re.I)
DIFF = re.compile(r"(differentiat|cultur|flush|harvest|isolat|generat|derived|ng/ml|ng/mL|U/ml|%|days?|supplement)", re.I)
REFLINE = re.compile(r"^\s*\d+\s*[.:]?\s*[A-Z][a-z]+ [A-Z]{1,3},")

def sentences(text):
    # split on sentence boundaries, keep reasonably
    parts = re.split(r"(?<=[.;])\s+(?=[A-Z0-9(])", text)
    return parts

for fn in sorted(os.listdir(RAW)):
    pid = fn[:-4]
    out=[]
    seen=set()
    for line in open(os.path.join(RAW,fn), encoding="utf-8", errors="replace"):
        line=line.rstrip("\n")
        m=re.match(r"^(L\d+):(.*)$", line)
        if not m: continue
        ln, txt = m.group(1), m.group(2)
        for s in sentences(txt):
            s=s.strip()
            if len(s)<20 or len(s)>1200: continue
            if not KEY.search(s): continue
            if not (MARROW.search(s) or re.search(r"(M-?CSF|L-?929|GM-?CSF|CSF-?1)", s, re.I)): continue
            if not DIFF.search(s): continue
            # drop obvious reference entries
            if re.search(r"(J Immunol|Nat Immunol|Blood\.|doi:|PubMed|et al\.\s*$|;\s*\d{3}:\s*\d+)", s) and not re.search(r"ng/m|U/ml|days|supplemented", s, re.I):
                continue
            k=s[:120]
            if k in seen: continue
            seen.add(k)
            out.append(f"{ln}|{s}")
    with open(f"cand/{pid}.txt","w",encoding="utf-8") as fh:
        fh.write("\n".join(out))
    print(pid, len(out), sum(len(x) for x in out))
