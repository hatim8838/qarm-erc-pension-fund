"""Page « About us » : présentation des six membres du groupe.

Cette page est autonome : elle n'importe aucun autre fichier du projet.
Elle reprend le design « Amber » du site (Inter, pêche #FFCC99, ambre #CC6600, barres marine).

COMMENT LA PERSONNALISER (voir la liste TEAM juste en dessous)
  - Remplir ``role``, ``bio``, ``tags`` et ``linkedin`` de chaque membre.
  - Ajouter une photo : copier l'image dans  streamlit/assets/team/
    et la nommer comme le prénom en minuscules, par exemple  hatim.jpg
    (formats acceptés : .jpg .jpeg .png .webp).
    Les photos s'affichent en couleur, dans un cercle.
    Sans photo, un cercle coloré avec l'initiale s'affiche.
"""

from __future__ import annotations

import base64
import io
from html import escape
from pathlib import Path

import streamlit as st

APP_DIR = Path(__file__).resolve().parent
PHOTO_DIR = APP_DIR / "assets" / "team"
PHOTO_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")
BANNER_PATH = APP_DIR / "assets" / "leman_banner.png"  # image de la page d'accueil
FIRM_NAME = "Leman Wealth Management"

# --------------------------------------------------------------------------- #
# À COMPLÉTER PAR LE GROUPE
# --------------------------------------------------------------------------- #
# Les rôles ci-dessous sont fictifs : les échanger entre vous comme vous voulez.
# role     : titre court affiché sous le nom (laisser "" pour « Team member »)
# bio      : 1 à 2 phrases (laisser "" pour ne rien afficher)
# tags     : 2 à 4 mots-clés, par exemple ["Python", "Optimisation ERC"]
# linkedin : lien complet du profil (laisser "" pour masquer le bouton)
TEAM = [
    {
        "name": "Sami",
        "role": "Founder & CEO",
        "bio": "Defines the firm's vision and investment philosophy, and leads the relationship with our investors.",
        "tags": ["Strategy", "Governance"],
        "linkedin": "",
    },
    {
        "name": "Hatim",
        "role": "CIO · Quantitative Research",
        "bio": "Leads portfolio construction and the quantitative research behind our risk-based allocation.",
        "tags": ["Portfolio construction", "Risk budgeting"],
        "linkedin": "",
    },
    {
        "name": "Yazid",
        "role": "Head of Data",
        "bio": "Oversees our data infrastructure, ensuring reliable and consistent market data across all strategies.",
        "tags": ["Market data", "Data quality"],
        "linkedin": "",
    },
    {
        "name": "Elvedin",
        "role": "Head of Risk & ESG",
        "bio": "Monitors portfolio risk and integrates ESG criteria into our investment process.",
        "tags": ["Risk management", "ESG"],
        "linkedin": "",
    },
    {
        "name": "Ishaq",
        "role": "Head of Platform",
        "bio": "Builds and maintains the digital platform through which investors access our analytics.",
        "tags": ["Digital platform", "Analytics"],
        "linkedin": "",
    },
    {
        "name": "Mathieu",
        "role": "COO · Investor Relations",
        "bio": "Manages operations and client communication, ensuring a transparent and responsive service.",
        "tags": ["Operations", "Client relations"],
        "linkedin": "",
    },
]

DEFAULT_ROLE = "Team member"

# True  : le bouton LinkedIn s'affiche toujours (grisé tant que le lien est vide).
# False : le bouton n'apparaît que si le lien est rempli.
SHOW_EMPTY_LINKEDIN = True

# Couleurs de l'avatar (quand il n'y a pas encore de photo) : palette « Amber » (bleu, or, ambre, marine).
AVATAR_GRADIENTS = [
    ("#1976D2", "#64A8EC"),
    ("#CC6600", "#F2A65A"),
    ("#1A2A6C", "#3F5BB0"),
    ("#F9A825", "#FFD27A"),
    ("#E8A15C", "#CC6600"),
    ("#0D47A1", "#1976D2"),
]

