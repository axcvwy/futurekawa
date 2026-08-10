# app/routes/auth.py
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import (
    creer_token,
    get_current_user,
    hacher_mot_de_passe,
    require_role,
    verifier_mot_de_passe,
)
from app.database.db import get_db
from app.models.entrepot import Entrepot
from app.models.pays import Pays
from app.models.utilisateur import ROLES, Utilisateur
from app.schemas import (
    LoginRequest,
    MessageResponse,
    TokenResponse,
    UtilisateurCreate,
    UtilisateurOut,
    UtilisateurUpdate,
)

router = APIRouter(tags=["Authentification"])


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Connexion : échange email + mot de passe contre un JWT."""
    utilisateur = db.query(Utilisateur).filter(Utilisateur.email == payload.email).first()
    if utilisateur is None or not verifier_mot_de_passe(payload.mot_de_passe, utilisateur.mot_de_passe_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )
    if not utilisateur.actif:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte désactivé",
        )
    return TokenResponse(
        access_token=creer_token(utilisateur),
        utilisateur=UtilisateurOut.model_validate(utilisateur),
    )


@router.get("/auth/me", response_model=UtilisateurOut)
def me(utilisateur: Utilisateur = Depends(get_current_user)):
    """Profil de l'utilisateur connecté (rôle + périmètre)."""
    return utilisateur


# Gestion des comptes (réservée à ADMIN_SIEGE)
@router.get("/utilisateurs", response_model=list[UtilisateurOut])
def list_utilisateurs(
    _admin: Utilisateur = Depends(require_role("ADMIN_SIEGE")),
    db: Session = Depends(get_db),
):
    return db.query(Utilisateur).order_by(Utilisateur.nom).all()


@router.post("/utilisateurs", response_model=UtilisateurOut, status_code=201)
def create_utilisateur(
    payload: UtilisateurCreate,
    _admin: Utilisateur = Depends(require_role("ADMIN_SIEGE")),
    db: Session = Depends(get_db),
):
    if payload.role not in ROLES:
        raise HTTPException(status_code=400, detail=f"Rôle invalide. Valeurs : {ROLES}")
    if db.query(Utilisateur).filter(Utilisateur.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Un compte existe déjà avec cet email")

    _valider_perimetre(db, payload.role, payload.pays_id, payload.entrepot_id)

    utilisateur = Utilisateur(
        email=payload.email,
        nom=payload.nom,
        mot_de_passe_hash=hacher_mot_de_passe(payload.mot_de_passe),
        role=payload.role,
        actif=payload.actif,
        pays_id=payload.pays_id,
        entrepot_id=payload.entrepot_id,
    )
    db.add(utilisateur)
    db.commit()
    db.refresh(utilisateur)
    return utilisateur


@router.put("/utilisateurs/{utilisateur_id}", response_model=UtilisateurOut)
def update_utilisateur(
    utilisateur_id: uuid.UUID,
    payload: UtilisateurUpdate,
    _admin: Utilisateur = Depends(require_role("ADMIN_SIEGE")),
    db: Session = Depends(get_db),
):
    utilisateur = db.get(Utilisateur, utilisateur_id)
    if utilisateur is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    if payload.role is not None:
        if payload.role not in ROLES:
            raise HTTPException(status_code=400, detail=f"Rôle invalide. Valeurs : {ROLES}")
        utilisateur.role = payload.role

    nouveau_pays = payload.pays_id if payload.pays_id is not None else utilisateur.pays_id
    nouveau_entrepot = payload.entrepot_id if payload.entrepot_id is not None else utilisateur.entrepot_id
    _valider_perimetre(db, utilisateur.role, nouveau_pays, nouveau_entrepot)

    for champ in ("nom", "actif", "pays_id", "entrepot_id"):
        valeur = getattr(payload, champ)
        if valeur is not None:
            setattr(utilisateur, champ, valeur)
    if payload.mot_de_passe:
        utilisateur.mot_de_passe_hash = hacher_mot_de_passe(payload.mot_de_passe)

    db.commit()
    db.refresh(utilisateur)
    return utilisateur


@router.delete("/utilisateurs/{utilisateur_id}", response_model=MessageResponse)
def delete_utilisateur(
    utilisateur_id: uuid.UUID,
    admin: Utilisateur = Depends(require_role("ADMIN_SIEGE")),
    db: Session = Depends(get_db),
):
    utilisateur = db.get(Utilisateur, utilisateur_id)
    if utilisateur is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    if utilisateur.id == admin.id:
        raise HTTPException(status_code=400, detail="Impossible de supprimer votre propre compte")
    db.delete(utilisateur)
    db.commit()
    return MessageResponse(message="Utilisateur supprimé")


def _valider_perimetre(db: Session, role: str, pays_id, entrepot_id) -> None:
    """Un non-admin doit être rattaché à un pays ; le responsable d'entrepôt en plus à un entrepôt."""
    if role == "ADMIN_SIEGE":
        return
    if pays_id is None:
        raise HTTPException(status_code=400, detail="Un utilisateur non-admin doit être rattaché à un pays")
    if db.get(Pays, pays_id) is None:
        raise HTTPException(status_code=404, detail="Pays introuvable")
    if role == "RESPONSABLE_ENTREPOT":
        if entrepot_id is None:
            raise HTTPException(status_code=400, detail="Un responsable d'entrepôt doit être rattaché à un entrepôt")
        if db.get(Entrepot, entrepot_id) is None:
            raise HTTPException(status_code=404, detail="Entrepôt introuvable")
