"""Page « About us » : présentation des six membres du groupe.

Cette page est autonome : elle n'importe aucun autre fichier du projet.
Elle reprend l'identité visuelle de la page d'accueil (noir & blanc, gris, typographie à empattements).

COMMENT LA PERSONNALISER (voir la liste TEAM juste en dessous)
  - Remplir ``role``, ``bio``, ``tags`` et ``linkedin`` de chaque membre.
  - Ajouter une photo : copier l'image dans  streamlit/assets/team/
    et la nommer comme le prénom en minuscules, par exemple  hatim.jpg
    (formats acceptés : .jpg .jpeg .png .webp).
    Les photos s'affichent automatiquement en noir et blanc.
    Sans photo, un cercle gris avec l'initiale s'affiche.
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

# Couleurs de l'avatar (quand il n'y a pas encore de photo) : dégradés de gris.
AVATAR_GRADIENTS = [
    ("#2B2F36", "#5A6068"),
    ("#3A3F47", "#7A8088"),
    ("#4A4F57", "#8C9199"),
    ("#2F3338", "#686E76"),
    ("#41464E", "#80868E"),
    ("#363A41", "#6F757D"),
]

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=EB+Garamond:wght@400;500;600&display=swap');
.qt-hero {
  position: relative; border-radius: 6px; padding: 3.4rem 3rem 3.2rem 3rem; color: #FFFFFF;
  background-color: #2B2F36; background-size: cover; background-position: center 60%;
  margin-bottom: 2.6rem; overflow: hidden;
}
.qt-hero::before {content: ""; position: absolute; inset: 0;
  background: linear-gradient(90deg, rgba(22,24,28,.78) 0%, rgba(22,24,28,.50) 55%, rgba(22,24,28,.30) 100%);}
.qt-hero > * {position: relative;}
.qt-firm {font-family: 'EB Garamond', Georgia, 'Times New Roman', serif; font-size: 1.15rem; opacity: .92; margin-bottom: 1.6rem;}
.qt-hero h1 {
  font-family: 'EB Garamond', Georgia, 'Times New Roman', serif; font-weight: 500;
  color: #FFFFFF; font-size: 3.4rem; line-height: 1.08; margin: 0 0 1rem 0; padding: 0; letter-spacing: -.01em;
}
.qt-hero p {color: #ECECEA; font-size: 1.04rem; line-height: 1.65; max-width: 44rem; margin: 0;}
.qt-section {font-family: 'EB Garamond', Georgia, 'Times New Roman', serif; font-size: 1.9rem; font-weight: 500;
  color: #1E2127; margin: 2.2rem 0 .3rem 0;}
.qt-sub {color: #6B7078; margin: 0 0 1.6rem 0;}
.qt-grid {display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.4rem;}
.qt-card {
  background: #FFFFFF; border: 1px solid #E3E3E0; border-radius: 6px; overflow: hidden;
  text-align: center; padding: 0 1.4rem 1.7rem 1.4rem;
  transition: transform .2s ease, box-shadow .2s ease, border-color .2s ease;
}
.qt-card:hover {transform: translateY(-4px); box-shadow: 0 14px 30px rgba(30, 33, 39, .12); border-color: #C9C9C5;}
.qt-banner {height: 74px; margin: 0 -1.4rem; background: linear-gradient(120deg, #2B2F36, #6B7078);}
.qt-avatar {
  width: 124px; height: 124px; border-radius: 50%; margin: -62px auto 1.1rem auto;
  border: 5px solid #FFFFFF; box-shadow: 0 6px 16px rgba(30, 33, 39, .22);
  display: flex; align-items: center; justify-content: center; overflow: hidden;
  color: #FFFFFF; font-family: 'EB Garamond', Georgia, serif; font-size: 3rem; font-weight: 500;
}
.qt-avatar img {width: 100%; height: 100%; object-fit: cover; display: block; filter: grayscale(100%) contrast(1.03);}
.qt-name {font-family: 'EB Garamond', Georgia, 'Times New Roman', serif; font-size: 1.55rem; font-weight: 500;
  color: #1E2127; margin: 0; line-height: 1.2;}
.qt-role {
  display: block; margin: .35rem 0 .85rem 0; color: #6B7078;
  font-size: .72rem; font-weight: 600; letter-spacing: .12em; text-transform: uppercase;
}
.qt-bio {color: #4A4F57; font-size: .93rem; line-height: 1.6; margin: 0 0 .9rem 0;}
.qt-tags {margin-bottom: 1rem;}
.qt-tag {
  display: inline-block; margin: .15rem .15rem; padding: .12rem .65rem; border-radius: 999px;
  background: #F0F0EE; color: #4A4F57; font-size: .74rem; font-weight: 600;
}
.qt-link {
  display: inline-block; padding: .35rem 1.2rem; border-radius: 999px; border: 1.5px solid #2B2F36;
  color: #2B2F36 !important; font-size: .82rem; font-weight: 600; text-decoration: none !important;
  transition: background .2s ease, color .2s ease;
}
.qt-link:hover {background: #2B2F36; color: #FFFFFF !important;}
.qt-link-off {
  display: inline-block; padding: .35rem 1.2rem; border-radius: 999px; border: 1.5px solid #D4D4D0;
  color: #A3A6AB; font-size: .82rem; font-weight: 600; cursor: default;
}
.qt-note {color: #6B7078; font-size: .82rem; margin-top: 2.6rem; padding-top: 1rem; border-top: 1px solid #E3E3E0;}
@media (max-width: 640px) {.qt-hero {padding: 2.2rem 1.4rem;} .qt-hero h1 {font-size: 2.5rem;}}
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
    except Exception:  # image ou Pillow absent : le dégradé gris prend le relais
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
