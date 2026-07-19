# ============================================================================
# PostgreSQL 16 — Notaire LBC/FT/FP (SaaS multi-tenant, isolation par schéma)
# ----------------------------------------------------------------------------
# Un schéma `shared` (annuaire de routage) + un schéma `tenant_<uuid>` par
# cabinet notarial. L'isolation par schéma permet de sauvegarder, restaurer et
# purger un cabinet indépendamment des autres — exigence forte pour des données
# LBC/FT soumises à l'Ordonnance N°2023-875.
#
# Aucun fichier de configuration additionnel n'est monté : l'ancien
# `custom.cnf` MySQL n'existait que pour `log_bin_trust_function_creators`,
# paramètre qui n'a ni équivalent ni raison d'être sous PostgreSQL.
# ============================================================================
FROM postgres:16

# Joué UNE SEULE FOIS, à l'initialisation d'un volume de données vierge.
# Sur un volume déjà initialisé, ce script est ignoré par l'entrypoint officiel.
COPY init.sql /docker-entrypoint-initdb.d/01_init.sql
