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
<p>SELECIONE O PACIENTE PARA AJUSTAR OS ACESSORIOS E CRIAR A AUTOMAÇÃO</p>
<?php
error_reporting(E_ALL);
ini_set('display_errors', 1);
include("conn.php");

try {

	$data = $db->query('SELECT * FROM patient');
	$result = $data->fetchAll();
	//passa resultado do nome da coluna
	$col_name = array_keys($result[0]);
	//var_dump($result);
	$num_col =count($result[0]);
	$num_lin =count($result);

	//print("num_col".$num_col. "num_lin".$num_lin);
	//modo facil de plotar: display_data($result);
	if (count($result)) {
		echo("<table>");
		for($i = 0; $i < $num_lin; $i++) {
			if($i==0){
				echo("<tr>");
				for($j = 0; $j < $num_col; $j+=2) {
					echo("<td><p>'");
					$index_col = $j/2;
					echo($index_col."-".$col_name[$j]);
					echo("'</p></td>");	
				}
				echo("<td> <p>Deletar</p> </td>");
				echo("</tr>");
			}
			echo("<tr>");
			for($l = 0; $l < $num_col/2; $l++) {
				echo "<td><p>'";
				//echo("'PATIENT_ID".$result[$i][0]."'");
				echo('<a href="field.php?PATIENT_ID='.$result[$i][0].'">');
				echo $result[$i][$l];
				echo "</a></p></td>";
			}
			#echo('<td><p><a href="delete.php?PATIENT_ID='.$result[$i][0].'">Del</	p></a>');
			echo('<td><p>Del</p>');
			echo("</td>");
			echo("</tr>");
			
		}
		PRINT("</table>");

	} else {
		echo "Nennhum resultado retornado.";
	}
}
catch (PDOException $e) {
echo $e->getMessage();
}
$db=null; //close conection



?>
</body>
</html>
		