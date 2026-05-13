#!/bin/bash
# ============================================================
# MediaCrawler 一站式启停脚本
# 包含: Xvfb + x11vnc + noVNC + WebUI(api.main)
# 用法: ./mediacrawler.sh {start|stop|restart|status|logs [服务名]}
# ============================================================

# ---------- 可调参数 ----------
PROJECT_DIR="/opt/MediaCrawler-main"
LOG_DIR="/var/log/mediacrawler"
DISPLAY_NUM=":99"
SCREEN_GEOMETRY="1920x1080x24"
VNC_PORT=5900
NOVNC_PORT=6080
WEBUI_PORT=8080
VNC_PASSWD_FILE="/root/.vnc/passwd"
NOVNC_DIR="/opt/noVNC"
UV_BIN="$(command -v uv || echo /root/.local/bin/uv)"
# -------------------------------

mkdir -p "$LOG_DIR"

is_running()  { pgrep -f "$1" >/dev/null 2>&1; }

wait_port() {
    for i in {1..15}; do
        ss -lnt | grep -q ":$1 " && return 0
        sleep 0.3
    done
    return 1
}

start_xvfb() {
    if is_running "Xvfb $DISPLAY_NUM"; then echo "[Xvfb] already running"; return; fi
    rm -f "/tmp/.X${DISPLAY_NUM#:}-lock" "/tmp/.X11-unix/X${DISPLAY_NUM#:}"
    nohup Xvfb "$DISPLAY_NUM" -screen 0 "$SCREEN_GEOMETRY" -ac \
        > "$LOG_DIR/xvfb.log" 2>&1 &
    sleep 1
    is_running "Xvfb $DISPLAY_NUM" && echo "[Xvfb] started" \
        || { echo "[Xvfb] FAILED"; tail -20 "$LOG_DIR/xvfb.log"; exit 1; }
}

start_x11vnc() {
    if is_running "x11vnc -display $DISPLAY_NUM"; then echo "[x11vnc] already running"; return; fi
    if [ ! -f "$VNC_PASSWD_FILE" ]; then
        echo "[x11vnc] password file missing: $VNC_PASSWD_FILE"
        echo "请先执行: x11vnc -storepasswd 你的密码 $VNC_PASSWD_FILE"
        exit 1
    fi
    nohup x11vnc -display "$DISPLAY_NUM" -forever -shared -loop \
        -rfbport "$VNC_PORT" -rfbauth "$VNC_PASSWD_FILE" \
        > "$LOG_DIR/x11vnc.log" 2>&1 &
    wait_port "$VNC_PORT" && echo "[x11vnc] listening on $VNC_PORT" \
        || { echo "[x11vnc] FAILED"; tail -20 "$LOG_DIR/x11vnc.log"; exit 1; }
}

start_novnc() {
    if is_running "novnc_proxy.*$NOVNC_PORT"; then echo "[noVNC] already running"; return; fi
    nohup "$NOVNC_DIR/utils/novnc_proxy" \
        --vnc "localhost:$VNC_PORT" --listen "$NOVNC_PORT" \
        > "$LOG_DIR/novnc.log" 2>&1 &
    wait_port "$NOVNC_PORT" && echo "[noVNC] listening on $NOVNC_PORT" \
        || { echo "[noVNC] FAILED"; tail -20 "$LOG_DIR/novnc.log"; exit 1; }
}

start_webui() {
    if is_running "api.main"; then echo "[WebUI] already running"; return; fi
    cd "$PROJECT_DIR" || exit 1
    DISPLAY="$DISPLAY_NUM" nohup "$UV_BIN" run python -m api.main \
        > "$LOG_DIR/webui.log" 2>&1 &
    wait_port "$WEBUI_PORT" && echo "[WebUI] listening on $WEBUI_PORT" \
        || { echo "[WebUI] FAILED"; tail -30 "$LOG_DIR/webui.log"; exit 1; }
}

stop_all() {
    echo "Stopping all services..."
    pkill -f "api.main"        2>/dev/null
    pkill -f "novnc_proxy"     2>/dev/null
    pkill -f "websockify"      2>/dev/null
    pkill -f "x11vnc -display $DISPLAY_NUM" 2>/dev/null
    pkill -f "Xvfb $DISPLAY_NUM"            2>/dev/null
    pkill -f "chrome.*user-data-dir"        2>/dev/null
    sleep 1
    rm -f "/tmp/.X${DISPLAY_NUM#:}-lock"
    echo "All stopped."
}

show_status() {
    printf "%-12s %s\n" "Service" "Status"
    printf "%-12s %s\n" "--------" "------"
    for kw in "Xvfb $DISPLAY_NUM" "x11vnc -display $DISPLAY_NUM" "novnc_proxy" "api.main"; do
        name=$(echo "$kw" | awk '{print $1}')
        if is_running "$kw"; then
            printf "%-12s \033[32mRUNNING\033[0m  pid=%s\n" "$name" "$(pgrep -f "$kw" | head -1)"
        else
            printf "%-12s \033[31mSTOPPED\033[0m\n" "$name"
        fi
    done
    echo
    echo "Listening ports:"
    ss -lnt | grep -E "$VNC_PORT|$NOVNC_PORT|$WEBUI_PORT" || echo "  (none)"
    echo
    IP=$(curl -s --max-time 2 ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
    echo "Access URLs:"
    echo "  WebUI : http://$IP:$WEBUI_PORT"
    echo "  noVNC : http://$IP:$NOVNC_PORT/vnc_lite.html?autoconnect=true&resize=scale"
}

start_all() {
    start_xvfb
    start_x11vnc
    start_novnc
    start_webui
    echo
    show_status
}

case "${1:-start}" in
    start)   start_all ;;
    stop)    stop_all ;;
    restart) stop_all; sleep 2; start_all ;;
    status)  show_status ;;
    logs)
        svc="${2:-webui}"
        tail -f "$LOG_DIR/${svc}.log"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs [xvfb|x11vnc|novnc|webui]}"
        exit 1
        ;;
esac
