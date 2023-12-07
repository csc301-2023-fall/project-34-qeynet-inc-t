from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, Row
from sqlalchemy import select, insert, update, delete
from sqlalchemy.orm import sessionmaker

from astra.data.database.db_initializer import (
    initialize_sqlite_db,
    Device,
    Tag,
    Alarm,
    Data,
)

# Docstring types have not been corrected in the latest change,
# since those will be going away anyway.
# TODO: put docstrings in the correct format


# auto initialize the database
# an Engine, which the Session will use for connection
engine = initialize_sqlite_db()

# a sessionmaker factory that will create new Session objects
Session = sessionmaker(engine, expire_on_commit=False)


def create_update_tag(tag_name: str, tag_parameter: dict, device_id: int):
    """
        create (if not exist) or update the tag in database
        tag exists means the combination of tag_name and device_id
        exists in database
    Args:
        tag_name (str): the name of the tag
        tag_parameter (dict): the parameter of the tag
        device_id (int): the id of the device
    """
    with Session.begin() as session:
        # check if tag exists in database
        check_stmt = select(Tag).where(
            Tag.tag_name == tag_name,
            Tag.device_id == device_id,
        )
        tag_exist = session.execute(check_stmt).first()
        if tag_exist:
            # update tag parameter
            update_stmt = (
                update(Tag)
                .where(
                    Tag.tag_name == tag_name,
                    Tag.device_id == device_id,
                )
                .values(
                    tag_parameter=tag_parameter,
                )
            )
            session.execute(update_stmt)
        else:
            # create a new tag in database
            create_stmt = insert(Tag).values(
                tag_name=tag_name,
                tag_parameter=tag_parameter,
                device_id=device_id,
            )
            session.execute(create_stmt)


def create_update_device(metadata: dict):
    """
        create (if not exist) or update the device in database
    Args:
        metadata (_type_): metadata of the configuration file
    """
    device_id = None
    device = get_device(metadata["device"])
    with Session.begin() as session:
        # check if device exists in database
        if device:
            device_id = device.device_id
            # update device description
            update_stmt = (
                update(Device)
                .where(Device.device_name == metadata["device"])
                .values(
                    device_description=metadata["description"],
                )
            )
            session.execute(update_stmt)
        else:
            # create a new device in database
            new_device = Device(
                device_name=metadata["device"],
                device_description=metadata["description"],
            )
            session.add(new_device)

    if device_id is None:
        device_id = new_device.device_id

    return device_id


def create_update_alarm(dictionary_of_alarms: dict, device_id: int):
    """
        if alarm for the device exists in database, delete the old alarm and
        create new alarms in database based on the dictionary of alarms
    Args:
        dictionary_of_alarms (dict): a dictionary that contains the alarm's
                                     criticality and data
        device_id (int): the id of the device
    """
    with Session.begin() as session:
        # check if alarm for the device exists in database
        check_stmt = select(Alarm).where(
            Alarm.device_id == device_id,
        )
        alarm_exist = session.execute(check_stmt).first()
        if alarm_exist:
            # delete the old alarm
            delete_stmt = delete(Alarm).where(Alarm.device_id == device_id)
            session.execute(delete_stmt)

        # create new alarms in database
        alarm_list = []
        for alarm_dict in dictionary_of_alarms:
            alarm = Alarm(
                alarm_criticality=alarm_dict["criticality"],
                alarm_data=alarm_dict["event"],
                device_id=device_id,
            )
            alarm_list.append(alarm)
        session.add_all(alarm_list)


def get_device(device_name: str) -> Device | None:
    """
        check if device exists in database and return the device
    Args:
        device_name (str): the name of the device

    Returns:
        Device | None: the device with the given name, or None if none exists
    """
    with Session.begin() as session:
        # check if device exists in database
        device_exist = (
            session.query(Device)
            .filter(Device.device_name == device_name)
            .first()
        )
        return None if device_exist is None else device_exist


def device_exists(device_name: str) -> bool:
    """
        check if device exists in database
    Args:
        device_name (str): the name of the device

    Returns:
        bool: True if device exists in database, False otherwise
    """
    return get_device(device_name) is not None


