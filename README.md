# conf

mes configurations personnelles

---

## conky

Thème Conky GitHub Dark / Linux Mint affiché en haut à gauche du bureau : horloge, météo (via `weather.py`), uptime, kernel, charge CPU, température, RAM et swap. Palette verte Mint, fond entièrement transparent, largeur fixe 420 px. Sur Cinnamon/Muffin, `start-conky.sh` pose un _strut_ de 448 px pour que les fenêtres maximisées ne recouvrent jamais le panneau.

![conky](conky/conky.png)

1. Copier les fichiers dans `~/.config/conky/` :

   ```bash
   cp conky/conky.conf conky/start-conky.sh conky/weather.py conky/top_procs.py ~/.config/conky/
   chmod +x ~/.config/conky/start-conky.sh
   ```

2. Lancer manuellement :

   ```bash
   ~/.config/conky/start-conky.sh
   ```

3. Ajouter `~/.config/conky/start-conky.sh` aux applications au démarrage de Cinnamon pour le lancer automatiquement à la session.
