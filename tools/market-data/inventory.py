from s3lib import client
from collections import defaultdict
c=client(); p=c.get_paginator('list_objects_v2')
ds=defaultdict(lambda:[0,0]); srcs=defaultdict(set)
for page in p.paginate(Bucket='market-data'):
    for o in page.get('Contents',[]):
        parts=o['Key'].split('/')
        top=parts[0]
        ds[top][0]+=1; ds[top][1]+=o['Size']
        for seg in parts[1:]:
            if seg.startswith('source='): srcs[top].add(seg[7:])
print(f"{'DATASET':<32}{'FILES':>7}{'SIZE_MB':>10}   sources")
print("-"*80)
tf=ts=0
for k in sorted(ds):
    f,s=ds[k]; tf+=f; ts+=s
    sr=",".join(sorted(srcs[k]))[:34]
    print(f"{k:<32}{f:>7}{s/1e6:>10.1f}   {sr}")
print("-"*80)
print(f"{'TOTAL: '+str(len(ds))+' datasets':<32}{tf:>7}{ts/1e6:>10.1f}")
