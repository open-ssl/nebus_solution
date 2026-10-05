from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from shared.db.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.security import require_api_key
from api.schemas import PaymentAccepted, PaymentCreate, PaymentResponse
from api.services.payment_service import PaymentService


router = APIRouter(prefix="/api/v1", tags=["payments"], dependencies=[Depends(require_api_key)])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.post("/payments", status_code=status.HTTP_202_ACCEPTED, response_model=PaymentAccepted)
async def create_payment(
    body: PaymentCreate,
    session: SessionDep,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> PaymentAccepted:
    payment = await PaymentService(session).create(body, idempotency_key)
    return PaymentAccepted.from_model(payment)


@router.get("/payments/{payment_id}", response_model=PaymentResponse)
async def get_payment(payment_id: uuid.UUID, session: SessionDep) -> PaymentResponse:
    payment = await PaymentService(session).get(payment_id)
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return PaymentResponse.from_model(payment)
