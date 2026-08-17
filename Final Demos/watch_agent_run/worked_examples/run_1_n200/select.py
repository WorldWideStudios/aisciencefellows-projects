import os, re, glob
src = re.compile(r'femur|femora|tibia|bone marrow|marrow cell', re.I)
fac = re.compile(r'L-?\s?929|M-?CSF|CSF-?1|GM-CSF|conditioned medium|conditioned media', re.I)
det = re.compile(r'\bday|\bdays\b|ng/m|%|differentiat|cultur|DMEM|RPMI|IMDM|α-?MEM|alpha-?MEM|FBS|FCS|flush', re.I)
mouse = re.compile(r'\bmice\b|\bmouse\b|murine|C57BL|BALB', re.I)
out = open('candidates.txt','w')
summary=[]
for f in sorted(glob.glob('hits/*.txt')):
    pid = os.path.basename(f)[:-4]
    lines = open(f, errors='replace').read().split('\n')
    keep=[]
    for ln in lines:
        if src.search(ln) and fac.search(ln) and det.search(ln):
            keep.append(ln)
    if keep:
        out.write(f'===== {pid} =====\n')
        for k in keep[:12]:
            out.write(k[:1500]+'\n')
        summary.append((pid,len(keep)))
    else:
        summary.append((pid,0))
out.close()
print('papers with candidate lines:', sum(1 for p,n in summary if n))
print('papers with none:', [p for p,n in summary if n==0])
print('bytes', os.path.getsize('candidates.txt'))
