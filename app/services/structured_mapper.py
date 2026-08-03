from typing import Type, TypeVar, Any
from sqlalchemy.inspection import inspect

T = TypeVar("T")


class StructuredDataMapper:
    """
    Generic mapper to convert extracted JSON data
    into SQLAlchemy model instances.
    """

    @staticmethod
    def map_to_model(
        model_class: Type[T],
        data: dict[str, Any],
        extra_fields: dict[str, Any] | None = None,
    ) -> T:
        """
        Map JSON dictionary into SQLAlchemy model.

        Example:
        MedicalVisit(
            doctor_name="John",
            visit_date="2026-08-01"
        )
        """

        model_columns = {
            column.key
            for column in inspect(model_class).mapper.column_attrs
        }

        filtered_data = {
            key: value
            for key, value in data.items()
            if key in model_columns
        }

        if extra_fields:
            filtered_data.update(extra_fields)

        return model_class(**filtered_data)