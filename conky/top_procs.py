#!/usr/bin/env python3
"""
Liste des processus les plus gourmands, regroupes par logiciel.

Principes :
- Les processus sont regroupes par "logiciel" plutot qu'affiches un par un :
  tous les processus enfants d'une meme application (rendu, GPU, utilitaires,
  threads de travail...) sont fusionnes en une seule ligne, avec somme du
  CPU% et de la memoire.
- Les noms affiches sont lisibles (ex : "Brave", "Zed", "Terminal"), pas des
  noms d'executable bruts ou des noms de thread internes.
- Si un processus a un nom "bizarre" (identifiant auto-genere, hash, thread
  sans signification - ex. "MainThread", "VQ68........") on ne l'affiche
  jamais tel quel : on remonte l'arbre des processus parents jusqu'a trouver
  un ancetre au nom exploitable, et on rattache ses ressources (CPU/RAM) au
  logiciel de cet ancetre.
- Exception : Zoho Mail (lance dans un profil Brave dedie) est toujours
  affiche a part, jamais fusionne avec le reste du navigateur.
"""

import os
import re
import subprocess

# ── Filtrage des processus indesirables (bruit systeme) ──────────────
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
    "idle_inject",
    "cpuhp/",
    "watchdog",
]
EXCLUDE_EXACT = {"ps", "awk", "grep", "sh", "bash", "python3"}

# ── Noms "generiques"/internes a ne jamais afficher tels quels ───────
GENERIC_DENYLIST = {
    "mainthread", "main thread",
    "threadpoolforegroundworker", "threadpoolsingle", "threadpoolsingl",
    "tokio-runtime-w", "tokio-runtime-worker",
    "pool_workqueue_release",
    "worker", "workerthread",
}

MAX_PROCS  = 10
NAME_WIDTH = 24

# ── Noms lisibles pour les logiciels courants ────────────────────────
READABLE = {
    "brave":                 "Brave",
    "zed-editor":            "Zed",
    "gnome-terminal-server": "Terminal",
    "gnome-terminal":        "Terminal",
    "cinnamon":              "Cinnamon",
    "nemo-desktop":          "Bureau (Nemo)",
    "nemo":                  "Fichiers (Nemo)",
    "xorg":                  "Xorg",
    "conky":                 "Conky",
    "pipewire":              "Audio (PipeWire)",
    "pipewire-pulse":        "Audio (PipeWire)",
    "wireplumber":           "Audio (WirePlumber)",
    "devilspie2":            "Devilspie2",
    "xdg-desktop-portal":    "Portail XDG",
    "gitlab-runner":         "GitLab Runner",
    "dockerd":               "Docker",
    "containerd":            "Docker (containerd)",
    "containerd-shim":       "Docker (containerd)",
    "containerd-shim-runc-v2": "Docker (containerd)",
    "mintupdate":            "Mise a jour (Mint)",
    "mintreport-tray":       "Rapport systeme (Mint)",
    "node":                  "Node.js",
    "ollama":                "Ollama",
}

# ── "Familles" de logiciels multi-processus avec regles speciales ───
# match: fonction(exe_path, full_cmdline) -> bool
# zoho_marker: sous-chaine indiquant le profil Brave dedie a Zoho Mail
FAMILIES = [
    {
        "id": "brave",
        "match": lambda exe, cmd: "brave.com/brave" in exe,
        "label": "Brave",
        "zoho_marker": "Brave-Browser-Zoho",
        "zoho_label": "Zoho Mail",
    },
]


def get_exe_path(pid: int):
    try:
        path = os.readlink(f"/proc/{pid}/exe")
    except OSError:
        return None
    # Le noyau ajoute un suffixe si le binaire a ete remplace/supprime
    # depuis le lancement du processus (mises a jour, venv temporaires...)
    for suffix in (" (deleted)", "(deleted)"):
        if path.endswith(suffix):
            path = path[: -len(suffix)].rstrip()
    return path


def read_cmdline(pid: int):
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            data = f.read()
    except (PermissionError, FileNotFoundError):
        return None
    if not data:
        return None
    parts = [p.decode("utf-8", errors="replace") for p in data.split(b"\x00") if p != b""]
    return parts or None


def is_garbled(name: str) -> bool:
    """Detecte les noms auto-generes / sans signification (hash, code court
    sans voyelles, nom de thread interne...)."""
    if not name:
        return True
    lname = name.lower().strip()
    if lname in GENERIC_DENYLIST:
        return True
    # identifiant hexadecimal (hash, id de conteneur...)
    if re.fullmatch(r"[0-9a-f]{6,40}", lname):
        return True
    # code court avec chiffres et sans voyelle (ex: "VQ68", "X7K9F")
    if re.fullmatch(r"[A-Za-z0-9]{2,15}", name):
        has_digit = any(c.isdigit() for c in name)
        letters = re.sub(r"[^A-Za-z]", "", name)
        vowels = sum(1 for c in letters.lower() if c in "aeiouy")
        if has_digit and letters and vowels == 0:
            return True
    return False