_CSS = """
<style>
.qt-hero {
  position: relative; border-radius: 15px; padding: 4rem 3rem; color: #FFFFFF; min-height: 320px;
  display: flex; flex-direction: column; justify-content: center;
  background-color: #1A2A6C; background-size: cover; background-position: center 60%;
  margin-bottom: 1rem; overflow: hidden;
}
.qt-hero::before {content: ""; position: absolute; inset: 0;
  background: linear-gradient(90deg, rgba(0,0,0,.62) 0%, rgba(0,0,0,.35) 55%, rgba(0,0,0,.10) 100%);}
.qt-hero > * {position: relative;}
.qt-firm {font-size: .85rem; font-weight: 700; letter-spacing: .14em; text-transform: uppercase;
  color: #FFCC99; margin-bottom: 1rem;}
.qt-hero h1 {
  font-family: 'Inter', 'Segoe UI', sans-serif !important; font-weight: 700 !important;
  color: #FFFFFF; font-size: 3.2rem; line-height: 1.08; margin: 0 0 1rem 0; padding: 0;
  text-shadow: 0 1px 2px rgba(0,0,0,.5);
}
.qt-hero p {color: #F2F2F2; font-size: 1.1rem; line-height: 1.65; max-width: 44rem; margin: 0;}
.qt-section {font-size: 2rem; font-weight: 600; margin: 3rem 0 .6rem 0; border-left: 5px solid #1A2A6C;
  padding-left: 15px; line-height: 1.2;}
.qt-sub {color: #555; font-size: 18px; margin: 0 0 1.8rem 0;}
.qt-grid {display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem;}
.qt-card {
  background: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 12px; overflow: hidden;
  text-align: center; padding: 0 1.4rem 1.7rem 1.4rem; box-shadow: 0 2px 5px rgba(0,0,0,.05);
  transition: transform .2s ease, box-shadow .2s ease, border-color .2s ease;
}
.qt-card:hover {transform: translateY(-4px); box-shadow: 0 14px 30px rgba(0,0,0,.10); border-color: #FFCC99;}
.qt-banner {height: 78px; margin: 0 -1.4rem; background: linear-gradient(120deg, #FFCC99, #CC6600);}
.qt-avatar {
  width: 124px; height: 124px; border-radius: 50%; margin: -62px auto 1.1rem auto;
  border: 5px solid #FFFFFF; box-shadow: 0 6px 16px rgba(0,0,0,.18);
  display: flex; align-items: center; justify-content: center; overflow: hidden;
  color: #FFFFFF; font-size: 3rem; font-weight: 700;
}
.qt-avatar img {width: 100%; height: 100%; object-fit: cover; display: block;}
.qt-name {font-size: 1.45rem !important; font-weight: 700; margin: 0 !important; line-height: 1.2;}
.qt-role {
  display: block; margin: .35rem 0 .85rem 0; color: #CC6600;
  font-size: .74rem; font-weight: 700; letter-spacing: .12em; text-transform: uppercase;
}
.qt-bio {color: #444; font-size: .95rem; line-height: 1.6; margin: 0 0 .9rem 0;}
.qt-tags {margin-bottom: 1.1rem;}
.qt-tag {
  display: inline-block; margin: .15rem .15rem; padding: .15rem .7rem; border-radius: 999px;
  background: #FFCC99; color: #000; font-size: .76rem; font-weight: 600;
}
.qt-link {
  display: inline-block; padding: .4rem 1.3rem; border-radius: 8px; border: 2px solid transparent;
  color: #2E86C1 !important; font-size: .9rem; font-weight: 600; text-decoration: none !important;
  transition: background .18s ease, color .18s ease, border-color .18s ease;
}
.qt-link:hover {background: #FFCC99; color: #000 !important; border-color: #CC6600;}
.qt-link-off {
  display: inline-block; padding: .4rem 1.3rem; border-radius: 8px; border: 2px solid #E0E0E0;
  color: #A3A6AB; font-size: .9rem; font-weight: 600; cursor: default;
}
.qt-note {color: #888; font-size: .82rem; margin-top: 2.6rem; text-align: center;}
@media (max-width: 640px) {.qt-hero {padding: 2.2rem 1.4rem;} .qt-hero h1 {font-size: 2.4rem;}}
</style>
"""


