<?php
// API para rodar no Windows 7 com XAMPP
// Cole este arquivo na pasta htdocs do XAMPP no Windows

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST');

error_reporting(E_ALL);
ini_set('display_errors', 1);

// Como o XAMPP está na mesma máquina do Access, use caminho local
// Opção 1: Caminho local direto (ajuste conforme necessário)
$db = 'C:\\primeview\\DB\\standalone.mdb';

// Opção 2: Se ainda for caminho de rede, mantenha:
// $db = '\\\\al03-primus-rv\\primeview\\DB\\standalone.mdb';

if(!file_exists($db)){
    http_response_code(500);
    echo json_encode(['error' => 'Database not found', 'path' => $db]);
    exit;
}

try {
    $dbConn = "Driver={Microsoft Access Driver (*.mdb, *.accdb)};Dbq=".$db.";Uid=; Pwd=;";
    $conn = new PDO("odbc:".$dbConn);
    $conn->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    
    $action = $_GET['action'] ?? $_POST['action'] ?? 'test';
    
    switch($action) {
        case 'test':
            echo json_encode(['status' => 'success', 'message' => 'Connection OK']);
            break;
            
        case 'query':
            $sql = $_POST['sql'] ?? $_GET['sql'] ?? '';
            if(empty($sql)) {
                http_response_code(400);
                echo json_encode(['error' => 'SQL query required']);
                exit;
            }
            
            $stmt = $conn->prepare($sql);
            $stmt->execute();
            $results = $stmt->fetchAll(PDO::FETCH_ASSOC);
            
            echo json_encode([
                'status' => 'success',
                'data' => $results,
                'count' => count($results)
            ]);
            break;
            
        case 'tables':
            // Lista todas as tabelas
            $stmt = $conn->query("SELECT MSysObjects.Name FROM MSysObjects WHERE MSysObjects.Type=1 AND MSysObjects.Flags=0");
            $tables = $stmt->fetchAll(PDO::FETCH_COLUMN);
            echo json_encode(['status' => 'success', 'tables' => $tables]);
            break;
            
        default:
            http_response_code(400);
            echo json_encode(['error' => 'Invalid action']);
    }
    
} catch(PDOException $e) {
    http_response_code(500);
    echo json_encode(['error' => $e->getMessage()]);
}
?>
