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
//var_dump($_GET);

if(isset($_GET['PATIENT_ID'])){ 
	$PATIENT_ID = $_GET['PATIENT_ID'];
}?>

<form action="delete.php" method="POST">
<input type="hidden" name="PATIENT_ID" value="<?php echo($PATIENT_ID)?>">
<input type="hidden" name="UPDATE_STATUS" value="1">
<input type="submit" name="submit" value="DELETAR">
</form>

<form action="field_update.php" method="POST">
<input type="hidden" name="PATIENT_ID" value="<?php echo($PATIENT_ID)?>">
<input type="hidden" name="UPDATE_STATUS" value="1">
<input type="submit" name="submit" value="EDITAR">
<?php
include("conn.php");
echo ("Tabela FIELD");
try {
	$query = $db->prepare('SELECT * FROM FIELD WHERE PATIENT_ID LIKE ? ORDER BY SITE_ID, FIELD_ID, FIELD_NAME ASC');
	$query->execute(array($PATIENT_ID));
	$result = $query->fetchAll();

	if (count($result)) {
		$col_name = array_keys($result[0]);
		$num_col =count($result[0]);
		$num_lin =count($result);
		//echo("<pre>");
		//var_dump($col_name);
		//print("num_col".$num_col. "/num_lin".$num_lin);
		echo("<table>");
		for($i = 0; $i < $num_lin; $i++) {
			if($i==0){
				echo("<tr>");
				for($j = 0; $j < $num_col; $j+=2) {
					echo("<td><p>'");
					$index_col = $j/2;
					echo($index_col."-".$col_name[$j]);
					echo("'<br></p></td>");	
				}
				echo("</tr>");
			}
			echo("<tr>");
			for($l = 0; $l < $num_col/2; $l++) {
				echo "<td><p>'";
				echo $result[$i][$l];
				echo "'<br></p></td>";
			}
			echo("</tr>");
		}
		echo("</table>");
	} else {
		echo "Nennhum resultado retornado.";
	}
}
catch (PDOException $e) {
	echo $e->getMessage();
}
ECHO ("<BR>");
echo ("Tabela SMSGROUP");
ECHO ("<BR>");
try {
	/*

SELECT column_name(s)
FROM table1
INNER JOIN table2
ON table1.column_name = table2.column_name;
	*/
	$query = $db->prepare('SELECT * FROM SMSGROUP WHERE PATIENT_ID LIKE ?');
	$query->execute(array($PATIENT_ID));
	$result = $query->fetchAll();

	if (count($result)) {
		$col_name = array_keys($result[0]);
		$num_col =count($result[0]);
		$num_lin =count($result);
		//var_dump($result[0]);
		//print("num_col".$num_col. "/num_lin".$num_lin);
		echo("<table>");
		for($i = 0; $i < $num_lin; $i++) {
			if($i==0){
				echo("<tr>");
				for($j = 0; $j < $num_col; $j+=2) {
					echo("<td><p>'");
					$index_col = $j/2;
					echo($index_col."-".$col_name[$j]);
					echo("'<br></p></td>");	
				}
				echo("</tr>");
			}
			echo("<tr>");
			for($l = 0; $l < $num_col/2; $l++) {
				echo "<td><p>'";
				echo $result[$i][$l];
				echo "'<br></p></td>";
			}
			echo("</tr>");
		}
		echo("</table>");
	} else {
		echo "Nennhum resultado retornado.";
	}
}
catch (PDOException $e) {
	echo $e->getMessage();
}




$db=null; //close conection
?>
</form>
</body>
</html>
		