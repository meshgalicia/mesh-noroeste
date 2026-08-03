"""Pruebas del adaptador de MeshCore Map."""

from __future__ import annotations

from datetime import datetime, timezone
import unittest

import msgpack

from mesh_noroeste.meshcore_map import (
    MeshCoreMapError,
    parse_meshcore_map,
)


INSERTED_AT = datetime(
    2026,
    7,
    20,
    9,
    10,
    tzinfo=timezone.utc,
)

UPDATED_AT = datetime(
    2026,
    7,
    25,
    11,
    58,
    tzinfo=timezone.utc,
)

PUBLIC_KEY = bytes.fromhex("01" * 32)


def record(
    *,
    public_key: bytes = PUBLIC_KEY,
    node_type: int = 2,
) -> dict[str, object]:
    return {
        "pk": public_key,
        "t": node_type,
        "n": " Repetidor de prueba ",
        "id": INSERTED_AT,
        "la": datetime(
            1970,
            1,
            1,
            tzinfo=timezone.utc,
        ),
        "ud": UPDATED_AT,
        "lat": 43.1,
        "lon": -8.1,
        "p": {
            "freq": 869.618,
            "bw": 62.5,
            "sf": 8,
            "cr": 8,
        },
        "s": "u",
        "l": b"\x11\x00",
    }


def pack(records: object) -> bytes:
    return msgpack.packb(
        records,
        use_bin_type=True,
        datetime=True,
    )


class MeshCoreMapTests(unittest.TestCase):
    def test_valid_record_is_normalized(
        self,
    ) -> None:
        observations = parse_meshcore_map(
            pack([record()])
        )

        self.assertEqual(len(observations), 1)

        observation = observations[0]

        self.assertEqual(
            observation.id,
            "meshcore:" + "01" * 32,
        )
        self.assertEqual(
            observation.source,
            "meshcore_map",
        )
        self.assertEqual(
            observation.network,
            "meshcore",
        )
        self.assertEqual(
            observation.short_name,
            "Repetidor de prueba",
        )
        self.assertEqual(
            observation.node_type,
            "repeater",
        )
        self.assertEqual(
            observation.first_seen,
            "2026-07-20T09:10:00Z",
        )
        self.assertEqual(
            observation.observed_at,
            "2026-07-25T11:58:00Z",
        )
        self.assertEqual(
            observation.position_updated_at,
            "2026-07-25T11:58:00Z",
        )
        self.assertEqual(
            observation.latitude,
            43.1,
        )
        self.assertEqual(
            observation.longitude,
            -8.1,
        )
        self.assertEqual(
            observation.radio["frequency_mhz"],
            869.618,
        )
        self.assertEqual(
            observation.radio["bandwidth_khz"],
            62.5,
        )
        self.assertEqual(
            observation.radio["spreading_factor"],
            8,
        )
        self.assertEqual(
            observation.radio["coding_rate"],
            8,
        )

    def test_all_documented_node_types_are_mapped(
        self,
    ) -> None:
        expected = {
            1: "client",
            2: "repeater",
            3: "room_server",
            4: "sensor",
        }

        records = [
            record(
                public_key=bytes([code]) * 32,
                node_type=code,
            )
            for code in expected
        ]

        observations = parse_meshcore_map(
            pack(records)
        )

        self.assertEqual(
            [
                observation.node_type
                for observation in observations
            ],
            list(expected.values()),
        )

    def test_unknown_type_is_preserved_as_unknown(
        self,
    ) -> None:
        observation = parse_meshcore_map(
            pack([record(node_type=99)])
        )[0]

        self.assertEqual(
            observation.node_type,
            "unknown",
        )

    def test_last_advert_is_not_used_as_last_seen(
        self,
    ) -> None:
        observation = parse_meshcore_map(
            pack([record()])
        )[0]

        self.assertEqual(
            observation.observed_at,
            "2026-07-25T11:58:00Z",
        )
        self.assertNotEqual(
            observation.observed_at,
            "1970-01-01T00:00:00Z",
        )

    def test_invalid_public_key_is_rejected(
        self,
    ) -> None:
        invalid = record(
            public_key=b"\x01" * 31
        )

        with self.assertRaisesRegex(
            MeshCoreMapError,
            "pk debe contener 32 bytes",
        ):
            parse_meshcore_map(pack([invalid]))

    def test_invalid_root_is_rejected(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            MeshCoreMapError,
            "raíz.*lista",
        ):
            parse_meshcore_map(
                pack({"nodes": []})
            )

    def test_invalid_messagepack_is_rejected(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            MeshCoreMapError,
            "MessagePack válido",
        ):
            parse_meshcore_map(b"\xc1")
            

if __name__ == "__main__":
    unittest.main()
