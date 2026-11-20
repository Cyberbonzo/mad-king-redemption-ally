"""Ouro fixo para o build 26417954 com os ajustes existentes do Ally."""
from hashlib import sha256
from pathlib import Path
import argparse
import runpy


BASE = "7755867e43f6a6cff43cb229ecda9d0788aae46892906438e9f8d645da1d346c"
# Os endereços abaixo são RVAs da revisão inglesa de GameAssembly.
CHANGES = (
    # LoadGame: inicializa a carteira persistente e seu registro de diagnóstico.
    (0x75AF37, "8b4b18488d5424708948488b4318", "b9ffffff7f894848488d54247091"),
    # Carteira inicial de um novo jogo.
    (0x75C14E, "c7404896000000", "c74048ffffff7f"),
    # Mantém notificações, objetos comprados e estatísticas. Somente a
    # operação aritmética da carteira é omitida, evitando overflow na coleta.
    (0x6F71BA, "015148", "909090"),  # AddGoldSilent
    (0x6F71FA, "015148", "909090"),  # AddGold
    (0x6F72DA, "295148", "909090"),  # SubtractGold
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dll", type=Path)
    parser.add_argument("backup", type=Path)
    parser.add_argument("--restore", action="store_true")
    args = parser.parse_args()
    target = args.dll.resolve()
    backup = args.backup.resolve()
    if target == backup:
        parser.error("Escolha um backup separado.")
    helpers = runpy.run_path(str(Path(__file__).with_name("ajustes-mad-king.py")))
    current = target.read_bytes()
    base = backup.read_bytes() if backup.exists() else current
    if sha256(base).hexdigest() != BASE:
        parser.error("A revisão da DLL ou os ajustes existentes são diferentes.")
    fixed = bytearray(base)
    for rva, old, new in CHANGES:
        helpers["edit"](fixed, rva - 0xE00, bytes.fromhex(old), bytes.fromhex(new))
    if current != base and current != fixed:
        parser.error("A DLL atual contém outras alterações.")
    desired = base if args.restore else fixed
    if current != desired:
        helpers["backup_once"](target, backup, base)
        helpers["replace"](target, current, desired)
    print(sha256(desired).hexdigest())


if __name__ == "__main__":
    main()
