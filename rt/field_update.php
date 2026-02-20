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
	$UPDATE_STATUS = $_POST['UPDATE_STATUS']; //value = 1 rodar atualizacao
}
?>


<?php
include("conn.php");

try {
	$query = $db->prepare('SELECT * FROM FIELD WHERE PATIENT_ID LIKE ?');
	$query->execute(array($PATIENT_ID));
	$result = $query->fetchAll();

	$col_name = array_keys($result[0]);
	$num_col =count($result[0]);
	$num_lin =count($result);
	//var_dump($result[0]);
	for($i = 0; $i < $num_lin; $i++) {

		try {
			if (strpos($result[$i][15], 'VW') !== false or strpos($result[$i][15], 'EA') !== false){
				$SQL_CAMPOS[$i]="UPDATE FIELD SET MACHINE_ID='0', DOSERATE='0', SLOT1='".$result[$i][15]."', SLOT2=' ', COMMENT='ATAUALIZADO' WHERE PATIENT_ID=". $PATIENT_ID." AND PLAN_ID=".$result[$i][1]." AND SITE_ID=".$result[$i][2]." AND FIELD_ID ='".$result[$i][3]."'";
				//print($SQL_CAMPOS[$i]."<br>");
			} else{
				$SQL_CAMPOS[$i]="UPDATE FIELD SET MACHINE_ID='0', DOSERATE='0', SLOT1=' ', SLOT2=' ', COMMENT='ATAUALIZADO' WHERE PATIENT_ID=". $PATIENT_ID." AND PLAN_ID=".$result[$i][1]." AND SITE_ID=".$result[$i][2]." AND FIELD_ID ='".$result[$i][3]."'";
				//print($SQL_CAMPOS[$i]."<br>");
			}
			
			$statement = $db->prepare($SQL_CAMPOS[$i]);
			$statement = $db->exec($SQL_CAMPOS[$i]);

		} catch (exec $e) {
				$pdo->rollBack();
				echo $e->getMessage();
				return false;
		}
	}
}
catch (PDOException $e) {
	echo $e->getMessage();
}

try {
	
	$query = $db->prepare('SELECT * FROM FIELD WHERE PATIENT_ID LIKE ? ORDER BY SITE_ID, FIELD_ID, FIELD_NAME ASC');
	$query->execute(array($PATIENT_ID));
	$result = $query->fetchAll();

	if (count($result)) {
		$col_name = array_keys($result[0]);
		$num_col =count($result[0]);
		$num_lin =count($result);
		//var_dump($col_name);
		//print("num_col".$num_col. "/num_lin".$num_lin);

		$SITE_ID_col = array_column($result, 'SITE_ID');
		$SITE_ID_lin = count($SITE_ID_col);
		$SITE_ID_num = array_count_values($SITE_ID_col);
		$SITE_ID_values = array_keys($SITE_ID_num);
		
		$site_id_num_contador = 0;
		$ww = 0;
		//var_dump($result);
		for($j = 0; $j < count($SITE_ID_values); $j++) { 
			//echo("j:".$j."/SITE_ID_num:".$SITE_ID_num[$SITE_ID_values[$j]]."<br>");
			for($i = 0; $i < $SITE_ID_num[$SITE_ID_values[$j]]; $i++) { 
			//corre o numero de resultados pesquisados pelo ID paciente
				//echo("i:".$i."<br>");
				$ww = $i + $site_id_num_contador;
				//echo("ww:".$ww."<br>");
				//echo("site_id_num_contador + i:".$ww."<br>");
				$PATIENT_ID2= $result[$ww][0];
				$SITE_ID= $result[$ww][2];
				$PLAN_ID= $result[$ww][1];
				$FIELD_ID= $result[$ww][3];
				$g = $j+1;
				$GROUPNAME= "ASGroup".$g;
				if (strpos($result[$ww][3], '_') !== false){
					$SUBGROUP= "IMGroup".$result[$ww][6];
					$POSITION= $result[$ww][6];
					$ii = explode("_", $result[$ww][3]);
					$SUBPOSITION= $ii[1];
				}else{
					$SUBGROUP= "";
					$POSITION= $result[$ww][6];
					$SUBPOSITION="0";
				}
				$ISIMGROUP="0";
				$ISINTERRUPT="0";
				$INTDESCRIPTION=null;
				$PORTTYPE="0";
				$DOUBLEEXP="0";
				$PORT1="0";
				$PORT2="0";
				$PORT1POS="0";
				$PORT2POS="0";
				$gg = $ww+1;
				$FIELDORDER= $gg;
				$OPENDATE= null;
				$CLOSEDATE= null;
				$HRGROUP= null;
				$PRVFLDNAME= null;
				$MLC_TOLERANCE= "2";



				try {
	
					$SQL_AUTO[$ww] ="INSERT INTO SMSGROUP (PATIENT_ID,PLAN_ID,SITE_ID,FIELD_ID,GROUPNAME,SUBGROUP,POSITION,SUBPOSITION,ISIMGROUP,ISINTERRUPT,INTDESCRIPTION,PORTTYPE,DOUBLEEXP,PORT1,PORT2,PORT1POS,PORT2POS,FIELDORDER,OPENDATE,CLOSEDATE,HRGROUP,PRVFLDNAME,MLC_TOLERANCE) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)";

					$values_data = [ intval($PATIENT_ID2), $PLAN_ID, $SITE_ID, $FIELD_ID, $GROUPNAME, $SUBGROUP, $POSITION, $SUBPOSITION, $ISIMGROUP, $ISINTERRUPT, $INTDESCRIPTION, $PORTTYPE, $DOUBLEEXP, $PORT1, $PORT2, $PORT1POS, $PORT2POS, $FIELDORDER, $OPENDATE, $CLOSEDATE, $HRGROUP, $PRVFLDNAME, $MLC_TOLERANCE ];
					//echo $values_data."<br>";

    			$statement = $db->prepare($SQL_AUTO[$ww]);
			    $statementRet = $statement->execute($values_data);

				} catch (exec $e) {
						$pdo->rollBack();
						echo $e->getMessage();
						return false;
				}
			}
			//echo("<br>site_id_num_contador:".$site_id_num_contador."+");
			$site_id_num_contador = $site_id_num_contador + $SITE_ID_num[$SITE_ID_values[$j]];
			//echo("/<br>");
		}



		echo ("<br>Tabela FIELD<br>");
		echo("<table>");
		for($i = 0; $i < $num_lin; $i++) { //corre o numero de resultados pesquisados pelo ID paciente
			if($i==0){
				echo("<tr>");
				for($j = 0; $j < $num_col; $j+=2) {
					echo("<td><p>'");
					//$index_col = $j/2;
					//echo($index_col."-".$col_name[$j]);
					echo($col_name[$j]);
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

echo ("<br>Tabela SMSGROUP");


try {
	echo ("<br>PATIENT_ID:".$PATIENT_ID);
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
					//$index_col = $j/2;
					//echo($index_col."-".$col_name[$j]);
					echo($col_name[$j]);
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

</body>
</html>
		