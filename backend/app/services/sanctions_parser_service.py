"""
Parsing des formats natifs de listes de sanctions — reproduit la logique du
projet assujetti, adapté pour retourner directement des entrées exploitables.

Formats supportés :
  - PDF  : liste nationale 1373 (CI)
  - HTML : liste ONU consolidée (CSDNU) — ex. consolidatedLegacyByNAME.html
  - CSV  : 1 à 4 colonnes (nom, date_naissance, nationalite, lieu_naissance)

Chaque parser retourne une liste de dicts :
  {nom, date_naissance, nationalite, lieu_naissance}
`nom` et `nationalite`/`lieu_naissance` sont normalisés (majuscules, sans diacritiques).
"""
import csv
import io
import re
import unicodedata


# ── Normalisation ─────────────────────────────────────────────────────────────

def normalize(text: str) -> str:
    """Majuscules + suppression des diacritiques combinants."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).upper().strip()


# ── Parser CSV ────────────────────────────────────────────────────────────────

def parse_csv(content: bytes) -> list[dict]:
    """CSV 1 à 4 colonnes : nom[, date_naissance, nationalite, lieu_naissance]."""
    reader = csv.reader(io.StringIO(content.decode("utf-8-sig", errors="replace")))
    entries: list[dict] = []
    seen: set[str] = set()
    for row in reader:
        if not row or not row[0].strip():
            continue
        nom = normalize(row[0])
        if not nom or len(nom) <= 2 or nom in seen:
            continue
        seen.add(nom)
        entries.append({
            "nom": nom,
            "date_naissance": row[1].strip() if len(row) > 1 else "",
            "nationalite": normalize(row[2]) if len(row) > 2 else "",
            "lieu_naissance": normalize(row[3]) if len(row) > 3 else "",
        })
    return entries


# ── Parser PDF (liste nationale 1373 CI) ─────────────────────────────────────

_PDF_NOM     = re.compile(r"Nom et pr[eé]noms\s*:\s*(.+)", re.IGNORECASE)
_PDF_DDN     = re.compile(r"Date et lieu de naissance\s*:\s*le\s+(\d{2}/\d{2}/\d{4})", re.IGNORECASE)
_PDF_DDN_ALT = re.compile(r"Date et lieu de naissance\s*:\s*(\d{2}/\d{2}/\d{4})", re.IGNORECASE)
_PDF_LIEU    = re.compile(
    r"Date et lieu de naissance\s*:[^\n]*\d{2}/\d{2}/\d{4}\s+[aà]\s+([^\n,]+?)(?:\s*[-,\n]|$)",
    re.IGNORECASE,
)
_PDF_NAT     = re.compile(r"Nationalit[eé]\s*:\s*(.+)", re.IGNORECASE)


def parse_pdf_nationale_1373(content: bytes) -> list[dict]:
    """Parse le PDF liste nationale 1373 (CI) — Nom, DDN, Nationalité, Lieu."""
    import pdfplumber

    entries: list[dict] = []
    seen: set[str] = set()

    with pdfplumber.open(io.BytesIO(content)) as pdf:
        full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    name_positions = list(_PDF_NOM.finditer(full_text))
    if not name_positions:
        return entries

    for i, nom_m in enumerate(name_positions):
        nom = normalize(nom_m.group(1))
        if not nom or nom in seen:
            continue
        seen.add(nom)

        end = name_positions[i + 1].start() if i + 1 < len(name_positions) else nom_m.start() + 600
        window = full_text[nom_m.start():end]

        ddn_m = _PDF_DDN.search(window) or _PDF_DDN_ALT.search(window)
        ddn = ddn_m.group(1).strip() if ddn_m else ""

        lieu_m = _PDF_LIEU.search(window)
        lieu = normalize(lieu_m.group(1)) if lieu_m else ""

        nat_m = _PDF_NAT.search(window)
        nat = normalize(nat_m.group(1)) if nat_m else ""

        entries.append({"nom": nom, "date_naissance": ddn, "nationalite": nat, "lieu_naissance": lieu})

    return entries


# ── Parser HTML (liste ONU consolidée CSDNU) ──────────────────────────────────

_ND_VALUES    = {"N.D.", "ND", "N.D", "N/D"}
_PSEUDO_SPLIT = re.compile(r"[;]|\s+[a-z]\)")
_ONU_DDN      = re.compile(
    r"Date de naissance\s*:\s*([\d/\-,\s\w]+?)(?=Lieu de naissance|Pseudonyme|Nationalit[eé]|$)",
    re.IGNORECASE | re.DOTALL,
)
_ONU_NAT      = re.compile(
    r"Nationalit[eé]\s*:\s*(.+?)(?=Num[eé]ro|Adresse|Date d.inscription|Renseignements|$)",
    re.IGNORECASE | re.DOTALL,
)


def _clean_dob(raw: str) -> str:
    """Nettoie et normalise une DDN extraite du HTML ONU."""
    raw = raw.strip()
    year_only = re.search(r"\b(\d{4})\b", raw)
    full_date = re.search(r"(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})", raw)
    if full_date:
        d, m, y = full_date.group(1), full_date.group(2), full_date.group(3)
        return f"{d.zfill(2)}/{m.zfill(2)}/{y}"
    if year_only:
        return year_only.group(1)
    return ""


def parse_html_onu_consolidated(content: bytes) -> list[dict]:
    """Parse le HTML liste ONU consolidée — Nom (parties) + pseudonymes fiables."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(content, "lxml")
    entries: list[dict] = []
    seen: set[str] = set()

    def _add(nom: str, ddn: str, nat: str) -> None:
        n = normalize(nom)
        if n and len(n) > 2 and n not in seen:
            entries.append({"nom": n, "date_naissance": ddn, "nationalite": normalize(nat), "lieu_naissance": ""})
            seen.add(n)

    for td in soup.select("tr.rowtext td"):
        text = td.get_text(" ", strip=True)

        ddn_m = _ONU_DDN.search(text)
        ddn = _clean_dob(ddn_m.group(1)) if ddn_m else ""
        nat_m = _ONU_NAT.search(text)
        nat = nat_m.group(1).strip() if nat_m else ""

        nom_match = re.search(r"Nom\s*:\s*((?:\d+\s*:\s*\S+\s*)+)", text)
        if nom_match:
            parts = re.findall(r"\d+\s*:\s*(\S+)", nom_match.group(1))
            parts = [p for p in parts if p.upper() not in _ND_VALUES]
            if parts:
                _add(" ".join(parts), ddn, nat)

        pseudo_match = re.search(
            r"Pseudonyme fiable\s*:\s*(.+?)(?=Pseudonyme peu fiable|Nationalit[eé]|$)",
            text, re.DOTALL,
        )
        if pseudo_match:
            for chunk in _PSEUDO_SPLIT.split(pseudo_match.group(1)):
                chunk = chunk.strip().strip(")").strip()
                if chunk and chunk.upper() not in _ND_VALUES and len(chunk) > 3:
                    _add(chunk, ddn, nat)

    return entries


# ── Détection automatique ─────────────────────────────────────────────────────

def detect_and_parse(filename: str, content: bytes) -> list[dict]:
    """Détecte le format par extension et retourne une liste d'entrées normalisées."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in (filename or "") else ""
    if ext == "pdf":
        return parse_pdf_nationale_1373(content)
    if ext in ("html", "htm"):
        return parse_html_onu_consolidated(content)
    return parse_csv(content)
