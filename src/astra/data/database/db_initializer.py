"""
This module initializes the database and provides the schema for the tables.
"""
from datetime import datetime
from sqlalchemy import (
    create_engine,
    ForeignKey,
)
from sqlalchemy.orm import (
    declarative_base,
    Mapped,
    mapped_column,
    relationship,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.schema import UniqueConstraint

# A declarative base class that helps mapping to the relational schema
Base = declarative_base()


def initialize_sqlite_db():
    """initializes the sqlite database and creates the tables

    Returns:
        an Engine, which the Session will use for connection
    """
    engine = create_engine("sqlite:///astra.db")
    Base.metadata.create_all(engine)
    return engine


class Device(Base):
    """A table that holds the device data.

        device_id (int): unique id for device (primary key)
        device_name (Optional[str | None]): device name
        device_description (Optional[str | None]): device description
        tags (Set["Tag"]): tags of the device (one-to-many relationship)
        alarms (Set["Alarm"]): alarms of the device (one-to-many relationship)

    Args:
        Base: a declarative base class that helps mapping to the relational
              schema
    """

    __tablename__ = "Device"

    device_id: Mapped[int] = mapped_column(primary_key=True)
    device_name: Mapped[str | None] = mapped_column(unique=True)
    device_description: Mapped[str | None] = mapped_column()

    # one-to-many relationship
    _tags: Mapped[set["Tag"]] = relationship(
        "Tag",
        back_populates="_device",
        cascade="all, delete",
        passive_deletes=True,
        # lazy="selectin",
        # TODO: uncomment this when we need to access the
        #       tags outside the session
    )
    _alarms: Mapped[set["Alarm"]] = relationship(
        "Alarm",
        back_populates="_device",
        cascade="all, delete",
        passive_deletes=True,
    )


class Tag(Base):
    """A table that holds the tag data.

         tag_id (int): unique id for tag
         tag_name (str): tag name
         tag_parameter ()
         device_id (int): unique id for device (foreign key)
         device (Device): device of the tag (many-to-one relationship)
         data (List["Data"]): data of the tag (one-to-many relationship

    Args:
        Base: a declarative base class that helps mapping to the relational
              schema
    """

    __tablename__ = "Tag"

    tag_id: Mapped[int] = mapped_column(primary_key=True)

    # foreign key & many-to-one relationship
    device_id: Mapped[int] = mapped_column(
        ForeignKey("Device.device_id", ondelete="CASCADE")
    )
    _device: Mapped["Device"] = relationship(back_populates="_tags")

    tag_name: Mapped[str]
    tag_parameter: Mapped[dict] = mapped_column(JSON)

    # one-to-many relationship
    _data: Mapped[list["Data"]] = relationship(
        "Data",
        back_populates="_tag",
        cascade="all, delete",
        passive_deletes=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "tag_name", "device_id", name="tag_device_unique_constraint"
        ),
    )


class Alarm(Base):
    """A table that holds the alarm data.

        alarm_id (int): unique id for alarm (primary key)
        alarm_criticality (str): criticality of the alarm
                                 (Warning, Low, Medium, High, Critical)
        device_id (int): unique id for device (foreign key)
        device (Device): device of the alarm (many-to-one relationship)

    Args:
        Base: a declarative base class that helps mapping to the relational
              schema
    """

    __tablename__ = "Alarm"
    alarm_id: Mapped[int] = mapped_column(primary_key=True)

    # foreign key & many-to-one relationship
    device_id: Mapped[int] = mapped_column(
        ForeignKey("Device.device_id", ondelete="CASCADE")
    )
    _device: Mapped["Device"] = relationship(back_populates="_alarms")

    alarm_criticality: Mapped[str]
    alarm_data: Mapped[dict] = mapped_column(JSON)


class Data(Base):
    """A table that holds the data for the tags with timestamps.

        data_id (int): unique id for data (primary key)
        timestamp (datetime): timestamp of the data
        value (float | None): raw value of the data (before conversion)
        last_modified (datetime): last modified date of the data
        tag_id (int): unique id for tag (foreign key)
        tag (Tag): tag of the data (many-to-one relationship)

    Args:
        Base: a declarative base class that helps mapping to the relational
              schema
    """

    __tablename__ = "Data"

    data_id: Mapped[int] = mapped_column(primary_key=True)

    # foreign key & many-to-one relationship
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("Tag.tag_id", ondelete="CASCADE")
    )
    _tag: Mapped["Tag"] = relationship(back_populates="_data")

    timestamp: Mapped[datetime]
    value: Mapped[float | None]
    last_modified: Mapped[datetime] = mapped_column()
    # last_modified: Mapped[datetime] = mapped_column(
    #     DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    # )


if __name__ == "__main__":
    initialize_sqlite_db()
