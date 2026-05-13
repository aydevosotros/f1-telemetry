from struct import pack
from types import SimpleNamespace

from f1_telemetry.ingest.parser import F125PacketParser


def test_packet_id_reads_2025_header() -> None:
    payload = bytearray(32)
    payload[0:2] = pack("<H", 2025)
    payload[6] = 6

    assert F125PacketParser().packet_id(bytes(payload)) == 6


def test_packet_id_rejects_other_format() -> None:
    payload = bytearray(32)
    payload[0:2] = pack("<H", 2024)
    payload[6] = 6

    assert F125PacketParser().packet_id(bytes(payload)) is None


def test_samples_from_packet_includes_lap_context() -> None:
    packet = SimpleNamespace(
        header=SimpleNamespace(session_time=91.5),
        car_telemetry_data=[
            SimpleNamespace(
                speed=240,
                throttle=0.8,
                brake=0.0,
                steer=0.1,
                gear=7,
                engine_rpm=11900,
                drs=1,
                current_lap_num=3,
                lap_distance=1250.5,
            )
        ],
    )

    sample = F125PacketParser()._samples_from_packet(packet)[0]

    assert sample.lap_number == 3
    assert sample.lap_distance == 1250.5


def test_laps_from_packet_reads_lap_packet_context() -> None:
    packet = SimpleNamespace(
        lap_data=[
            SimpleNamespace(current_lap_num=4, lap_distance=1400.25),
            SimpleNamespace(current_lap_num=5, lap_distance=23.5),
        ]
    )

    laps = F125PacketParser()._laps_from_packet(packet)

    assert laps[0].lap_number == 4
    assert laps[0].lap_distance == 1400.25
    assert laps[1].car_index == 1


def test_drivers_from_packet_reads_participant_names() -> None:
    packet = SimpleNamespace(
        num_active_cars=2,
        participants=[
            SimpleNamespace(name=b"ALONSO\x00\x00", team_id=3),
            SimpleNamespace(name=b"VERSTAPPEN\x00", team_id=1),
            SimpleNamespace(name=b"unused", team_id=9),
        ],
    )

    drivers = F125PacketParser()._drivers_from_packet(packet)

    assert [driver.driver_name for driver in drivers] == ["ALONSO", "VERSTAPPEN"]
    assert drivers[0].car_index == 0
    assert drivers[0].team_id == 3


def test_game_session_from_packet_reads_header_and_session_data() -> None:
    packet = SimpleNamespace(
        header=SimpleNamespace(session_uid=123456, session_time=1.5),
        session_type=5,
        track_id=10,
        track_length=7004,
    )

    game_session = F125PacketParser()._game_session_from_packet(packet)

    assert game_session is not None
    assert game_session.session_uid == 123456
    assert game_session.session_type == 5
    assert game_session.track_id == 10
    assert game_session.track_length == 7004
