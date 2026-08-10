# app/core/permissions.py
from typing import Optional
from uuid import UUID

from app.models.utilisateur import Utilisateur


def pays_autorise(utilisateur: Utilisateur) -> Optional[UUID]:
    """Pays auquel l'utilisateur est restreint (None = aucun filtre, vue globale)."""
    if utilisateur.role == "ADMIN_SIEGE":
        return None
    return utilisateur.pays_id


def entrepot_autorise(utilisateur: Utilisateur) -> Optional[UUID]:
    """Entrepôt auquel un RESPONSABLE_ENTREPOT est restreint (None = aucun filtre)."""
    if utilisateur.role == "RESPONSABLE_ENTREPOT":
        return utilisateur.entrepot_id
    return None


def appliquer_filtre_pays(query, model, utilisateur: Utilisateur):
    """Restreint une requête SQLAlchemy au périmètre pays de l'utilisateur."""
    pays = pays_autorise(utilisateur)
    if pays is not None:
        colonne = model.pays_id if hasattr(model, "pays_id") else model.id
        query = query.filter(colonne == pays)
    return query


def appliquer_filtre_entrepot(query, model, utilisateur: Utilisateur):
    """Restreint une requête SQLAlchemy au périmètre entrepôt de l'utilisateur."""
    entrepot = entrepot_autorise(utilisateur)
    if entrepot is not None:
        colonne = model.entrepot_id if hasattr(model, "entrepot_id") else model.id
        query = query.filter(colonne == entrepot)
    return query
