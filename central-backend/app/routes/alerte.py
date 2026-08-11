# app/routes/alerte.py
import uuid
from datetime import UTC, datetime

import requests
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import SYNC_REQUEST_TIMEOUT
from app.core.permissions import appliquer_filtre_entrepot, appliquer_filtre_pays
from app.core.security import get_current_user
from app.database.db import get_db
from app.models.alerte import Alerte
from app.models.entrepot import Entrepot
from app.models.pays import Pays
from app.models.utilisateur import Utilisateur
from app.schemas import AlerteDetailOut, AlerteOut, AlerteUpdate, EntrepotRef, PaysRef

router = APIRouter(prefix="/alertes", tags=["Supervision des Alertes"])

_STATUTS_VALIDES = {"ACTIVE", "PRISE_EN_COMPTE", "RESOLUE", "IGNOREE"}
_ACCES_ALERTE = {"ADMIN_SIEGE", "RESPONSABLE_EXPLOITATION", "REFERENT_QUALITE"}
# Le responsable d'entrepôt peut seulement acquitter une alerte de son entrepôt.
_ACCES_ACQUITTEMENT = _ACCES_ALERTE | {"RESPONSABLE_ENTREPOT"}


@router.get("", response_model=list[AlerteDetailOut])
def list_alertes(
    statut: str | None = None,
    pays_id: uuid.UUID | None = None,
    type_alerte: str | None = None,
    limite: int = 100,
    utilisateur: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Consolidation des alertes du groupe pour le dashboard (périmètre = rôle)."""
    query = db.query(Alerte)
    query = appliquer_filtre_pays(query, Alerte, utilisateur)
    query = appliquer_filtre_entrepot(query, Alerte, utilisateur)
    if statut is not None:
        query = query.filter(Alerte.statut == statut)
    if pays_id is not None:
        query = query.filter(Alerte.pays_id == pays_id)
    if type_alerte is not None:
        query = query.filter(Alerte.type_alerte == type_alerte)
    alertes = query.order_by(Alerte.date_declenchement.desc()).limit(min(limite, 1000)).all()

    result = []
    for alerte in alertes:
        entrepot = db.get(Entrepot, alerte.entrepot_id) if alerte.entrepot_id else None
        pays = db.get(Pays, alerte.pays_id) if alerte.pays_id else None
        result.append(
            AlerteDetailOut(
                **AlerteOut.model_validate(alerte).model_dump(),
                pays=PaysRef.model_validate(pays) if pays else None,
                entrepot=EntrepotRef.model_validate(entrepot) if entrepot else None,
            )
        )
    return result


@router.patch("/{alerte_id}")
def update_alerte(
    alerte_id: uuid.UUID,
    payload: AlerteUpdate,
    utilisateur: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Acquitte/résout une alerte : met à jour la copie centrale ET propage au nœud local
    (source de vérité). Si le nœud local est injoignable, la modification reste appliquée
    au niveau du Siège et le transfert est signalé en warning.

    Droits : ADMIN_SIEGE, RESPONSABLE_EXPLOITATION et REFERENT_QUALITE résolvent/ignorent
    dans leur pays ; RESPONSABLE_ENTREPOT ne peut qu'acquitter (PRISE_EN_COMPTE) et
    uniquement pour son entrepôt.
    """
    if payload.statut not in _STATUTS_VALIDES:
        raise HTTPException(status_code=400, detail=f"Statut invalide. Valeurs : {sorted(_STATUTS_VALIDES)}")

    alerte = db.get(Alerte, alerte_id)
    if alerte is None:
        raise HTTPException(status_code=404, detail="Alerte introuvable")

    _verifier_droits_alerte(alerte, payload.statut, utilisateur, db)

    alerte.statut = payload.statut
    if payload.commentaire_resolution is not None:
        alerte.commentaire_resolution = payload.commentaire_resolution
    if payload.statut == "RESOLUE" and alerte.date_resolution is None:
        alerte.date_resolution = datetime.now(UTC)

    transfert_local = "OK"
    pays = db.get(Pays, alerte.pays_id) if alerte.pays_id else None
    if pays is not None:
        try:
            url = f"{pays.api_base_url.rstrip('/')}/alertes/{alerte.source_id}"
            corps = {"statut": payload.statut}
            if payload.commentaire_resolution is not None:
                corps["commentaire_resolution"] = payload.commentaire_resolution
            response = requests.put(
                url,
                headers={"X-API-Key": pays.api_key},
                json=corps,
                timeout=SYNC_REQUEST_TIMEOUT,
            )
            if response.status_code not in (200, 204):
                transfert_local = f"Nœud local a répondu {response.status_code}"
        except requests.exceptions.RequestException as exc:
            transfert_local = f"Nœud local injoignable : {exc}"

    db.commit()
    db.refresh(alerte)
    result = AlerteOut.model_validate(alerte).model_dump()
    result["transfert_local"] = transfert_local
    return result


def _verifier_droits_alerte(alerte: Alerte, nouveau_statut: str, utilisateur: Utilisateur, db: Session) -> None:
    """Règles métier de résolution par rôle et par périmètre."""
    if utilisateur.role == "RESPONSABLE_ENTREPOT":
        if nouveau_statut != "PRISE_EN_COMPTE":
            raise HTTPException(
                status_code=403,
                detail="Le responsable d'entrepôt ne peut qu'acquitter une alerte (PRISE_EN_COMPTE)",
            )
        if alerte.entrepot_id is None or alerte.entrepot_id != utilisateur.entrepot_id:
            raise HTTPException(status_code=403, detail="Accès refusé : alerte hors de votre entrepôt")
        return

    if utilisateur.role not in _ACCES_ALERTE:
        raise HTTPException(status_code=403, detail="Rôle insuffisant pour traiter les alertes")

    if utilisateur.pays_id is not None and alerte.pays_id != utilisateur.pays_id:
        raise HTTPException(status_code=403, detail="Accès refusé : alerte hors de votre périmètre")