def humanize(name: str) -> str:
    key = name.lower()
    if key in READABLE:
        return READABLE[key]
    cleaned = name.replace("-", " ").replace("_", " ").strip()
    return " ".join(w.capitalize() for w in cleaned.split()) or name


def raw_name_for(pid: int, comm: str):
    """Retourne (nom_brut, exe_path) pour un pid, exe_path resolu en
    priorite (plus fiable que le nom de commande/thread)."""
    exe_path = get_exe_path(pid)
    if exe_path:
        return os.path.basename(exe_path), exe_path
    args = read_cmdline(pid)
    if args:
        return os.path.basename(args[0]), None
    return comm, None


def match_family(exe_path: str, full_cmd: str):
    for fam in FAMILIES:
        if fam["match"](exe_path or "", full_cmd or ""):
            return fam
    return None


def fmt_mem(rss_kb: float) -> str:
    rss_kb = int(rss_kb)
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


# ── Lecture de tous les processus (une seule fois) ───────────────────
result = subprocess.run(
    ["ps", "-eo", "pid,ppid,%cpu,rss,comm", "--no-headers"],
    capture_output=True, text=True,
)

procs = {}  # pid -> {ppid, cpu, rss, comm}
for line in result.stdout.splitlines():
    parts = line.split(None, 4)
    if len(parts) < 5:
        continue
    try:
        pid, ppid = int(parts[0]), int(parts[1])
        cpu, rss = float(parts[2]), int(parts[3])
    except ValueError:
        continue
    procs[pid] = {"ppid": ppid, "cpu": cpu, "rss": rss, "comm": parts[4].strip()}

identity_cache = {}


def resolve_identity(pid: int, depth: int = 0):
    """Retourne (group_key, label) pour un pid : le logiciel auquel
    rattacher ses ressources. Remonte l'arbre des parents si le nom du
    processus est bizarre/generique, jusqu'a trouver un ancetre exploitable."""
    if pid in identity_cache:
        return identity_cache[pid]

    info = procs.get(pid)
    if info is None or depth > 25:
        return ("name:systeme", "Systeme")

    exe_path = get_exe_path(pid) or ""
    args = read_cmdline(pid)
    full_cmd = " ".join(args) if args else info["comm"]

    fam = match_family(exe_path, full_cmd)
    if fam:
        if fam.get("zoho_marker") and fam["zoho_marker"] in full_cmd:
            result_id = (f"zoho:{fam['id']}", fam["zoho_label"])
        else:
            result_id = (f"family:{fam['id']}", fam["label"])
        identity_cache[pid] = result_id
        return result_id

    raw, _ = raw_name_for(pid, info["comm"])

    if raw and not is_garbled(raw):
        label = humanize(raw)
        # cle de regroupement basee sur le libelle final affiche, pour que
        # deux noms bruts differents mappes vers le meme libelle (ex :
        # "containerd-shim" et "containerd-shim-runc-v2" -> "Docker
        # (containerd)") soient bien fusionnes en un seul groupe.
        result_id = (f"label:{label.lower()}", label)
        identity_cache[pid] = result_id
        return result_id

    # Nom bizarre/generique : on rattache au parent
    ppid = info["ppid"]
    if ppid and ppid != pid and ppid in procs:
        result_id = resolve_identity(ppid, depth + 1)
        identity_cache[pid] = result_id
        return result_id

    # Aucun parent exploitable : dernier recours
    result_id = ("name:processus", "Processus")
    identity_cache[pid] = result_id
    return result_id


# ── Agregation par logiciel ───────────────────────────────────────────
groups = {}

for pid, info in procs.items():
    comm = info["comm"]

    quick_name, _ = raw_name_for(pid, comm)
    if is_excluded(quick_name or "", comm):
        continue

    key, label = resolve_identity(pid)

    g = groups.setdefault(key, {"label": label, "cpu": 0.0, "rss": 0, "count": 0, "pid": pid})
    g["cpu"] += info["cpu"]
    g["rss"] += info["rss"]
    g["count"] += 1
    if pid < g["pid"]:
        g["pid"] = pid

# ── Tri et affichage ──────────────────────────────────────────────────
ordered = sorted(groups.values(), key=lambda g: g["rss"], reverse=True)

for g in ordered[:MAX_PROCS]:
    display = g["label"][:NAME_WIDTH]
    proc_col = f"x{g['count']}" if g["count"] > 1 else str(g["pid"])
    mem = fmt_mem(g["rss"])
    print(f"  {display:<{NAME_WIDTH}}  {proc_col:>7}   {g['cpu']:>5.1f}%   {mem}")
