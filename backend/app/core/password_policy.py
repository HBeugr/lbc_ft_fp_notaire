"""Politique de robustesse des mots de passe (alignée immo) — ≥12 caractères + 4 classes."""


def validate_password_strength(v: str) -> str:
    if len(v) < 12:
        raise ValueError("Le mot de passe doit contenir au moins 12 caractères.")
    if not any(c.isupper() for c in v):
        raise ValueError("Le mot de passe doit contenir au moins une majuscule.")
    if not any(c.islower() for c in v):
        raise ValueError("Le mot de passe doit contenir au moins une minuscule.")
    if not any(c.isdigit() for c in v):
        raise ValueError("Le mot de passe doit contenir au moins un chiffre.")
    if not any(not c.isalnum() for c in v):
        raise ValueError("Le mot de passe doit contenir au moins un caractère spécial.")
    return v
