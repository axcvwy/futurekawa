# app/routes/synchronisation.py
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.permissions import appliquer_filtre_pays
from app.core.security import get_current_user, require_role
from app.database.db import get_db
from app.models.pays import Pays
from app.models.synchronisation import Synchronisation
from app.models.utilisateur import Utilisateur
from app.schemas import SynchronisationOut
from app.services.syncer import synchronize_pays

router = APIRouter(prefix="/synchronisations", tags=["Synchronisations"])


@router.get("", response_model=list[SynchronisationOut])
def list_synchronisations(
    pays_id: uuid.UUID | None = None,
    limite: int = 50,
    utilisateur: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Historique des exécutions (fraîcheur des données par pays, périmètre = rôle)."""
    query = db.query(Synchronisation)
    query = appliquer_filtre_pays(query, Synchronisation, utilisateur)
    if pays_id is not None:
        query = query.filter(Synchronisation.pays_id == pays_id)
    return query.order_by(Synchronisation.demarree_le.desc()).limit(min(limite, 500)).all()


@router.get("/{synchronisation_id}", response_model=SynchronisationOut)
def get_synchronisation(
    synchronisation_id: uuid.UUID,
    utilisateur: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    run = db.get(Synchronisation, synchronisation_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Exécution de synchronisation introuvable")
    if appliquer_filtre_pays(db.query(Synchronisation), Synchronisation, utilisateur).filter(
        Synchronisation.id == run.id
    ).first() is None:
        raise HTTPException(status_code=403, detail="Accès refusé : synchronisation hors de votre périmètre")
    return run


@router.post("/pays/{pays_id}", response_model=SynchronisationOut, status_code=201)
def synchronize_now(
    pays_id: uuid.UUID,
    utilisateur: Utilisateur = Depends(require_role("ADMIN_SIEGE", "RESPONSABLE_EXPLOITATION")),
    db: Session = Depends(get_db),
):
    """Bouton « Synchroniser maintenant » : même logique que le planificateur, declencheur = MANUEL.
    Autorisé pour l'admin (tout pays) et le responsable d'exploitation (son pays)."""
    pays = db.get(Pays, pays_id)
    if pays is None:
        raise HTTPException(status_code=404, detail="Pays introuvable")
    if utilisateur.role == "RESPONSABLE_EXPLOITATION" and utilisateur.pays_id != pays.id:
        raise HTTPException(status_code=403, detail="Accès refusé : pays hors de votre périmètre")
    run = synchronize_pays(db, pays, declencheur="MANUEL")
    db.commit()
    db.refresh(run)
    return run
