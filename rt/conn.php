<?php
error_reporting(E_ALL);
ini_set('memory_limit', '-1');
ini_set('display_errors', 1);

// URL da API no Windows 7 (192.168.12.59 - máquina com Access + XAMPP)
define('WINDOWS_API_URL', 'http://192.168.12.59/api.php');

class AccessAPIClient {
    private $apiUrl;
    
    public function __construct($apiUrl) {
        $this->apiUrl = $apiUrl;
    }
    
    public function testConnection() {
        $response = $this->makeRequest('test');
        return $response;
    }
    
    public function query($sql) {
        $response = $this->makeRequest('query', ['sql' => $sql]);
        if(isset($response['status']) && $response['status'] === 'success') {
            return $response['data'];
        }
        throw new Exception('Query failed: ' . json_encode($response));
    }
    
    public function getTables() {
        $response = $this->makeRequest('tables');
        if(isset($response['status']) && $response['status'] === 'success') {
            return $response['tables'];
        }
        return [];
    }
    
    private function makeRequest($action, $params = []) {
        $params['action'] = $action;
        
        $ch = curl_init();
        curl_setopt($ch, CURLOPT_URL, $this->apiUrl);
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, http_build_query($params));
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 30);
        
        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        
        if(curl_errno($ch)) {
            throw new Exception('Connection error: ' . curl_error($ch));
        }
        
        curl_close($ch);
        
        $data = json_decode($response, true);
        if($data === null) {
            throw new Exception('Invalid JSON response: ' . $response);
        }
        
        return $data;
    }
}

// Inicializa o cliente
$db = new AccessAPIClient(WINDOWS_API_URL);

// Testa a conexão
try {
    $test = $db->testConnection();
    if(isset($test['status']) && $test['status'] === 'success') {
        echo "<p style='color:green;'>✓ Conexão com Access OK via API Windows</p><br>";
    } else {
        echo "<p style='color:red;'>✗ Erro na conexão: " . json_encode($test) . "</p><br>";
    }
} catch(Exception $e) {
    die("<p style='color:red;'>✗ Erro ao conectar com API Windows: " . $e->getMessage() . "</p>");
}
?>