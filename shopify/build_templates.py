#!/usr/bin/env python3
"""Turn the four static pages into Shopify page templates.

The static build is the source of truth for copy, so the templates are
generated from it rather than retyped. Run this again after editing the HTML
and re-push the theme.

Images ship inside the theme (assets/kaibo-<name>), films live in the store's
Content > Files and are referenced by bare file name.
"""
import html
import io
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'shopify', 'templates')

VIDEO_EXT = ('.mp4', '.mov', '.webm')


def asset(path):
    """uploads/web/foo.png -> kaibo-foo.png (theme asset) or foo.mp4 (Files)."""
    if not path:
        return ''
    name = os.path.basename(path.strip().strip('"\''))
    return name if name.lower().endswith(VIDEO_EXT) else 'kaibo-' + name


def text(fragment):
    """Inner text of a fragment: tags dropped, entities resolved.

    Entities are turned into the characters themselves so the theme editor
    shows readable copy instead of &nbsp; and &trade;. The non-breaking space
    still holds "LE Audio" together exactly as the entity did.
    """
    if fragment is None:
        return ''
    s = re.sub(r'<[^>]+>', '', fragment)
    s = html.unescape(s)
    return re.sub(r'[ \t\r\n]+', ' ', s).strip()


def rich(fragment):
    """Body copy for an inline_richtext setting: no wrapping <p>, because the
    section's own paragraph already supplies one."""
    return text(fragment)


def grab(pattern, source, group=1, flags=re.S):
    m = re.search(pattern, source, flags)
    return m.group(group) if m else None


def band(page, marker, closer='\n</section>'):
    """The markup of one top-level <section>, found by a substring in its tag."""
    start = page.find(marker)
    if start < 0:
        return None
    start = page.rfind('<section', 0, start)
    end = page.find(closer, start)
    return page[start:end + len(closer)]


def hero_of(page):
    b = page[page.find('</header>'):]
    b = b[:b.find('\n</section>')]
    media = grab(r'class="kb-hero-media"[^>]*background-image:url\(([^)]+)\)', b)
    video = grab(r'<video[^>]*src="([^"]+)"', b)
    body = grab(r'<p[^>]*>(.*?)</p>', b)
    return {
        'type': 'kaibo-hero',
        'settings': {
            'video': asset(video) if video else '',
            'poster': asset(media),
            'focus': (grab(r'class="kb-hero-media"[^>]*background-position:([^;"]+)', b) or 'center').strip(),
            'start': grab(r'<video[^>]*data-start="([^"]+)"', b) or '',
            'eyebrow': text(grab(r'text-transform:uppercase[^>]*>(.*?)</span>', b)
                            or grab(r'text-transform:uppercase[^>]*>(.*?)</div>', b)),
            'heading': text(grab(r'<h1[^>]*>(.*?)</h1>', b)),
            'body': rich(body),
            'body_width': (grab(r'max-width:(\d+ch)[^"]*"[^>]*>' + re.escape(text(body)[:24]), b)
                           if body else None) or '46ch',
            'overlay': (grab(r'inset:0;background:(linear-gradient\(to (?:bottom|right).*?);pointer-events:none', b) or '').strip(),
        },
    }


def scenes_of(page):
    b = band(page, 'id="scenes"')
    if not b:
        return None
    blocks = {}
    order = []
    for i, chunk in enumerate(re.findall(r'<div class="snap scene".*?(?=<div class="snap scene"|</section>)', b, re.S)):
        key = 'scene_%d' % (i + 1)
        order.append(key)
        media_first = chunk.find('scene-media') < chunk.find('scene-text')
        poster = (grab(r'class="scene-media"[^>]*background-image:url\(([^)]+)\)', chunk)
                  or grab(r'class="scene-media".*?<img[^>]*src="([^"]+)"', chunk))
        focus = grab(r'class="scene-media"[^>]*background-position:([^;"]+)', chunk) or 'center'
        blocks[key] = {
            'type': 'scene',
            'settings': {
                'media_side': 'left' if media_first else 'right',
                'video': asset(grab(r'<video[^>]*src="([^"]+)"', chunk)),
                'poster': asset(poster),
                'focus': focus.strip(),
                'start': grab(r'<video[^>]*data-start="([^"]+)"', chunk) or '',
                'eyebrow': text(grab(r'text-transform:uppercase[^>]*>(.*?)</div>', chunk)),
                'heading': text(grab(r'<h2[^>]*>(.*?)</h2>', chunk)),
                'body': rich(grab(r'<p[^>]*>(.*?)</p>', chunk)),
            },
        }
    return {'type': 'kaibo-scenes', 'blocks': blocks, 'block_order': order,
            'settings': {'anchor': 'scenes'}}


def head_of(b):
    """The eyebrow / h2 / lede every band below the hero shares."""
    return (text(grab(r'text-transform:uppercase[^>]*>(.*?)</div>', b)),
            text(grab(r'<h2[^>]*>(.*?)</h2>', b)),
            rich(grab(r'</h2>\s*(?:</div>\s*)?<p[^>]*>(.*?)</p>', b)))


