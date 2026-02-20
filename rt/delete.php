<html xmlns="http://www.w3.org/1999/xhtml">
<style>
body {
  background-color: lightblue;
}
h1 {
  color: white;
  text-align: center;
}
p {
  font-family: verdana;
  font-size: 10px;
}
table, th, td {
  border: 1px solid black;
  border-collapse: collapse;
}
</style>
<head>
<title>PRIME WIZARD AJUSTE</title>	
</head>
<body>
<h1>PRIME WIZARD AJUSTE DO RTP</h1>
<p>O PACIENTE SELECIONADO PARA AJUSTAR OS ACESSORIOS E CRIAR A AUTOMAÇÃO</p>
<?php
error_reporting(E_ALL);
ini_set('display_errors', 1);
//var_dump($_POST);

if(isset($_POST['PATIENT_ID'])){ 
	$PATIENT_ID = $_POST['PATIENT_ID'];
}

//var_dump($PATIENT_ID);
?>


<?php
include("conn.php");
echo ("Tabela FIELD");
try {
	$query = $db->prepare('DELETE * FROM PATIENT WHERE PATIENT_ID LIKE ?');
	$query->execute(array($PATIENT_ID));
	$result = $query->fetchAll();
	echo ($result);
}
catch (PDOException $e) {
	echo $e->getMessage();
}


try {
	$query = $db->prepare('DELETE * FROM CP WHERE PATIENT_ID LIKE ?');
	$query->execute(array($PATIENT_ID));
	$result = $query->fetchAll();
}
catch (PDOException $e) {
	echo $e->getMessage();
}
try {
	$query = $db->prepare('DELETE * FROM CP_HST WHERE PATIENT_ID LIKE ?');
	$query->execute(array($PATIENT_ID));
	$result = $query->fetchAll();
}
catch (PDOException $e) {
	echo $e->getMessage();
}
try {
	$query = $db->prepare('DELETE * FROM FIELD WHERE PATIENT_ID LIKE ?');
	$query->execute(array($PATIENT_ID));
	$result = $query->fetchAll();
}
catch (PDOException $e) {
	echo $e->getMessage();
}
try {
	$query = $db->prepare('DELETE * FROM FIELD_HST WHERE PATIENT_ID LIKE ?');
	$query->execute(array($PATIENT_ID));
	$result = $query->fetchAll();
}
catch (PDOException $e) {
	echo $e->getMessage();
}
try {
	$query = $db->prepare('DELETE * FROM MLC WHERE PATIENT_ID LIKE ?');
	$query->execute(array($PATIENT_ID));
	$result = $query->fetchAll();
}
catch (PDOException $e) {
	echo $e->getMessage();
}
try {
	$query = $db->prepare('DELETE * FROM MLC_HST WHERE PATIENT_ID LIKE ?');
	$query->execute(array($PATIENT_ID));
	$result = $query->fetchAll();
}
catch (PDOException $e) {
	echo $e->getMessage();
}
try {
	$query = $db->prepare('DELETE * FROM SITE WHERE PATIENT_ID LIKE ?');
	$query->execute(array($PATIENT_ID));
	$result = $query->fetchAll();
}
catch (PDOException $e) {
	echo $e->getMessage();
}
try {
	$query = $db->prepare('DELETE * FROM SMSGROUP WHERE PATIENT_ID LIKE ?');
	$query->execute(array($PATIENT_ID));
	$result = $query->fetchAll();
}
catch (PDOException $e) {
	echo $e->getMessage();
}


header("Location: index.php");
die();
?>
</body>
</html>
		