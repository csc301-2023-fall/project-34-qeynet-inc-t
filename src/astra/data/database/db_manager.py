from astra.data.database.db_initializer import initialize_sqlite_db, Device, Tag, Alarm, Data
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, insert, update, delete
from datetime import datetime

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
    device = device_exists(metadata["device"])
    with Session.begin() as session:
        # check if device exists in database
        if device:
            device = device[0]
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


def device_exists(device_name: str) -> [Device | None]:
    """
        check if device exists in database
    Args:
        device_name (str): the name of the device

    Returns:
        bool: return true if device exists in database
    """
    with Session.begin() as session:
        # check if device exists in database
        check_stmt = select(Device).where(Device.device_name == device_name)
        device_exist = session.execute(check_stmt).first()
        return None if device_exist is None else device_exist


def get_device(device_name: str) -> Device | None:
    """
        get device if it exists
    Args:
        device_name (str): the name of the device

    Returns:
        Device | None: the device with the given name, or None if none exists
    """
    with Session.begin() as session:
        check_stmt = select(Device).where(Device.device_name == device_name)
        return session.execute(check_stmt).scalar()


def get_tags_for_device(device_name: str) -> list[Tag]:
    """
        return all tags for the given device
    Args:
        device_name (str): the name of the device

    Returns:
        list[Tag]: a list of tags for the given device
    """
    with Session.begin() as session:
        check_stmt = select(Device).where(Device.device_name == device_name)
        device = session.execute(check_stmt).first()
        if device:
            return device[0].tags
        else:
            return []


def tags_to_tag_ids(device_name: str) -> list[int]:
    """
        A helper function that fetches the tags for a device and
        converts that to a list of tag_ids
    Args:
        device_name (str): the name of the device
    Returns:
        list[int]: a list of tag_ids
    """
    tags = get_tags_for_device(device_name)
    tag_ids = []
    for tag in tags:
        tag_ids.append(tag.tag_id)
    return tag_ids


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
    device = device_exists(device_name)
    with Session.begin() as session:
        if device:
            device_name = device[0].device_name
            tag_ids = tags_to_tag_ids(device_name)
            # TODO: I know it's ugly to have if-else, feel free to modify here
            if start_time is None and end_time is None:
                # TODO: may add a maximum number of frames returned
                select_stmt = select(Data).where(Data.tag_id.in_(tag_ids))
            elif start_time is None:
                select_stmt = (
                    select(Data)
                    .where(Data.tag_id.in_(tag_ids))
                    .where(Data.timestamp <= end_time)
                )
            elif end_time is None:
                select_stmt = (
                    select(Data)
                    .where(Data.tag_id.in_(tag_ids))
                    .where(Data.timestamp >= start_time)
                )
            else:
                select_stmt = (
                    select(Data)
                    .where(Data.tag_id.in_(tag_ids))
                    .where(Data.timestamp >= start_time)
                    .where(Data.timestamp <= end_time)
                )
            return len(session.execute(select_stmt).all())
        else:
            raise ValueError("Device does not exist in database")


def get_timestamp_by_index(
    device_name: str,
    start_time: datetime | None,
    end_time: datetime | None,
    index: int,
) -> datetime:
    """
        The <index>th timestamp for a device between start_time and end_time
        May assume: 0 <= <index> < <number of timestamps>
    Args:
        device_name (str): name of the device
        start_time (datetime | None): the start time of the data
        end_time (datetime | None): the end time of the data
        index (int): the index of the timestamp
                     (unlike the array index, this starts from 1)
                     # TODO: may change to start from 0

    Returns:
        datetime: the ith timestamp for the given device between start_time
                  and end_time
    """
    device = device_exists(device_name)
    with Session.begin() as session:
        if device:
            device_name = device[0].device_name
            tag_ids = tags_to_tag_ids(device_name)
            # TODO: I know it's ugly to have if-else, feel free to modify here
            if start_time is None and end_time is None:
                # TODO: may add a maximum number of frames returned
                select_stmt = (
                    select(Data.timestamp)
                    .where(Data.tag_id.in_(tag_ids))
                    .group_by(Data.timestamp)
                    .order_by(Data.timestamp)
                    .limit(index)
                )
            elif start_time is None:
                select_stmt = (
                    select(Data.timestamp)
                    .where(Data.tag_id.in_(tag_ids))
                    .group_by(Data.timestamp)
                    .having(Data.timestamp <= end_time)
                    .order_by(Data.timestamp)
                    .limit(index)
                )
            elif end_time is None:
                select_stmt = (
                    select(Data.timestamp)
                    .where(Data.tag_id.in_(tag_ids))
                    .group_by(Data.timestamp)
                    .having(Data.timestamp >= start_time)
                    .order_by(Data.timestamp)
                    .limit(index)
                )
            else:
                select_stmt = (
                    select(Data.timestamp)
                    .where(Data.tag_id.in_(tag_ids))
                    .group_by(Data.timestamp)
                    .having(Data.timestamp >= start_time)
                    .having(Data.timestamp <= end_time)
                    .order_by(Data.timestamp)
                    .limit(index)
                )
            return session.execute(select_stmt).all()[-1][0]
        else:
            raise ValueError("Device does not exist in database")


