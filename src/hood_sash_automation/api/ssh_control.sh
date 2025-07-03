#!/bin/bash
# SSH Control Script for Fume Hood Sash Automation
# Usage: ./ssh_control.sh <pi-ip> <command> [position]

PI_IP="$1"
COMMAND="$2"
POSITION="$3"

if [ -z "$PI_IP" ] || [ -z "$COMMAND" ]; then
    echo "Usage: $0 <pi-ip> <command> [position]"
    echo ""
    echo "Commands:"
    echo "  status       - Get current status"
    echo "  position     - Get current position"
    echo "  move <pos>   - Move to position 1-5"
    echo "  stop         - Emergency stop"
    echo "  logs         - Show recent logs"
    echo "  restart      - Restart the service"
    echo ""
    echo "Examples:"
    echo "  $0 192.168.1.100 status"
    echo "  $0 192.168.1.100 move 3"
    echo "  $0 192.168.1.100 stop"
    exit 1
fi

case "$COMMAND" in
    "status")
        echo "🔍 Getting system status..."
        ssh pi@$PI_IP "curl -s http://localhost:5000/status | jq ."
        ;;
    "position")
        echo "📍 Getting current position..."
        ssh pi@$PI_IP "curl -s http://localhost:5000/position | jq ."
        ;;
    "move")
        if [ -z "$POSITION" ]; then
            echo "❌ Error: Position required for move command (1-5)"
            exit 1
        fi
        echo "🚀 Moving to position $POSITION..."
        ssh pi@$PI_IP "curl -X POST http://localhost:5000/move -H 'Content-Type: application/json' -d '{\"position\": $POSITION}' | jq ."
        ;;
    "stop")
        echo "🛑 Emergency stop..."
        ssh pi@$PI_IP "curl -X POST http://localhost:5000/stop | jq ."
        ;;
    "logs")
        echo "📋 Recent logs..."
        ssh pi@$PI_IP "journalctl -u actuator.service -n 20 --no-pager"
        ;;
    "restart")
        echo "🔄 Restarting service..."
        ssh pi@$PI_IP "sudo systemctl restart actuator.service"
        echo "✅ Service restarted"
        ;;
    *)
        echo "❌ Unknown command: $COMMAND"
        exit 1
        ;;
esac 