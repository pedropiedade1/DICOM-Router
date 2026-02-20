import streamlit as st
import docker
import pandas as pd
import time
from datetime import datetime
from pathlib import Path
import json
import subprocess
import socket
import os
import shutil

# Configuração da Página
st.set_page_config(
    page_title="DICOM Router Manager",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🏥 DICOM Router - Painel de Controle Avançado")

# Constantes
DICOM_ROOT = Path("/home/dicom")
METADATA_FILE = DICOM_ROOT / ".metadata.json"
STATUS_FILE = DICOM_ROOT / ".send_status.json"
ENV_FILE = Path("/home/prowess/dicomrs/.env")
DICOM_ARCHIVE_ROOT = Path("/home/dicom")  # Pasta com estudos organizados

# --- Funções Auxiliares ---

def load_env():
    """Carrega variáveis do .env"""
    env_vars = {}
    if ENV_FILE.exists():
        with open(ENV_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value
    return env_vars

def load_metadata():
    """Carrega metadados dos estudos"""
    if METADATA_FILE.exists():
        try:
            with open(METADATA_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def load_send_status():
    """Carrega status de envio dos estudos"""
    if STATUS_FILE.exists():
        try:
            with open(STATUS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_send_status(status_data):
    """Salva status de envio dos estudos"""
    try:
        with open(STATUS_FILE, 'w') as f:
            json.dump(status_data, f, indent=2)
        return True
    except Exception as e:
        return False

def update_study_status(study_name: str, status: str, message: str = "", sent_count: int = 0, total_count: int = 0):
    """Atualiza o status de um estudo específico"""
    status_data = load_send_status()
    status_data[study_name] = {
        'status': status,  # 'enviado', 'falha', 'pendente', 'enviando'
        'message': message,
        'sent_count': sent_count,
        'total_count': total_count,
        'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    save_send_status(status_data)

def save_metadata(metadata):
    """Salva metadados dos estudos"""
    try:
        with open(METADATA_FILE, 'w') as f:
            json.dump(metadata, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar metadados: {e}")
        return False

def get_study_folders():
    """Lista pastas de estudos no disco com status de envio"""
    folders = []
    status_data = load_send_status()
    try:
        for d in DICOM_ARCHIVE_ROOT.iterdir():
            if d.is_dir() and not d.name.startswith('.'):
                dcm_files = list(d.glob("*.dcm"))
                if dcm_files:
                    study_status = status_data.get(d.name, {})
                    folders.append({
                        'path': d,
                        'name': d.name,
                        'file_count': len(dcm_files),
                        'size_mb': sum(f.stat().st_size for f in dcm_files) / (1024*1024),
                        'status': study_status.get('status', 'pendente'),
                        'status_message': study_status.get('message', ''),
                        'last_update': study_status.get('last_update', ''),
                        'sent_count': study_status.get('sent_count', 0),
                        'total_count': study_status.get('total_count', 0)
                    })
    except Exception as e:
        st.error(f"Erro ao listar pastas: {e}")
    return folders

def resend_study(folder_path: Path, target_host: str, target_port: str, target_aet: str):
    """Reenvia um estudo DICOM para o destino usando gdcmscu dentro do container storescu"""
    dcm_files = list(folder_path.glob("*.dcm"))
    if not dcm_files:
        update_study_status(folder_path.name, 'falha', 'Nenhum arquivo DICOM encontrado')
        return False, "Nenhum arquivo DICOM encontrado na pasta"
    
    total_files = len(dcm_files)
    
    # Atualiza status para "enviando"
    update_study_status(folder_path.name, 'enviando', f'Enviando {total_files} arquivos...', 0, total_files)
    
    container = get_container("storescu")
    if not container:
        update_study_status(folder_path.name, 'falha', 'Container storescu não encontrado')
        return False, "Container storescu não encontrado"
    
    # Caminho dentro do container
    container_path = f"/home/dicom/{folder_path.name}"
    
    try:
        # Envia todos os arquivos da pasta de uma vez usando sintaxe correta do gdcmscu
        # gdcmscu --store -H host -p port --call AET -r -i "pasta"
        cmd = f'gdcmscu --store -H {target_host} -p {target_port} --call {target_aet} -r -i "{container_path}" --verbose'
        exec_result = container.exec_run(["bash", "-c", cmd], tty=True)
        output = exec_result.output.decode('utf-8', errors='ignore')
        
        if exec_result.exit_code == 0:
            update_study_status(folder_path.name, 'enviado', f'Enviado com sucesso!', total_files, total_files)
            return True, f"Estudo reenviado com sucesso! ({total_files} arquivos)"
        else:
            # Tenta contar quantos foram enviados
            sent_count = output.count('successfully')
            error_msg = output[:300] if output else "Erro desconhecido"
            update_study_status(folder_path.name, 'falha', f'Erro no envio: {error_msg}', sent_count, total_files)
            return False, f"Erro ao reenviar: {error_msg}"
    except Exception as e:
        update_study_status(folder_path.name, 'falha', f'Exceção: {str(e)}')
        return False, f"Exceção: {str(e)}"

def test_connection(host, port, timeout=2):
    """Testa conexão TCP"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, int(port)))
        sock.close()
        return result == 0
    except:
        return False

def check_port_listening(port):
    """Verifica se porta está escutando localmente"""
    try:
        # Tenta conectar na porta para verificar se está escutando
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('172.22.61.14', int(port)))
        sock.close()
        if result == 0:
            return True
        # Fallback: verifica via netstat sem sudo
        result = subprocess.run(
            f"netstat -tlnp 2>/dev/null | grep ':{port}' || ss -tlnp | grep ':{port}'",
            shell=True, capture_output=True, text=True
        )
        return len(result.stdout) > 0
    except:
        return True  # Em caso de dúvida, assume que está funcionando

def get_firewall_status():
    """Verifica status do firewall/iptables"""
    try:
        result = subprocess.run(
            "sudo iptables -L -n | head -20",
            shell=True, capture_output=True, text=True, timeout=2
        )
        return result.stdout
    except:
        return "Erro ao verificar firewall"

# --- Conexão Docker ---
try:
    client = docker.from_env()
except Exception as e:
    st.error(f"❌ Erro ao conectar com Docker: {e}")
    st.stop()

def get_container(service_name_part):
    containers = client.containers.list(all=True)
    for c in containers:
        if service_name_part in c.name:
            return c
    return None

scp_container = get_container("storescp")
scu_container = get_container("storescu")
dash_container = get_container("dashboard")

# --- Carrega Configurações ---
env_vars = load_env()
HTR_IP = env_vars.get('HTR_IP', '172.22.61.14')
TARGET_HOST = env_vars.get('TARGET_HOST', '192.168.10.16')
TARGET_PORT = env_vars.get('TARGET_PORT', '4243')
TARGET_AET = env_vars.get('TARGET_AET', 'ZEROCLICK')

# ==================== SIDEBAR ====================
st.sidebar.header("⚙️ Status do Sistema")

# Status dos serviços
def show_container_status(container, name, emoji):
    if container:
        status = container.status
        if status == "running":
            st.sidebar.success(f"{emoji} **{name}**: ✅ Ativo")
        else:
            st.sidebar.error(f"{emoji} **{name}**: ❌ {status.upper()}")
        
        col1, col2 = st.sidebar.columns(2)
        if col2.button(f"🔄 Restart", key=f"rst_{name}", use_container_width=True):
            with st.spinner(f"Reiniciando {name}..."):
                container.restart()
                time.sleep(2)
                st.rerun()
    else:
        st.sidebar.warning(f"{emoji} **{name}**: ⚠️ Não encontrado")

show_container_status(scp_container, "Recebimento", "📥")
show_container_status(scu_container, "Envio", "📤")
show_container_status(dash_container, "Dashboard", "📊")

st.sidebar.divider()

# Testes de Conectividade
st.sidebar.subheader("🌐 Conectividade")

# Teste Rede HTR
htr_listening = check_port_listening(104)
if htr_listening:
    st.sidebar.success(f"✅ Porta 104 escutando em {HTR_IP}")
else:
    st.sidebar.error("❌ Porta 104 não está escutando")

# Teste Rede Clínica
target_reachable = test_connection(TARGET_HOST, TARGET_PORT)
if target_reachable:
    st.sidebar.success(f"✅ Zero Click alcançável ({TARGET_HOST}:{TARGET_PORT})")
else:
    st.sidebar.warning(f"⚠️ Zero Click não responde ({TARGET_HOST}:{TARGET_PORT})")

# Echo Test
if st.sidebar.button("🔍 Executar Echo Test", use_container_width=True):
    with st.spinner("Testando conectividade..."):
        st.sidebar.write("**Teste de Ping HTR:**")
        result_htr = subprocess.run(f"ping -c 2 {HTR_IP}", shell=True, capture_output=True, text=True)
        st.sidebar.code(result_htr.stdout[-200:], language="bash")
        
        st.sidebar.write(f"**Teste de Ping Zero Click:**")
        result_target = subprocess.run(f"ping -c 2 {TARGET_HOST}", shell=True, capture_output=True, text=True)
        st.sidebar.code(result_target.stdout[-200:], language="bash")

st.sidebar.divider()

# Auto-refresh
auto_refresh = st.sidebar.checkbox('🔄 Auto-refresh (10s)', value=False)
if auto_refresh:
    time.sleep(10)
    st.rerun()

# ==================== ABAS PRINCIPAIS ====================
tab1, tab2, tab3, tab4 = st.tabs(["📊 Estudos DICOM", "📝 Logs em Tempo Real", "🔧 Diagnóstico", "⚙️ Configurações"])

# ==================== ABA 1: ESTUDOS DICOM ====================
with tab1:
    st.subheader("📁 Estudos Recebidos e em Processamento")
    
    # Carrega pastas do disco diretamente
    study_folders = get_study_folders()
    
    if not study_folders:
        st.info("ℹ️ Nenhum estudo recebido ainda. Aguardando imagens da tomografia...")
    else:
        # Métricas
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Total de Estudos", len(study_folders))
        with col2:
            total_images = sum([f['file_count'] for f in study_folders])
            st.metric("Total de Imagens", total_images)
        with col3:
            enviados = len([f for f in study_folders if f['status'] == 'enviado'])
            st.metric("✅ Enviados", enviados)
        with col4:
            falhas = len([f for f in study_folders if f['status'] == 'falha'])
            st.metric("❌ Falhas", falhas)
        with col5:
            pendentes = len([f for f in study_folders if f['status'] == 'pendente'])
            st.metric("⏳ Pendentes", pendentes)
        
        st.divider()
        
        # Lista de estudos com botão de reenvio
        st.write("### 📋 Lista de Estudos no Disco")
        
        # Função para obter ícone de status
        def get_status_icon(status):
            icons = {
                'enviado': '✅',
                'falha': '❌',
                'pendente': '⏳',
                'enviando': '🔄'
            }
            return icons.get(status, '❓')
        
        def get_status_color(status):
            colors = {
                'enviado': 'green',
                'falha': 'red',
                'pendente': 'orange',
                'enviando': 'blue'
            }
            return colors.get(status, 'gray')
        
        for idx, folder in enumerate(study_folders):
            status_icon = get_status_icon(folder['status'])
            status_text = folder['status'].upper()
            
            with st.expander(f"{status_icon} {folder['name']} ({folder['file_count']} imagens) - **{status_text}**", expanded=False):
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.write(f"**Pasta:** `{folder['path']}`")
                    st.write(f"**Arquivos DICOM:** {folder['file_count']}")
                    st.write(f"**Tamanho:** {folder['size_mb']:.2f} MB")
                    
                    # Mostrar status detalhado
                    st.divider()
                    status_color = get_status_color(folder['status'])
                    st.markdown(f"**Status:** :{status_color}[{status_icon} {status_text}]")
                    
                    if folder['last_update']:
                        st.write(f"**Última atualização:** {folder['last_update']}")
                    
                    if folder['status_message']:
                        st.write(f"**Mensagem:** {folder['status_message'][:100]}")
                    
                    if folder['status'] in ['enviado', 'falha'] and folder['total_count'] > 0:
                        st.write(f"**Enviados:** {folder['sent_count']}/{folder['total_count']} arquivos")
                
                with col2:
                    # Botão de Reenvio
                    if st.button("🔄 Reenviar ao ZeroClick", key=f"resend_{idx}", type="primary", use_container_width=True):
                        with st.spinner(f"Reenviando estudo para {TARGET_HOST}:{TARGET_PORT}..."):
                            success, message = resend_study(
                                folder['path'], 
                                TARGET_HOST, 
                                TARGET_PORT, 
                                TARGET_AET
                            )
                            if success:
                                st.success(f"✅ {message}")
                            else:
                                st.error(f"❌ {message}")
                            st.rerun()
                
                with col3:
                    # Botão para ver arquivos
                    if st.button("📂 Ver Arquivos", key=f"view_{idx}", use_container_width=True):
                        try:
                            files = list(folder['path'].glob("*.dcm"))[:20]
                            st.write("**Primeiros 20 arquivos:**")
                            for f in files:
                                st.text(f"• {f.name}")
                            if folder['file_count'] > 20:
                                st.text(f"... e mais {folder['file_count'] - 20} arquivos")
                        except Exception as e:
                            st.error(f"Erro: {e}")
        
        st.divider()
        
        # Reenvio em lote
        st.write("### 🔄 Reenvio em Lote")
        col1, col2 = st.columns(2)
        
        with col1:
            selected_studies = st.multiselect(
                "Selecione os estudos para reenviar:",
                options=[f['name'] for f in study_folders],
                key="batch_select"
            )
        
        with col2:
            if st.button("🚀 Reenviar Selecionados", type="primary", disabled=len(selected_studies) == 0):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for i, study_name in enumerate(selected_studies):
                    folder = next((f for f in study_folders if f['name'] == study_name), None)
                    if folder:
                        status_text.text(f"Enviando: {study_name}...")
                        success, message = resend_study(
                            folder['path'], 
                            TARGET_HOST, 
                            TARGET_PORT, 
                            TARGET_AET
                        )
                        if success:
                            st.success(f"✅ {study_name}: Enviado com sucesso!")
                        else:
                            st.error(f"❌ {study_name}: {message}")
                    
                    progress_bar.progress((i + 1) / len(selected_studies))
                
                status_text.text("Concluído!")
        
        st.divider()
        
        # Informações de disco
        st.write("### 💾 Uso de Disco")
        try:
            result = subprocess.run("df -h /home/dicom", shell=True, capture_output=True, text=True)
            st.code(result.stdout, language="bash")
        except:
            st.warning("Não foi possível verificar uso de disco")

# ==================== ABA 2: LOGS ====================
with tab2:
    def parse_logs(container, lines=100):
        if not container:
            return []
        logs = container.logs(tail=lines).decode('utf-8', errors='ignore').split('\n')
        return [l for l in logs if l.strip()]

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📥 Recebimento (HTR → Servidor)")
        if scp_container:
            logs_scp = parse_logs(scp_container)
            st.text_area("Logs SCP", value="\n".join(logs_scp[::-1]), height=500, key="logs_scp")
        else:
            st.info("Container SCP não encontrado")

    with col2:
        st.subheader("📤 Envio (Servidor → Zero Click)")
        if scu_container:
            logs_scu = parse_logs(scu_container)
            st.text_area("Logs SCU", value="\n".join(logs_scu[::-1]), height=500, key="logs_scu")
        else:
            st.info("Container SCU não encontrado")

# ==================== ABA 3: DIAGNÓSTICO ====================
with tab3:
    st.subheader("🔧 Informações de Diagnóstico")
    
    diag_col1, diag_col2 = st.columns(2)
    
    with diag_col1:
        st.write("**🔌 Portas em Uso:**")
        try:
            result = subprocess.run(
                "sudo netstat -tlnp | grep -E ':104|:4100|:8501|:4243'",
                shell=True, capture_output=True, text=True
            )
            if result.stdout:
                st.code(result.stdout, language="bash")
            else:
                st.warning("Nenhuma porta DICOM detectada")
        except:
            st.error("Erro ao verificar portas")
        
        st.write("**🛣️ Tabela de Rotas:**")
        try:
            result = subprocess.run("ip route show", shell=True, capture_output=True, text=True)
            st.code(result.stdout, language="bash")
        except:
            st.error("Erro ao verificar rotas")
    
    with diag_col2:
        st.write("**🖧 Interfaces de Rede:**")
        try:
            result = subprocess.run(
                "ip addr show | grep -E 'inet |^[0-9]'",
                shell=True, capture_output=True, text=True
            )
            st.code(result.stdout, language="bash")
        except:
            st.error("Erro ao verificar interfaces")
        
        st.write("**🛡️ Firewall (iptables):**")
        try:
            firewall_status = get_firewall_status()
            st.code(firewall_status, language="bash")
        except:
            st.error("Erro ao verificar firewall")
    
    st.divider()
    
    # Botão para diagnóstico completo
    if st.button("📋 Gerar Relatório Completo de Diagnóstico", type="primary"):
        with st.spinner("Gerando relatório..."):
            report = f"""
=== RELATÓRIO DE DIAGNÓSTICO ===
Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

1. CONTAINERS DOCKER:
{subprocess.run('cd /home/prowess/dicomrs && sudo docker compose ps', shell=True, capture_output=True, text=True).stdout}

2. PORTAS:
{subprocess.run("sudo netstat -tlnp | grep -E ':104|:4100|:8501'", shell=True, capture_output=True, text=True).stdout}

3. CONECTIVIDADE:
Ping HTR ({HTR_IP}):
{subprocess.run(f'ping -c 2 {HTR_IP}', shell=True, capture_output=True, text=True).stdout}

Ping Zero Click ({TARGET_HOST}):
{subprocess.run(f'ping -c 2 {TARGET_HOST}', shell=True, capture_output=True, text=True).stdout}

4. DISCO:
{subprocess.run('df -h /home/dicom', shell=True, capture_output=True, text=True).stdout}

5. ARQUIVOS DICOM:
{subprocess.run('ls -lh /home/prowess/dicomrs/dicom/ | head -20', shell=True, capture_output=True, text=True).stdout}
"""
            st.download_button(
                label="💾 Baixar Relatório",
                data=report,
                file_name=f"diagnostic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
            )
            st.code(report, language="bash")

# ==================== ABA 4: CONFIGURAÇÕES ====================
with tab4:
    st.subheader("⚙️ Configurações do Sistema")
    
    st.write("**Arquivo .env atual:**")
    if ENV_FILE.exists():
        with open(ENV_FILE, 'r') as f:
            env_content = f.read()
        st.code(env_content, language="bash")
    else:
        st.warning("Arquivo .env não encontrado")
    
    st.divider()
    
    st.write("**📍 Caminhos Importantes:**")
    st.code(f"""
Workspace: /home/prowess/dicomrs/
Arquivos DICOM: {DICOM_ROOT}
Metadados: {METADATA_FILE}
Configuração: {ENV_FILE}
    """, language="bash")
    
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Reiniciar Todos os Serviços", type="primary"):
            with st.spinner("Reiniciando containers..."):
                subprocess.run("cd /home/prowess/dicomrs && sudo docker compose restart", shell=True)
                time.sleep(3)
                st.success("✅ Serviços reiniciados!")
                time.sleep(1)
                st.rerun()
    
    with col2:
        if st.button("🧹 Limpar Metadados (Cuidado!)", type="secondary"):
            if METADATA_FILE.exists():
                METADATA_FILE.unlink()
                st.success("✅ Metadados limpos!")
                st.rerun()

# Rodapé
st.divider()
st.markdown("""
<div style='text-align: center; color: gray; font-size: 0.8em;'>
DICOM Router v2.0 | Desenvolvido para LCC | Última atualização: Janeiro 2026
</div>
""", unsafe_allow_html=True)
