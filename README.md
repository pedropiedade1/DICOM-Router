# 🏥 DICOM Router - Documentação Completa

> **Versão 2.0** | Janeiro 2026 | Liga de Combate ao Câncer

## 📚 Índice da Documentação

### 🚀 Início Rápido
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Guia rápido com comandos essenciais
- **[UPGRADE_SUMMARY.md](UPGRADE_SUMMARY.md)** - ⭐ Resumo das novidades v2.0

### 🔧 Operação e Manutenção
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - ⭐ Guia completo de resolução de problemas
- **[IMPLEMENTATION_NOTES.md](IMPLEMENTATION_NOTES.md)** - Detalhes técnicos da v2.0

### 🎯 Este Documento (README.md)
Documentação técnica original sobre conectividade e segurança.

---

## ✨ Novidades da v2.0

### 📁 Organização Automática de Arquivos
- Arquivos DICOM organizados em pastas por paciente
- Estrutura: `TIMESTAMP_PatientID_PatientName/`
- Imagens do mesmo estudo agrupadas automaticamente
- Metadados persistentes em `.metadata.json`

### 📊 Dashboard Avançado
- Tabela de estudos com: Paciente, ID, Modalidade, Imagens, Status
- Testes de conectividade (HTR e Zero Click)
- Status de firewall, portas e rotas
- Echo tests com ping
- Diagnóstico completo exportável
- Monitoramento de disco em tempo real

### 🔧 Melhor Troubleshooting
- Guia completo de diagnóstico
- Comandos prontos para uso
- Checklist de verificação
- Histórico de problemas resolvidos

### 📖 Para Atualizar
Execute: `./upgrade_to_v2.sh`  
Ou leia: [UPGRADE_SUMMARY.md](UPGRADE_SUMMARY.md)

---

## Visão Geral
Este serviço atua como um "Store-and-Forward" (Roteador DICOM) para intermediar o envio de imagens entre a rede de equipamentos (HTR/Tomografia) e a rede clínica (Radioterapia/Zero Click). O sistema opera em containers Docker isolados.

## Topologia de Rede
O servidor hospedeiro deve possuir duas interfaces de rede (NICs) ou rotas distintas para garantir o isolamento ou direcionamento correto do tráfego:
1. **Rede HTR**: Dedicada ao recebimento de imagens da Tomografia.
2. **Rede Clínica**: Dedicada ao envio de imagens para o sistema Zero Click.

## Fluxo de Dados e Portas

### 1. Entrada (Inbound) - Recebimento
*   **Serviço:** DICOM Store SCP (Container `storescp`)
*   **Protocolo:** DICOM (Baseado em TCP)
*   **Porta Local:** `104`
*   **Interface de Escuta:** O serviço é configurado para ouvir **apenas** no IP da interface da rede HTR (`172.22.61.14` definido na variável `HTR_IP` no arquivo `.env`).
*   **Origem do Tráfego:** Equipamentos de imagem (CT Scanners) na rede HTR.
*   **Segurança de Rede:** Ao vincular a porta 104 especificamente ao IP `172.22.61.14`, previne-se que dispositivos na rede Clínica ou outras interfaces acessem este serviço de recepção.

### 2. Saída (Outbound) - Envio
*   **Serviço:** DICOM Store SCU (Container `storescu`)
*   **Protocolo:** DICOM (Baseado em TCP)
*   **Porta de Destino:** `4243` (Padrão, configurável via `TARGET_PORT` no `.env`)
*   **Destino:** Servidor Zero Click (`TARGET_HOST`, padrão: 192.168.10.16).
*   **Mecanismo:** O container inicia uma conexão TCP ativa (client) para o servidor de destino. O roteamento para a interface de rede correta (Rede Clínica) é gerenciado pela tabela de rotas do Sistema Operacional hospedeiro.

## Armazenamento de Dados (Data at Rest)
*   **Localização:** As imagens são salvas temporariamente em um volume Docker mapeado para a pasta `./dicom` no host.
*   **Ciclo de Vida:** O sistema opera em regime de fluxo contínuo.
    1. A imagem é recebida e gravada em disco.
    2. O serviço de envio detecta o arquivo novo.
    3. Após a confirmação de recebimento bem-sucedido pelo destino (Zero Click), **o arquivo é deletado imediatamente** do disco local.
    *   *Nota: Se o destino estiver indisponível, os arquivos acumularão em disco até que a conexão seja restabelecida.*

## Matriz de Firewall Necessária

| Direção | Origem IP | Porta Origem | Destino IP | Porta Destino | Protocolo | Descrição |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Entrada** | `[IP da Tomografia]` | `Qualquer` | **`172.22.61.14`** | `104` | TCP | Recebimento de Imagens |
| **Saída** | `[IP Placa Clínica]` | `Qualquer` | `192.168.10.16` | `4243` | TCP | Envio para Zero Click |

## Considerações de Segurança
1.  **Sem Criptografia:** O protocolo DICOM padrão utilizado trafega dados (incluindo PHI - Protected Health Information) em texto claro/binário sem criptografia. É mandatório que as redes HTR e Clínica sejam redes locais seguras (LAN/VLAN) sem acesso público.
2.  **Validação de AETitle:** O serviço de recepção (`storescp`) está configurado em modo "promíscuo", aceitando conexões de qualquer AETitle. Isso visa operacionalidade para evitar rejeições por erros de configuração nas modalidades, mas não implementa lista branca de dispositivos.
3.  **Isolamento de Processos:** Os serviços rodam em containers Docker com privilégios limitados, sem acesso direto ao restante do sistema de arquivos do host além do volume compartilhado.

## Deploy e Inicialização (Linux Server)

### Pré-requisitos
*   Docker e Docker Compose instalados.
*   Usuário com permissão no grupo `docker`.
*   Arquivo `.env` configurado conforme instruções acima.

### Instalação como Serviço (Systemd)
Para garantir que o serviço inicie automaticamente com o servidor e possa ser gerenciado de forma robusta:

1.  Copie o repositório para uma pasta padrão, ex: `/opt/dicomrs`.
2.  Copie o arquivo de serviço:
    ```bash
    sudo cp dicomrs.service /etc/systemd/system/
    ```
3.  Edite o arquivo para ajustar o caminho correto:
    ```bash
    sudo nano /etc/systemd/system/dicomrs.service
    # Ajuste 'WorkingDirectory' para /opt/dicomrs (ou onde clonou)
    # Ajuste 'ExecStart' com o caminho correto do docker-compose (descubra com 'which docker-compose')
    ```
4.  Habilite a inicialização automática e inicie:
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable dicomrs
    sudo systemctl start dicomrs
    ```

### Monitoramento
*   **Via Terminal:**
    ```bash
    docker-compose logs -f
    ```
*   **Via Dashboard Web:**
    Acesse `http://<IP_DO_SERVIDOR>:8501` para visualizar logs em tempo real e reiniciar serviços individualmente.
# DICOM-Router
