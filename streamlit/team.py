"""Page « Équipe » : présentation des six membres du groupe.

Cette page est autonome : elle n'importe aucun autre fichier du projet.

COMMENT LA PERSONNALISER (voir la liste TEAM juste en dessous)
  - Remplir ``role``, ``bio``, ``tags`` et ``linkedin`` de chaque membre.
  - Ajouter une photo : copier l'image dans  streamlit/assets/team/
    et la nommer comme le prénom en minuscules, par exemple  hatim.jpg
    (formats acceptés : .jpg .jpeg .png .webp).
    Sans photo, un cercle avec l'initiale s'affiche automatiquement.
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

# Couleurs de l'avatar (quand il n'y a pas encore de photo).
AVATAR_GRADIENTS = [
    ("#1B365D", "#3E6FA8"),
    ("#2E7D5B", "#5BB08A"),
    ("#3E6FA8", "#7A9CC6"),
    ("#C08A3E", "#E0B16B"),
    ("#8C5A7A", "#B98AA8"),
    ("#2F4A6D", "#5B6B7F"),
]

_CSS = """
<style>
.qt-hero {
  background: linear-gradient(120deg, #1B365D 0%, #264A7C 55%, #3E6FA8 100%);
  border-radius: 18px; padding: 2.6rem 2.8rem; color: #FFFFFF;
  box-shadow: 0 10px 30px rgba(27, 54, 93, .22); margin-bottom: 2.2rem;
}
.qt-eyebrow {font-size: .78rem; letter-spacing: .14em; text-transform: uppercase; opacity: .78;}
.qt-hero h1 {color: #FFFFFF; font-size: 2.6rem; line-height: 1.15; margin: .35rem 0 .8rem 0; padding: 0;}
.qt-hero p {color: #E6EDF7; font-size: 1.05rem; line-height: 1.6; max-width: 46rem; margin: 0;}
.qt-section {font-size: 1.35rem; font-weight: 700; color: #1B365D; margin: 2.4rem 0 .2rem 0;}
.qt-sub {color: #5B6B7F; margin: 0 0 1.2rem 0;}
.qt-grid {display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.4rem;}
.qt-card {
  background: #FFFFFF; border: 1px solid #E3E8EF; border-radius: 16px; overflow: hidden;
  text-align: center; padding: 0 1.4rem 1.6rem 1.4rem;
  box-shadow: 0 2px 10px rgba(27, 54, 93, .06);
  transition: transform .2s ease, box-shadow .2s ease;
}
.qt-card:hover {transform: translateY(-5px); box-shadow: 0 14px 30px rgba(27, 54, 93, .16);}
.qt-banner {height: 78px; margin: 0 -1.4rem; background: linear-gradient(120deg, #1B365D, #3E6FA8);}
.qt-avatar {
  width: 128px; height: 128px; border-radius: 50%; margin: -64px auto 1rem auto;
  border: 5px solid #FFFFFF; box-shadow: 0 6px 16px rgba(27, 54, 93, .25);
  display: flex; align-items: center; justify-content: center; overflow: hidden;
  color: #FFFFFF; font-size: 3rem; font-weight: 700;
}
.qt-avatar img {width: 100%; height: 100%; object-fit: cover; display: block;}
.qt-name {font-size: 1.3rem; font-weight: 700; color: #1A1F2B; margin: 0;}
.qt-role {
  display: inline-block; margin: .45rem 0 .7rem 0; padding: .18rem .75rem; border-radius: 999px;
  background: #EEF1F5; color: #1B365D; font-size: .8rem; font-weight: 600;
}
.qt-bio {color: #5B6B7F; font-size: .93rem; line-height: 1.55; margin: 0 0 .8rem 0;}
.qt-tags {margin-bottom: .9rem;}
.qt-tag {
  display: inline-block; margin: .15rem .15rem; padding: .12rem .6rem; border-radius: 999px;
  background: #E5F2EC; color: #2E7D5B; font-size: .74rem; font-weight: 600;
}
.qt-link {
  display: inline-block; padding: .35rem 1.1rem; border-radius: 999px; border: 1.5px solid #1B365D;
  color: #1B365D !important; font-size: .82rem; font-weight: 600; text-decoration: none !important;
  transition: background .2s ease, color .2s ease;
}
.qt-link:hover {background: #1B365D; color: #FFFFFF !important;}
.qt-note {color: #5B6B7F; font-size: .82rem; margin-top: 2.4rem; padding-top: 1rem; border-top: 1px solid #E3E8EF;}
@media (max-width: 640px) {.qt-hero {padding: 1.8rem 1.4rem;} .qt-hero h1 {font-size: 2rem;}}
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
    parts.append("</div>")
    return "".join(parts)


def render() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)

    st.markdown(
        '<div class="qt-hero">'
        '<div class="qt-eyebrow">Quantitative portfolio management</div>'
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
