#!/usr/bin/env python3
"""
Liste des 10 processus les plus gourmands en CPU.
- Noms complets (via /proc/PID/cmdline, pas la limite 15 chars de comm)
- Dédupliqués par nom
- Filtrage des processus indésirables
- Affiche PID au lieu du rang
"""

import subprocess
import os

# Chaînes à exclure (correspondance partielle, insensible à la casse)
EXCLUDE = [
    "web content",
    "isolated web co",
    "kworker",
    "ksoftirqd",
    "migration",
    "rcu_",
    "scsi_",
    "jbd2",
    "kcompactd",
    "khugepaged",
]

# Noms exacts à exclure (comparaison stricte)
EXCLUDE_EXACT = {"ps", "awk", "grep", "sh", "bash", "python3"}

MAX_PROCS  = 10
NAME_WIDTH = 24   # largeur colonne nom


def full_name(pid: int) -> str | None:
    """Retourne le basename de l'exécutable depuis /proc/PID/cmdline."""
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            data = f.read()
        if not data:
            return None  # thread noyau
        exe = data.split(b"\x00")[0].decode("utf-8", errors="replace")
        return os.path.basename(exe) or None
    except (PermissionError, FileNotFoundError):
        return None


def fmt_mem(rss_kb: int) -> str:
    if rss_kb >= 1_048_576:
        return f"{rss_kb / 1_048_576:.1f}G"
    if rss_kb >= 1024:
        return f"{rss_kb // 1024}M"
    return f"{rss_kb}K"


def is_excluded(name: str, comm: str) -> bool:
    if name in EXCLUDE_EXACT or comm in EXCLUDE_EXACT:
        return True
    haystack = (name + " " + comm).lower()
    return any(pattern in haystack for pattern in EXCLUDE)


result = subprocess.run(
    ["ps", "-eo", "pid,%cpu,rss,comm", "--sort=-rss", "--no-headers"],
    capture_output=True, text=True,
)

seen:  set[str] = set()
count: int      = 0

for line in result.stdout.splitlines():
    parts = line.split(None, 3)
    if len(parts) < 4:
        continue

    pid  = int(parts[0])
    cpu  = parts[1]
    rss  = int(parts[2])
    comm = parts[3].strip()

    name = full_name(pid) or comm

    if is_excluded(name, comm):
        continue
    if name in seen:
        continue
    seen.add(name)

    mem = fmt_mem(rss)
    # truncate name if still too long
    display = name[:NAME_WIDTH]
    print(f"  {display:<{NAME_WIDTH}}  {pid:>7}   {float(cpu):>5.1f}%   {mem}")

    count += 1
    if count >= MAX_PROCS:
        break