def technology_of(page):
    b = band(page, 'id="technology"')
    if not b:
        return None
    eyebrow, heading, body = head_of(b)
    cards = grab(r'class="tech-cards"[^>]*>(.*)', b)
    blocks, order = {}, []
    for i, chunk in enumerate(re.findall(r'<div style="padding:38px 32px 42px">(.*?)</p>', cards, re.S)):
        key = 'card_%d' % (i + 1)
        order.append(key)
        blocks[key] = {'type': 'card', 'settings': {
            'illustration': asset(grab(r'<img[^>]*src="([^"]+)"', chunk)),
            'title': text(grab(r'font-weight:600;margin-bottom:10px">(.*?)</div>', chunk)),
            'body': rich(grab(r'<p[^>]*>(.*)', chunk)),
        }}
    return {'type': 'kaibo-technology', 'blocks': blocks, 'block_order': order,
            'settings': {'anchor': 'technology', 'eyebrow': eyebrow,
                         'heading': heading, 'body': body}}


def products_of(page):
    b = band(page, 'id="products"')
    if not b:
        return None
    eyebrow, heading, body = head_of(b)
    feature = grab(r'(class="cards feature".*?)(?=<div class="cards")', b)
    blocks, order = {}, []
    if feature:
        order.append('feature')
        blocks['feature'] = {'type': 'feature', 'settings': {
            'image': asset(grab(r'<img[^>]*src="([^"]+)"', feature)),
            'eyebrow': text(grab(r'text-transform:uppercase[^>]*>(.*?)</div>', feature)),
            'title': text(grab(r'<h3[^>]*>(.*?)</h3>', feature)),
            'body': rich(grab(r'<p[^>]*>(.*?)</p>', feature)),
        }}
    grid = b[b.find('border-top:none'):] if 'border-top:none' in b else ''
    for i, chunk in enumerate(re.findall(r'<div data-reveal=""[^>]*>\s*<div style="height:180px.*?</p>', grid, re.S)):
        key = 'product_%d' % (i + 1)
        order.append(key)
        blocks[key] = {'type': 'product', 'settings': {
            'image': asset(grab(r'<img[^>]*src="([^"]+)"', chunk)),
            'title': text(grab(r'<h3[^>]*>(.*?)</h3>', chunk)),
            'body': rich(grab(r'<p[^>]*>(.*)', chunk)),
        }}
    panel = grab(r'class="cards feature".*?<div data-reveal=""[^>]*background:(#[0-9a-fA-F]+)', b)
    return {'type': 'kaibo-products', 'blocks': blocks, 'block_order': order,
            'settings': {'anchor': 'products', 'eyebrow': eyebrow, 'heading': heading,
                         'body': body, 'card_bg': 'light' if panel == '#fff' else 'dark'}}


def story_of(page):
    b = band(page, 'id="story"')
    if not b:
        return None
    eyebrow, heading, body = head_of(b)
    blocks, order = {}, []
    for i, chunk in enumerate(re.findall(r'<div class="kb-tl-item".*?(?=<div class="kb-tl-item"|</div>\s*</div>\s*</section>)', b, re.S)):
        key = 'milestone_%d' % (i + 1)
        order.append(key)
        year = grab(r'class="kb-tl-year">(.*?)</div>', chunk)
        blocks[key] = {'type': 'milestone', 'settings': {
            'year': text(re.sub(r'<span class="kb-tl-tag">.*?</span>', '', year or '', flags=re.S)),
            'tag': text(grab(r'class="kb-tl-tag">(.*?)</span>', chunk)),
            'heading': text(grab(r'<h3[^>]*>(.*?)</h3>', chunk)),
            'body': rich(grab(r'<p[^>]*>(.*?)</p>', chunk)),
            'image': asset(grab(r'<img[^>]*src="([^"]+)"', chunk)),
            'image_alt': html.unescape(grab(r'<img[^>]*alt="([^"]*)"', chunk) or ''),
        }}
    return {'type': 'kaibo-story', 'blocks': blocks, 'block_order': order,
            'settings': {'anchor': 'story', 'eyebrow': eyebrow, 'heading': heading, 'body': body}}


PAGE_URL = {'index.html': '/pages/kaibo-tv', 'tour.html': '/pages/kaibo-tour',
            'personal.html': '/pages/kaibo-personal', 'about.html': '/pages/kaibo-about'}


