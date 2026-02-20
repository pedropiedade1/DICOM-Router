import streamlit as st
import docker
import pandas as pd
import time
from datetime import datetime
import re

# Configuração da Página
st.set_page_config(
    page_title="DICOM Router Manager",
    page_icon="🏥",
    layout="wide"
)

st.title("🏥 Painel de Controle - DICOM Router")

# Conexão com o Docker
try:
    client = docker.from_env()
except Exception as e:
    st.error(f"Erro ao conectar com Docker: {e}")
    st.stop()

# Definição dos nomes dos containers (baseado no docker-compose)
# O nome geralmente é pasta_servico_1, mas vamos buscar por rótulos ou nomes parciais para ser seguro
def get_container(service_name_part):
    containers = client.containers.list(all=True)
    for c in containers:
        if service_name_part in c.name:
            return c
    return None

scp_container = get_container("storescp")
scu_container = get_container("storescu")

# --- Sidebar: Status e Controle ---
st.sidebar.header("Status dos Serviços")

def show_status(container, name):
    if container:
        status = container.status
        color = "green" if status == "running" else "red"
        st.sidebar.markdown(f"**{name}**: :{color}[{status.upper()}]")
        
        col1, col2 = st.sidebar.columns(2)
        if col1.button(f"Oferecer Logs {name}", key=f"log_{name}"):
            pass # Apenas atualiza a página
        if col2.button(f"Restart {name}", type="primary", key=f"rst_{name}"):
            with st.spinner(f"Reiniciando {name}..."):
                container.restart()
                time.sleep(2)
                st.rerun()
    else:
        st.sidebar.warning(f"{name} não encontrado")

show_status(scp_container, "Recebimento (SCP)")
show_status(scu_container, "Envio (SCU)")

st.sidebar.divider()
auto_refresh = st.sidebar.checkbox('Auto-refresh logs (5s)', value=False)
if auto_refresh:
    time.sleep(5)
    st.rerun()

# --- Área Principal: Logs ---

def parse_logs(container, lines=50):
    if not container:
        return []
    
    # Pega os logs brutos (bytes) e decodifica
    logs = container.logs(tail=lines).decode('utf-8', errors='ignore').split('\n')
    return [l for l in logs if l.strip()]

col1, col2 = st.columns(2)

with col1:
    st.subheader("📥 Recebimento (HTR -> Local)")
    if scp_container:
        logs_scp = parse_logs(scp_container)
        # Inverte para mostrar o mais recente no topo
        st.text_area("Logs HTR", value="\n".join(logs_scp[::-1]), height=400)
    else:
        st.info("Container SCP aguardando...")

with col2:
    st.subheader("📤 Envio (Local -> Zero Click)")
    if scu_container:
        logs_scu = parse_logs(scu_container)
        st.text_area("Logs Envio", value="\n".join(logs_scu[::-1]), height=400)
    else:
        st.info("Container SCU aguardando...")

# Rodapé com instruções
st.divider()
st.markdown("""
**Legenda:**
* **Recebimento:** Mostra logs do `storescp` ouvindo na porta 104.
* **Envio:** Mostra logs do script Python processando e enviando para o Zero Click.
""")
