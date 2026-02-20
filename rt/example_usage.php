<?php
// Exemplo de como usar a conexão com Access via API

require_once('conn.php');

echo "<h2>Exemplos de uso do Access via API</h2>";

// Exemplo 1: Listar tabelas
echo "<h3>1. Tabelas disponíveis:</h3>";
try {
    $tables = $db->getTables();
    echo "<ul>";
    foreach($tables as $table) {
        echo "<li>$table</li>";
    }
    echo "</ul>";
} catch(Exception $e) {
    echo "<p style='color:red;'>Erro: " . $e->getMessage() . "</p>";
}

// Exemplo 2: Fazer uma consulta SELECT
echo "<h3>2. Exemplo de consulta:</h3>";
try {
    // AJUSTE O NOME DA TABELA AQUI
    $sql = "SELECT TOP 10 * FROM SuaTabela";
    $results = $db->query($sql);
    
    if(count($results) > 0) {
        echo "<table border='1' cellpadding='5'>";
        
        // Cabeçalho
        echo "<tr>";
        foreach(array_keys($results[0]) as $column) {
            echo "<th>$column</th>";
        }
        echo "</tr>";
        
        // Dados
        foreach($results as $row) {
            echo "<tr>";
            foreach($row as $value) {
                echo "<td>$value</td>";
            }
            echo "</tr>";
        }
        
        echo "</table>";
    } else {
        echo "<p>Nenhum resultado encontrado.</p>";
    }
    
} catch(Exception $e) {
    echo "<p style='color:red;'>Erro: " . $e->getMessage() . "</p>";
    echo "<p><em>Dica: Ajuste o nome da tabela no código para uma tabela que existe no seu banco.</em></p>";
}

?>
