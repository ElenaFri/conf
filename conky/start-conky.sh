#!/bin/bash
# Lance Conky et applique les struts pour que les fenêtres maximisées
# ne le recouvrent jamais (nécessaire sur Cinnamon/Muffin).

pkill -x conky 2>/dev/null
sleep 1

conky -d

# Attendre que la fenêtre Conky apparaisse (max 10 secondes)
for i in $(seq 1 20); do
    WIN_ID=$(wmctrl -lG 2>/dev/null | awk '/conky \(perso\)/{print $1}' | head -1)
    [ -n "$WIN_ID" ] && break
    sleep 0.5
done

if [ -z "$WIN_ID" ]; then
    echo "Conky window not found" >&2
    exit 1
fi

# Strut gauche : 448px (gap_x 18 + largeur 420 + marge 10)
# _NET_WM_STRUT        : left right top bottom
# _NET_WM_STRUT_PARTIAL : + left_start_y left_end_y right_* top_* bottom_*
xprop -id "$WIN_ID" \
    -f _NET_WM_STRUT 32c \
    -set _NET_WM_STRUT "448, 0, 0, 0"

xprop -id "$WIN_ID" \
    -f _NET_WM_STRUT_PARTIAL 32c \
    -set _NET_WM_STRUT_PARTIAL "448, 0, 0, 0, 0, 1079, 0, 0, 0, 0, 0, 0"
