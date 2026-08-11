# app/routes/capteur.py
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.permissions import appliquer_filtre_entrepot, appliquer_filtre_pays
from app.core.security import get_current_user, require_role
from app.database.db import get_db
from app.models.capteur import Capteur
from app.models.entrepot import Entrepot
from app.models.utilisateur import Utilisateur
from app.schemas import CapteurCreate, CapteurOut, CapteurUpdate, MessageResponse
from app.services.proxy import creer_capteur_local, maj_capteur_local, supprimer_capteur_local

router = APIRouter(prefix="/capteurs", tags=["Capteurs"])


@router.get("", response_model=list[CapteurOut])
def list_capteurs(
    pays_id: uuid.UUID | None = None,
    entrepot_id: uuid.UUID | None = None,
    statut: str | None = None,
    utilisateur: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Capteur)
    query = appliquer_filtre_pays(query, Capteur, utilisateur)
    query = appliquer_filtre_entrepot(query, Capteur, utilisateur)
    if pays_id is not None:
        query = query.filter(Capteur.pays_id == pays_id)
    if entrepot_id is not None:
        query = query.filter(Capteur.entrepot_id == entrepot_id)
    if statut is not None:
        query = query.filter(Capteur.statut == statut)
    return query.order_by(Capteur.reference).all()


@router.get("/{capteur_id}", response_model=CapteurOut)
def get_capteur(
    capteur_id: uuid.UUID,
    utilisateur: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    capteur = db.get(Capteur, capteur_id)
    if capteur is None:
        raise HTTPException(status_code=404, detail="Capteur introuvable")
    requete = appliquer_filtre_entrepot(
        appliquer_filtre_pays(db.query(Capteur), Capteur, utilisateur),
        Capteur,
        utilisateur,
    )
    if requete.filter(Capteur.id == capteur.id).first() is None:
        raise HTTPException(status_code=403, detail="Accès refusé : capteur hors de votre périmètre")
    return capteur


@router.post("", response_model=CapteurOut, status_code=201)
def create_capteur(
    payload: CapteurCreate,
    admin: Utilisateur = Depends(require_role("ADMIN_SIEGE")),
    db: Session = Depends(get_db),
):
    """Crée un capteur côté backend local du pays (proxy) puis resynchronise."""
    entrepot = db.get(Entrepot, payload.entrepot_id)
    if entrepot is None:
        raise HTTPException(status_code=404, detail="Entrepôt introuvable")
    if entrepot.pays.mock:
        raise HTTPException(status_code=400, detail=f"Le pays {entrepot.pays.code_iso} est en mode simulation")
    resultat = creer_capteur_local(
        db,
        pays_id=entrepot.pays_id,
        entrepot_central_id=payload.entrepot_id,
        corps=payload.model_dump(exclude={"pays_id"}),
    )
    capteur = db.query(Capteur).filter(Capteur.pays_id == entrepot.pays_id, Capteur.source_id == resultat["id"]).first()
    if capteur is None:
        return resultat
    return capteur


@router.put("/{capteur_id}", response_model=CapteurOut)
def update_capteur(
    capteur_id: uuid.UUID,
    payload: CapteurUpdate,
    admin: Utilisateur = Depends(require_role("ADMIN_SIEGE")),
    db: Session = Depends(get_db),
):
    capteur = db.get(Capteur, capteur_id)
    if capteur is None:
        raise HTTPException(status_code=404, detail="Capteur introuvable")
    entrepot = db.get(Entrepot, capteur.entrepot_id)
    pays = entrepot.pays if entrepot is not None else None
    if pays is None or pays.mock:
        raise HTTPException(status_code=400, detail="Le pays est en mode simulation")
    maj_capteur_local(
        db,
        pays_id=capteur.pays_id,
        capteur_central_id=capteur_id,
        corps=payload.model_dump(exclude_none=True),
    )
    capteur = db.get(Capteur, capteur_id)
    if capteur is None:
        raise HTTPException(status_code=404, detail="Capteur introuvable")
    return capteur


@router.delete("/{capteur_id}", response_model=MessageResponse)
def delete_capteur(
    capteur_id: uuid.UUID,
    _admin: Utilisateur = Depends(require_role("ADMIN_SIEGE")),
    db: Session = Depends(get_db),
):
    """Supprime un capteur côté backend local (proxy) puis resynchronise. Réservé ADMIN_SIEGE."""
    capteur = db.get(Capteur, capteur_id)
    if capteur is None:
        raise HTTPException(status_code=404, detail="Capteur introuvable")
    entrepot = db.get(Entrepot, capteur.entrepot_id)
    pays = entrepot.pays if entrepot is not None else None
    if pays is None or pays.mock:
        raise HTTPException(status_code=400, detail="Le pays est en mode simulation")
    supprimer_capteur_local(db, pays_id=capteur.pays_id, capteur_central_id=capteur.id)
    return {"message": "Capteur supprimé et resynchronisé"}
