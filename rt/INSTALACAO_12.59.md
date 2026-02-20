# Instalação no Windows 192.168.12.59

## Configuração:
- **192.168.12.59**: Windows 7 + Access + XAMPP (nova instalação)
- **192.168.12.35**: Linux + PHP (este servidor) - cliente da API

## Passos na máquina 192.168.12.59:

### 1. Instalar XAMPP
- Baixe: https://www.apachefriends.org/download.html
- Versão recomendada: XAMPP para Windows (PHP 7.x ou 8.x)
- Instale em: `C:\xampp`

### 2. Copiar o arquivo da API
- Copie o arquivo `/home/prowess/dicomrs/rt/windows_api/api.php`
- Cole em: `C:\xampp\htdocs\api.php`

### 3. Ajustar o caminho do Access
Edite o arquivo `C:\xampp\htdocs\api.php` e ajuste a linha do caminho do banco:

**Se o Access está na mesma máquina (C:\):**
```php
$db = 'C:\primeview\DB\standalone.mdb';
```

**Se o Access está em rede (\\al03-primus-rv\):**
```php
$db = '\\\\al03-primus-rv\\primeview\\DB\\standalone.mdb';
```

### 4. Iniciar o XAMPP
1. Abra o XAMPP Control Panel
2. Clique em "Start" no Apache
3. Verifique se está verde

### 5. Testar localmente
No navegador do Windows (192.168.12.59), acesse:
```
http://localhost/api.php?action=test
```

**Resposta esperada:**
```json
{"status":"success","message":"Connection OK"}
```

### 6. Liberar no Firewall
1. Painel de Controle → Firewall do Windows
2. Configurações Avançadas → Regras de Entrada
3. Nova Regra → Porta → TCP → Porta 80
4. Permitir conexão → Perfis: Todos
5. Nome: "XAMPP Apache"

### 7. Testar da rede
De outro computador, acesse:
```
http://192.168.12.59/api.php?action=test
```

## No servidor Linux (192.168.12.35):

Já está configurado! Apenas teste:

```bash
cd /home/prowess/dicomrs/rt
./test_connection.sh
```

Digite o IP: **192.168.12.59**

## Troubleshooting:

### Erro: "Database not found"
- Verifique o caminho do Access no `api.php`
- Confirme que o arquivo .mdb existe

### Erro: "Connection refused"
- Firewall do Windows bloqueando porta 80
- Apache não está rodando no XAMPP

### Erro: ODBC Driver
- Instale os drivers Access: https://www.microsoft.com/download (Microsoft Access Database Engine)
