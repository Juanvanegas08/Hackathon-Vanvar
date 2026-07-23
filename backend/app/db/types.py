"""Reusable SQLAlchemy column type aliases."""

from decimal import Decimal
from typing import Annotated

from sqlalchemy import Numeric, SmallInteger, Text
from sqlalchemy.dialects.postgresql import CITEXT, JSONB, UUID
from sqlalchemy.orm import mapped_column

Money = Annotated[Decimal, mapped_column(Numeric(14, 2))]
MoneyPrecise = Annotated[Decimal, mapped_column(Numeric(14, 6))]
Percentage = Annotated[Decimal, mapped_column(Numeric(7, 4))]
Confidence = Annotated[Decimal, mapped_column(Numeric(5, 4))]
Score = Annotated[int, mapped_column(SmallInteger)]
JsonDict = Annotated[dict[str, object], mapped_column(JSONB)]
UuidPk = Annotated[object, mapped_column(UUID(as_uuid=True), primary_key=True)]
CitextEmail = Annotated[str, mapped_column(CITEXT)]
LongText = Annotated[str, mapped_column(Text)]
