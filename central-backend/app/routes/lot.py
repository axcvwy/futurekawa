# app/routes/lot.py
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.permissions import appliquer_filtre_entrepot, appliquer_filtre_pays
from app.core.security import get_current_user, require_role
from app.database.db import get_db
from app.models.entrepot import Entrepot
from app.models.lot import Lot
from app.models.mesure import Mesure
from app.models.pays import Pays
from app.models.utilisateur import Utilisateur
from app.schemas import (
    EntrepotRef,
    ExploitationRef,
    LotCreate,
    LotDetailOut,
    LotOut,
    LotUpdate,
    MesureOut,
    PaysRef,
)
from app.services.proxy import creer_lot_local, maj_lot_local

router = APIRouter(prefix="/lots", tags=["Lots & Stocks (FIFO)"])

_STATUTS_VALIDES = {"EN_STOCK", "EN_ALERTE", "CONFORME", "A_VERIFIER", "EXPORTE"}


@router.get("", response_model=list[LotOut])
def list_lots(
    pays_id: uuid.UUID | None = None,
    entrepot_id: uuid.UUID | None = None,
    exploitation_id: uuid.UUID | None = None,
    statut: str | None = None,
    ordre: str = "fifo",
    utilisateur: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Stocks consolidés du Siège (périmètre = rôle de l'utilisateur). ordre=fifo => tri date_stockage croissante."""
    query = db.query(Lot)
    query = appliquer_filtre_pays(query, Lot, utilisateur)
    query = appliquer_filtre_entrepot(query, Lot, utilisateur)
    if pays_id is not None:
        query = query.filter(Lot.pays_id == pays_id)
    if entrepot_id is not None:
        query = query.filter(Lot.entrepot_id == entrepot_id)
    if exploitation_id is not None:
        query = query.join(Entrepot, Lot.entrepot_id == Entrepot.id).filter(Entrepot.exploitation_id == exploitation_id)
    if statut is not None:
        query = query.filter(Lot.statut == statut)

    if ordre == "fifo":
        query = query.order_by(Lot.date_stockage.asc(), Lot.cree_le.asc())
    else:
        query = query.order_by(Lot.date_stockage.desc(), Lot.cree_le.desc())
    return query.all()


@router.get("/{lot_id}", response_model=LotDetailOut)
def get_lot(
    lot_id: uuid.UUID,
    utilisateur: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lot = db.get(Lot, lot_id)
    if lot is None:
        raise HTTPException(status_code=404, detail="Lot introuvable")
    requete = appliquer_filtre_entrepot(
        appliquer_filtre_pays(db.query(Lot), Lot, utilisateur),
        Lot,
        utilisateur,
    )
    if requete.filter(Lot.id == lot.id).first() is None:
        raise HTTPException(status_code=403, detail="Accès refusé : lot hors de votre périmètre")
    entrepot = db.get(Entrepot, lot.entrepot_id) if lot.entrepot_id else None
    pays = db.get(Pays, lot.pays_id) if lot.pays_id else None
    exploitation = db.get(Entrepot, lot.entrepot_id).exploitation if entrepot else None
    return LotDetailOut(
        **LotOut.model_validate(lot).model_dump(),
        entrepot=EntrepotRef.model_validate(entrepot) if entrepot else None,
        pays=PaysRef.model_validate(pays) if pays else None,
        exploitation=ExploitationRef.model_validate(exploitation) if exploitation else None,
    )


@router.get("/{lot_id}/mesures", response_model=list[MesureOut])
def get_lot_mesures(
    lot_id: uuid.UUID,
    utilisateur: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Courbes IoT d'un lot. Si aucune mesure n'est liée au lot, bascule sur les mesures
    d'ambiance de l'entrepôt (données de l'environnement de stockage)."""
    lot = db.get(Lot, lot_id)
    if lot is None:
        raise HTTPException(status_code=404, detail="Lot introuvable")
    requete = appliquer_filtre_entrepot(
        appliquer_filtre_pays(db.query(Lot), Lot, utilisateur),
        Lot,
        utilisateur,
    )
    if requete.filter(Lot.id == lot.id).first() is None:
        raise HTTPException(status_code=403, detail="Accès refusé : lot hors de votre périmètre")

    mesures = (
        db.query(Mesure)
        .filter(Mesure.lot_id == lot_id)
        .order_by(Mesure.date_mesure.asc())
        .limit(500)
        .all()
    )
    if not mesures and lot.entrepot_id:
        mesures = (
            db.query(Mesure)
            .filter(
                Mesure.entrepot_id == lot.entrepot_id,
                Mesure.date_mesure >= lot.date_stockage,
            )
            .order_by(Mesure.date_mesure.asc())
            .limit(500)
            .all()
        )
    return mesures


@router.post("", response_model=LotOut, status_code=201)
def create_lot(
    payload: LotCreate,
    utilisateur: Utilisateur = Depends(require_role("ADMIN_SIEGE", "RESPONSABLE_EXPLOITATION", "RESPONSABLE_ENTREPOT")),
    db: Session = Depends(get_db),
):
    """Crée un lot côté backend local du pays (proxy) puis resynchronise le cache Siège."""
    entrepot = db.get(Entrepot, payload.entrepot_id)
    if entrepot is None:
        raise HTTPException(status_code=404, detail="Entrepôt introuvable")
    _verifier_ecriture(entrepot, utilisateur, db)
    resultat = creer_lot_local(
        db,
        pays_id=entrepot.pays_id,
        entrepot_central_id=entrepot.id,
        corps=payload.model_dump(),
    )
    lot = db.query(Lot).filter(Lot.code_lot == payload.code_lot, Lot.entrepot_id == entrepot.id).first()
    if lot is None:
        return resultat
    return lot


@router.put("/{lot_id}", response_model=LotOut)
def update_lot(
    lot_id: uuid.UUID,
    payload: LotUpdate,
    utilisateur: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Met à jour un lot (proxy local). Un REFERENT_QUALITE ne peut modifier que le statut
    (EN_ALERTE / CONFORME / A_VERIFIER) et seulement dans son périmètre pays."""
    lot = db.get(Lot, lot_id)
    if lot is None:
        raise HTTPException(status_code=404, detail="Lot introuvable")
    _verifier_ecriture(db.get(Entrepot, lot.entrepot_id), utilisateur, db)

    corps = payload.model_dump(exclude_none=True)
    if utilisateur.role == "REFERENT_QUALITE":
        champs_interdits = set(corps.keys()) - {"statut"}
        if champs_interdits:
            raise HTTPException(
                status_code=403,
                detail=f"Le référent qualité ne peut modifier que le statut (champs refusés : {sorted(champs_interdits)})",
            )
        if "statut" in corps and corps["statut"] not in {"EN_ALERTE", "CONFORME", "A_VERIFIER"}:
            raise HTTPException(
                status_code=400,
                detail="Statut autorisé pour le référent qualité : EN_ALERTE, CONFORME, A_VERIFIER",
            )

    resultat = maj_lot_local(
        db,
        pays_id=lot.pays_id,
        lot_central_id=lot.id,
        corps=corps,
    )
    db.refresh(lot)
    return lot


def _verifier_ecriture(entrepot: Entrepot | None, utilisateur: Utilisateur, db: Session) -> None:
    """Restreint les écritures au périmètre du rôle (pays pour exploitation/qualité,
    entrepôt précis pour le responsable d'entrepôt)."""
    if entrepot is None:
        raise HTTPException(status_code=404, detail="Entrepôt introuvable")
    if utilisateur.role == "ADMIN_SIEGE":
        return
    if utilisateur.role == "RESPONSABLE_ENTREPOT":
        if entrepot.id != utilisateur.entrepot_id:
            raise HTTPException(status_code=403, detail="Accès refusé : entrepôt hors de votre périmètre")
        return
    if utilisateur.pays_id != entrepot.pays_id:
        raise HTTPException(status_code=403, detail="Accès refusé : pays hors de votre périmètre")
