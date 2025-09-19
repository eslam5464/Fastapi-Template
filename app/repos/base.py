import uuid
from sqlalchemy import insert, select, text, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.engine import Result

from typing import Generic, Type, TypeVar, Any, Sequence
from pydantic import BaseModel

from app.models import Base

Model = TypeVar("Model", bound=Base)
CreateSchema = TypeVar("CreateSchema", bound=BaseModel)
UpdateSchema = TypeVar("UpdateSchema", bound=BaseModel)


class BaseRepository(Generic[Model, CreateSchema, UpdateSchema]):
    def __init__(
        self,
        session: AsyncSession,
        model: Type[Model],
    ):
        """
        Initialize the repository with a session and model.

        Args:
            session (AsyncSession): The database session.
            model (Type[Model]): The model class.
        """
        self.session = session
        self.model = model

    def _validate_column_exists(self, column_name: str) -> None:
        """
        Validate that a column exists on the model.

        Args:
            column_name (str): The name of the column to validate.

        Raises:
            ValueError: If the column doesn't exist on the model.
        """
        if not hasattr(self.model, column_name):
            raise ValueError(
                f"Column '{column_name}' does not exist on model {self.model.__name__}"
            )

        # Additional check for SQLAlchemy column attributes
        try:
            getattr(self.model, column_name)
        except AttributeError:
            raise ValueError(
                f"Column '{column_name}' is not a valid SQLAlchemy column on model {self.model.__name__}"
            )

    async def create_one(self, schema: CreateSchema) -> Model:
        """
        Create a new object in the database.

        Args:
            schema (CreateSchema): The data to create the object.

        Returns:
            Model: The created object.

        Raises:
            Exception: If the object creation fails.
        """
        stmt = (
            insert(self.model)
            .values(**schema.model_dump(exclude_none=True))
            .returning(self.model)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one()

    async def create_bulk(self, schemas: Sequence[CreateSchema]) -> Sequence[Model]:
        """
        Create multiple objects in the database.

        Args:
            schemas (Sequence[CreateSchema]): The list of data to create objects.

        Returns:
            Sequence[Model]: The Sequence of created objects.

        Raises:
            Exception: If the bulk creation fails.
        """
        if not schemas:
            return []

        values = [schema.model_dump(exclude_none=True) for schema in schemas]
        stmt = insert(self.model).values(values).returning(self.model)
        result = await self.session.execute(stmt)
        await self.session.commit()

        return result.scalars().all()

    async def get_by_id(
        self,
        obj_id: str | int | uuid.UUID,
        id_column_name: str = "id",
    ) -> Model | None:
        """
        Retrieve an object by its ID.

        Args:
            obj_id (int | uuid.UUID): The ID of the object to retrieve.
            id_column_name (str): The name of the ID column in the model.

        Returns:
            Model | None: The retrieved object or None if not found.

        Raises:
            ValueError: If the id_column_name doesn't exist on the model.
        """
        self._validate_column_exists(id_column_name)
        stmt = select(self.model).where(getattr(self.model, id_column_name) == obj_id)
        result = await self.session.execute(stmt)

        return result.scalar_one_or_none()

    async def get_multi(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Model]:
        """
        Retrieve multiple objects from the database.

        Args:
            skip (int): The number of records to skip.
            limit (int): The maximum number of records to retrieve.

        Returns:
            Sequence[Model]: A Sequence of retrieved objects.
        """
        stmt = select(self.model).offset(skip).limit(limit)
        result = await self.session.execute(stmt)

        return result.scalars().all()

    async def get_by_ids(
        self,
        obj_ids: Sequence[int | uuid.UUID],
        id_column_name: str = "id",
    ) -> Sequence[Model]:
        """
        Retrieve multiple objects by their IDs.

        Args:
            obj_ids (Sequence[int | uuid.UUID]): The IDs of the objects to retrieve.
            id_column_name (str): The name of the ID column in the model.

        Returns:
            Sequence[Model]: A Sequence of retrieved objects.

        Raises:
            ValueError: If the id_column_name doesn't exist on the model.
        """
        if not obj_ids:
            return []

        self._validate_column_exists(id_column_name)

        stmt = select(self.model).where(
            getattr(self.model, id_column_name).in_(obj_ids)
        )
        result = await self.session.execute(stmt)

        return result.scalars().all()

    async def update_by_id(
        self,
        obj_id: int | uuid.UUID,
        schema: UpdateSchema,
        id_column_name: str = "id",
    ) -> Model | None:
        """
        Update an object by its ID.

        Args:
            obj_id (int | uuid.UUID): The ID of the object to update.
            schema (UpdateSchema): The data to update the object.
            id_column_name (str): The name of the ID column in the model.

        Returns:
            Model | None: The updated object or None if not found.

        Raises:
            ValueError: If the id_column_name doesn't exist on the model.
        """
        self._validate_column_exists(id_column_name)
        existing = await self.get_by_id(obj_id, id_column_name)

        if not existing:
            return None

        stmt = (
            update(self.model)
            .where(getattr(self.model, id_column_name) == obj_id)
            .values(**schema.model_dump(exclude_none=True))
            .returning(self.model)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()

        return result.scalar_one_or_none()

    async def update_bulk(
        self,
        updates: Sequence[tuple[int | uuid.UUID, UpdateSchema]],
        id_column_name: str = "id",
    ) -> list[Model]:
        """
        Update multiple objects by their IDs.

        Args:
            updates (Sequence[tuple[int | uuid.UUID, UpdateSchema]]): List of tuples containing (id, update_data).
            id_column_name (str): The name of the ID column in the model.

        Returns:
            list[Model]: A list of updated objects.

        Raises:
            ValueError: If the id_column_name doesn't exist on the model.
        """
        if not updates:
            return []

        self._validate_column_exists(id_column_name)
        updated_objects = []

        for obj_id, update_schema in updates:
            stmt = (
                update(self.model)
                .where(getattr(self.model, id_column_name) == obj_id)
                .values(**update_schema.model_dump(exclude_none=True))
                .returning(self.model)
            )
            result = await self.session.execute(stmt)
            updated_obj = result.scalar_one_or_none()

            if updated_obj:
                updated_objects.append(updated_obj)

        await self.session.commit()
        return updated_objects

    async def delete_by_id(
        self,
        obj_id: int | uuid.UUID,
        id_column_name: str = "id",
    ) -> bool:
        """
        Delete an object by its ID.

        Args:
            obj_id (int | uuid.UUID): The ID of the object to delete.
            id_column_name (str): The name of the ID column in the model.

        Returns:
            bool: True if the object was deleted, False otherwise.

        Raises:
            ValueError: If the id_column_name doesn't exist on the model.
        """
        self._validate_column_exists(id_column_name)
        stmt = delete(self.model).where(getattr(self.model, id_column_name) == obj_id)
        result = await self.session.execute(stmt)
        await self.session.commit()

        return result.rowcount > 0

    async def delete_by_ids(
        self,
        obj_ids: Sequence[int | uuid.UUID],
        id_column_name: str = "id",
    ) -> int:
        """
        Delete multiple objects by their IDs.

        Args:
            obj_ids (Sequence[int | uuid.UUID]): The IDs of the objects to delete.
            id_column_name (str): The name of the ID column in the model.

        Returns:
            int: The number of objects deleted.

        Raises:
            ValueError: If the id_column_name doesn't exist on the model.
        """
        if not obj_ids:
            return 0

        self._validate_column_exists(id_column_name)
        stmt = delete(self.model).where(
            getattr(self.model, id_column_name).in_(obj_ids)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()

        return result.rowcount

    async def custom_query(self, query: str) -> Result[Any]:
        """
        Execute a custom SQL query.

        Args:
            query (str): The SQL query to execute.

        Returns:
            Result: The result of the executed query.
        """
        result = await self.session.execute(text(query))

        return result
