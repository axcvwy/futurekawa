# app/models/entrepot.py
from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import relationship

from app.database.db import Base
from app.models.base import UUIDTimestampMixin


class Entrepot(UUIDTimestampMixin, Base):
    """Copie centrale d'un entrepôt local."""

    __tablename__ = "entrepots"
    __table_args__ = (
        UniqueConstraint("pays_id", "source_id", name="uq_entrepots_pays_source"),
    )

    pays_id = Column(Uuid(as_uuid=True), ForeignKey("pays.id", ondelete="CASCADE"), nullable=False, index=True)
    exploitation_id = Column(
        Uuid(as_uuid=True), ForeignKey("exploitations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_id = Column(Uuid(as_uuid=True), nullable=False)  # UUID local original
    nom = Column(String(150), nullable=False)
    ville = Column(String(150), nullable=False)
    code_pays = Column(String(3), nullable=False)
    nom_responsable = Column(String(150), nullable=False)
    email_responsable = Column(String(255), nullable=False)
    temperature_min_c = Column(Numeric(5, 2), nullable=False)
    temperature_max_c = Column(Numeric(5, 2), nullable=False)
    humidite_min_pct = Column(Numeric(5, 2), nullable=False)
    humidite_max_pct = Column(Numeric(5, 2), nullable=False)
    source_cree_le = Column(DateTime(timezone=True), nullable=False)
    source_mis_a_jour_le = Column(DateTime(timezone=True), nullable=False)
    synchronise_le = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    pays = relationship("Pays", back_populates="entrepots")
    exploitation = relationship("Exploitation")
