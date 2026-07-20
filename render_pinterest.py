import sys

quote_text, attribution, source, row_id = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]

card_html = f'''<div style="position:relative;width:1000px;height:1500px;background:#F3ECDE;box-sizing:border-box;font-family:Georgia, serif;">
<div style="position:absolute;top:50px;left:50px;right:50px;bottom:50px;border:2.5px solid #B8862E;box-sizing:border-box;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:70px;text-align:center;">
<div style="font-size:130px;color:#B8862E;opacity:0.5;line-height:1;">&ldquo;</div>
<div style="font-size:44px;font-style:italic;color:#2E2419;line-height:1.6;max-width:780px;margin-top:20px;">{quote_text}</div>
<div style="width:80px;height:2px;background:#B8862E;margin:60px 0 50px;"></div>
<div style="font-size:26px;letter-spacing:3px;color:#6B5A42;text-transform:uppercase;">{attribution}</div>
<div style="font-size:22px;color:#6B5A42;opacity:0.8;margin-top:10px;">{source}</div>
</div>
<div style="position:absolute;bottom:70px;left:0;right:0;text-align:center;font-size:22px;color:#6B5A42;opacity:0.6;">@the_higher_being</div>
</div>'''

with open('card.html', 'w') as f:
    f.write(card_html)
