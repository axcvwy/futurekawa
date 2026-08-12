# app/routes/erp.py
"""Flux d'intégration ERP (machine-to-machine).

Expose des contrats plats orientés consommateur externe (SAP, MS Dynamics, mock) :
stocks consolidés, alertes qualité et historique de mesures. Authentification par
header X-ERP-Key — aucun compte JWT requis pour l'ERP.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.security import verifier_cle_erp
from app.database.db import get_db
from app.schemas import ERPAlerteListOut, ERPMesureListOut, ERPStockListOut, ERPStockOut
from app.services.erp_export import SOURCE_NOM, _generated_at, lister_alertes, lister_mesures, lister_stocks

router = APIRouter(prefix="/erp", tags=["Intégration ERP (X-ERP-Key)"], dependencies=[Depends(verifier_cle_erp)])


@router.get("/stocks", response_model=ERPStockListOut, summary="Stock consolidé (vue ERP)")
def get_stocks(db: Session = Depends(get_db)):
    """Stock FIFO consolidé par pays / entrepôt / lot : disponibilité, traçabilité,
    statut qualité, dernières conditions de conservation et fraîcheur de synchro."""
    return ERPStockListOut(
        generated_at=_generated_at(),
        source=SOURCE_NOM,
        lots=lister_stocks(db),
    )


@router.get("/stocks/{lot_id}", response_model=ERPStockOut, summary="Traçabilité d'un lot")
def get_stock_lot(lot_id: str, db: Session = Depends(get_db)):
    """Une ligne de stock précise, à partir du code lot métier partagé."""
    resultats = [stock for stock in lister_stocks(db) if stock.lot_id == lot_id]
    if not resultats:
        raise HTTPException(status_code=404, detail="Lot inconnu du SI central")
    return resultats[0]


@router.get("/alertes", response_model=ERPAlerteListOut, summary="Exceptions qualité (vue ERP)")
def get_alertes(db: Session = Depends(get_db)):
    """Alertes de qualité et de conservation (température, humidité, lots trop anciens)."""
    return ERPAlerteListOut(
        generated_at=_generated_at(),
        source=SOURCE_NOM,
        alertes=lister_alertes(db),
    )


@router.get("/mesures", response_model=ERPMesureListOut, summary="Historique de mesures (vue ERP)")
def get_mesures(
    entrepot_id: uuid.UUID | None = Query(default=None, description="Filtrer sur un entrepôt précis"),
    limite: int = Query(default=500, ge=1, le=5000, description="Nombre maximal de lignes"),
    db: Session = Depends(get_db),
):
    """Historique des télémesures IoT consolidé (température & humidité)."""
    return ERPMesureListOut(
        generated_at=_generated_at(),
        source=SOURCE_NOM,
        mesures=lister_mesures(db, entrepot_id=str(entrepot_id) if entrepot_id else None, limite=limite),
    )
