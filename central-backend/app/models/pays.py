# app/models/pays.py
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database.db import Base
from app.models.base import UUIDTimestampMixin


class Pays(UUIDTimestampMixin, Base):
    """Pays / nœud régional connecté au Siège."""

    __tablename__ = "pays"

    nom = Column(String(100), nullable=False)
    code_iso = Column(String(3), unique=True, nullable=False)
    api_base_url = Column(String(500), nullable=False)
    api_key = Column(String(500), nullable=False)  # SECRET : jamais exposé par une API GET
    actif = Column(Boolean, nullable=False, default=True)
    mock = Column(Boolean, nullable=False, default=False)  # True => données simulées, pas d'appel HTTP
    intervalle_sync_secondes = Column(Integer, nullable=False, default=300)
    derniere_sync_reussie_le = Column(DateTime(timezone=True), nullable=True)
    dernier_statut_sync = Column(String(30), nullable=False, default="JAMAIS")  # statuts possibles ci-dessous
    derniere_erreur_sync = Column(Text, nullable=True)

    # Conditions idéales de conservation du café (par pays) + tolérance acceptable.
    # La bande cible = cible ± tolérance (ex : Brésil 29°C ± 3 => 26–32°C).
    temperature_cible_c = Column(Float, nullable=True)
    humidite_cible_pct = Column(Float, nullable=True)
    tolerance_temperature_c = Column(Float, nullable=True)
    tolerance_humidite_pct = Column(Float, nullable=True)

    entrepots = relationship("Entrepot", back_populates="pays", cascade="all, delete-orphan")
