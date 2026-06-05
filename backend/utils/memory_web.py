"""Memory Box shareable Web View — produces a single self-contained HTML page
that animates the 6 scenes with CSS keyframes. The page auto-plays on open
and works on WhatsApp in-app browsers + iOS/Android.

Stored at /app/backend/static/memory_boxes/<center>/<box_id>.html and served
publicly (no auth) via the /api/memory-box/view/<box_id> route.
"""
from __future__ import annotations

import base64
import os
from typing import Dict, List, Optional

from PIL import Image

from .memory_qr import make_qr_png


def _b64_png(im: Image.Image) -> str:
    import io
    buf = io.BytesIO()
    im.convert("RGB").save(buf, format="JPEG", quality=82, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def _b64_qr(data: str, size: int = 360) -> str:
    return ("data:image/png;base64," +
            base64.b64encode(make_qr_png(data, size=size)).decode())


HTML_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>Memory Box — {{ guest_name }}</title>
<style>
:root{
  --gold:#dcaf50; --gold-dim:#b48c3c; --choc:#2b1810; --cream:#faf0dc;
  --shadow:0 18px 50px rgba(0,0,0,.45);
}
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;background:#0b0703;color:var(--cream);
  font-family:'Cormorant Garamond','Georgia',serif;overflow-x:hidden}