def get_telemetry_data_by_timestamp(
    device_name: str, tags: set[str], timestamp: datetime
) -> list[Data]:
    """
        All the data for the telemetry frame with the given timestamp for a device.
        May assume: timestamp is valid for the device
    Args:
        device_name (str): name of the device
        tags (set[str]): set of tags for the data to be returned
        timestamp (datetime): the timestamp of the data

    Returns:
        list[Data]: a list of data for the given device/tags with the given timestamp
    """
    device = device_exists(device_name)
    with Session.begin() as session:
        if device:
            device_name = device[0].device_name
            if tags is not None:
                tag_ids = []
                for tag in tags:
                    tag_ids.append(tag.tag_id)
                select_stmt = (
                    select(Data)
                    .where(Data.timestamp == timestamp)
                    .where(Data.tag_id.in_(tag_ids))
                )
            else:
                tag_ids = tags_to_tag_ids(device_name)
                select_stmt = (
                    select(Data)
                    .where(Data.tag_id.in_(tag_ids))
                    .where(Data.timestamp == timestamp)
                )
            return session.execute(select_stmt).all()
        else:
            raise ValueError("Device does not exist in database")


def get_telemetry_data_by_tag(
    device_name: str,
    start_time: datetime | None,
    end_time: datetime | None,
    tag: str,
) -> list[Data]:
    """
        All the data for the given tag for a device between start_time and end_time
        Should be sorted by time -- 0 earliest, <num frames> - 1 latest
        May assume: tag exists for the given device
    Args:
        device_name (str): name of the device
        start_time (datetime | None): the start time of the data
        end_time (datetime | None): the end time of the data
        tag (str): the tag of the data

    Returns:
        list[Data]: a list of data for the given device/tag between start_time
                    and end_time
    """
    device = device_exists(device_name)
    with Session.begin() as session:
        if device:
            device_id = device[0].device_id
            select_stmt = (
                select(Tag)
                .where(Tag.tag_name == tag)
                .where(Tag.device_id == device_id)
            )
            tag_obj = session.execute(select_stmt).all()[0][0]
            # TODO: I know it's ugly to have if-else, feel free to modify here
            if start_time is None and end_time is None:
                # TODO: may add a maximum number of frames returned
                return tag_obj.data
            elif start_time is None:
                return tag_obj.data.filter(Data.timestamp <= end_time)
            elif end_time is None:
                return tag_obj.data.filter(Data.timestamp >= start_time)
            else:
                return tag_obj.data.filter(
                    Data.timestamp >= start_time,
                    Data.timestamp <= end_time,
                )
        else:
            raise ValueError("Device does not exist in database")


if __name__ == "__main__":
    a = get_timestamp_by_index(
        "DF71ZLMI9W",
        "2023-10-11 19:32:43.000000",
        "2023-10-11 19:33:32.000000",
        1,
    )
    # print(a)
    # b = get_telemetry_data_by_timestamp("DF71ZLMI9W", None, a)
    # print(b)
    # c = get_telemetry_data_by_tag("DF71ZLMI9W", None, None, "XXTT3038")
    # print(c)
