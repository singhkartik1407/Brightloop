from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException

from app.models import Product


def calculate_unit_price(product: Product, selected_variant_ids: list[UUID]) -> Decimal:
    """Return the base price plus each selected active variant adjustment.

    Subscription/quotation modules call this domain helper when they are introduced.
    """
    if len(selected_variant_ids) != len(set(selected_variant_ids)):
        raise HTTPException(status_code=422, detail="A variant may be selected only once")

    variants_by_id = {variant.id: variant for variant in product.variants if variant.is_active}
    selected = []
    for variant_id in selected_variant_ids:
        variant = variants_by_id.get(variant_id)
        if variant is None:
            raise HTTPException(status_code=422, detail="Selected variant does not belong to the active product")
        selected.append(variant)
    return Decimal(product.sales_price) + sum((Decimal(variant.price_adjustment) for variant in selected), Decimal("0.00"))
