from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

# --- FEATURE[auth] START ---
from app.api.v1.deps.auth import get_current_user

# --- FEATURE[auth] END ---
from app.api.v1.deps.items import get_item_service

# --- FEATURE[redis_rate_limit] START ---
from app.api.v1.deps.rate_limit import rate_limit_api, rate_limit_responses

# --- FEATURE[redis_rate_limit] END ---
from app.core import responses
from app.core.exceptions import http_exceptions
from app.schemas.item import ItemCreate, ItemResponse, ItemUpdate
from app.services.exceptions.base import DuplicateResourceError, ResourceNotFoundError
from app.services.item_service import ItemService

router = APIRouter(
    dependencies=[
        # --- FEATURE[auth] START ---
        Depends(get_current_user),
        # --- FEATURE[auth] END ---
        # --- FEATURE[redis_rate_limit] START ---
        Depends(rate_limit_api),
        # --- FEATURE[redis_rate_limit] END ---
    ],
    responses={
        # --- FEATURE[auth] START ---
        status.HTTP_401_UNAUTHORIZED: {"model": responses.UnauthorizedResponse},
        # --- FEATURE[auth] END ---
        # --- FEATURE[redis_rate_limit] START ---
        **rate_limit_responses(limit=100),
        # --- FEATURE[redis_rate_limit] END ---
    },
)


@router.get(
    "",
    response_model=list[ItemResponse],
    summary="List items",
    description="List items, oldest first, one page at a time.",
)
async def list_items(
    service: Annotated[ItemService, Depends(get_item_service)],
    skip: Annotated[int, Query(ge=0, description="Number of items to skip")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum number of items to return")] = 50,
) -> list[ItemResponse]:
    items = await service.list_items(skip=skip, limit=limit)
    return [ItemResponse.model_validate(item) for item in items]


@router.post(
    "",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_409_CONFLICT: {"model": responses.ConflictResponse},
    },
    summary="Create an item",
    description="Create an item. Item names are unique.",
)
async def create_item(
    data: ItemCreate,
    service: Annotated[ItemService, Depends(get_item_service)],
) -> ItemResponse:
    try:
        item = await service.create_item(data)
    except DuplicateResourceError as ex:
        raise http_exceptions.ConflictException(detail=str(ex))

    return ItemResponse.model_validate(item)


@router.get(
    "/{item_id}",
    response_model=ItemResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": responses.NotFoundResponse},
    },
    summary="Read an item",
    description="Get one item by its ID.",
)
async def read_item(
    item_id: int,
    service: Annotated[ItemService, Depends(get_item_service)],
) -> ItemResponse:
    try:
        item = await service.get_item(item_id)
    except ResourceNotFoundError as ex:
        raise http_exceptions.NotFoundException(detail=str(ex))

    return ItemResponse.model_validate(item)


@router.patch(
    "/{item_id}",
    response_model=ItemResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": responses.NotFoundResponse},
        status.HTTP_409_CONFLICT: {"model": responses.ConflictResponse},
    },
    summary="Update an item",
    description="Change the given fields of an item. Fields left out keep their value.",
)
async def update_item(
    item_id: int,
    data: ItemUpdate,
    service: Annotated[ItemService, Depends(get_item_service)],
) -> ItemResponse:
    try:
        item = await service.update_item(item_id, data)
    except ResourceNotFoundError as ex:
        raise http_exceptions.NotFoundException(detail=str(ex))
    except DuplicateResourceError as ex:
        raise http_exceptions.ConflictException(detail=str(ex))

    return ItemResponse.model_validate(item)


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": responses.NotFoundResponse},
    },
    summary="Delete an item",
    description="Delete one item by its ID.",
)
async def delete_item(
    item_id: int,
    service: Annotated[ItemService, Depends(get_item_service)],
) -> None:
    try:
        await service.delete_item(item_id)
    except ResourceNotFoundError as ex:
        raise http_exceptions.NotFoundException(detail=str(ex))
