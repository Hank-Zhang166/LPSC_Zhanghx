"""Generate matched editable draw.io, vector SVG and 2x PNG from one layout."""
from pathlib import Path
from xml.etree import ElementTree as E
from html import escape
from PIL import Image, ImageDraw, ImageFont
import os, math

OUT=Path(__file__).resolve().parent
W,H=1200,445
P={'teal':('#D9EFE9','#076E62'),'blue':('#E4EDF6','#26597E'),'gold':('#F8EDDB','#855717'),'gray':('#EDF0F1','#405966')}
FONT=os.getenv('P8_CJK_FONT','C:/Windows/Fonts/msyh.ttc')
BOLD=os.getenv('P8_CJK_BOLD','C:/Windows/Fonts/msyhbd.ttc')
def box(x,y,w,h,title,sub,color='teal'):
    return (x,y,w,h,title,sub,color)
def edge(a,b,ports='rl',dashed=False):
    return a,b,ports,dashed
def pt(b,side):
    x,y,w,h,*_=b
    return {'r':(x+w,y+h/2),'l':(x,y+h/2),'t':(x+w/2,y),'b':(x+w/2,y+h)}[side]

graphs={
'architecture':('势能如何进入输运判断',[
box(8,35,260,94,'周期构型','type[N] · R[N,3] · H[3,3]','gray'),
box(312,35,270,94,'邻域与边局部坐标','径向基、截断、邻居掩码','blue'),
box(625,35,260,94,'SeZM 等变消息','SO(3) 旋转 / SO(2) 卷积','blue'),
box(929,35,263,94,'标量描述符','末层 ℓ=0 分量 h[N,d]','blue'),
box(929,190,263,91,'原子能量头','各原子 eᵢ 求和为总能 E'),
box(625,190,260,91,'力与 virial','坐标与形变导数'),
box(312,190,270,91,'MD 积分与统计','多轨迹 / 温度 / 时间区间'),
box(8,190,260,91,'输运与样品比较','相组成、致密度、接触','gold'),
box(920,335,272,82,'可选性质任务','冻结表示，另配性质标签','gold')],
[edge(0,1),edge(1,2),edge(2,3),edge(3,4,'bt'),edge(4,5,'lr'),edge(5,6,'lr'),edge(6,7,'lr')]),
'gradient':('谁提供标签，谁接收梯度',[
box(8,48,238,88,'源域保留批次','参考口径一致 / 抑制遗忘','gray'),
box(8,210,238,88,'目标域 DFT','E、F，可选 virial','gold'),
box(300,127,242,96,'按系统组批','元素映射、原子数、掩码','gray'),
box(590,127,252,96,'描述符 θ 和能量头 φ','前向得到 E，求导得到 F','blue'),
box(922,127,270,96,'损失与权重','wE LE + wF LF + wΞ LΞ','gold'),
box(922,312,270,80,'优化器反向传播','全量、LoRA 或冻结参数','teal'),
box(590,312,252,80,'更新开放的参数','梯度回传到选定模块','teal'),
box(300,312,242,80,'检查点与独立留出','物理验收后才发布','gray')],
[edge(0,2),edge(1,2),edge(2,3),edge(3,4),edge(4,5,'bt'),edge(5,6,'lr'),edge(6,3,'tb',True),edge(6,7,'lr')]),
'levels':('从三种可观测量定位分歧',[
box(12,52,345,100,'原子构型','局域力、相对能量、参考口径','blue'),
box(429,52,342,100,'晶内轨迹','自扩散、集体位移、跳跃数','teal'),
box(842,52,346,100,'真实压片','阻抗谱、厚度、面积、温度','gold'),
box(12,243,345,102,'独立参考','分层留出 DFT 对比 E / F','blue'),
box(429,243,342,102,'重复采样','多初态、区块误差、有限尺寸','teal'),
box(842,243,346,102,'独立制样','同粉体两压实条件与新批确认','gold')],
[edge(0,1),edge(1,2),edge(0,3,'bt'),edge(1,4,'bt'),edge(2,5,'bt')]),
'release':('一次证据如何获得行动资格',[
box(12,55,260,92,'初相 / 成分报告','粉体批号及不确定性','gold'),
box(315,55,255,92,'审核并发布','记录 qc_released_at','gray'),
box(625,55,256,92,'结构候选集','改占位族与抽样权重','blue'),
box(931,55,258,92,'补作业或保留','只动尚可调整的任务','teal'),
box(12,258,260,92,'独立 DFT 偏差','跨构型族复现问题','gold'),
box(315,258,255,92,'有价值的标签批','分层选帧、剔除近邻','gray'),
box(625,258,256,92,'训练与独立验收','检查目标改善与源域遗忘','blue'),
box(931,258,258,92,'新势可用','重算赶得上冻结才行动','teal')],
[edge(0,1),edge(1,2),edge(2,3),edge(4,5),edge(5,6),edge(6,7)]),
}