@st.cache_data(show_spinner=False)
def _photo_data_uri(path_str: str, mtime: float) -> str | None:
    """Image -> data URI, reduced to 480 px so the page stays light.

    ``mtime`` only serves to refresh the cache when the file is replaced.
    """
    path = Path(path_str)
    try:
        raw = path.read_bytes()
        try:
            from PIL import Image, ImageOps

            img = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
            img.thumbnail((480, 480))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=88)
            return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
        except Exception:  # Pillow missing or unreadable image: use the raw file
            mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
            return f"data:{mime};base64," + base64.b64encode(raw).decode()
    except OSError:
        return None


@st.cache_data(show_spinner=False)
def _hero_background() -> str:
    """Bas de la bannière d'accueil (montagnes + lac, sans le texte) en fond du titre. '' si indisponible."""
    try:
        from PIL import Image

        img = Image.open(BANNER_PATH).convert("RGB")
        w, h = img.size
        img = img.crop((0, int(h * 0.44), w, h))  # on garde le paysage, on retire le texte du haut
        img.thumbnail((1600, 1600))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=82)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:  # image ou Pillow absent : le fond marine prend le relais
        return ""


def _find_photo(name: str) -> str | None:
    stem = name.strip().lower()
    for ext in PHOTO_EXTENSIONS:
        path = PHOTO_DIR / f"{stem}{ext}"
        if path.is_file():
            return _photo_data_uri(str(path), path.stat().st_mtime)
    return None


def _card(index: int, member: dict) -> str:
    name = member["name"]
    photo = _find_photo(name)
    if photo:
        avatar = f'<div class="qt-avatar"><img src="{photo}" alt="{escape(name)}"></div>'
    else:
        c1, c2 = AVATAR_GRADIENTS[index % len(AVATAR_GRADIENTS)]
        avatar = (
            f'<div class="qt-avatar" style="background: linear-gradient(135deg, {c1}, {c2});">'
            f"{escape(name[:1].upper())}</div>"
        )
    role = escape(member.get("role") or DEFAULT_ROLE)
    parts = [
        '<div class="qt-card">',
        '<div class="qt-banner"></div>',
        avatar,
        f'<p class="qt-name">{escape(name)}</p>',
        f'<span class="qt-role">{role}</span>',
    ]
    if member.get("bio"):
        parts.append(f'<p class="qt-bio">{escape(member["bio"])}</p>')
    if member.get("tags"):
        tags = "".join(f'<span class="qt-tag">{escape(t)}</span>' for t in member["tags"])
        parts.append(f'<div class="qt-tags">{tags}</div>')
    link = (member.get("linkedin") or "").strip()
    if link:
        if not link.lower().startswith(("http://", "https://")):
            link = "https://" + link  # tolerate "linkedin.com/in/..." pasted without https
        parts.append(
            f'<a class="qt-link" href="{escape(link, quote=True)}" '
            'target="_blank" rel="noopener noreferrer">LinkedIn</a>'
        )
    elif SHOW_EMPTY_LINKEDIN:
        parts.append('<span class="qt-link-off" title="Profile link coming soon">LinkedIn</span>')
    parts.append("</div>")
    return "".join(parts)


def render() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)

    bg = _hero_background()
    bg_style = f' style="background-image: url({bg});"' if bg else ""
    st.markdown(
        f'<div class="qt-hero"{bg_style}>'
        f'<div class="qt-firm">{escape(FIRM_NAME)}</div>'
        "<h1>Our team</h1>"
        "<p>Our team unites expertise in quantitative research, risk management and investor "
        "relations. Together, we build multi-asset portfolios for pension funds on a clear "
        "principle: every asset should contribute equally to risk, not only to capital.</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="qt-section">Meet the team</div>', unsafe_allow_html=True)
    st.markdown(
        '<p class="qt-sub">Six professionals, one shared objective: giving investors a transparent view of how risk is distributed across their portfolio.</p>',
        unsafe_allow_html=True,
    )
    cards = "".join(_card(i, m) for i, m in enumerate(TEAM))
    st.markdown(f'<div class="qt-grid">{cards}</div>', unsafe_allow_html=True)

    st.markdown(
        '<div class="qt-note">Fictional presentation for educational purposes. '
        "This application does not constitute investment advice.</div>",
        unsafe_allow_html=True,
    )


render()
