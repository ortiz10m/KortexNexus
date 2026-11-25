#!/usr/bin/env bash
set -euo pipefail

echo "============================================================"
echo "  KORTEX NEXUS v2.0 — Desinstalador para Linux"
echo "============================================================"

if [ "$(id -u)" -eq 0 ]; then
    INSTALL_DIR="/opt/kortex-nexus"
    BIN_DIR="/usr/local/bin"
    DESKTOP_DIR="/usr/share/applications"
    ICON_FILE="/usr/share/pixmaps/kortex-nexus.png"
    REAL_USER="${SUDO_USER:-root}"
    REAL_HOME="$(eval echo "~${REAL_USER}")"

    if command -v systemctl >/dev/null 2>&1 && [ -f /etc/systemd/system/kortex-nexus.service ]; then
        systemctl disable --now kortex-nexus.service 2>/dev/null || true
        rm -f /etc/systemd/system/kortex-nexus.service
        systemctl daemon-reload 2>/dev/null || true
    fi
else
    INSTALL_DIR="${HOME}/.local/share/kortex-nexus"
    BIN_DIR="${HOME}/.local/bin"
    DESKTOP_DIR="${HOME}/.local/share/applications"
    ICON_FILE="${HOME}/.local/share/icons/hicolor/256x256/apps/kortex-nexus.png"
    REAL_HOME="${HOME}"
fi

pkill -f "kortex-nexus/main.py" 2>/dev/null || true

rm -f "${BIN_DIR}/kortex-nexus" "${BIN_DIR}/kortex-daemon"
rm -f "${DESKTOP_DIR}/kortex-nexus.desktop" "${ICON_FILE}"
rm -f "${REAL_HOME}/.config/autostart/kortex-nexus.desktop"
rm -rf "${INSTALL_DIR}"

echo "Kortex Nexus fue desinstalado."
echo "Tus datos personales siguen intactos en ${REAL_HOME}/.kortex_nexus"
echo "(si deseas borrarlos ejecuta: rm -rf \"${REAL_HOME}/.kortex_nexus\")"
