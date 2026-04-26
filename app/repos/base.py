import uuid
from typing import Any, Generic, Sequence, Type, TypeVar

from pydantic import BaseModel
from sqlalchemy import delete, insert, select, text, update
from sqlalchemy.engine import Result
from sqlalchemy.exc import MultipleResultsFound
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

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

    async def create_one(
        self, schema: CreateSchema, exclude_none: bool = True, auto_commit: bool = True
    ) -> Model:
        """
        Create a new object in the database.

        Args:
            schema (CreateSchema): The data to create the object.
            exclude_none (bool): Whether to exclude None values from the creation.
            auto_commit (bool): Whether to commit the transaction. Pass False when
                deps layer coordinates multi-step transactions.

        Returns:
            created_object (Model): The created object.

        Raises:
            Exception: If the object creation fails.
        """
        stmt = (
            insert(self.model)
            .values(**schema.model_dump(exclude_none=exclude_none))
            .returning(self.model)
        )
        result = await self.session.execute(stmt)
        if auto_commit:
            await self.session.commit()
        return result.scalar_one()

    async def create_bulk(
        self,
        schemas: Sequence[CreateSchema],
        exclude_none: bool = True,
        auto_commit: bool = True,
    ) -> Sequence[Model]:
        """
        Create multiple objects in the database.

        Args:
            schemas (Sequence[CreateSchema]): The list of data to create objects.
            exclude_none (bool): Whether to exclude None values from the creation.
            auto_commit (bool): Whether to commit the transaction. Pass False when
                deps layer coordinates multi-step transactions.

        Returns:
            created_objects (Sequence[Model]): The Sequence of created objects.

        Raises:
            Exception: If the bulk creation fails.
        """
        if not schemas:
            return []

        values = [schema.model_dump(exclude_none=exclude_none) for schema in schemas]
        stmt = insert(self.model).values(values).returning(self.model)
        result = await self.session.execute(stmt)
        if auto_commit:
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

    async def get_multi_by_ids(
        self,
        skip: int = 0,
        limit: int = 100,
        id_column_name: str = "id",
        obj_ids: Sequence[str | int | uuid.UUID] = [],
    ) -> Sequence[Model]:
        """
        Retrieve multiple objects from the database.

        Args:
            skip (int): The number of records to skip.
            limit (int): The maximum number of records to retrieve.
            id_column_name (str): The name of the ID column in the model.
            obj_ids (Sequence[str | int | uuid.UUID]): The IDs of the objects to retrieve

        Returns:
            retrieved_objects (Sequence[Model]): A Sequence of retrieved objects.
        """
        self._validate_column_exists(id_column_name)
        stmt = (
            select(self.model)
            .where(getattr(self.model, id_column_name).in_(obj_ids))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)

        return result.scalars().all()

    async def update_by_id(
        self,
        obj_id: str | int | uuid.UUID,
        schema: UpdateSchema,
        id_column_name: str = "id",
        exclude_none: bool = True,
        auto_commit: bool = True,
    ) -> Model | None:
        """
        Update an object by its ID.

        Args:
            obj_id (int | uuid.UUID): The ID of the object to update.
            schema (UpdateSchema): The data to update the object.
            id_column_name (str): The name of the ID column in the model.
            exclude_none (bool): Whether to exclude None values from the update.
            auto_commit (bool): Whether to commit the transaction. Pass False when
                deps layer coordinates multi-step transactions.

        Returns:
            updated_object (Model | None): The updated object or None if not found.

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
            .values(**schema.model_dump(exclude_none=exclude_none))
            .returning(self.model)
        )
        result = await self.session.execute(stmt)
        if auto_commit:
            await self.session.commit()

        return result.scalar_one_or_none()

    async def update_bulk(
        self,
        updates: Sequence[tuple[str | int | uuid.UUID, UpdateSchema]],
        id_column_name: str = "id",
        exclude_none: bool = True,
        auto_commit: bool = True,
        *,
        allow_multiple: bool = False,
    ) -> list[Model]:
        """
        Update multiple objects by identifier values.

        By default each update tuple is expected to match at most one row. If a
        tuple matches multiple rows (for example when ``id_column_name`` refers
        to a non-unique column), the in-flight transaction is rolled back and
        ``MultipleResultsFound`` is raised. Pass ``allow_multiple=True`` to
        explicitly opt in to multi-row updates per tuple.

        Args:
            updates (Sequence[tuple[str | int | uuid.UUID, UpdateSchema]]): List of tuples containing (identifier_value, update_data).
            id_column_name (str): The name of the identifier column in the model.
            exclude_none (bool): Whether to exclude None values from the update.
            auto_commit (bool): Whether to commit the transaction. Pass False when
                deps layer coordinates multi-step transactions.
            allow_multiple (bool): When False (default), enforce a single-row
                match per update tuple and raise ``MultipleResultsFound`` if a
                tuple updates more than one row. When True, allow a single
                tuple to update and return multiple rows.

        Returns:
            updated_objects (list[Model]): A flat list of updated objects.

        Raises:
            ValueError: If the id_column_name doesn't exist on the model.
            MultipleResultsFound: If ``allow_multiple`` is False and any update
                tuple matches more than one row. The session is rolled back
                before raising, regardless of ``auto_commit``.
        """
        if not updates:
            return []

        self._validate_column_exists(id_column_name)
        updated_objects: list[Model] = []

        for obj_id, update_schema in updates:
            stmt = (
                update(self.model)
                .where(getattr(self.model, id_column_name) == obj_id)
                .values(**update_schema.model_dump(exclude_none=exclude_none))
                .returning(self.model)
            )
            result = await self.session.execute(stmt)

            if allow_multiple:
                updated_rows = result.scalars().all()
                if not updated_rows:
                    continue
                updated_objects.extend(updated_rows)
                continue

            try:
                updated_row = result.scalar_one_or_none()
            except MultipleResultsFound:
                await self.session.rollback()
                raise MultipleResultsFound(
                    f"update_bulk matched multiple rows for "
                    f"{self.model.__name__}.{id_column_name} == {obj_id!r}; "
                    "pass allow_multiple=True to permit multi-row updates."
                ) from None

            if updated_row is None:
                continue

            updated_objects.append(updated_row)

        if auto_commit:
            await self.session.commit()
        return updated_objects

    async def delete_by_id(
        self,
        obj_id: str | int | uuid.UUID,
        id_column_name: str = "id",
        auto_commit: bool = True,
        *,
        allow_multiple: bool = False,
    ) -> bool:
        """
        Delete an object by its ID.

        By default each call is expected to match at most one row. If the
        identifier matches multiple rows (for example when ``id_column_name``
        refers to a non-unique column), the in-flight transaction is rolled
        back and ``MultipleResultsFound`` is raised. Pass
        ``allow_multiple=True`` to explicitly opt in to multi-row deletes.

        Args:
            obj_id (str | int | uuid.UUID): The ID of the object to delete.
            id_column_name (str): The name of the ID column in the model.
            auto_commit (bool): Whether to commit the transaction. Pass False when
                deps layer coordinates multi-step transactions.
            allow_multiple (bool): When False (default), enforce a single-row
                match and raise ``MultipleResultsFound`` if the identifier
                deletes more than one row. When True, allow a single call to
                delete multiple rows.

        Returns:
            is_deleted (bool): True if at least one row was deleted, False otherwise.

        Raises:
            ValueError: If the id_column_name doesn't exist on the model.
            MultipleResultsFound: If ``allow_multiple`` is False and the
                identifier matches more than one row. The session is rolled
                back before raising, regardless of ``auto_commit``.
        """
        self._validate_column_exists(id_column_name)
        id_column = getattr(self.model, id_column_name)
        stmt = delete(self.model).where(id_column == obj_id).returning(id_column)
        result = await self.session.execute(stmt)
        deleted_count = len(result.scalars().all())

        if deleted_count > 1 and not allow_multiple:
            await self.session.rollback()
            raise MultipleResultsFound(
                f"delete_by_id matched {deleted_count} rows for "
                f"{self.model.__name__}.{id_column_name} == {obj_id!r}; "
                "pass allow_multiple=True to permit multi-row deletes."
            )

        if auto_commit:
            await self.session.commit()

        return bool(deleted_count)

    async def delete_by_ids(
        self,
        obj_ids: Sequence[str | int | uuid.UUID],
        id_column_name: str = "id",
        auto_commit: bool = True,
    ) -> int:
        """
        Delete multiple objects by their IDs.

        Args:
            obj_ids (Sequence[str | int | uuid.UUID]): The IDs of the objects to delete.
            id_column_name (str): The name of the ID column in the model.
            auto_commit (bool): Whether to commit the transaction. Pass False when
                deps layer coordinates multi-step transactions.

        Returns:
            deleted_count (int): The number of physical rows deleted. When
                ``id_column_name`` refers to a non-unique column this can
                exceed ``len(obj_ids)``.

        Raises:
            ValueError: If the id_column_name doesn't exist on the model.
        """
        if not obj_ids:
            return 0

        self._validate_column_exists(id_column_name)
        id_column = getattr(self.model, id_column_name)
        stmt = delete(self.model).where(id_column.in_(obj_ids)).returning(id_column)
        result = await self.session.execute(stmt)
        deleted_count = len(result.scalars().all())
        if auto_commit:
            await self.session.commit()

        return deleted_count

    async def custom_query(
        self,
        query: str,
        params: dict[str, Any] | None = None,
    ) -> Result[Any]:
        """
        Execute a custom parameterized SQL query.

        SECURITY WARNING: Always use parameterized queries to prevent SQL injection.
        Never concatenate user input directly into the query string.

        Args:
            query (str): The SQL query with named parameters (e.g., "SELECT * FROM users WHERE id = :user_id")
            params (dict[str, Any] | None): Dictionary of parameter names to values

        Returns:
            result (Result): The result of the executed query.

        Example:
            await repo.custom_query(
                "SELECT * FROM users WHERE email = :email AND status = :status",
                {"email": user_email, "status": "active"}
            )

        Reference:
            https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html
        """
        stmt = text(query)
        if params:
            stmt = stmt.bindparams(**params)
        return await self.session.execute(stmt)
