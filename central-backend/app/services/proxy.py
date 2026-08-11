# app/services/proxy.py
"""Écritures « en écriture directe » vers les backends pays.

Le frontend ne contacte jamais les backends locaux : le Siège joue le rôle de
proxy et retransmet les créations/mises à jour (lots, entrepôts, capteurs) au
nœud local de chaque pays via son API REST (X-API-Key), puis relance une
synchronisation pour rafraîchir le cache central.
"""

import uuid

import requests
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import SYNC_REQUEST_TIMEOUT
from app.models.capteur import Capteur
from app.models.entrepot import Entrepot
from app.models.lot import Lot
from app.models.pays import Pays
from app.services.syncer import synchronize_pays


def _pays_local(pays: Pays):
    if pays is None:
        raise HTTPException(status_code=404, detail="Pays introuvable")
    if pays.mock:
        raise HTTPException(
            status_code=400,
            detail=f"Le pays {pays.code_iso} est en mode simulation : aucune écriture locale possible.",
        )
    if not pays.actif:
        raise HTTPException(status_code=400, detail=f"Le pays {pays.code_iso} est désactivé")
    return pays


def _poster(pays: Pays, resource: str, corps: dict) -> dict:
    url = f"{pays.api_base_url.rstrip('/')}/{resource}/"
    try:
        response = requests.post(
            url,
            headers={"X-API-Key": pays.api_key},
            json=corps,
            timeout=SYNC_REQUEST_TIMEOUT,
        )
    except requests.exceptions.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Nœud local injoignable : {exc}") from exc
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()


def _mettre_a_jour(pays: Pays, resource: str, source_id: uuid.UUID, corps: dict) -> dict:
    url = f"{pays.api_base_url.rstrip('/')}/{resource}/{source_id}"
    try:
        response = requests.put(
            url,
            headers={"X-API-Key": pays.api_key},
            json=corps,
            timeout=SYNC_REQUEST_TIMEOUT,
        )
    except requests.exceptions.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Nœud local injoignable : {exc}") from exc
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()


def _supprimer(pays: Pays, resource: str, source_id: uuid.UUID) -> None:
    url = f"{pays.api_base_url.rstrip('/')}/{resource}/{source_id}"
    try:
        response = requests.delete(
            url,
            headers={"X-API-Key": pays.api_key},
            timeout=SYNC_REQUEST_TIMEOUT,
        )
    except requests.exceptions.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Nœud local injoignable : {exc}") from exc
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)


def _synchroniser_apres_ecriture(db: Session, pays: Pays) -> None:
    try:
        synchronize_pays(db, pays, declencheur="MANUEL")
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=502,
            detail=f"Écriture locale réussie mais resynchronisation impossible : {exc}",
        ) from exc


#  Lots


def creer_lot_local(db: Session, pays_id: uuid.UUID, entrepot_central_id: uuid.UUID, corps: dict) -> dict:
    """Crée un lot sur le backend local du pays puis resynchronise le Siège."""
    pays = _pays_local(db.get(Pays, pays_id))
    entrepot = db.get(Entrepot, entrepot_central_id)
    if entrepot is None or entrepot.pays_id != pays.id:
        raise HTTPException(status_code=404, detail="Entrepôt introuvable pour ce pays")

    corps_local = {
        "code_lot": corps["code_lot"],
        "entrepot_id": str(entrepot.source_id),
        "produit": corps["produit"],
        "quantite_kg": corps["quantite_kg"],
        "date_stockage": str(corps["date_stockage"]),
        "statut": corps.get("statut", "EN_STOCK"),
    }
    resultat = _poster(pays, "lots", corps_local)
    _synchroniser_apres_ecriture(db, pays)
    return resultat


def maj_lot_local(
    db: Session,
    pays_id: uuid.UUID,
    lot_central_id: uuid.UUID,
    corps: dict,
) -> dict:
    """Met à jour un lot côté local puis resynchronise le Siège."""
    pays = _pays_local(db.get(Pays, pays_id))
    lot = db.get(Lot, lot_central_id)
    if lot is None or lot.pays_id != pays.id:
        raise HTTPException(status_code=404, detail="Lot introuvable pour ce pays")

    corps_local = {}
    if "code_lot" in corps and corps["code_lot"] is not None:
        corps_local["code_lot"] = corps["code_lot"]
    if "produit" in corps and corps["produit"] is not None:
        corps_local["produit"] = corps["produit"]
    if "quantite_kg" in corps and corps["quantite_kg"] is not None:
        corps_local["quantite_kg"] = corps["quantite_kg"]
    if "date_stockage" in corps and corps["date_stockage"] is not None:
        corps_local["date_stockage"] = str(corps["date_stockage"])
    if "statut" in corps and corps["statut"] is not None:
        corps_local["statut"] = corps["statut"]

    resultat = _mettre_a_jour(pays, "lots", lot.source_id, corps_local)
    _synchroniser_apres_ecriture(db, pays)
    return resultat


