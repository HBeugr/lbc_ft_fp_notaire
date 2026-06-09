-- Initialisation MySQL — Notaire LBC/FT/FP

-- dos_user : accès restreint aux tables DOS uniquement (ADR-003)
CREATE USER IF NOT EXISTS 'dos_user'@'%' IDENTIFIED BY 'changeme_dos_password';

-- notaire_user a besoin de WITH GRANT OPTION pour la migration Alembic (grants dos_user)
GRANT ALL PRIVILEGES ON notaire_lbcft.* TO 'notaire_user'@'%' WITH GRANT OPTION;
FLUSH PRIVILEGES;
