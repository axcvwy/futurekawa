# app/routes/pays.py
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.permissions import appliquer_filtre_pays
from app.core.security import get_current_user, require_role
from app.database.db import get_db
from app.models.pays import Pays
from app.models.utilisateur import Utilisateur
from app.schemas import PaysOut, PaysUpdate

router = APIRouter(prefix="/pays", tags=["Pays"])


@router.get("", response_model=list[PaysOut])
def list_pays(
    utilisateur: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Liste des pays visibles par l'utilisateur (l'api_key n'est jamais exposée)."""
    query = db.query(Pays)
    query = appliquer_filtre_pays(query, Pays, utilisateur)
    return query.order_by(Pays.code_iso).all()


@router.get("/{pays_id}", response_model=PaysOut)
def get_pays(
    pays_id: uuid.UUID,
    utilisateur: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pays = db.get(Pays, pays_id)
    if pays is None:
        raise HTTPException(status_code=404, detail="Pays introuvable")
    pays_autorise = appliquer_filtre_pays(db.query(Pays), Pays, utilisateur).filter(Pays.id == pays_id).first()
    if pays_autorise is None:
        raise HTTPException(status_code=403, detail="Accès refusé : pays hors de votre périmètre")
    return pays


@router.put("/{pays_id}", response_model=PaysOut)
def update_pays(
    pays_id: uuid.UUID,
    payload: PaysUpdate,
    _admin: Utilisateur = Depends(require_role("ADMIN_SIEGE")),
    db: Session = Depends(get_db),
):
    """Active/désactive un pays ou ajuste son intervalle de synchronisation (réservé ADMIN_SIEGE)."""
    pays = db.get(Pays, pays_id)
    if pays is None:
        raise HTTPException(status_code=404, detail="Pays introuvable")
    if payload.actif is not None:
        pays.actif = payload.actif
    if payload.intervalle_sync_secondes is not None:
        pays.intervalle_sync_secondes = payload.intervalle_sync_secondes
    if payload.api_base_url is not None:
        pays.api_base_url = payload.api_base_url
    db.commit()
    db.refresh(pays)
    return pays
