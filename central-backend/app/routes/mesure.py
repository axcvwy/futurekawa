# app/routes/mesure.py
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.permissions import appliquer_filtre_entrepot, appliquer_filtre_pays
from app.core.security import get_current_user
from app.database.db import get_db
from app.models.mesure import Mesure
from app.models.utilisateur import Utilisateur
from app.schemas import MesureOut

router = APIRouter(prefix="/mesures", tags=["Métriques Temporelles IoT"])


@router.get("", response_model=list[MesureOut])
def list_mesures(
    pays_id: uuid.UUID | None = None,
    entrepot_id: uuid.UUID | None = None,
    capteur_id: uuid.UUID | None = None,
    lot_id: uuid.UUID | None = None,
    date_mesure_depuis: datetime | None = None,
    date_mesure_jusqua: datetime | None = None,
    limit: int = 200,
    offset: int = 0,
    utilisateur: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Historique chronologique des télémesures pour Chart.js (périmètre = rôle)."""
    query = db.query(Mesure)
    query = appliquer_filtre_pays(query, Mesure, utilisateur)
    query = appliquer_filtre_entrepot(query, Mesure, utilisateur)
    if pays_id is not None:
        query = query.filter(Mesure.pays_id == pays_id)
    if entrepot_id is not None:
        query = query.filter(Mesure.entrepot_id == entrepot_id)
    if capteur_id is not None:
        query = query.filter(Mesure.capteur_id == capteur_id)
    if lot_id is not None:
        query = query.filter(Mesure.lot_id == lot_id)
    if date_mesure_depuis is not None:
        query = query.filter(Mesure.date_mesure >= date_mesure_depuis)
    if date_mesure_jusqua is not None:
        query = query.filter(Mesure.date_mesure <= date_mesure_jusqua)
    return (
        query.order_by(Mesure.date_mesure.desc())
        .offset(offset)
        .limit(min(limit, 1000))
        .all()
    )


@router.get("/{mesure_id}", response_model=MesureOut)
def get_mesure(
    mesure_id: uuid.UUID,
    utilisateur: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    mesure = db.get(Mesure, mesure_id)
    if mesure is None:
        raise HTTPException(status_code=404, detail="Mesure introuvable")
    requete = appliquer_filtre_entrepot(
        appliquer_filtre_pays(db.query(Mesure), Mesure, utilisateur),
        Mesure,
        utilisateur,
    )
    if requete.filter(Mesure.id == mesure.id).first() is None:
        raise HTTPException(status_code=403, detail="Accès refusé : mesure hors de votre périmètre")
    return mesure
