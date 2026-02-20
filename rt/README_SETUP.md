# Setup - PHP Linux -> Access Windows

## Passos para configurar:

### 1. No Windows 7 (XAMPP):

1. Copie o arquivo `windows_api/api.php` para a pasta `htdocs` do XAMPP
   - Exemplo: `C:\xampp\htdocs\api.php`

2. Inicie o Apache no XAMPP

3. Teste a API acessando no navegador do Windows:
   ```
   http://localhost/api.php?action=test
   ```
   - Deve retornar: `{"status":"success","message":"Connection OK"}`

4. Descubra o IP do Windows na rede:
   - Abra o CMD e digite: `ipconfig`
   - Anote o IPv4 (exemplo: 192.168.1.100)

### 2. No Linux (este servidor):

1. Edite o arquivo `conn.php` e ajuste o IP na linha:
   ```php
   define('WINDOWS_API_URL', 'http://192.168.1.100/api.php');
   ```
   - Coloque o IP do seu Windows 7

2. Teste acessando: `http://seu-servidor-linux/rt/conn.php`

### 3. Como usar nos seus scripts PHP (Linux):

```php
<?php
require_once('conn.php');

// Fazer uma consulta
try {
    $results = $db->query("SELECT * FROM SuaTabela");
    foreach($results as $row) {
        echo $row['campo'] . "<br>";
    }
} catch(Exception $e) {
    echo "Erro: " . $e->getMessage();
}

// Listar tabelas disponíveis
$tables = $db->getTables();
print_r($tables);
?>
```

## Firewall do Windows:

Se não conectar, libere a porta 80 no firewall do Windows:
1. Painel de Controle > Firewall do Windows
2. Configurações Avançadas
3. Regras de Entrada > Nova Regra
4. Porta > TCP > Porta 80
5. Permitir conexão

## Segurança (IMPORTANTE):

A API atual não tem autenticação. Para produção, adicione:
- Token de autenticação
- Validação de origem (IP whitelist)
- HTTPS