def generate(key,title,nodes,edges, *, title_size=23, detail_size=16, two_line=False):
    model=E.Element('mxGraphModel',{'adaptiveColors':'auto','pageWidth':str(W),'pageHeight':str(H)})
    root=E.SubElement(model,'root')
    E.SubElement(root,'mxCell',id='0')
    E.SubElement(root,'mxCell',id='1',parent='0')
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><title>{title}</title><rect width="100%" height="100%" fill="white"/>']
    img=Image.new('RGB',(2*W,2*H),'white')
    d=ImageDraw.Draw(img)
    def line(points,c='#586E74',width=2,dashed=False):
        if dashed:
            (a,b),(u,v)=points
            length=math.hypot(u-a,v-b)
            for i in range(0,int(length),12):
                k=min(i+6,length)
                d.line([(2*(a+(u-a)*t/length),2*(b+(v-b)*t/length)) for t in (i,k)],fill=c,width=width*2)
        else:d.line([(x*2,y*2) for x,y in points],fill=c,width=width*2)
    def branch(vertices):
        return ' '.join(f'{x:.1f},{y:.1f}' for x,y in vertices)
    if key=='architecture':
        # The optional property head branches from h, independently of the energy head.
        edges=edges+[(3,8,'rr',True)]
    for j,(a,b,ports,dashed) in enumerate(edges):
        xy=pt(nodes[a],ports[0]); uv=pt(nodes[b],ports[1])
        if ports=='rr':
            xy=(nodes[a][0]+nodes[a][2]*.75,nodes[a][1]+nodes[a][3])
            uv=(nodes[b][0]+nodes[b][2]*.9,nodes[b][1])
            path=[xy,(xy[0],153),(902,153),(902,310),(uv[0],310),uv]
        elif abs(xy[0]-uv[0])>8 and abs(xy[1]-uv[1])>8:
            mid=(xy[0]+uv[0])/2
            path=[xy,(mid,xy[1]),(mid,uv[1]),uv]
        else:path=[xy,uv]
        dash=' stroke-dasharray="6 6"' if dashed else ''
        svg.append(f'<polyline points="{branch(path)}" fill="none" stroke="#586E74" stroke-width="2"{dash}/>')
        for p,q in zip(path,path[1:]):line([p,q],dashed=dashed)
        x,y=uv; dx=x-path[-2][0];dy=y-path[-2][1]
        length=math.hypot(dx,dy);dx/=length;dy/=length
        tri=[(x,y),(x-10*dx+4*dy,y-10*dy-4*dx),(x-10*dx-4*dy,y-10*dy+4*dx)]
        d.polygon([(2*a,2*b) for a,b in tri],fill='#586E74')
        svg.append(f'<polygon points="{branch(tri)}" fill="#586E74"/>')
        anchor={'r':'1;exitY=0.5','l':'0;exitY=0.5','b':'0.5;exitY=1','t':'0.5;exitY=0'}
        ent=anchor[ports[1]].replace('exitY','entryY')
        style=f'edgeStyle=orthogonalEdgeStyle;html=1;endArrow=block;strokeColor=#586E74;strokeWidth=2;exitX={anchor[ports[0]]};entryX={ent};dashed={int(dashed)};'
        e=E.SubElement(root,'mxCell',id='e'+str(j),parent='1',edge='1',source='n'+str(a),target='n'+str(b),style=style)
        E.SubElement(e,'mxGeometry',{'relative':'1','as':'geometry'})
    for i,(x,y,w,h,label,sub,kind) in enumerate(nodes):
        bg,fg=P[kind]
        style=f'rounded=1;arcSize=13;html=1;whiteSpace=wrap;fillColor={bg};fontColor={fg};strokeColor={bg};fontFamily=Microsoft YaHei;fontSize=20;'
        details = [sub]
        if two_line:
            face = ImageFont.truetype(FONT, 2*detail_size)
            details = [""]
            for char in sub:
                if details[-1] and face.getlength(details[-1]+char) > 2*(w-18):
                    details.append("")
                details[-1] += char
        detail_html = "<br>".join(escape(detail) for detail in details)
        value=(f'<b style="font-size:{title_size}px">{escape(label)}</b><br>'
               f'<font style="font-size:{detail_size}px">{detail_html}</font>')
        if not two_line:
            value=f'<b>{label}</b><br><font style="font-size:15px">{sub}</font>'
        cell=E.SubElement(root,'mxCell',id='n'+str(i),parent='1',vertex='1',value=value,style=style)
        E.SubElement(cell,'mxGeometry',{'x':str(x),'y':str(y),'width':str(w),'height':str(h),'as':'geometry'})
        d.rounded_rectangle((2*x,2*y,2*(x+w),2*(y+h)),radius=14,fill=bg)
        svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="7" fill="{bg}"/>')
        top = y+h/2-(24 if len(details)>1 else 14)
        baseline = y+h/2+(6 if len(details)>1 else 18)
        labels = [(label,top,title_size,True)]
        labels.extend((detail,baseline+i*(detail_size+2),detail_size,False)
                      for i,detail in enumerate(details))
        for text,cy,size,bold in labels:
            font=ImageFont.truetype(BOLD if bold else FONT,2*size)
            d.text((2*(x+w/2),2*cy),text,fill=fg,font=font,anchor='mm')
            svg.append(f'<text x="{x+w/2}" y="{cy+size*.32}" font-family="Microsoft YaHei,sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" text-anchor="middle" fill="{fg}">{escape(text)}</text>')
    svg.append('</svg>')
    (OUT/(key+'.svg')).write_text(''.join(svg),encoding='utf8')
    img.save(OUT/(key+'.png'),optimize=True)
    mx=E.Element('mxfile',host='app.diagrams.net')
    E.SubElement(mx,'diagram',name=title,id=key).append(model)
    E.ElementTree(mx).write(OUT/(key+'.drawio'),encoding='utf-8',xml_declaration=True)

if __name__=='__main__':
    for key,(title,nodes,edges) in graphs.items():generate(key,title,nodes,edges)
