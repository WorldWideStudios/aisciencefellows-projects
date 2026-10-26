from pathlib import Path
import numpy as np,trimesh as tm,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
P=Path(__file__).resolve().parent
fig=plt.figure(figsize=(15,10),facecolor='#f7f8fa')
def view(index, meshes,title,elev,azim):
 ax=fig.add_subplot(2,2,index,projection='3d');ax.set_facecolor('#f7f8fa')
 for m,color in meshes:
  normals=m.face_normals;light=np.array([.5,-.3,.8]);sh=.45+.55*np.abs(normals@light)
  from matplotlib.colors import to_rgb
  colors=np.clip(np.array(to_rgb(color))[None,:]*sh[:,None],0,1)
  ax.add_collection3d(Poly3DCollection(m.triangles,facecolor=colors,linewidth=0,rasterized=True))
 b=np.vstack([m.bounds for m,c in meshes]);center=(b.min(0)+b.max(0))/2;r=max(np.ptp(b,axis=0))/2*1.07
 ax.set_xlim(center[0]-r,center[0]+r);ax.set_ylim(center[1]-r,center[1]+r);ax.set_zlim(center[2]-r,center[2]+r);ax.set_box_aspect([1,1,1]);ax.view_init(elev,azim);ax.set_axis_off();ax.set_title(title,fontsize=13)
m=tm.load(P/'male_v3_SO101_fitted.stl');f=tm.load(P/'pipette_collar_31mm_fitted.stl')
view(1,[(m,'#5686b3')],'Male: corrected wrist holes and screw access',35,35)
view(2,[(f,'#68a998')],'Female: 31 mm bore cleared',5,0)
view(3,[(m,'#5686b3')],'Male underside: 14 mm bolt circle / horn recess',-55,35)
ax=fig.add_subplot(2,2,4);ax.set_aspect('equal');ax.grid(alpha=.2)
for mesh,col,label in [(tm.load(P/'inputs/pipette_collar_31mm.stl'),'#dc795a','Original obstruction'),(f,'#398d7e','Revised collar')]:
 sec=mesh.section(plane_origin=[15.5,0,0],plane_normal=[1,0,0])
 for i,line in enumerate(sec.discrete):ax.plot(line[:,1],line[:,2],color=col,label=label if i==0 else None,lw=1.8)
ax.set_xlabel('Y (mm)');ax.set_ylabel('Z (mm)');ax.set_title('Collar side section: before / after (X = 15.5)');ax.legend(fontsize=9)
fig.suptitle('Pipette swapper v3 — SO-101 fit revision',fontsize=21)
fig.tight_layout();fig.savefig(P/'fit_preview.png',dpi=150)
