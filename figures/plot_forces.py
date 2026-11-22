"""Reproduce reference-force quantiles from the independent file audit."""
from pathlib import Path
import json, os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
root=Path(__file__).resolve().parents[1]
records=json.loads((root/'refs/oxford_force_profile.json').read_text('utf-8'))['compositions']
font=Path(os.getenv('P8_CJK_FONT','C:/Windows/Fonts/msyh.ttc'))
if font.exists():
    font_manager.fontManager.addfont(font)
    plt.rcParams['font.family']=font_manager.FontProperties(fname=font).get_name()
plt.rcParams.update({'svg.fonttype':'none','axes.unicode_minus':False,'font.size':12})
fig,ax=plt.subplots(figsize=(9.4,3.35))
fig.subplots_adjust(left=.19,right=.95,top=.86,bottom=.23)
ax.grid(axis='x',color='#E1E8E6',lw=.7,zorder=0)
for i,(label,row) in enumerate(records.items()):
    y=2-i
    lo,hi=row['median'],row['p90']
    ax.plot([lo,hi],[y,y],lw=3,color='#ADC7C2')
    for v,col,m in [(lo,'#12695D','o'),(hi,'#C07539','D')]:
        ax.scatter(v,y,c=col,marker=m,s=72,zorder=3)
        ax.text(v,y+.16,f'{v:.3f}',ha='center',fontsize=11,color=col)
ax.set_yticks([2,1,0],[r'$\mathrm{Li_6PS_5Cl}$',r'$\mathrm{Li_5PS_4Cl_2}$',r'$\mathrm{Li_7PS_6}$'])
ax.set_ylim(-.55,2.45)
ax.set_xlim(0,1.35)
ax.set_xlabel('Li 参考力模（按 ASE 常规单位解读，eV/Å）',labelpad=9)
ax.plot([],[],marker='o',ls='',c='#12695D',label='中位数')
ax.plot([],[],marker='D',ls='',c='#C07539',label='第 90 百分位')
ax.legend(frameon=False,ncol=2,loc='lower right',bbox_to_anchor=(1,1.01))
for side in ['top','left','right']:ax.spines[side].set_visible(False)
ax.spines['bottom'].set_color('#B8C8C4')
ax.tick_params(length=0,pad=8)
for ext in ['png','svg']:fig.savefig(root/f'figures/force_profile.{ext}',dpi=200,facecolor='white')

