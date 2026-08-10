# app/core/security.py
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models.utilisateur import ROLES, Utilisateur

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-a-changer-en-production")
ALGORITHM = "HS256"
TOKEN_EXPIRATION_MINUTES = int(os.getenv("JWT_EXPIRATION_MINUTES", "480"))  # 8 h

bearer_scheme = HTTPBearer(auto_error=False)


#  Hachage & vérification de mot de passe 

def hacher_mot_de_passe(mot_de_passe: str) -> str:
    return bcrypt.hashpw(mot_de_passe.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verifier_mot_de_passe(mot_de_passe: str, hash_stocke: str) -> bool:
    try:
        return bcrypt.checkpw(mot_de_passe.encode("utf-8"), hash_stocke.encode("utf-8"))
    except ValueError:
        return False


#  JWT 

def creer_token(utilisateur: Utilisateur) -> str:
    expiration = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRATION_MINUTES)
    payload = {
        "sub": str(utilisateur.id),
        "email": utilisateur.email,
        "role": utilisateur.role,
        "pays_id": str(utilisateur.pays_id) if utilisateur.pays_id else None,
        "entrepot_id": str(utilisateur.entrepot_id) if utilisateur.entrepot_id else None,
        "exp": expiration,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decoder_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None


#  Dépendances FastAPI 

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Utilisateur:
    """Authentifie l'utilisateur via un JWT Bearer."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentification requise (Bearer token)",
        )
    payload = decoder_token(credentials.credentials)
    if payload is None or payload.get("sub") is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré",
        )
    utilisateur = db.get(Utilisateur, payload["sub"])
    if utilisateur is None or not utilisateur.actif:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Compte introuvable ou désactivé",
        )
    return utilisateur


def require_role(*roles: str):
    """Restreint l'accès à certains rôles (ex : require_role("ADMIN_SIEGE"))."""

    def verificateur(utilisateur: Utilisateur = Depends(get_current_user)) -> Utilisateur:
        if utilisateur.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Rôle insuffisant. Requis : {', '.join(roles)}",
            )
        return utilisateur

    return verificateur


def est_admin(utilisateur: Utilisateur) -> bool:
    return utilisateur.role == "ADMIN_SIEGE"
