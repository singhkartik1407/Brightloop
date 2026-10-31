from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models import Product, ProductVariant, User, UserRole
from app.modules.products.schemas import ProductCreateRequest, ProductListResponse, ProductRead, ProductUpdateRequest


router = APIRouter(prefix="/api/v1/products", tags=["Products"])
admin_staff = require_roles(UserRole.ADMIN, UserRole.STAFF)


def get_product_or_404(db: Session, product_id: UUID) -> Product:
    product = db.scalar(
        select(Product).options(selectinload(Product.variants)).where(Product.id == product_id)
    )
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


def save_product(db: Session, product: Product) -> Product:
    try:
        db.commit()
        db.refresh(product)
        product.variants.sort(key=lambda variant: (variant.attribute_name, variant.attribute_value, str(variant.id)))
        return product
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Product operation failed due to a data conflict")


def serialize_product(product: Product, user: User) -> ProductRead:
    response = ProductRead.model_validate(product)
    if user.role != UserRole.ADMIN.value:
        response.cost_price = None
    return response


def replace_variants(product: Product, variants) -> None:
    existing = {
        (variant.attribute_name.casefold(), variant.attribute_value.casefold()): variant
        for variant in product.variants
    }
    requested = set()
    for input_variant in variants:
        key = (input_variant.attribute_name.casefold(), input_variant.attribute_value.casefold())
        requested.add(key)
        variant = existing.get(key)
        if variant is None:
            product.variants.append(ProductVariant(**input_variant.model_dump(by_alias=False)))
        else:
            variant.attribute_name = input_variant.attribute_name
            variant.attribute_value = input_variant.attribute_value
            variant.price_adjustment = input_variant.price_adjustment
            variant.is_active = True
    for key, variant in existing.items():
        if key not in requested:
            variant.is_active = False


@router.post("", response_model=ProductRead, response_model_by_alias=True, response_model_exclude_none=True, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreateRequest, db: Session = Depends(get_db), user: User = Depends(admin_staff)):
    if user.role != UserRole.ADMIN.value:
        raise HTTPException(status_code=403, detail="Only Admin may set cost price or create products")
    data = payload.model_dump(exclude={"variants"}, by_alias=False)
    product = Product(**data)
    for variant in payload.variants or []:
        product.variants.append(ProductVariant(**variant.model_dump(by_alias=False)))
    db.add(product)
    return serialize_product(save_product(db, product), user)


@router.get("", response_model=ProductListResponse, response_model_by_alias=True, response_model_exclude_none=True)
def list_products(
    search: str | None = Query(default=None, max_length=120),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    is_active: bool | None = Query(default=None, alias="isActive"),
    db: Session = Depends(get_db),
    user: User = Depends(admin_staff),
):
    conditions = [Product.is_active.is_(True)] if is_active is None else [Product.is_active.is_(is_active)]
    search_term = (search or "").strip()
    if search_term:
        escaped = search_term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        conditions.append(or_(Product.name.ilike(pattern, escape="\\"), Product.notes.ilike(pattern, escape="\\")))
    total = db.scalar(select(func.count(Product.id)).where(*conditions)) or 0
    products = db.scalars(
        select(Product).options(selectinload(Product.variants)).where(*conditions)
        .order_by(Product.created_at.desc(), Product.id).offset((page - 1) * page_size).limit(page_size)
    ).unique().all()
    for product in products:
        product.variants.sort(key=lambda variant: (variant.attribute_name, variant.attribute_value, str(variant.id)))
    return ProductListResponse(items=[serialize_product(product, user) for product in products], total=total, page=page, page_size=page_size)


@router.get("/{productId}", response_model=ProductRead, response_model_by_alias=True, response_model_exclude_none=True)
def get_product(product_id: UUID = Path(alias="productId"), db: Session = Depends(get_db), user: User = Depends(admin_staff)):
    return serialize_product(get_product_or_404(db, product_id), user)


@router.patch("/{productId}", response_model=ProductRead, response_model_by_alias=True, response_model_exclude_none=True)
def update_product(payload: ProductUpdateRequest, product_id: UUID = Path(alias="productId"), db: Session = Depends(get_db), user: User = Depends(admin_staff)):
    product = get_product_or_404(db, product_id)
    if not product.is_active:
        raise HTTPException(status_code=409, detail="Archived product must be restored before updating")
    if user.role != UserRole.ADMIN.value and "cost_price" in payload.model_fields_set:
        raise HTTPException(status_code=403, detail="Only Admin may modify cost price")
    changes = payload.model_dump(exclude_unset=True, exclude={"variants"}, by_alias=False)
    if not changes and "variants" not in payload.model_fields_set:
        raise HTTPException(status_code=400, detail="No fields provided for update")
    for field, value in changes.items():
        setattr(product, field, value)
    if "variants" in payload.model_fields_set:
        replace_variants(product, payload.variants or [])
    return serialize_product(save_product(db, product), user)


@router.post("/{productId}/archive", status_code=status.HTTP_204_NO_CONTENT)
def archive_product(product_id: UUID = Path(alias="productId"), db: Session = Depends(get_db), user: User = Depends(admin_staff)):
    product = get_product_or_404(db, product_id)
    if product.is_active:
        product.is_active = False
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
