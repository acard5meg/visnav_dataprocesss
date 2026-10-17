from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Tuple

from rosbags.highlevel import AnyReader


class ROSBagException(Exception):
    pass


@dataclass(frozen=True)
class _TopicInfo:
    msg_type: str
    message_count: int
    connections: int
    frequency: Optional[float]


class _RosbagTime:
    def __init__(self, timestamp_ns: int):
        self._timestamp_ns = int(timestamp_ns)

    def to_sec(self) -> float:
        return self._timestamp_ns / 1e9

    def to_time(self) -> float:
        return self.to_sec()


class Bag:
    def __init__(self, bag_path: str):
        self._bag_path = Path(bag_path)
        if not self._bag_path.exists():
            raise ROSBagException(f"Bag file does not exist: {self._bag_path}")

        self._reader = AnyReader([self._bag_path])
        try:
            self._reader.open()
        except Exception as exc:
            raise ROSBagException(str(exc)) from exc

        self._connections_by_topic: Dict[str, list] = defaultdict(list)
        for connection in self._reader.connections:
            self._connections_by_topic[connection.topic].append(connection)

    def close(self) -> None:
        self._reader.close()

    def __enter__(self) -> "Bag":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def get_message_count(self, topic: Optional[str] = None) -> int:
        if topic is None:
            return sum(conn.msgcount for conn in self._reader.connections)
        return sum(conn.msgcount for conn in self._connections_by_topic.get(topic, []))

    def get_start_time(self) -> float:
        return float(self._reader.start_time) / 1e9

    def read_messages(self, topics: Optional[Iterable[str]] = None) -> Iterator[Tuple[str, object, _RosbagTime]]:
        selected_connections = None
        if topics is not None:
            selected_connections = []
            for topic in topics:
                selected_connections.extend(self._connections_by_topic.get(topic, []))

        for connection, timestamp_ns, rawdata in self._reader.messages(connections=selected_connections):
            msg = self._reader.deserialize(rawdata, connection.msgtype)
            yield connection.topic, msg, _RosbagTime(timestamp_ns)

    def get_type_and_topic_info(self) -> Tuple[dict, dict]:
        type_info = {}
        topic_info = {}

        for topic, connections in self._connections_by_topic.items():
            if not connections:
                continue

            msg_type = connections[0].msgtype
            msg_count = sum(conn.msgcount for conn in connections)
            topic_info[topic] = _TopicInfo(
                msg_type=msg_type,
                message_count=msg_count,
                connections=len(connections),
                frequency=None,
            )
            type_info[msg_type] = msg_type

        return type_info, topic_info
