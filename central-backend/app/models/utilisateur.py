# app/models/utilisateur.py
from sqlalchemy import Boolean, Column, ForeignKey, String, Uuid
from sqlalchemy.orm import relationship

from app.database.db import Base
from app.models.base import UUIDTimestampMixin

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
