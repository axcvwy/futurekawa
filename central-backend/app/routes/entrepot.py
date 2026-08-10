# app/routes/entrepot.py
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.permissions import appliquer_filtre_entrepot, appliquer_filtre_pays
from app.core.security import get_current_user, require_role
from app.database.db import get_db
from app.models.entrepot import Entrepot
from app.models.pays import Pays
from app.models.utilisateur import Utilisateur
from app.schemas import (
    EntrepotCreate,
    EntrepotDetailOut,
    EntrepotOut,
    EntrepotUpdate,
    ExploitationRef,
    MessageResponse,
    PaysRef,
)
from app.services.proxy import creer_entrepot_local, maj_entrepot_local, supprimer_entrepot_local

router = APIRouter(prefix="/entrepots", tags=["Entrepôts"])


@router.post("", response_model=EntrepotOut, status_code=201)
def create_entrepot(
    payload: EntrepotCreate,
    _admin: Utilisateur = Depends(require_role("ADMIN_SIEGE")),
    db: Session = Depends(get_db),
):
    """Crée un entrepôt côté backend local du pays (proxy) puis resynchronise. Réservé ADMIN_SIEGE."""
    pays = db.get(Pays, payload.pays_id)
    if pays is None:
        raise HTTPException(status_code=404, detail="Pays introuvable")
    if pays.mock:
        raise HTTPException(status_code=400, detail=f"Le pays {pays.code_iso} est en mode simulation")
    corps = payload.model_dump(exclude={"pays_id"})
    corps["code_pays"] = pays.code_iso
    resultat = creer_entrepot_local(db, pays_id=pays.id, corps=corps)
    entrepot = (
        db.query(Entrepot)
        .filter(Entrepot.pays_id == pays.id, Entrepot.source_id == resultat["id"])
        .first()
    )
    if entrepot is None:
        return resultat
    return entrepot


@router.get("", response_model=list[EntrepotOut])
def list_entrepots(
    pays_id: uuid.UUID | None = None,
    exploitation_id: uuid.UUID | None = None,
    utilisateur: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Entrepot)
    query = appliquer_filtre_pays(query, Entrepot, utilisateur)
    query = appliquer_filtre_entrepot(query, Entrepot, utilisateur)
    if pays_id is not None:
        query = query.filter(Entrepot.pays_id == pays_id)
    if exploitation_id is not None:
        query = query.filter(Entrepot.exploitation_id == exploitation_id)
    return query.order_by(Entrepot.nom).all()


@router.get("/{entrepot_id}", response_model=EntrepotDetailOut)
def get_entrepot(
    entrepot_id: uuid.UUID,
    utilisateur: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entrepot = db.get(Entrepot, entrepot_id)
    if entrepot is None:
        raise HTTPException(status_code=404, detail="Entrepôt introuvable")
    _verifier_perimetre(entrepot, utilisateur, db)
    return EntrepotDetailOut(
        **EntrepotOut.model_validate(entrepot).model_dump(),
        pays=PaysRef.model_validate(entrepot.pays) if entrepot.pays else None,
        exploitation=ExploitationRef.model_validate(entrepot.exploitation) if entrepot.exploitation else None,
    )


@router.put("/{entrepot_id}", response_model=EntrepotOut)
def update_entrepot(
    entrepot_id: uuid.UUID,
    payload: EntrepotUpdate | None = None,
    exploitation_id: uuid.UUID | None = None,
    _admin: Utilisateur = Depends(require_role("ADMIN_SIEGE")),
    db: Session = Depends(get_db),
):
    """Met à jour un entrepôt côté backend local (proxy) ; peut aussi réaffecter l'exploitation.
    Réservé ADMIN_SIEGE."""
    entrepot = db.get(Entrepot, entrepot_id)
    if entrepot is None:
        raise HTTPException(status_code=404, detail="Entrepôt introuvable")

    if payload is not None:
        corps = payload.model_dump(exclude_none=True)
    else:
        corps = {}
    if corps:
        pays = db.get(Pays, entrepot.pays_id)
        if pays.mock:
            raise HTTPException(status_code=400, detail=f"Le pays {pays.code_iso} est en mode simulation")
        resultat = maj_entrepot_local(db, pays_id=pays.id, entrepot_central_id=entrepot.id, corps=corps)
        entrepot = db.get(Entrepot, entrepot_id)
        if entrepot is None:
            return resultat

    if exploitation_id is not None:
        entrepot.exploitation_id = exploitation_id
        db.commit()
        db.refresh(entrepot)
    return entrepot


@router.delete("/{entrepot_id}", response_model=MessageResponse)
def delete_entrepot(
    entrepot_id: uuid.UUID,
    _admin: Utilisateur = Depends(require_role("ADMIN_SIEGE")),
    db: Session = Depends(get_db),
):
    """Supprime un entrepôt côté backend local (proxy) puis resynchronise. Réservé ADMIN_SIEGE."""
    entrepot = db.get(Entrepot, entrepot_id)
    if entrepot is None:
        raise HTTPException(status_code=404, detail="Entrepôt introuvable")
    pays = db.get(Pays, entrepot.pays_id)
    if pays.mock:
        raise HTTPException(status_code=400, detail=f"Le pays {pays.code_iso} est en mode simulation")
    supprimer_entrepot_local(db, pays_id=pays.id, entrepot_central_id=entrepot.id)
    return {"message": "Entrepôt supprimé et resynchronisé"}


def _verifier_perimetre(entrepot: Entrepot, utilisateur: Utilisateur, db: Session) -> None:
    """Refuse l'accès à un entrepôt hors du périmètre pays/entrepôt de l'utilisateur."""
    requete = appliquer_filtre_entrepot(
        appliquer_filtre_pays(db.query(Entrepot), Entrepot, utilisateur),
        Entrepot,
        utilisateur,
    )
    if requete.filter(Entrepot.id == entrepot.id).first() is None:
        raise HTTPException(status_code=403, detail="Accès refusé : entrepôt hors de votre périmètre")