#  Entrepôts


def creer_entrepot_local(db: Session, pays_id: uuid.UUID, corps: dict) -> dict:
    pays = _pays_local(db.get(Pays, pays_id))
    resultat = _poster(pays, "entrepots", corps)
    _synchroniser_apres_ecriture(db, pays)
    return resultat


def maj_entrepot_local(
    db: Session,
    pays_id: uuid.UUID,
    entrepot_central_id: uuid.UUID,
    corps: dict,
) -> dict:
    """Met à jour un entrepôt côté local puis resynchronise le Siège."""
    pays = _pays_local(db.get(Pays, pays_id))
    entrepot = db.get(Entrepot, entrepot_central_id)
    if entrepot is None or entrepot.pays_id != pays.id:
        raise HTTPException(status_code=404, detail="Entrepôt introuvable pour ce pays")

    resultat = _mettre_a_jour(pays, "entrepots", entrepot.source_id, corps)
    _synchroniser_apres_ecriture(db, pays)
    return resultat


def supprimer_entrepot_local(db: Session, pays_id: uuid.UUID, entrepot_central_id: uuid.UUID) -> None:
    """Supprime un entrepôt côté local puis resynchronise et retire la copie centrale."""
    pays = _pays_local(db.get(Pays, pays_id))
    entrepot = db.get(Entrepot, entrepot_central_id)
    if entrepot is None or entrepot.pays_id != pays.id:
        raise HTTPException(status_code=404, detail="Entrepôt introuvable pour ce pays")

    _supprimer(pays, "entrepots", entrepot.source_id)
    # La synchronisation ne fait que des upserts (elle ne supprime pas les orphelins) :
    # on retire donc la copie centrale après l'appel local pour refléter la suppression.
    _synchroniser_apres_ecriture(db, pays)
    db.delete(entrepot)
    db.commit()


#  Capteurs


def creer_capteur_local(db: Session, pays_id: uuid.UUID, entrepot_central_id: uuid.UUID, corps: dict) -> dict:
    pays = _pays_local(db.get(Pays, pays_id))
    entrepot = db.get(Entrepot, entrepot_central_id)
    if entrepot is None or entrepot.pays_id != pays.id:
        raise HTTPException(status_code=404, detail="Entrepôt introuvable pour ce pays")

    corps_local = {
        **corps,
        "entrepot_id": str(entrepot.source_id),
    }
    resultat = _poster(pays, "capteurs", corps_local)
    _synchroniser_apres_ecriture(db, pays)
    return resultat


def maj_capteur_local(
    db: Session,
    pays_id: uuid.UUID,
    capteur_central_id: uuid.UUID,
    corps: dict,
) -> dict:
    pays = _pays_local(db.get(Pays, pays_id))
    capteur = db.get(Capteur, capteur_central_id)
    if capteur is None or capteur.pays_id != pays.id:
        raise HTTPException(status_code=404, detail="Capteur introuvable pour ce pays")

    corps_local = dict(corps)
    if "entrepot_id" in corps_local and corps_local["entrepot_id"] is not None:
        entrepot = db.get(Entrepot, corps_local["entrepot_id"])
        if entrepot is None or entrepot.pays_id != pays.id:
            raise HTTPException(status_code=404, detail="Entrepôt introuvable pour ce pays")
        corps_local["entrepot_id"] = str(entrepot.source_id)

    resultat = _mettre_a_jour(pays, "capteurs", capteur.source_id, corps_local)
    _synchroniser_apres_ecriture(db, pays)
    return resultat


def supprimer_capteur_local(db: Session, pays_id: uuid.UUID, capteur_central_id: uuid.UUID) -> None:
    """Supprime un capteur côté local puis resynchronise et retire la copie centrale."""
    pays = _pays_local(db.get(Pays, pays_id))
    capteur = db.get(Capteur, capteur_central_id)
    if capteur is None or capteur.pays_id != pays.id:
        raise HTTPException(status_code=404, detail="Capteur introuvable pour ce pays")

    _supprimer(pays, "capteurs", capteur.source_id)
    _synchroniser_apres_ecriture(db, pays)
    db.delete(capteur)
    db.commit()
