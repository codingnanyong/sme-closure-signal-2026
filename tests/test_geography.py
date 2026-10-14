import struct

import pytest

from sme_closure_signal.geography import read_dbf


def test_dbf_character_codes_preserve_leading_zeros_and_decode_korean():
    columns = [("AREA", "C", 6), ("NAME", "C", 12), ("SIZE", "N", 5)]
    header_length = 33 + 32 * len(columns)
    row_length = 1 + sum(c[2] for c in columns)
    payload = bytearray(header_length + row_length)
    struct.pack_into("<IHH", payload, 4, 1, header_length, row_length)
    for i, (name, kind, width) in enumerate(columns):
        offset = 32 + 32 * i
        payload[offset:offset + len(name)] = name.encode()
        payload[offset + 11], payload[offset + 16] = ord(kind), width
    payload[header_length - 1] = 13
    payload[header_length:] = b" " + b"001234" + "종로구".encode().ljust(12) + b"  123"
    frame = read_dbf(bytes(payload), "utf-8")
    assert frame.iloc[0].to_dict() == {"AREA": "001234", "NAME": "종로구", "SIZE": 123.0}
    with pytest.raises(ValueError, match="길이"):
        read_dbf(bytes(payload[:-1]), "utf-8")
