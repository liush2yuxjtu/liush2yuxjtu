"""Light editorial SVG for verified npm observations. No interpolation of gaps."""
import datetime as dt
import html


def render(records, cutoff, date_range, aligned_series):
    first = min(min(dt.date.fromisoformat(r['created']) for r in records), cutoff)
    dates = date_range(first, cutoff)
    verified = [r for r in records if r['status'] == 'available']
    aligned = [aligned_series(r, dates) for r in verified]
    total = sum(r['total'] for r in verified)
    # Packages not yet published contribute zero to the aggregate only before launch.
    totals = [sum(s[1][i] or 0 for s in aligned) for i in range(len(dates))]
    daily = [sum(s[0][i] or 0 for s in aligned) for i in range(len(dates))]
    start = max(0, len(dates)-30)
    ds, ts, vs = dates[start:], totals[start:], daily[start:]
    month = sum(vs)
    height = 870 + max(0, len(records)-8)*43
    e = []
    def text(x,y,value,cls='body',extra=''):
        e.append(f'<text x="{x}" y="{y}" class="{cls}" {extra}>{html.escape(str(value))}</text>')
    def line(x1,y1,x2,y2):
        e.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#e6ecea"/>')
    text(52,48,'刘师宇 / 开源作品','eyebrow')
    text(1148,48,f'数据截至 {cutoff} · UTC','small','text-anchor="end"')
    text(52,104,'每一次下载，都留下轨迹。','heading')
    text(52,135,'npm 官方数据 · 不平滑、不补零、不把下载当用户数','muted')
    for x,label,value,note in [(52,'已知累计下载',f'{total:,}' if verified else 'N/A','自各包首次发布起'),(445,'最近 30 天下载',f'{month:,}' if verified else 'N/A','按实际日期加总'),(838,'已发布 npm 包',str(len(records)),f'{len(verified)} 个有完整下载统计')]:
        text(x,187,label,'muted');text(x,238,value,'metric');text(x,264,note,'small')
    line(52,289,1148,289)
    text(52,328,'累计趋势','section');text(750,328,'最近 30 天','small','text-anchor="end"')
    x,y,w,h=86,378,652,195
    ymax=max(total,1)
    for step in range(4):
        yy=y+h-step*h/3
        line(x,yy,x+w,yy)
        text(x-13,yy+4,f'{ymax*step/3:,.0f}','axis','text-anchor="end"')
    coords=[(x+w*i/max(1,len(ts)-1),y+h-h*v/ymax) for i,v in enumerate(ts)]
    if coords and verified:
        pts=' '.join(f'{xx:.1f},{yy:.1f}' for xx,yy in coords)
        e.append(f'<polygon points="{x},{y+h} {pts} {x+w},{y+h}" fill="url(#area)"/>')
        e.append(f'<polyline points="{pts}" fill="none" stroke="#087f6b" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"/>')
        xx,yy=coords[-1];e.append(f'<circle cx="{xx}" cy="{yy}" r="5" fill="#087f6b" stroke="white" stroke-width="2"/>')
        text(xx,yy-15,f'{total:,}','endpoint','text-anchor="end"')
    for i in sorted({0,(len(ds)-1)//2,len(ds)-1}):
        text(x+w*i/max(1,len(ds)-1),600,ds[i],'axis','text-anchor="'+('start' if i==0 else 'end' if i==len(ds)-1 else 'middle')+'"')
    line(790,314,790,622)
    text(825,328,'各包累计下载','section')
    for i,r in enumerate(sorted(records,key=lambda r:-(r['total'] if r['total'] is not None else -1))):
        yy=370+i*32
        name=r['name'].removeprefix('@liushiyumathxjtu/')
        text(825,yy,name,'package')
        text(1148,yy,f'{r["total"]:,}' if r['total'] is not None else '待统计','package','text-anchor="end"')
        if r['total'] is not None:
            length=235*r['total']/max([rr['total'] or 0 for rr in records]+[1])
            e.append(f'<rect x="825" y="{yy+7}" width="{length:.1f}" height="3" rx="1.5" fill="#b7d9ce"/>')
    lower=660+max(0,len(records)-8)*43
    text(52,lower,'每日下载','section');text(1148,lower,'原始计数 · 与上方使用相同 30 天区间','small','text-anchor="end"')
    bw=1096/max(1,len(vs));maximum=max(vs+[1]);base=lower+106
    line(52,base,1148,base)
    for i,v in enumerate(vs if verified else []):
        bh=78*v/maximum
        if v:
            e.append(f'<rect x="{52+i*bw+3:.1f}" y="{base-bh:.1f}" width="{bw-6:.1f}" height="{bh:.1f}" rx="2" fill="#6caf9b"><title>{ds[i]}：{v} 次</title></rect>')
        else:e.append(f'<circle cx="{52+(i+.5)*bw:.1f}" cy="{base}" r="1.5" fill="#a4b7b0"/>')
        if v==maximum:text(52+(i+.5)*bw,base-bh-7,str(v),'axis','text-anchor="middle"')
    text(52,base+24,ds[0],'axis');text(1148,base+24,ds[-1],'axis','text-anchor="end"')
    text(52,height-28,'来源：npm Downloads API · 当天排除 · 待统计包不纳入合计 · 下载包含重复安装及 CI','small')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="{height}" viewBox="0 0 1200 {height}" role="img" aria-labelledby="title desc">
<title id="title">npm 下载曲线</title><desc id="desc">截至 {cutoff}：{len(records)} 个包，{len(verified)} 个包有完整统计，已知累计 {total} 次。每日下载为原始计数。</desc>
<defs><linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#b8ded1" stop-opacity=".65"/><stop offset="100%" stop-color="#eaf4ef" stop-opacity=".3"/></linearGradient></defs>
<style>text{{font-family:"PingFang SC","Noto Sans CJK SC",sans-serif;fill:#223d35}}.heading{{font-size:34px;font-weight:650;letter-spacing:-1px}}.eyebrow{{font-size:15px;font-weight:600}}.muted{{font-size:15px;fill:#536d64}}.small{{font-size:12px;fill:#62756e}}.metric{{font-family:"Avenir Next",sans-serif;font-size:48px;font-weight:600;letter-spacing:-2px}}.section{{font-size:18px;font-weight:600}}.axis{{font-size:11px;fill:#65766e}}.package{{font-family:"Avenir Next",sans-serif;font-size:13px}}.endpoint{{font-size:16px;font-weight:600;fill:#087f6b}}</style>
<rect width="1200" height="{height}" rx="20" fill="#fafcf9"/>{''.join(e)}</svg>'''
