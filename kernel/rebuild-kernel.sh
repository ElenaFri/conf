#!/bin/bash
# Recompile un noyau Debian "perso" : HZ=1000 + optimisations CPU (march/mtune),
# à partir des sources Debian patchées (linux-source-6.12), sans le paquet -dbg
# (qui est énorme et inutile pour un usage desktop).
#
# Pré-requis (à faire une fois, ou à chaque montée de version majeure du noyau) :
#   sudo apt update
#   sudo apt install -y linux-source-6.12 build-essential libncurses-dev bison \
#       flex libssl-dev libelf-dev dwarves bc rsync kmod cpio fakeroot
#
# Usage :
#   ./rebuild-kernel.sh
#
# Puis pour installer le résultat (nécessite sudo, à faire toi-même) :
#   sudo dpkg -i ~/kernel-build/linux-headers-*-perso_*.deb ~/kernel-build/linux-image-*-perso_*.deb
#
# Adapter les variables ci-dessous si besoin.

set -e

BUILD_DIR="${HOME}/kernel-build"
SRC_TARBALL="/usr/src/linux-source-6.12.tar.xz"
SRC_DIR="${BUILD_DIR}/linux-source-6.12"
LOCALVERSION="-perso"
MARCH="tigerlake"   # `lscpu` -> Model name, puis vérifier avec `gcc -march=native -E -v -` si besoin de changer
JOBS="6"            # laisse de la marge RAM (8 threads dispo mais 8 Go de RAM)

echo "=== Version de linux-source-6.12 disponible ==="
apt-cache policy linux-source-6.12 | head -5

echo "=== Nettoyage de l'ancien répertoire source (si présent) ==="
rm -rf "${SRC_DIR}"
mkdir -p "${BUILD_DIR}"

echo "=== Extraction des sources ==="
tar -xJf "${SRC_TARBALL}" -C "${BUILD_DIR}"

cd "${SRC_DIR}"

echo "=== Récupération de la config du noyau stock actuellement démarrable la plus récente ==="
LATEST_STOCK_CONFIG=$(ls -t /boot/config-*+deb13-amd64 2>/dev/null | head -1)
if [ -z "${LATEST_STOCK_CONFIG}" ]; then
  echo "Impossible de trouver une config stock dans /boot, abandon." >&2
  exit 1
fi
echo "Base de config : ${LATEST_STOCK_CONFIG}"
cp "${LATEST_STOCK_CONFIG}" .config

make olddefconfig

echo "=== Application du réglage HZ=1000 ==="
./scripts/config --disable CONFIG_HZ_250 --enable CONFIG_HZ_1000 --set-val CONFIG_HZ 1000
make olddefconfig

echo "=== Compilation (sans le paquet -dbg, ça peut prendre 20-45 min) ==="
DEB_BUILD_PROFILES="pkg.linux-upstream.nokerneldbg" \
  make -j"${JOBS}" bindeb-pkg LOCALVERSION="${LOCALVERSION}" \
  KCFLAGS="-march=${MARCH} -mtune=${MARCH}"

echo "=== Terminé. Paquets générés : ==="
ls -la "${BUILD_DIR}"/*.deb

echo ""
echo "Pour installer (nécessite sudo) :"
echo "  sudo dpkg -i ${BUILD_DIR}/linux-headers-*${LOCALVERSION}_*.deb ${BUILD_DIR}/linux-image-*${LOCALVERSION}_*.deb"
echo ""
echo "Pense a nettoyer les anciennes versions du noyau perso une fois la nouvelle validee :"
echo "  dpkg -l | grep ${LOCALVERSION}"
echo "  sudo dpkg -r linux-image-ANCIENNE-VERSION${LOCALVERSION} linux-headers-ANCIENNE-VERSION${LOCALVERSION}"
