from pathlib import Path
import numpy as np,trimesh as tm,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from matplotlib.colors import to_rgb
P=Path(__file__).resolve().parent
old=tm.load(P.parent/'tool_swapper_v3/male_v3_SO101_fitted.stl');new=tm.load(P/'male_v3_SO101_thin_wall.stl')
fig=plt.figure(figsize=(13,8),facecolor='#f8fafc')
for idx,m,title,color in [(1,old,'Before: open access slots near dowels','#99a8ba'),(2,new,'After: continuous 0.3 mm backing wall','#4485b5')]:
 ax=fig.add_subplot(2,2,idx,projection='3d');ax.set_facecolor('#f8fafc')
 light=np.array([-.55,.55,.7]);sh=.45+.55*np.abs(m.face_normals@light)
 ax.add_collection3d(Poly3DCollection(m.triangles,facecolor=np.clip(np.array(to_rgb(color))[None,:]*sh[:,None],0,1),linewidth=0,rasterized=True))
 ax.set(xlim=(-18,18),ylim=(-18,18),zlim=(-3,20));ax.set_box_aspect([36,36,23]);ax.view_init(25,125);ax.set_axis_off();ax.set_title(title,fontsize=13)
ax=fig.add_subplot(2,2,3)
for mesh,col,label in [(old,'#d78062','Previous outline'),(new,'#347cb0','Reinforced outline')]:
 sec=mesh.section(plane_origin=[0,0,8],plane_normal=[0,0,1])
 for i,line in enumerate(sec.discrete):ax.plot(line[:,0],line[:,1],color=col,label=label if i==0 else None,linewidth=1.4)
ax.set_aspect('equal');ax.set_xlabel('X (mm)');ax.set_ylabel('Y (mm)');ax.grid(alpha=.15);ax.set_title('Section through dowel centers');ax.legend(fontsize=9,loc='lower right')
ax=fig.add_subplot(2,2,4);ax.axis('off')
ax.text(.03,.88,'Existing female retained',fontsize=17,weight='bold',color='#24364b')
ax.text(.03,.74,'0.3 mm continuous wall at dowel roots\nØ20.2 mm body in Ø20.5 mm socket\nØ3 mm dowels; 2.9 mm projection\nScrew-head access checked at Ø5.5 mm\nØ6 mm heads no longer pass straight through',fontsize=13,linespacing=1.5,va='top',color='#24364b')
ax.text(.03,.08,'Wall shown in section; verify the thin wall\nappears in your slicer before printing.',fontsize=11,linespacing=1.5,color='#5b6676')
fig.suptitle('Pipette swapper — thin-wall reinforcement',fontsize=20);fig.tight_layout();fig.savefig(P/'thin_wall_preview.png',dpi=160)
