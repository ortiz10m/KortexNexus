#!/usr/bin/env bash
set -euo pipefail

echo "============================================================"
echo "  KORTEX NEXUS v2.0 — Instalador Universal para Linux"
echo "  Compatible con Debian/Ubuntu, Arch, Fedora, openSUSE,"
echo "  Alpine, Void (X11 y Wayland)"
echo "  100% Offline · Cero Telemetria · Cero Fugas de Datos"
echo "============================================================"
echo

AUTO_YES=0
for arg in "$@"; do
    if [ "$arg" = "-y" ] || [ "$arg" = "--yes" ]; then
        AUTO_YES=1
    fi
done

if [ "${AUTO_YES}" -eq 0 ] && [ -t 0 ]; then
    echo "Al continuar aceptas los Terminos de Uso y la Politica de Privacidad"
    echo "de Kortex Nexus v2.0 (Copyright (c) 2026 David Santiago Ortiz Rincon)."
    echo "Tus datos y metricas permanecen 100% locales en ~/.kortex_nexus (permisos 0700)."
    read -r -p "¿Aceptas y deseas instalar Kortex Nexus? [S/n]: " RESP
    RESP="${RESP:-S}"
    if [[ ! "${RESP}" =~ ^[SsYy]$ ]]; then
        echo "Instalacion cancelada por el usuario."
        exit 0
    fi
    echo
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_SRC="${SCRIPT_DIR}/app"

if [ ! -f "${APP_SRC}/main.py" ]; then
    echo "[ERROR] No se encontro ${APP_SRC}/main.py"
    exit 1
fi

ES_ROOT=0
if [ "$(id -u)" -eq 0 ]; then
    ES_ROOT=1
    INSTALL_DIR="/opt/kortex-nexus"
    BIN_DIR="/usr/local/bin"
    DESKTOP_DIR="/usr/share/applications"
    ICON_DIR="/usr/share/pixmaps"
    REAL_USER="${SUDO_USER:-root}"
    REAL_HOME="$(eval echo "~${REAL_USER}")"
else
    INSTALL_DIR="${HOME}/.local/share/kortex-nexus"
    BIN_DIR="${HOME}/.local/bin"
    DESKTOP_DIR="${HOME}/.local/share/applications"
    ICON_DIR="${HOME}/.local/share/icons/hicolor/256x256/apps"
    REAL_USER="$(whoami)"
    REAL_HOME="${HOME}"
fi

instalar_dependencias_so() {
    echo "[1/5] Verificando dependencias base del sistema..."
    if [ "${ES_ROOT}" -eq 0 ]; then
        if ! command -v python3 >/dev/null 2>&1; then
            echo "[ERROR] python3 no esta instalado. Ejecuta con sudo o instala python3, tk y python3-venv."
            exit 1
        fi
        return
    fi

    if command -v apt-get >/dev/null 2>&1; then
        apt-get update -qq
        apt-get install -y python3 python3-venv python3-tk x11-utils libnotify-bin || true
    elif command -v pacman >/dev/null 2>&1; then
        pacman -Sy --noconfirm --needed python tk xorg-xprop libnotify || true
    elif command -v dnf >/dev/null 2>&1; then
        dnf install -y python3 python3-tkinter xprop libnotify || true
    elif command -v zypper >/dev/null 2>&1; then
        zypper --non-interactive install python3 python3-tk xprop libnotify-tools || true
    elif command -v apk >/dev/null 2>&1; then
        apk add --no-cache python3 py3-pip py3-tkinter xprop libnotify || true
    elif command -v xbps-install >/dev/null 2>&1; then
        xbps-install -Sy python3 python3-tkinter xprop libnotify || true
    else
        echo "[AVISO] Gestor de paquetes no reconocido. Asegurate de tener python3, venv y tkinter."
    fi
}

instalar_dependencias_so

echo "[2/5] Copiando Kortex Nexus en ${INSTALL_DIR}..."
mkdir -p "${INSTALL_DIR}" "${BIN_DIR}" "${DESKTOP_DIR}" "${ICON_DIR}"
cp -a "${APP_SRC}/." "${INSTALL_DIR}/"
cp -f "${SCRIPT_DIR}/uninstall_linux.sh" "${INSTALL_DIR}/uninstall_linux.sh"
chmod +x "${INSTALL_DIR}/uninstall_linux.sh"

