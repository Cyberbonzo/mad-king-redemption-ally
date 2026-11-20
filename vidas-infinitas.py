"""Enable repeatable hero resurrection in Steam build 26417954."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import tempfile

ORIGINAL = "d6b24b170ae1b7dbcefaceeef08f9e03866df913feba0b5ac9133ac0252cf1cd"
EDITS = (
    # RecomputeInstanceStats uses max(1, calculated_resurrections).
    (0x62D739, "0f49f2", "eb1790"),
    (0x62D752, "cc" * 13, "83fa01be010000000f4ff2ebdd"),
    # The resurrection goes through normally, without spending a charge.
    (0x852FFE, "ff89e0000000", "909090909090"),
    (0x853010, "ff4168", "909090"),
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def patch(data):
    if digest(data) != ORIGINAL:
        raise ValueError("GameAssembly.dll incompatível com o build 26417954.")
    result = bytearray(data)
    for offset, expected, replacement in EDITS:
        before, after = bytes.fromhex(expected), bytes.fromhex(replacement)
        end = offset + len(before)
        if len(after) != len(before) or result[offset:end] != before:
            raise ValueError(f"Posição de patch inesperada: {offset:#x}")
        result[offset:end] = after
    return result


def apply(target, backup, restore):
    source = target.read_bytes()
    original = backup.read_bytes() if backup.exists() else source
    patched = patch(original)
    if source != original and source != patched:
        raise ValueError("O executável ativo mudou desde a criação do backup.")
    desired = original if restore else patched
    if source == desired:
        return
    if not backup.exists():
        backup.parent.mkdir(parents=True, exist_ok=True)
        # Link to the original inode when both paths are on the same disk.
        try:
            os.link(target, backup)
        except OSError:
            with backup.open("xb") as dest:
                dest.write(original)
    if digest(backup.read_bytes()) != ORIGINAL:
        raise ValueError("Falha na verificação do arquivo original.")
    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as out:
        staged = Path(out.name)
        try:
            out.write(desired)
            out.flush()
            os.fsync(out.fileno())
            shutil.copymode(target, staged)
        except BaseException:
            staged.unlink(missing_ok=True)
            raise
    try:
        if target.read_bytes() != source:
            raise ValueError("O arquivo ativo mudou durante a preparação.")
        if staged.read_bytes() != desired:
            raise ValueError("Falha na verificação do arquivo preparado.")
        os.replace(staged, target)
    finally:
        staged.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path)
    parser.add_argument("backup", type=Path)
    parser.add_argument("--restore", action="store_true")
    args = parser.parse_args()
    apply(args.target.resolve(), args.backup.resolve(), args.restore)


if __name__ == "__main__":
    main()