.stage{
  position:relative;max-width:560px;margin:0 auto;height:100vh;height:100dvh;
  background:radial-gradient(ellipse at center,#3a2418 0%,#1a0f08 70%,#000 100%);
  overflow:hidden;box-shadow:var(--shadow);
}
.scene{
  position:absolute;inset:0;display:flex;flex-direction:column;
  align-items:center;justify-content:center;padding:30px;text-align:center;
  opacity:0;transform:translateY(20px) scale(.98);
  transition:opacity .9s ease, transform .9s ease;
  pointer-events:none;
}
.scene.active{opacity:1;transform:translateY(0) scale(1);pointer-events:auto}
.scene::before{
  content:"";position:absolute;inset:0;
  background-image:radial-gradient(circle at 30% 20%,rgba(220,175,80,.18),transparent 40%),
                   radial-gradient(circle at 70% 80%,rgba(220,175,80,.12),transparent 50%);
  pointer-events:none;
}
.frame{
  position:absolute;inset:18px;border:2px solid var(--gold);
  border-radius:18px;pointer-events:none;
}
.title{font-size:48px;color:var(--gold);font-weight:700;letter-spacing:.5px;
  text-shadow:0 2px 8px rgba(0,0,0,.6)}
.sub{font-size:22px;color:var(--cream);margin-top:14px;max-width:90%;line-height:1.4}
.center-name{font-size:32px;color:var(--gold);margin-top:24px;font-weight:600}
.box-icon{width:240px;height:170px;margin-bottom:24px;position:relative}
.box-icon .lid{
  position:absolute;left:-10px;right:-10px;top:0;height:60px;
  background:linear-gradient(180deg,var(--gold),var(--gold-dim));
  border-radius:8px 8px 4px 4px;
  transform-origin:bottom center;
  animation:lidOpen 1.8s ease-out forwards;
}
.box-icon .body{
  position:absolute;left:10px;right:10px;top:60px;bottom:0;
  background:linear-gradient(180deg,#5a3a22,#3a2418);
  border:3px solid var(--gold);border-radius:0 0 8px 8px;
}
.box-icon .ribbon{
  position:absolute;left:50%;top:0;bottom:0;width:24px;margin-left:-12px;
  background:linear-gradient(180deg,var(--gold-dim),var(--gold));z-index:2;
}
@keyframes lidOpen{
  0%{transform:rotate(0deg) translateY(0)}
  60%{transform:rotate(-35deg) translateY(-6px)}
  100%{transform:rotate(-25deg) translateY(-2px)}
}
.sparkles span{
  position:absolute;width:8px;height:8px;background:var(--cream);border-radius:50%;
  box-shadow:0 0 6px var(--gold);opacity:0;
  animation:sparkle 2.2s ease-in-out infinite;
}
@keyframes sparkle{
  0%,100%{opacity:0;transform:scale(.5)}
  50%{opacity:1;transform:scale(1.2)}
}
.collage{display:grid;gap:18px;width:100%;max-width:480px;}
.collage img{width:100%;border-radius:8px;border:6px solid var(--cream);
  box-shadow:0 8px 24px rgba(0,0,0,.55);transform:rotate(0deg);
  opacity:0;animation:photoIn .9s ease-out forwards}
.collage.c-1 img:nth-child(1){animation-delay:.2s}
.collage.c-2{grid-template-columns:1fr 1fr}
.collage.c-2 img:nth-child(1){transform:rotate(-5deg);animation-delay:.2s}
.collage.c-2 img:nth-child(2){transform:rotate(4deg);animation-delay:.6s}
.collage.c-3{grid-template-columns:1fr 1fr 1fr;gap:10px}
.collage.c-3 img:nth-child(1){transform:rotate(-6deg);animation-delay:.2s}
.collage.c-3 img:nth-child(2){transform:rotate(2deg);animation-delay:.5s}
.collage.c-3 img:nth-child(3){transform:rotate(7deg);animation-delay:.8s}
@keyframes photoIn{
  0%{opacity:0;transform:translateY(40px) scale(.85) rotate(var(--r,0deg))}
  100%{opacity:1;transform:translateY(0) scale(1) rotate(var(--r,0deg))}
}
.scene-label{position:absolute;top:42px;left:0;right:0;font-size:24px;
  color:var(--gold);font-weight:600;letter-spacing:1px}
.team-photo{max-width:88%;border-radius:10px;border:5px solid var(--cream);
  box-shadow:0 8px 24px rgba(0,0,0,.55);margin-bottom:18px}
.team-list{display:flex;flex-wrap:wrap;justify-content:center;gap:8px;
  margin-top:8px;max-width:92%}
.team-list .pill{
  background:rgba(43,24,16,.85);border:1.5px solid var(--gold);
  border-radius:16px;padding:6px 14px;font-size:16px;color:var(--cream);
  opacity:0;animation:fadeUp .6s ease-out forwards;
}
@keyframes fadeUp{
  from{opacity:0;transform:translateY(8px)}
  to{opacity:1;transform:translateY(0)}
}
.story-card{
  background:var(--cream);color:var(--choc);
  padding:28px 28px;border-radius:14px;border:2px solid var(--gold);
  box-shadow:0 12px 30px rgba(0,0,0,.5);
  max-width:92%;line-height:1.5;font-size:19px;
}
.story-card .sig{font-size:18px;color:var(--gold-dim);margin-top:14px;text-align:right}
.discount-card{
  background:var(--cream);color:var(--choc);
  padding:34px 28px;border-radius:18px;border:3px solid var(--gold);
  box-shadow:0 14px 36px rgba(0,0,0,.55);max-width:88%;
}
.discount-card .big{font-size:72px;font-weight:700;color:var(--gold-dim);line-height:1}
.discount-card .code{
  display:inline-block;margin-top:14px;padding:10px 28px;border:3px dashed var(--gold);
  border-radius:10px;font-size:34px;font-weight:700;letter-spacing:2px;color:var(--choc)
}
.qr-card{
  background:#fff;padding:14px;border-radius:14px;
  border:3px solid var(--gold);box-shadow:0 10px 28px rgba(0,0,0,.5);
  display:inline-block;margin-top:16px;
}
.qr-card img{display:block;width:200px;height:200px}
.contact-row{font-size:20px;color:var(--cream);margin:6px 0}
.contact-row b{color:var(--gold)}
.nav{position:absolute;bottom:18px;left:0;right:0;display:flex;
  justify-content:center;gap:10px;z-index:99}
.nav .dot{width:10px;height:10px;border-radius:50%;
  background:rgba(255,255,255,.25);transition:background .3s}
.nav .dot.on{background:var(--gold)}
.tap-hint{position:absolute;bottom:60px;left:0;right:0;text-align:center;
  font-size:13px;color:rgba(255,255,255,.45);letter-spacing:1px;
  text-transform:uppercase}
.replay{position:absolute;top:18px;right:18px;background:rgba(0,0,0,.6);
  border:1.5px solid var(--gold);color:var(--gold);padding:8px 14px;
  border-radius:24px;font-size:14px;cursor:pointer;z-index:99}
.replay:active{transform:scale(.96)}
@media (max-width:430px){
  .title{font-size:38px}
  .sub{font-size:18px}
  .center-name{font-size:26px}
  .discount-card .big{font-size:60px}
}
</style>
</head>
<body>
<div class="stage" id="stage">
  <button class="replay" id="replay" onclick="replay()">↻ Replay</button>

  <!-- Scene 1: Box opens -->
  <section class="scene" data-scene="0">
    <div class="frame"></div>
    <div class="box-icon">
      <div class="ribbon"></div>
      <div class="lid"></div>
      <div class="body"></div>
    </div>
    <div class="title">Dhanyavad!</div>
    <div class="sub">{{ intro_line }}</div>
    <div class="center-name">{{ center_name }}</div>
  </section>

  {% for c in collages %}
  <!-- Scene 2.{{ loop.index }}: Collage -->
  <section class="scene" data-scene="{{ loop.index }}">
    <div class="frame"></div>
    <div class="scene-label">A Beautiful Moment · {{ loop.index }} of {{ collages|length }}</div>
    <div class="collage c-{{ c|length }}">
      {% for img in c %}<img src="{{ img }}" alt="">{% endfor %}
    </div>
  </section>
  {% endfor %}

  <!-- Scene 3: Team -->
  <section class="scene" data-scene="{{ team_scene_idx }}">
    <div class="frame"></div>
    <div class="scene-label">Our Team Who Cared for You</div>
    {% if team_photo %}<img class="team-photo" src="{{ team_photo }}" alt="team">{% endif %}
    {% if team %}
    <div class="team-list">
      {% for m in team %}
      <div class="pill" style="animation-delay:{{ loop.index0 * 0.15 }}s">
        {{ m.name }}{% if m.role %} · {{ m.role }}{% endif %}
      </div>
      {% endfor %}
    </div>
    {% else %}
    <div class="sub">Crafted with love by our entire team</div>
    {% endif %}
  </section>

  <!-- Scene 4: Story -->
  <section class="scene" data-scene="{{ story_scene_idx }}">
    <div class="frame"></div>
    <div class="scene-label">Your Story With Us</div>
    <div class="story-card">
      {{ story_text }}
      <div class="sig">— with love, Team Purnabramha</div>
    </div>
  </section>

  <!-- Scene 5: Discount -->
  <section class="scene" data-scene="{{ discount_scene_idx }}">
    <div class="frame"></div>
    <div class="scene-label">A Little Thank-You Gift</div>
    <div class="discount-card">
      <div class="big">10% OFF</div>
      <div style="margin-top:8px;font-size:22px">your next order</div>
      <div class="code">MEMORY10</div>
      <div style="margin-top:18px;font-size:14px">Show this at checkout or scan below</div>
    </div>
    <div class="qr-card"><img src="{{ discount_qr }}" alt="MEMORY10"></div>
  </section>

  <!-- Scene 6: Center contact -->
  <section class="scene" data-scene="{{ contact_scene_idx }}">
    <div class="frame"></div>
    <div class="scene-label">Stay Connected</div>
    <div class="center-name" style="margin-bottom:14px">{{ center_name }}</div>
    <div class="qr-card"><img src="{{ center_qr }}" alt="QR"></div>
    {% if instagram %}<div class="contact-row"><b>Instagram</b> · {{ instagram }}</div>{% endif %}
    {% if website %}<div class="contact-row"><b>Website</b> · {{ website }}</div>{% endif %}
    {% if phone %}<div class="contact-row"><b>Call</b> · {{ phone }}</div>{% endif %}
    <div class="sub" style="margin-top:18px;font-size:18px">
      Until we feed your family again — Dhanyavad
    </div>
  </section>

  <div class="nav" id="nav"></div>
  <div class="tap-hint">tap anywhere to advance</div>
</div>

<script>
const scenes=document.querySelectorAll('.scene');
const nav=document.getElementById('nav');
let idx=0,timer=null;
const sceneDurations=[5500,6500,6500,6500,5500,6000,5500,5500].slice(0,scenes.length);

function renderDots(){
  nav.innerHTML='';
  for(let i=0;i<scenes.length;i++){
    const d=document.createElement('div');
    d.className='dot'+(i===idx?' on':'');
    nav.appendChild(d);
  }
}
function show(i){
  if(i>=scenes.length)return;
  scenes.forEach((s,si)=>s.classList.toggle('active',si===i));
  idx=i;renderDots();
  if(timer)clearTimeout(timer);
  if(i<scenes.length-1){
    timer=setTimeout(()=>show(i+1),sceneDurations[i]||5500);
  }
}
function replay(){show(0)}
document.getElementById('stage').addEventListener('click',e=>{
  if(e.target.id==='replay')return;
  if(idx<scenes.length-1)show(idx+1);else replay();
});
show(0);
</script>
</body>
</html>
"""


def render_memory_html(
    *,
    out_path: str,
    guest_name: str,
    center_name: str,
    occasion: str,
    delivery_mode: str,
    photos_b64_by_set: List[List[str]],   # already AI-ranked → 3 collage sets of data-urls
    team_photo_b64: Optional[str],
    team: List[Dict[str, str]],
    story_text: str,
    center_info: Dict[str, str],
) -> Dict[str, int]:
    """Render the HTML page to `out_path`. Returns size_bytes & scenes."""
    from jinja2 import Template

    if delivery_mode == "function":
        intro_line = f"Thank you for hosting your {occasion} with us."
    else:
        intro_line = f"Thank you for choosing Purnabramha for your {occasion}."

    if not story_text or len(story_text.strip()) < 5:
        story_text = (f"Dear {guest_name or 'Friend'}, your celebration brought "
                      "warmth, laughter and the comforting taste of home to "
                      "every plate we served. Thank you for letting Purnabramha "
                      "be part of this beautiful chapter.")

    # Cap collages to 3 valid sets
    collages = [c for c in photos_b64_by_set if c][:3]

    n_collage = len(collages)
    team_idx = 1 + n_collage
    story_idx = team_idx + 1
    discount_idx = story_idx + 1
    contact_idx = discount_idx + 1

    instagram = (center_info.get("instagram_url") or "").strip()
    website = (center_info.get("website") or "").strip()
    phone = (center_info.get("phone") or "").strip()

    discount_qr = _b64_qr("MEMORY10")
    center_qr_data = instagram or website or "https://www.purnabramha.com"
    center_qr = _b64_qr(center_qr_data)

    tpl = Template(HTML_TEMPLATE)
    html = tpl.render(
        guest_name=guest_name or "Guest",
        center_name=center_name or "Purnabramha",
        intro_line=intro_line,
        collages=collages,
        team_photo=team_photo_b64 or "",
        team=team,
        story_text=story_text,
        instagram=instagram,
        website=website,
        phone=phone,
        discount_qr=discount_qr,
        center_qr=center_qr,
        team_scene_idx=team_idx,
        story_scene_idx=story_idx,
        discount_scene_idx=discount_idx,
        contact_scene_idx=contact_idx,
    )
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return {"scenes": 2 + n_collage + 3, "size_bytes": os.path.getsize(out_path)}