echo "[3/5] Creando entorno virtual ligero e instalando dependencias Python..."
rm -rf "${INSTALL_DIR}/venv"
python3 -m venv "${INSTALL_DIR}/venv"
"${INSTALL_DIR}/venv/bin/pip" install --upgrade pip --quiet || true
"${INSTALL_DIR}/venv/bin/pip" install -r "${INSTALL_DIR}/requirements.txt" --quiet

echo "[4/5] Creando comandos kortex-nexus y kortex-daemon..."
cat > "${BIN_DIR}/kortex-nexus" <<EOF
#!/usr/bin/env bash
exec "${INSTALL_DIR}/venv/bin/python" "${INSTALL_DIR}/main.py" "\$@"
EOF
chmod 0755 "${BIN_DIR}/kortex-nexus"

cat > "${BIN_DIR}/kortex-daemon" <<EOF
#!/usr/bin/env bash
exec "${INSTALL_DIR}/venv/bin/python" "${INSTALL_DIR}/main.py" --daemon "\$@"
EOF
chmod 0755 "${BIN_DIR}/kortex-daemon"

if [ -f "${INSTALL_DIR}/logo_kortex.png" ]; then
    cp -f "${INSTALL_DIR}/logo_kortex.png" "${ICON_DIR}/kortex-nexus.png"
    if [ "${ES_ROOT}" -eq 1 ]; then
        mkdir -p /usr/share/icons/hicolor/256x256/apps
        cp -f "${INSTALL_DIR}/logo_kortex.png" /usr/share/icons/hicolor/256x256/apps/kortex-nexus.png
        command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true
    fi
fi

cat > "${DESKTOP_DIR}/kortex-nexus.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Kortex Nexus
Comment=Optimizador Anti-Freeze para equipos de bajos recursos
Exec=${BIN_DIR}/kortex-nexus
Icon=kortex-nexus
Terminal=false
Categories=System;Utility;Monitor;
EOF
chmod 0644 "${DESKTOP_DIR}/kortex-nexus.desktop"
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "${DESKTOP_DIR}" 2>/dev/null || true

echo "[5/5] Configurando arranque automatico del daemon Anti-Freeze..."
if [ "${ES_ROOT}" -eq 1 ] && command -v systemctl >/dev/null 2>&1 && [ -d /run/systemd/system ]; then
    cat > /etc/systemd/system/kortex-nexus.service <<EOF
[Unit]
Description=Kortex Nexus v2.0 Anti-Freeze Daemon (ZRAM, BBR, Auto-Cryo)
After=multi-user.target

[Service]
Type=simple
ExecStart=${INSTALL_DIR}/venv/bin/python ${INSTALL_DIR}/main.py --daemon
Restart=on-failure
RestartSec=5
Nice=-5

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    systemctl enable --now kortex-nexus.service || true
    echo "      Servicio systemd kortex-nexus.service activado (con privilegios para ZRAM/BBR)."
else
    AUTOSTART_DIR="${REAL_HOME}/.config/autostart"
    mkdir -p "${AUTOSTART_DIR}"
    cat > "${AUTOSTART_DIR}/kortex-nexus.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Kortex Nexus Daemon
Comment=Monitor y optimizador Anti-Freeze de Kortex Nexus
Exec=${BIN_DIR}/kortex-daemon
Terminal=false
X-GNOME-Autostart-enabled=true
EOF
    if [ "${ES_ROOT}" -eq 1 ] && [ "${REAL_USER}" != "root" ]; then
        chown -R "${REAL_USER}:${REAL_USER}" "${AUTOSTART_DIR}" || true
    fi
    echo "      Auto-inicio configurado en ${AUTOSTART_DIR}/kortex-nexus.desktop"
fi

echo
echo "============================================================"
echo "  Instalacion completada en ${INSTALL_DIR}"
echo "  Comandos disponibles:"
echo "    kortex-nexus    -> Abre la interfaz grafica"
echo "    kortex-daemon   -> Ejecuta solo el motor ligero (<20 MB)"
echo "  Desinstalar:"
echo "    ${INSTALL_DIR}/uninstall_linux.sh"
echo "============================================================"
