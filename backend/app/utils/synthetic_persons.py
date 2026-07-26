"""Deterministic synthetic PII helpers for hackathon demo data.

All values are fictional. Document numbers use a reserved 9xxxxxxxxx range
so they never collide with the small curated mock_affiliates.json demos.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from random import Random
from uuid import UUID, NAMESPACE_URL, uuid5

from app.utils.normalization import strip_text

PERSON_NAMESPACE = uuid5(NAMESPACE_URL, "casalista:synthetic-persons")

FIRST_NAMES = (
    "Ana",
    "Andrés",
    "Camila",
    "Carlos",
    "Daniela",
    "David",
    "Diana",
    "Felipe",
    "Gabriel",
    "Isabella",
    "Juan",
    "Julián",
    "Laura",
    "Luis",
    "María",
    "Mateo",
    "Natalia",
    "Nicolás",
    "Paola",
    "Santiago",
    "Sofía",
    "Valentina",
    "Valeria",
    "Sebastián",
)

LAST_NAMES = (
    "García",
    "Rodríguez",
    "Martínez",
    "López",
    "González",
    "Pérez",
    "Sánchez",
    "Ramírez",
    "Torres",
    "Flores",
    "Rivera",
    "Gómez",
    "Díaz",
    "Cruz",
    "Morales",
    "Reyes",
    "Ortiz",
    "Gutierrez",
    "Ruiz",
    "Jiménez",
)

_AGE_RANGE_RE = re.compile(
    r"(?P<low>\d+)\s*(?:-|a|–|—)\s*(?P<high>\d+)",
    re.IGNORECASE,
)

_SALARY_BY_CATEGORY: dict[str, tuple[float, str]] = {
    "A": (1_800_000.0, "Hasta 2 SMMLV"),
    "B": (3_200_000.0, "Entre 2 y 4 SMMLV"),
    "C": (6_500_000.0, "Más de 4 SMMLV"),
}


@dataclass(frozen=True)
class SyntheticPersonDraft:
    """In-memory draft used to build seed artifacts and DB rows."""

    row_number: int
    person_id: str
    first_name: str
    last_name: str
    display_name: str
    document_type: str
    document_number: str
    document_hash: str
    document_last_four: str
    phone: str
    phone_hash: str
    phone_masked: str
    email: str
    email_hash: str
    email_masked: str
    affiliated: bool
    affiliation_status: str
    affiliation_category: str | None
    reported_salary: float | None
    salary_range: str | None
    dependents: int | None
    beneficiaries_registered: int | None
    company: str | None
    segment: str | None
    age_range: str | None
    estimated_age: int | None


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def person_uuid_for_row(row_number: int) -> UUID:
    return uuid5(PERSON_NAMESPACE, f"row:{int(row_number)}")


def affiliated_from_buyer_record(record: dict) -> bool | None:
    status = strip_text(record.get("affiliation_status"))
    if status == "affiliated":
        return True
    if status in {"non_affiliated", "non-affiliated", "not_affiliated"}:
        return False
    normalized = record.get("normalized_data") or {}
    if isinstance(normalized, dict) and "afiliado" in normalized:
        value = normalized.get("afiliado")
        if value is None:
            return None
        return bool(value)
    return None


def document_number_for_row(row_number: int) -> str:
    """Reserved fictional CC range: 9000000000 + row_number (10 digits)."""
    return f"{9_000_000_000 + int(row_number):010d}"


def mask_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    if len(digits) < 4:
        return "***"
    return f"***{digits[-4:]}"


def mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    if not domain:
        return "***"
    visible = local[:1] if local else "*"
    return f"{visible}***@{domain}"


def parse_age_range(raw: str | None) -> tuple[int, int] | None:
    if not raw:
        return None
    match = _AGE_RANGE_RE.search(raw)
    if not match:
        return None
    low = int(match.group("low"))
    high = int(match.group("high"))
    if low > high:
        low, high = high, low
    return low, high


def estimate_age(age_range: str | None, rng: Random) -> int | None:
    bounds = parse_age_range(age_range)
    if bounds is None:
        return None
    low, high = bounds
    return rng.randint(low, high)


def synthetic_category_for_row(row_number: int, affiliated: bool) -> str | None:
    if not affiliated:
        return "D"
    return ("A", "B", "C")[int(row_number) % 3]


def build_synthetic_person(
    *,
    row_number: int,
    person_id: str,
    affiliated: bool | None,
    dependents: int | None,
    age_range: str | None,
    segment: str | None,
    company_hint: str | None = None,
) -> SyntheticPersonDraft:
    """Build one deterministic fictional person for a buyer row."""
    rng = Random(f"casalista-synthetic-person:{row_number}")
    first = FIRST_NAMES[rng.randrange(len(FIRST_NAMES))]
    last = LAST_NAMES[rng.randrange(len(LAST_NAMES))]
    display = f"{first} {last}"
    doc_number = document_number_for_row(row_number)
    # Deterministic unique mobile in 300xxxxxxx range (demo only).
    phone = f"300{(int(row_number) % 10_000_000):07d}"
    email_local = (
        f"{first}.{last}.{row_number}"
        .lower()
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ñ", "n")
        .replace(" ", "")
    )
    # Use example.com so EmailStr / email-validator accept demo contacts.
    email = f"{email_local}@example.com"

    is_affiliated = bool(affiliated) if affiliated is not None else True
    category = synthetic_category_for_row(row_number, is_affiliated)
    salary: float | None = None
    salary_range: str | None = None
    if is_affiliated and category in _SALARY_BY_CATEGORY:
        salary, salary_range = _SALARY_BY_CATEGORY[category]
    elif not is_affiliated:
        category = "D"

    status = "affiliated" if is_affiliated else "non_affiliated"
    company = company_hint or (
        f"Empresa Demo {((row_number % 40) + 1):02d}" if is_affiliated else None
    )
    beneficiaries = dependents if is_affiliated else None

    return SyntheticPersonDraft(
        row_number=int(row_number),
        person_id=person_id,
        first_name=first,
        last_name=last,
        display_name=display,
        document_type="CC",
        document_number=doc_number,
        document_hash=sha256_hex(f"CC:CO:{doc_number}"),
        document_last_four=doc_number[-4:],
        phone=phone,
        phone_hash=sha256_hex(f"phone:{phone}"),
        phone_masked=mask_phone(phone),
        email=email,
        email_hash=sha256_hex(f"email:{email.lower()}"),
        email_masked=mask_email(email),
        affiliated=is_affiliated,
        affiliation_status=status,
        affiliation_category=category,
        reported_salary=salary,
        salary_range=salary_range,
        dependents=dependents,
        beneficiaries_registered=beneficiaries,
        company=company,
        segment=segment,
        age_range=age_range,
        estimated_age=estimate_age(age_range, rng),
    )


def draft_to_affiliate_record(draft: SyntheticPersonDraft) -> dict:
    """Shape compatible with MockAffiliateRecord / mock_affiliates JSON."""
    return {
        "document_number": draft.document_number,
        "document_type": draft.document_type,
        "first_name": draft.first_name,
        "last_name": draft.last_name,
        "phone": draft.phone,
        "email": draft.email,
        "affiliated": draft.affiliated,
        "affiliation_confirmed": draft.affiliated,
        "affiliation_category": draft.affiliation_category,
        "company": draft.company,
        "reported_salary": draft.reported_salary,
        "salary_range": draft.salary_range,
        "dependents": draft.dependents,
        "beneficiaries_registered": draft.beneficiaries_registered,
        "segment": draft.segment,
        "source": "mock_affiliation_service",
        "scenario": (
            f"Persona sintética fila {draft.row_number} "
            f"(rango_edad={draft.age_range or 'n/d'})"
        ),
        "last_updated_at": "2026-07-23",
    }


def draft_to_person_seed(draft: SyntheticPersonDraft) -> dict:
    """Shape used by seed_historical_data for identity + affiliation inserts."""
    return {
        "row_number": draft.row_number,
        "person_id": draft.person_id,
        "first_name": draft.first_name,
        "last_name": draft.last_name,
        "display_name": draft.display_name,
        "identity_status": (
            "known_affiliate" if draft.affiliated else "known_non_affiliate"
        ),
        "is_demo": True,
        "identifier": {
            "identifier_type": "CC",
            "identifier_hash": draft.document_hash,
            "identifier_ciphertext": draft.document_number,
            "identifier_last_four": draft.document_last_four,
            "country_code": "CO",
            "is_primary": True,
            "is_verified": False,
        },
        "contacts": [
            {
                "contact_type": "phone",
                "value_hash": draft.phone_hash,
                "value_ciphertext": draft.phone,
                "masked_value": draft.phone_masked,
                "is_primary": True,
                "is_verified": False,
            },
            {
                "contact_type": "email",
                "value_hash": draft.email_hash,
                "value_ciphertext": draft.email,
                "masked_value": draft.email_masked,
                "is_primary": True,
                "is_verified": False,
            },
        ],
        "affiliation": {
            "provider": "mock_affiliation_service",
            "status": draft.affiliation_status,
            "category": (
                draft.affiliation_category
                if draft.affiliation_category in {"A", "B", "C", "D"}
                else None
            ),
            "reported_salary": draft.reported_salary,
            "confirmed": draft.affiliated,
            "source_reference": f"synthetic_row:{draft.row_number}",
            "employer_name": draft.company,
        },
        "lookup": draft_to_affiliate_record(draft),
        "document_number": draft.document_number,
        "age_range": draft.age_range,
        "estimated_age": draft.estimated_age,
    }
