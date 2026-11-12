from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, JSONType


class Setting(Base):
    """Key/value settings. `pass_mark` holds the global quiz threshold."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(primary_key=True)
    value: Mapped[object] = mapped_column(JSONType)
