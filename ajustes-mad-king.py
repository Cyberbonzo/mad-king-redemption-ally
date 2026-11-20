"""Salvamento automático e pulo triplo para Mad King Redemption, build Steam 26417954."""
import argparse
from base64 import b64decode
from hashlib import sha256
import os
from pathlib import Path
import shutil
import struct
import tempfile


SUPPORTED = {
    "d6b24b170ae1b7dbcefaceeef08f9e03866df913feba0b5ac9133ac0252cf1cd",
    "10b0103e565a16274563a5775a06423d5e623cb858896571da8e306ff3d0d8ce",
}
CODE_RVA = 0x4842000
GOLD_RVA = 0x48420e0
JUMP_RCX_RVA = 0x4842140
JUMP_RDX_RVA = 0x484214b
MACHINE_CODE = b64decode(
    "SIPEQF+APSqxlv8AD4TEAAAASIsFTxxy/0iLgLgAAABIi0AQSIXAD4SpAAAASIN4EAAPhJ4A"
    "AABIi4hAAQAASIXJD4SOAAAAgHl5AQ+FhAAAAEyLWVBNhdt0e0iLUHhIhdJ0cotSSEUxwIA9"
    "jqeW/wB0L0yLBQZIa/9Ni4C4AAAATYsATYXAdBlNi4DYAAAATYXAdA1Ni0B4TYXAdARFi0A4"
    "TI0Nt5jC/0k5AXUSTTlZCHUMQTlREHUGRTlBFHQWSYkBTYlZCEGJURBFiUEUMdLpGqTx+8PM"
    "zMzMzMzMzMyAPU+wlv8AdFJIiwV4G3L/SIuAuAAAAEiLQBBIhcB0O0g5BVmYwv91MkiDeBAA"
    "dCtIObBAAQAAdSKAfnkBdRxIi1ZQSIXSdBNIORU5mML/dQpIi0B4SIXAdAHD6ZA26/vHgYwD"
    "AAADAAAAw8eCjAMAAAMAAADD"
)


def edit(data, offset, before, after):
    if len(before) != len(after) or data[offset:offset + len(before)] != before:
        raise ValueError(f"Bytes incompatíveis em {offset:#x}.")
    data[offset:offset + len(before)] = after


def branch(opcode, offset, expected, target):
    source_rva = offset + 0xE00
    return bytes((opcode,)) + struct.pack("<i", target - source_rva - 5) + b"\x90" * (len(expected) - 5)


def patch(data):
    if sha256(data).hexdigest() not in SUPPORTED:
        raise ValueError("GameAssembly.dll incompatível com o build Steam 26417954.")
    result = bytearray(data)
    # Add an RX section for the helpers. The small volatile snapshot fits
    # between the end of .data and the next section without moving any RVAs.
    raw_size = (len(MACHINE_CODE) + 0x1FF) & ~0x1FF
    if len(data) % 0x200:
        raise ValueError("O tamanho original da DLL não está alinhado.")
    section = struct.pack(
        "<8s6I2HI", b".mkrsave", len(MACHINE_CODE), CODE_RVA,
        raw_size, len(data), 0, 0, 0, 0, 0x60000020,
    )
    code_size = struct.unpack_from("<I", data, 0x13C)[0]
    edit(result, 0x126, b"\x07\x00", b"\x08\x00")
    edit(result, 0x13C, struct.pack("<I", code_size), struct.pack("<I", code_size + raw_size))
    edit(result, 0x170, struct.pack("<I", CODE_RVA), struct.pack("<I", CODE_RVA + 0x1000))
    edit(result, 0x2A8, struct.pack("<I", 0x635960), struct.pack("<I", 0x635978))
    edit(result, 0x340, bytes(40), section)

    # Update and SaveGame hooks, then the normal grounded movement resets.
    for offset, opcode, expected, target in (
        (0x825A7C, 0xE9, bytes.fromhex("48 83 c4 40 5f c3"), CODE_RVA),
        (0x75B8BD, 0xE8, bytes.fromhex("e8 0e 91 f9 ff"), GOLD_RVA),
        (0x62DB31, 0xE8, bytes.fromhex("89 81 8c 03 00 00"), JUMP_RCX_RVA),  # Idle
        (0x632E50, 0xE8, bytes.fromhex("89 81 8c 03 00 00"), JUMP_RCX_RVA),  # Mount_walking
        (0x63E3A0, 0xE8, bytes.fromhex("89 82 8c 03 00 00"), JUMP_RDX_RVA),  # Walking
    ):
        edit(result, offset, expected, branch(opcode, offset, expected, target))
    result.extend(MACHINE_CODE.ljust(raw_size, b"\0"))
    return result


def backup_once(target, backup, source):
    if not backup.exists():
        backup.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.link(target, backup)
        except OSError:
            with backup.open("xb") as out:
                out.write(source)
                out.flush()
                os.fsync(out.fileno())
    if backup.read_bytes() != source:
        raise ValueError("O backup da DLL é diferente da versão de origem.")


def replace(target, expected, desired):
    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as out:
        staged = Path(out.name)
        try:
            out.write(desired)
            out.flush()
            os.fsync(out.fileno())
        except BaseException:
            out.close()
            staged.unlink(missing_ok=True)
            raise
    try:
        shutil.copymode(target, staged)
        if target.read_bytes() != expected or staged.read_bytes() != desired:
            raise ValueError("Falha ao conferir a DLL antes de instalar.")
        os.replace(staged, target)
    finally:
        staged.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path)
    parser.add_argument("backup", type=Path)
    parser.add_argument("--restore", action="store_true")
    args = parser.parse_args()
    target, backup = args.target.resolve(), args.backup.resolve()
    if target == backup:
        parser.error("O backup precisa ser um arquivo separado da DLL ativa.")
    current = target.read_bytes()
    baseline = backup.read_bytes() if backup.exists() else current
    patched = patch(baseline)
    if current not in (baseline, patched):
        raise ValueError("A DLL ativa foi alterada após a criação do backup.")
    desired = baseline if args.restore else patched
    if current == desired:
        return
    backup_once(target, backup, baseline)
    replace(target, current, desired)


if __name__ == "__main__":
    main()

