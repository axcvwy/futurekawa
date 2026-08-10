# app/models/utilisateur.py
from sqlalchemy import Boolean, Column, ForeignKey, String, Uuid
from sqlalchemy.orm import relationship

from app.database.db import Base
from app.models.base import UUIDTimestampMixin

# Rôles métier (cf. organigramme + cahier des charges) :
#   ADMIN_SIEGE              -> plateforme + vue consolidée globale
#   RESPONSABLE_EXPLOITATION -> pays/exploitation assigné (réception des e-mails d'alerte)
#   RESPONSABLE_ENTREPOT     -> entrepôt assigné (opérations quotidiennes)
#   REFERENT_QUALITE         -> pays/exploitation assigné (alertes qualité, traçabilité)
ROLES = (
    "ADMIN_SIEGE",
    "RESPONSABLE_EXPLOITATION",
    "RESPONSABLE_ENTREPOT",
    "REFERENT_QUALITE",
)


class Utilisateur(UUIDTimestampMixin, Base):
    """Compte d'accès à la console Siège. Jamais de mot de passe exposé via les APIs."""

    __tablename__ = "utilisateurs"

    email = Column(String(255), unique=True, nullable=False, index=True)
    nom = Column(String(150), nullable=False)
    mot_de_passe_hash = Column(String(255), nullable=False)
    role = Column(String(30), nullable=False)
    actif = Column(Boolean, nullable=False, default=True)

    # Périmètre d'action :
    #   - ADMIN_SIEGE              : pays_id / entrepot_id None (tous les pays)
    #   - RESPONSABLE_EXPLOITATION : pays_id obligatoire
    #   - REFERENT_QUALITE         : pays_id obligatoire
    #   - RESPONSABLE_ENTREPOT     : pays_id + entrepot_id obligatoires
    pays_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("pays.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    entrepot_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("entrepots.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    pays = relationship("Pays")
    entrepot = relationship("Entrepot")