def get_tags_for_device(device_name: str) -> Sequence[Row[tuple[str, dict]]]:
    """
        return all tags for the given device
    Args:
        device_name (str): the name of the device

    Returns:
        list[tuple[str, dict]]: a list of tuples of (tag_name, tag_parameter)
    """
    with Session.begin() as session:
        select_stmt = (
            select(Tag.tag_name, Tag.tag_parameter)
            .where(Tag.device_id == Device.device_id)
            .where(Device.device_name == device_name)
        )
        return session.execute(select_stmt).all()


def get_alarm_base_info(device_name: str) -> Sequence[Row[tuple[str, dict]]]:
    """
        return all alarm info for the given device
    Args:
        device_name (str): the name of the device

    Returns:
        list[tuple[str, dict]]: a list of tuples of (alarm_criticality, alarm_data)
    """
    with Session.begin() as session:
        select_stmt = (
            select(Alarm.alarm_criticality, Alarm.alarm_data)
            .where(Alarm.device_id == Device.device_id)
            .where(Device.device_name == device_name)
        )
        return session.execute(select_stmt).all()


def get_tag_id_name(device_name: str) -> Sequence[Row[tuple[int, str]]]:
    """
        A helper function that fetches the tags for a device and
        converts that to a list of (tag_id, tag_name)
    Args:
        device_name (str): the name of the device
    Returns:
        list[tuple[int, str]]: a list of tuples of (tag_id, tag_name)
    """
    with Session.begin() as session:
        tag_id_name = (
            session.query(Tag.tag_id, Tag.tag_name)
            .filter(Tag.device_id == Device.device_id)
            .filter(Device.device_name == device_name)
        )
        return tag_id_name.all()


def num_telemetry_frames(
    device_name: str, start_time: datetime | None, end_time: datetime | None
) -> int:
    """
        Number of telemetry frames for a device between start_time and end_time
        For this function and all below functions: if start_time/end_time is None,
        treat as if there are no restrictions in the relevant direction.
    Args:
        device_name (str): name of the device
        start_time (datetime | None): the start time of the data
        end_time (datetime | None): the end time of the data

    Returns:
        int: the number of telemetry frames for the given device between
             start_time and end_time
    """
    device = get_device(device_name)
    with Session.begin() as session:
        if device:
            device_name = device.device_name
            # tag_id_name = get_tag_id_name(device_name)
            # tag_ids = [tag_id for tag_id, _ in tag_id_name]
            select_stmt = select(func.count(Data.timestamp.distinct())).where(
                Device.device_name == device_name,
                Tag.device_id == Device.device_id,
                Tag.tag_id == Data.tag_id,
            )
            if start_time is not None:
                select_stmt = select_stmt.where(Data.timestamp >= start_time)
            if end_time is not None:
                select_stmt = select_stmt.where(Data.timestamp <= end_time)
            result = session.execute(select_stmt).scalar()
            assert result is not None  # The way the query is constructed, shouldn't ever be None
            return result
        else:
            raise ValueError("Device does not exist in database")


def get_telemetry_data_by_index(
    device_name: str,
    tags: set[str] | None,
    start_time: datetime | None,
    end_time: datetime | None,
    index: int,
) -> tuple[Sequence[Row[tuple[str, float | None]]], datetime]:
    """
        All the data for the telemetry frame with the <index>th timestamp
        for a device between start_time and end_time.
        May assume: 0 <= <index> < <number of timestamps>
    Args:
        device_name (str): name of the device
        tags (set[str]): set of tags for the data to be returned
        start_time (datetime | None): the start time of the data
        end_time (datetime | None): the end time of the data
        index (int): the index of the timestamp

    Returns:
        tuple[list[tuple[str, float]], datetime]: a tuple that contains
         1. a list of tuple (tag_name, value) for the given device/tags with the
            given timestamp
         2. the timestamp for the data
    """
    device = get_device(device_name)
    if device:
        with Session.begin() as session:
            device_name = device.device_name
            sub_query = (
                session.query(Data.timestamp.label("timestamp"))
                .join(Data.tag)
                .join(Tag.device)
                .filter(
                    Device.device_name == device_name,
                )
                .group_by(Data.timestamp)
                .order_by(Data.timestamp)
            )
            # Check the range of the timestamp
            if start_time is not None:
                sub_query = sub_query.filter(Data.timestamp >= start_time)
            if end_time is not None:
                sub_query = sub_query.filter(Data.timestamp <= end_time)
            timestamp = sub_query.limit(1).offset(index).scalar()

            query = (
                session.query(Tag.tag_name, Data.value)
                .join(Data.tag)
                .join(Tag.device)
                .filter(
                    Device.device_name == device_name,
                    Data.timestamp == timestamp,
                )
            )

            if tags is not None:
                query = query.filter(Tag.tag_name.in_(tags))

            return query.all(), timestamp
    else:
        raise ValueError("Device does not exist in database")