def experiences_of(page):
    b = band(page, 'id="experiences"')
    if not b:
        return None
    eyebrow, heading, body = head_of(b)
    blocks, order = {}, []
    for i, chunk in enumerate(re.findall(r'<a class="kb-card-link".*?</a>', b, re.S)):
        key = 'card_%d' % (i + 1)
        order.append(key)
        href = grab(r'href="([^"]+)"', chunk)
        blocks[key] = {'type': 'card', 'settings': {
            'image': asset(grab(r'background-image:url\(([^)]+)\)', chunk)),
            'title': text(grab(r'<h3[^>]*>(.*?)</h3>', chunk)),
            'body': rich(grab(r'<p[^>]*>(.*?)</p>', chunk)),
            'url': PAGE_URL.get(href, href),
            'link_label': text(grab(r'class="kb-card-go">(.*?)<span', chunk)),
        }}
    return {'type': 'kaibo-experiences', 'blocks': blocks, 'block_order': order,
            'settings': {'anchor': 'experiences', 'eyebrow': eyebrow,
                         'heading': heading, 'body': body}}


def values_of(page):
    b = band(page, 'id="values"')
    if not b:
        return None
    eyebrow, heading, body = head_of(b)
    blocks, order = {}, []
    for i, chunk in enumerate(re.findall(r'<div data-reveal=""[^>]*padding:40px 34px 42px">(.*?)</p>', b, re.S)):
        key = 'value_%d' % (i + 1)
        order.append(key)
        blocks[key] = {'type': 'value', 'settings': {
            'title': text(grab(r'<h3[^>]*>(.*?)</h3>', chunk)),
            'body': rich(grab(r'<p[^>]*>(.*)', chunk)),
        }}
    return {'type': 'kaibo-values', 'blocks': blocks, 'block_order': order,
            'settings': {'anchor': 'values', 'eyebrow': eyebrow, 'heading': heading, 'body': body}}


def contact_of(page):
    b = band(page, 'id="contact"', closer='</section>')
    eyebrow, heading, body = head_of(b)
    options = [text(o) for o in re.findall(r'<option[^>]*>(.*?)</option>', b, re.S)]
    return {'type': 'kaibo-contact', 'settings': {
        'anchor': 'contact', 'eyebrow': eyebrow, 'heading': heading, 'body': body,
        'products': ', '.join(options),
        'thanks_title': text(grab(r'font-size:26px[^>]*>(.*?)</div>', b)),
        'thanks_body': text(grab(r'font-size:26px.*?<p[^>]*>(.*?)</p>', b)),
        'footer_logo': asset(grab(r'class="wordmark" src="([^"]+)"', b)),
        'footer_logo_alt': html.unescape(grab(r'class="wordmark"[^>]*alt="([^"]*)"', b) or ''),
        'tagline': text(grab(r'font-size:13px">(.*?)</span>', b)),
        'copyright': text(grab(r'<div style="color:#8A8A8F;font-size:13px">(.*?)</div>', b)),
    }}


NAV = [('tv', 'index.html'), ('tour', 'tour.html'),
       ('personal', 'personal.html'), ('about', 'about.html')]


def header_of(page, active):
    labels = dict(re.findall(r'data-nav="(\w+)">\s*<a class="kb-nav-top"[^>]*>(.*?)</a>', page, re.S))
    blocks, order = {}, []
    for key, href in NAV:
        blocks[key] = {'type': 'nav_item', 'settings': {
            'key': key, 'label': text(labels.get(key, key)), 'url': PAGE_URL[href],
            'show_subnav': key != 'about',
        }}
        order.append(key)
    return {'type': 'kaibo-header', 'blocks': blocks, 'block_order': order,
            'settings': {'logo_light': 'kaibo-logo_kaibo_light.webp',
                         'logo_dark': 'kaibo-logo_kaibo_dark.webp',
                         'logo_alt': 'Kaibo audio', 'home_url': PAGE_URL['index.html'],
                         'active': active, 'sub_1': 'Where it works', 'sub_2': 'Technology',
                         'sub_3': 'Products', 'cta_label': 'Contact us', 'cta_url': '#contact',
                         'menu_label': 'Menu'}}


PAGES = [('index.html', 'page.kaibo-tv', 'tv'), ('tour.html', 'page.kaibo-tour', 'tour'),
         ('personal.html', 'page.kaibo-personal', 'personal'),
         ('about.html', 'page.kaibo-about', 'about')]

BUILDERS = [hero_of, scenes_of, story_of, technology_of, experiences_of,
            products_of, values_of, contact_of]

os.makedirs(OUT, exist_ok=True)
for source, template, active in PAGES:
    page = io.open(os.path.join(ROOT, source), encoding='utf-8').read()
    sections = {'header': header_of(page, active)}
    order = ['header']
    for i, build in enumerate(BUILDERS):
        made = build(page)
        if not made:
            continue
        name = made.pop('type').replace('kaibo-', '')
        made = {'type': 'kaibo-' + name, **made}
        sections[name] = made
        order.append(name)
    doc = {'layout': 'kaibo', 'sections': sections, 'order': order}
    path = os.path.join(OUT, '%s.json' % template)
    io.open(path, 'w', encoding='utf-8').write(
        json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print('  %-28s %2d sections' % (os.path.basename(path), len(order)))
