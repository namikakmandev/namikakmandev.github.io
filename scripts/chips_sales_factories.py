"""US chip sales vs US chipmaking capacity -> assets/linkedin/chips-sales-factories.png

Run from the repo root: python3 scripts/chips_sales_factories.py
All figures are typed in from the sources listed on chips-sales-factories.html; no forecasts."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from matplotlib.patches import FancyBboxPatch, Rectangle
NAVY="#0B1E3A"; CARD="#132B4F"; ORANGE="#F28C28"; BLUE="#5AABFF"; WHITE="#FFFFFF"; GREY="#93A8C4"; DIM="#2B4A73"
IMG={k:plt.imread(f"assets/chips-study/flags/{k}.png") for k in ["us","tw","kr","cn"]}
fig=plt.figure(figsize=(10.8,13.5),dpi=100); fig.patch.set_facecolor(NAVY)
root=fig.add_axes([0,0,1,1]); root.set_xlim(0,1080); root.set_ylim(0,1350); root.axis("off")
def T(x,y,s,**k): root.text(x,y,s,color=k.pop("c",WHITE),**k)
def flag(ax_,k,x,y,z=0.27): ax_.add_artist(AnnotationBbox(OffsetImage(IMG[k],zoom=z),(x,y),frameon=False,zorder=8))

# chip glyph
cx,cy=990,1245
root.add_patch(FancyBboxPatch((cx-34,cy-34),68,68,boxstyle="round,pad=0,rounding_size=7",fc="#1E3D68",ec=BLUE,lw=2.5,zorder=3))
root.add_patch(Rectangle((cx-15,cy-15),30,30,fc=BLUE,alpha=.4,ec=BLUE,zorder=4))
for i in range(4):
    o=-21+i*14
    for (x,y,w,h) in [(cx+o-2.5,cy+34,5,10),(cx+o-2.5,cy-44,5,10),(cx+34,cy+o-2.5,10,5),(cx-44,cy+o-2.5,10,5)]:
        root.add_patch(Rectangle((x,y),w,h,fc=GREY,ec="none",zorder=2))

T(60,1270,"America kept the sales.",fontsize=38,weight="bold",va="center")
T(60,1212,"It gave away the factories.",fontsize=38,weight="bold",c=ORANGE,va="center")



from matplotlib.patches import Circle, Polygon
T(60,1150,"What drove chip demand",fontsize=17,weight="bold",c=GREY,va="center")
T(1020,1150,"main demand by era · 2023: PCs + phones = 57% of chip sales (SIA)",fontsize=11.5,c=GREY,va="center",ha="right")
eras=[("1980s","Mainframe\nmemory"),("1990s","PCs"),("2000s","Mobile\nphones"),("2010s","Smart-\nphones"),("2020s","AI data\ncentres")]
EW=180; EG=15; ex0=60
def icon(i,cx,cy):
    L=BLUE if i<4 else ORANGE
    if i==0:
        root.add_patch(FancyBboxPatch((cx-30,cy-32),60,64,boxstyle="round,pad=0,rounding_size=4",fc="none",ec=L,lw=2.5))
        for dx in (-13,13): root.add_patch(Circle((cx+dx,cy+12),9,fc="none",ec=L,lw=2.2))
        root.plot([cx-20,cx+20],[cy-14,cy-14],color=L,lw=2.2); root.plot([cx-20,cx+20],[cy-22,cy-22],color=L,lw=2.2)
    elif i==1:
        root.add_patch(FancyBboxPatch((cx-34,cy-14),68,46,boxstyle="round,pad=0,rounding_size=4",fc="none",ec=L,lw=2.5))
        root.plot([cx,cx],[cy-14,cy-26],color=L,lw=2.5); root.plot([cx-18,cx+18],[cy-28,cy-28],color=L,lw=3)
    elif i==2:
        root.add_patch(FancyBboxPatch((cx-15,cy-32),30,64,boxstyle="round,pad=0,rounding_size=6",fc="none",ec=L,lw=2.5))
        root.add_patch(Rectangle((cx-9,cy+6),18,16,fc="none",ec=L,lw=1.8))
        for r in range(3):
            for c_ in range(3): root.add_patch(Circle((cx-7+c_*7,cy-6-r*7),1.8,fc=L,ec="none"))
    elif i==3:
        root.add_patch(FancyBboxPatch((cx-19,cy-34),38,68,boxstyle="round,pad=0,rounding_size=8",fc="none",ec=L,lw=2.5))
        root.add_patch(FancyBboxPatch((cx-13,cy-24),26,50,boxstyle="round,pad=0,rounding_size=3",fc=L,alpha=.25,ec="none"))
        root.add_patch(Circle((cx,cy-29),2.5,fc=L,ec="none"))
    else:
        for k in range(4):
            y=cy+18-k*16
            root.add_patch(FancyBboxPatch((cx-30,y-6),60,13,boxstyle="round,pad=0,rounding_size=2",fc="none",ec=L,lw=2.2))
            root.add_patch(Circle((cx+21,y+0.5),2.2,fc=L,ec="none"))
            root.plot([cx-22,cx+5],[y+0.5,y+0.5],color=L,lw=1.5,alpha=.6)
for i,(dec,lab) in enumerate(eras):
    x=ex0+i*(EW+EG)
    col=BLUE if i<4 else ORANGE
    root.add_patch(FancyBboxPatch((x,975),EW,150,boxstyle="round,pad=0,rounding_size=14",fc=CARD,ec=col if i==4 else "none",lw=2))
    icon(i,x+46,1050)
    T(x+90,1078,dec,fontsize=17,weight="bold",c=col,va="center")
    T(x+90,1030,lab,fontsize=11.5,va="center",linespacing=1.25)
    if i<4: T(x+EW+EG/2,1050,"›",fontsize=22,c=DIM,ha="center",va="center")

ax=fig.add_axes([0.08,0.47,0.84,0.235]); ax.set_facecolor(NAVY)
ax.plot([1988,2025],[37,53.4],color=BLUE,lw=6,solid_capstyle="round",zorder=3)
ax.scatter([1988,2025],[37,53.4],s=140,color=BLUE,zorder=4)
cyr=[1990,2015,2019,2022]; cv=[37,13,11,10]
ax.plot(cyr,cv,color=ORANGE,lw=6,solid_capstyle="round",zorder=3)
ax.scatter([1990,2022],[37,10],s=140,color=ORANGE,zorder=4)
ax.text(1986.5,41,"37%",color=WHITE,fontsize=38,weight="bold",va="bottom")
ax.text(2025,57,"53%",color=BLUE,fontsize=46,weight="bold",ha="center",va="bottom")
ax.text(2025,46.5,"of world chip sales\nto US companies, 2025",color=WHITE,fontsize=14,ha="right",va="top",linespacing=1.25)
ax.text(2022,13,"10%",color=ORANGE,fontsize=46,weight="bold",ha="center",va="bottom")
ax.text(2018.6,-2,"of world chipmaking\ncapacity in the US, 2022",color=WHITE,fontsize=14,ha="right",va="center",linespacing=1.25)
ax.text(2003,46.6,"SALES",color=BLUE,fontsize=18,weight="bold",rotation=11,ha="center")
ax.text(2006,24,"FACTORIES",color=ORANGE,fontsize=18,weight="bold",rotation=-14,ha="center")
flag(ax,"us",2029.3,53.4,0.26)
ax.set_xlim(1984,2031); ax.set_ylim(-14,72)
ax.set_xticks([1990,2000,2010,2020]); ax.set_yticks([])
for s in ax.spines.values(): s.set_visible(False)
ax.spines["bottom"].set_visible(True); ax.spines["bottom"].set_color(DIM)
ax.tick_params(colors=GREY,labelsize=14,length=0,pad=6)


# policy band: 2022 carrot, 2026 stick
root.add_patch(FancyBboxPatch((50,410),980,165,boxstyle="round,pad=0,rounding_size=18",fc="#2A1E14",ec=ORANGE,lw=2.5))
T(80,550,"NOW AMERICA WANTS THE FACTORIES BACK",fontsize=14,weight="bold",c=ORANGE,va="center")
root.plot([540,540],[430,530],color=ORANGE,lw=1.5,alpha=.5)
T(80,505,"2022",fontsize=18,weight="bold",c=GREY,va="center")
T(150,505,"$52.7B",fontsize=40,weight="bold",c=WHITE,va="center")
T(80,448,"CHIPS Act subsidies to build factories at home",fontsize=13,c=WHITE,va="center")
T(570,505,"2026",fontsize=18,weight="bold",c=GREY,va="center")
T(640,505,"25% tariff",fontsize=40,weight="bold",c=ORANGE,va="center")
T(570,445,"on certain advanced chips made abroad,\nincl. US-designed Nvidia H200 & AMD MI325X",fontsize=12,c=WHITE,va="center",linespacing=1.25)

# nuance tiles
tiles=[(["us"],"DESIGN STAYED",BLUE,"Nvidia, Apple, AMD design\nthe chips. Design-only firms:\n14% → 35% of sales (2003→21)"),
       (["tw","kr"],"MAKING LEFT",ORANGE,"All capacity for chips below\n10 nm is in Taiwan (69%)\nand Korea (31%), 2022"),
       (["kr"],"EXCEPT MEMORY",ORANGE,"Samsung and SK hynix design\nand build their own. Korea has\n~half of DRAM; the US 3%")]
W=310; gap=25; x0=60
for i,(fl,head,col,body) in enumerate(tiles):
    x=x0+i*(W+gap)
    root.add_patch(FancyBboxPatch((x,165),W,215,boxstyle="round,pad=0,rounding_size=16",fc=CARD,ec=col,lw=2.2))
    for j,f in enumerate(fl):
        root.add_artist(AnnotationBbox(OffsetImage(IMG[f],zoom=0.24),(x+38+j*50,345),frameon=False,zorder=8))
    T(x+20,298,head,fontsize=15,weight="bold",c=col,va="center")
    T(x+20,228,body,fontsize=12.5,va="center",linespacing=1.4)

T(60,128,"Sources: SIA 2026 (US firms 53.4% of sales); White House fact sheet 14 Jan 2026 (25% Section 232 tariff);",fontsize=10.5,c=GREY,va="center")
T(60,108,"SIA/BCG 2021 & 2024 and CRS (US capacity 1990-2022, sub-10 nm and DRAM capacity 2022); IC Insights (fabless share);",fontsize=10.5,c=GREY,va="center")
T(60,88,"UPI 1989 (N. American firms 37%, 1988); CSET 2022 (Korea DRAM). Sales line joins two surveys. Measured data only.",fontsize=10.5,c=GREY,va="center")
fig.savefig("assets/linkedin/chips-sales-factories.png",facecolor=NAVY)
