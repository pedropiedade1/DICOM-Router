import os
import subprocess
import time
from pathlib import Path
import json

# Configurações do destino
TARGET_HOST = os.getenv("TARGET_HOST", "192.168.10.16")
TARGET_PORT = os.getenv("TARGET_PORT", "4243")
TARGET_AET = os.getenv("TARGET_AET", "ZEROCLICK")

# Diretório a ser monitorado
WATCH_FOLDER = Path("/home/dicom")
METADATA_FILE = WATCH_FOLDER / ".metadata.json"

def load_metadata():
    """Carrega metadados dos estudos"""
    if METADATA_FILE.exists():
        with open(METADATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_metadata(metadata):
    """Salva metadados"""
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f, indent=2)

def send_dicom(file_path):
    """Envia um arquivo DICOM"""
    print(f"📤 Enviando: {file_path}")
    try:
        result = subprocess.run([
            "gdcmscu", 
            "--verbose", 
            "--store", 
            TARGET_HOST, 
            TARGET_PORT, 
            "--call", 
            TARGET_AET, 
            file_path
        ], check=True, text=True, capture_output=True, timeout=30)
        
        print(f"✓ Enviado: {file_path}")
        return True
    except subprocess.TimeoutExpired:
        print(f"✗ Timeout ao enviar: {file_path}")
        return False
    except subprocess.CalledProcessError as e:
        print(f"✗ Erro ao enviar {file_path}: {e.stderr}")
        return False

def process_study_folder(folder_path):
    """
    Processa uma pasta de estudo completa
    Envia todos os arquivos e atualiza metadados
    """
    dcm_files = list(folder_path.glob("*.dcm"))
    
    if not dcm_files:
        return True  # Pasta vazia, pode deletar
    
    print(f"\n📁 Processando estudo: {folder_path.name}")
    print(f"   Arquivos: {len(dcm_files)}")
    
    success_count = 0
    failed_files = []
    
    for dcm_file in dcm_files:
        if send_dicom(str(dcm_file)):
            try:
                dcm_file.unlink()  # Deleta arquivo após envio
                success_count += 1
            except Exception as e:
                print(f"✗ Erro ao deletar {dcm_file}: {e}")
        else:
            failed_files.append(dcm_file.name)
    
    print(f"   ✓ Enviados: {success_count}/{len(dcm_files)}")
    
    # Se todos foram enviados, deleta a pasta
    if success_count == len(dcm_files):
        try:
            # Atualiza metadados antes de deletar
            metadata = load_metadata()
            for study_uid, study_data in metadata.items():
                if study_data.get('folder') == folder_path.name:
                    study_data['sent'] = True
                    study_data['sent_at'] = time.strftime("%Y%m%d_%H%M%S")
            save_metadata(metadata)
            
            # Remove pasta vazia
            folder_path.rmdir()
            print(f"   🗑️ Pasta removida: {folder_path.name}")
            return True
        except Exception as e:
            print(f"   ⚠ Não foi possível remover pasta: {e}")
    else:
        print(f"   ⚠ Falhas: {failed_files}")
    
    return False

def monitor_folders():
    """Monitora pastas de estudos e envia arquivos"""
    print("=" * 60)
    print("DICOM Store SCU - Cliente de Envio")
    print(f"Destino: {TARGET_HOST}:{TARGET_PORT} (AET: {TARGET_AET})")
    print(f"Monitorando: {WATCH_FOLDER}")
    print("=" * 60)
    
    processed_folders = set()
    
    while True:
        try:
            # Busca todas as pastas (ignora arquivos soltos na raiz)
            study_folders = [d for d in WATCH_FOLDER.iterdir() 
                           if d.is_dir() and not d.name.startswith('.')]
            
            for folder in study_folders:
                if folder not in processed_folders:
                    # Aguarda um pouco para garantir que recepção terminou
                    time.sleep(3)
                    
                    if process_study_folder(folder):
                        processed_folders.add(folder)
                    else:
                        # Se falhou, tenta novamente no próximo ciclo
                        print(f"   ⏸️ Reprocessará {folder.name} no próximo ciclo")
            
            time.sleep(5)  # Aguarda antes de verificar novamente
            
        except KeyboardInterrupt:
            print("\n⚠ Encerrando envio...")
            break
        except Exception as e:
            print(f"✗ Erro no monitor: {e}")
            time.sleep(10)

if __name__ == "__main__":
    monitor_folders()