def get_telemetry_data_by_tag(
    device_name: str,
    start_time: datetime | None,
    end_time: datetime | None,
    tag: str,
    step: int = 1,
) -> Sequence[Row[tuple[float, datetime]]]:
    """
        Every <step>th data for the given tag for a device between
        start_time and end_time
        Should be sorted by time -- 0 earliest, <num frames> - 1 latest
        May assume: tag exists for the given device
    Args:
        device_name (str): name of the device
        start_time (datetime | None): the start time of the data
        end_time (datetime | None): the end time of the data
        tag (str): the tag of the data
        step (int): the step of choosing the data within the given time range

    Returns:
        list[tuple[float, datetime]]:
            a list of tuple (value, timestamp) for the given device/tag between
            start_time and end_time
    """
    device = get_device(device_name)
    with Session.begin() as session:
        if device:
            device_id = device.device_id
            sub_query = session.query(
                Data.value.label("value"),
                Data.timestamp.label("timestamp"),
                func.row_number()
                .over(partition_by=Data.tag_id, order_by=Data.timestamp)
                .label("row_number"),
            ).filter(
                Data.tag_id == Tag.tag_id,
                Tag.device_id == device_id,
                Tag.tag_name == tag,
            )

            if start_time is not None:
                sub_query = sub_query.filter(Data.timestamp >= start_time)
            if end_time is not None:
                sub_query = sub_query.filter(Data.timestamp <= end_time)

            sub_query_alias = sub_query.subquery()

            query = session.query(
                sub_query_alias.c.value, sub_query_alias.c.timestamp
            ).filter((sub_query_alias.c.row_number - 1) % step == 0)

            return query.all()
        else:
            raise ValueError("Device does not exist in database")


def get_device_data() -> list[tuple[str, str]]:
    """
        Return all the names and descriptions of devices in the database
    Returns:
        list[tuple[str, str]]: a list of (device name, device description) tuples
    """
    with Session.begin() as session:
        select_stmt = select(Device.device_name, Device.device_description)
        return [(name, description) for name, description in session.execute(select_stmt)]


def delete_device(device_name: str) -> None:
    """
        Delete the device with the given name from the database
        Note that all the corresponding tags and data will be deleted as well
    Args:
        device_name (str): the name of the device
    """
    device = get_device(device_name)
    with Session.begin() as session:
        if device:
            delete_stmt = delete(Device).where(
                Device.device_name == device_name
            )
            session.execute(delete_stmt)
        else:
            raise ValueError("Device does not exist in database")


if __name__ == "__main__":
    # a = get_timestamp_by_index(
    #     "DF71ZLMI9W",
    #     "2023-10-11 19:32:43.000000",
    #     "2023-10-11 19:33:32.000000",
    #     5,
    # )
    # print(a)
    # b = get_telemetry_data_by_timestamp("DF71ZLMI9W", None, a)
    # print(b)
    # c = get_telemetry_data_by_tag("DF71ZLMI9W", a, None, "XXTT3038")
    # for cc in c:
    #     print(cc[0], cc[1])
    d = get_tags_for_device("DF71ZLMI9W")
    # for dd in d:
    #     print(dd)
    # e = num_telemetry_frames("DF71ZLMI9W", a, None)
    # print(e)

    # f should not pass unless we uncomment the lazy="selectin"
    # line in db_initializer.py
    # f = get_device("DF71ZLMI9W")
    # for ff in f._tags:
    #     print(ff.tag_name)
