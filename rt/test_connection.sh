#!/bin/bash
# Script para testar conexão com a API do Windows

echo "=========================================="
echo "Teste de Conexão - Linux -> Windows API"
echo "=========================================="
echo ""

# Solicita o IP do Windows
read -p "Digite o IP do Windows 7 (ex: 192.168.1.100): " WINDOWS_IP

if [ -z "$WINDOWS_IP" ]; then
    echo "Erro: IP não fornecido"
    exit 1
fi

API_URL="http://$WINDOWS_IP/api.php"

echo ""
echo "Testando: $API_URL"
echo ""

# Teste 1: Conexão básica
echo "1. Testando conexão básica..."
response=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "$API_URL?action=test" 2>&1)

if [ "$response" = "200" ]; then
    echo "   ✓ Conexão OK (HTTP 200)"
    
    # Teste 2: Resposta da API
    echo ""
    echo "2. Resposta da API:"
    curl -s "$API_URL?action=test" | python3 -m json.tool 2>/dev/null || curl -s "$API_URL?action=test"
    
    echo ""
    echo ""
    echo "=========================================="
    echo "✓ SUCESSO! API está respondendo."
    echo "=========================================="
    echo ""
    echo "Agora edite o arquivo conn.php e altere:"
    echo "define('WINDOWS_API_URL', 'http://$WINDOWS_IP/api.php');"
    echo ""
    
else
    echo "   ✗ Falha na conexão (HTTP $response)"
    echo ""
    echo "Possíveis problemas:"
    echo "  - Firewall do Windows bloqueando"
    echo "  - Apache não está rodando"
    echo "  - IP incorreto"
    echo "  - Computadores em redes diferentes"
    echo ""
    echo "No Windows, verifique:"
    echo "  1. XAMPP Apache está iniciado?"
    echo "  2. http://localhost/api.php funciona no Windows?"
    echo "  3. Firewall permite conexões na porta 80?"
fi
