# Kaibo on Shopify

The four static pages, rebuilt as theme sections so they can live in the
Narrative theme. `build_templates.py` generates the templates from the HTML, so
the static site stays the source of truth for the copy: edit the HTML, re-run
the script, push again.

```
assets/      kaibo-site.css, kaibo-site.js and every image the pages use
layout/      kaibo.liquid - a bare layout, so Narrative's own header and
             footer do not sit on top of the Kaibo bar
sections/    nine kaibo-* sections
templates/   page.kaibo-tv / -tour / -personal / -about
```

Every file is named `kaibo-*`, so pushing this adds to the theme rather than
replacing any of it.

The TV range is a page of its own rather than the theme's home. Narrative is a
Liquid-template theme and already carries `templates/index.liquid`; Shopify
refuses an `index.json` beside it, and taking the homepage would have meant
deleting theirs.

## Pushing it

Device authorization mails a code to the store owner's inbox, so pushes use a
Theme Access token instead (apps.shopify.com/theme-access, scoped to
`write_themes`, mailed to whoever needs it). Keep it out of the shell history:

```bash
SHOPIFY_CLI_THEME_TOKEN=$(cat ~/.kaibo-theme-token) \
npx @shopify/cli@latest theme push --store psa-tw --theme <id> \
  --path shopify --nodelete
```

`--nodelete` keeps every remote file that is not in this folder. The themes are
150948642969 (draft, "Narrative - Kaibo WIP") and 118422143129 (live,
"Narrative"); the live one needs `--allow-live`.

## What has to happen once, by hand

**The films go to Content > Files, not the theme.** Theme assets do not take
video. Drag these eight in and keep the names exactly as they are:

```
shot1_v7.mp4  shot2_v3.mp4  shot3_v3.mp4  shot4_v3.mp4
Tour_shot0_v1.mp4  Tour_shot1_v2.mp4  Tour_shot2_v2.mp4  Tour_shot3_v2.mp4
```

They are staged together in `~/Desktop/kaibo /shopify-upload/`. If a film still
does not appear after the upload, open Content > Files, copy its link, and
paste the whole URL into that section's video field: the sections take either a
file name or a full link.

**Four pages, with these handles.** Online Store > Pages > Add page, then set
the theme template on each. The handles are what the bar links to, so they have
to match or the tabs will 404.

| Page | Handle | Template |
| --- | --- | --- |
| TV Hearing Assistance | `kaibo-tv` | kaibo-tv |
| Tour Hearing Assistance | `kaibo-tour` | kaibo-tour |
| Personal Hearing Assistance | `kaibo-personal` | kaibo-personal |
| About us | `kaibo-about` | kaibo-about |

The template picker in the page editor reads the **live** theme, not a draft,
so the templates have to exist on the live theme before they can be chosen.

**The contact form.** Unlike the static build it posts for real, through
Shopify's own contact form. Enquiries go to the address in Settings >
Notifications > Customer contact.

## The domain

Only after the theme is published. At GoDaddy, point `kaibolife.com` at
Shopify, then connect it in Settings > Domains:

| Type | Name | Value |
| --- | --- | --- |
| A | `@` | `23.227.38.65` |
| CNAME | `www` | `shops.myshopify.com.` |

Up to 48 hours for the domain and its certificate to settle.

## Editing afterwards

Every heading, paragraph, product and milestone is a section setting, so the
copy can be changed in the theme editor without touching code. Image fields
take the file name of a theme asset (`kaibo-poster-hero.jpg`); to swap a
photograph, drop the new file into `assets/` under the same name and push.

To pull a round of copy changes across from the static site instead:

```bash
python3 shopify/build_templates.py
```

That rewrites the templates from the HTML. It overwrites whatever was edited in
the theme editor, so use one or the other, not both.

`theme check` reports eight `ImgWidthAndHeight` notices. Those images are sized
by CSS, and the static site carries the same markup; the attributes are left
off because the file names are editable settings and a stale size hint would be
worse than none.
