# 🔧 Guia de Troubleshooting - DICOM Router

## Última atualização: Janeiro 2026

---

## 📋 Índice
1. [Verificação Rápida de Status](#verificação-rápida-de-status)
2. [Problemas de Conectividade](#problemas-de-conectividade)
3. [Problemas de Recebimento (Porta 104)](#problemas-de-recebimento)
4. [Problemas de Envio](#problemas-de-envio)
5. [Problemas de Disco](#problemas-de-disco)
6. [Problemas de Rede e Firewall](#problemas-de-rede-e-firewall)
7. [Reinicialização dos Serviços](#reinicialização-dos-serviços)
8. [Configuração de Rotas](#configuração-de-rotas)

---

## Verificação Rápida de Status

### 1. Verificar containers Docker
```bash
cd /home/prowess/dicomrs
sudo docker compose ps
```
**Esperado:** Todos os containers com status "Up"

### 2. Verificar portas em uso
```bash
sudo netstat -tlnp | grep -E ":104|:4100|:8501"
```
**Esperado:**
- `172.22.61.14:104` - Recebimento DICOM (rede HTR)
- `0.0.0.0:4100` - Gestão interna
- `0.0.0.0:8501` - Dashboard web

### 3. Verificar fila de arquivos
```bash
ls -l /home/prowess/dicomrs/dicom/ | wc -l
du -sh /home/prowess/dicomrs/dicom/
```
**Normal:** Poucos arquivos (processamento rápido)  
**Atenção:** Mais de 1000 arquivos ou > 2GB

### 4. Acessar Dashboard
Abra no navegador: `http://<IP_SERVIDOR>:8501`

---

## Problemas de Conectividade

### Sintoma: Tomografia não consegue enviar imagens

#### Passo 1: Verificar se a porta 104 está escutando
```bash
sudo netstat -tlnp | grep :104
```
**Esperado:** `172.22.61.14:104`  
**Se não aparecer:** Container SCP não está rodando

#### Passo 2: Testar conectividade da rede HTR
```bash
ping 172.22.61.14
```
**Se falhar:** Problema na interface de rede `enp2s0`

#### Passo 3: Verificar configuração do AET na tomografia
- AET Title pode ser qualquer valor (modo promíscuo)
- IP destino: `172.22.61.14`
- Porta: `104`
- Protocolo: DICOM Store (C-STORE)

#### Passo 4: Verificar logs do container SCP
```bash
cd /home/prowess/dicomrs
sudo docker compose logs --tail=50 storescp
```
**Procure por:** "Association Received" ou "Received Store Request"

---

## Problemas de Recebimento

### Sintoma: Container SCP parou/crashou

#### Solução 1: Reiniciar container
```bash
cd /home/prowess/dicomrs
sudo docker compose restart storescp
```

#### Solução 2: Verificar se porta 104 está em uso
```bash
sudo lsof -i :104
```
**Se houver outro processo:** Matar processo ou mudar porta

#### Solução 3: Verificar permissões da pasta
```bash
ls -la /home/prowess/dicomrs/dicom/
```
**Deve permitir escrita pelo container (root)**

---

## Problemas de Envio

### Sintoma: Arquivos acumulando na pasta `/dicom`

#### Passo 1: Verificar conectividade com Zero Click
```bash
ping 192.168.10.16
telnet 192.168.10.16 4243
```
**Se ping falhar:** Problema de rota  
**Se telnet falhar:** Firewall bloqueando ou serviço down

#### Passo 2: Verificar logs do container SCU
```bash
cd /home/prowess/dicomrs
sudo docker compose logs --tail=100 storescu
```
**Procure por:** "Erro ao enviar" ou timeouts

#### Passo 3: Verificar se Zero Click está aceitando conexões
- Confirmar que AET no destino é "ZEROCLICK"
- Verificar se porta 4243 está aberta no firewall do destino

#### Solução: Reprocessar arquivos parados
```bash
cd /home/prowess/dicomrs
sudo docker compose restart storescu
```

---

## Problemas de Disco

### Sintoma: Disco cheio ou quase cheio

#### Verificar espaço em disco
```bash
df -h /home/prowess/dicomrs/dicom/
```

#### Limpar arquivos antigos (CUIDADO!)
```bash
# Verificar arquivos mais antigos
ls -lt /home/prowess/dicomrs/dicom/ | tail -20

# Limpar manualmente (SE NECESSÁRIO)
# ATENÇÃO: Só faça isso se tiver certeza que foram enviados!
cd /home/prowess/dicomrs/dicom/
sudo rm -f *.dcm
```

#### Prevenir: Verificar se envio está funcionando
O sistema deleta automaticamente após envio bem-sucedido.

---

## Problemas de Rede e Firewall

### Configuração das Duas Redes

#### Rede HTR (Tomografia)
- **Interface:** `enp2s0`
- **IP:** `172.22.61.14/22`
- **Gateway:** Próprio da rede HTR

#### Rede Clínica (Zero Click)
- **Interface:** `enxc8a362c5f56a`
- **IP:** `192.168.12.35` (principal)
- **Gateway:** `192.168.12.1`

### Verificar rotas configuradas
```bash
ip route show
```

**Rotas necessárias:**
```
172.22.60.0/22 dev enp2s0
192.168.10.9 via 192.168.12.1
192.168.10.113 via 192.168.12.1
```

### Adicionar rota manualmente (se necessário)
```bash
sudo ip route add 192.168.10.16/32 via 192.168.12.1 dev enxc8a362c5f56a
```

### Verificar interfaces de rede
```bash
ip addr show
```

### Testar conectividade entre redes
```bash
# Teste rede HTR
ping -c 3 172.22.61.14

# Teste rede Clínica
ping -c 3 192.168.10.16
```

---

## Reinicialização dos Serviços

### Reiniciar apenas containers (recomendado)
```bash
cd /home/prowess/dicomrs
sudo docker compose restart
```
**Downtime:** ~10 segundos

### Reiniciar containers do zero
```bash
cd /home/prowess/dicomrs
sudo docker compose down
sudo docker compose up -d
```
**Downtime:** ~20 segundos

### Verificar serviço systemd
```bash
sudo systemctl status dicomrs
```

### Reiniciar via systemd
```bash
sudo systemctl restart dicomrs
```

### Verificar se serviço inicia no boot
```bash
sudo systemctl is-enabled dicomrs
```
**Esperado:** "enabled"

---

## Comandos Úteis de Diagnóstico

### Monitorar logs em tempo real
```bash
cd /home/prowess/dicomrs
sudo docker compose logs -f
```

### Ver logs específicos de um serviço
```bash
sudo docker compose logs -f storescp   # Recebimento
sudo docker compose logs -f storescu   # Envio
sudo docker compose logs -f dashboard  # Dashboard
```

### Verificar uso de recursos
```bash
docker stats --no-stream
```

### Inspecionar um container
```bash
docker inspect dicomrs-storescp-1
```

### Entrar em um container (debug avançado)
```bash
docker exec -it dicomrs-storescp-1 /bin/bash
```

---

## Checklist de Troubleshooting Completo

- [ ] Containers rodando? `docker compose ps`
- [ ] Portas escutando? `netstat -tlnp`
- [ ] Fila de arquivos normal? `ls dicom/ | wc -l`
- [ ] Ping para HTR funciona? `ping 172.22.61.14`
- [ ] Ping para Zero Click funciona? `ping 192.168.10.16`
- [ ] Rotas configuradas? `ip route show`
- [ ] Espaço em disco OK? `df -h`
- [ ] Dashboard acessível? `http://IP:8501`
- [ ] Logs sem erros? `docker compose logs`

---

## Contatos e Informações

### Variáveis de Configuração (.env)
```bash
HTR_IP=172.22.61.14         # IP da rede HTR (recebimento)
TARGET_HOST=192.168.10.16   # IP do Zero Click (envio)
TARGET_PORT=4243            # Porta DICOM do Zero Click
TARGET_AET=ZEROCLICK        # AET Title do destino
```

### Arquivos Importantes
- `/home/prowess/dicomrs/.env` - Configurações
- `/home/prowess/dicomrs/docker-compose.yml` - Orquestração
- `/home/prowess/dicomrs/dicom/` - Fila de arquivos
- `/etc/systemd/system/dicomrs.service` - Serviço systemd

---

## Histórico de Problemas Resolvidos

### ✅ Problema: Porta 104 não binding no IP correto
**Solução:** Configurar `HTR_IP=172.22.61.14` no `.env` e usar `${HTR_IP}:104:104` no docker-compose

### ✅ Problema: Não alcança rede 192.168.10.x
**Solução:** Adicionar rotas específicas via gateway 192.168.12.1

### ✅ Problema: Serviço systemd falhando
**Solução:** Erro de binding da porta 104 - resolvido com binding específico ao IP da rede HTR

---

## 🆘 Quando Pedir Ajuda

Se após seguir todos os passos o problema persistir, colete estas informações:

```bash
# Salvar informações de diagnóstico
cd /home/prowess/dicomrs
echo "=== STATUS CONTAINERS ===" > diagnostic.txt
sudo docker compose ps >> diagnostic.txt
echo -e "\n=== PORTAS ===" >> diagnostic.txt
sudo netstat -tlnp | grep -E ":104|:4100|:8501" >> diagnostic.txt
echo -e "\n=== ROTAS ===" >> diagnostic.txt
ip route show >> diagnostic.txt
echo -e "\n=== INTERFACES ===" >> diagnostic.txt
ip addr show >> diagnostic.txt
echo -e "\n=== LOGS SCP ===" >> diagnostic.txt
sudo docker compose logs --tail=50 storescp >> diagnostic.txt
echo -e "\n=== LOGS SCU ===" >> diagnostic.txt
sudo docker compose logs --tail=50 storescu >> diagnostic.txt
echo -e "\n=== DISCO ===" >> diagnostic.txt
df -h >> diagnostic.txt
echo -e "\n=== FILA DICOM ===" >> diagnostic.txt
ls -lh /home/prowess/dicomrs/dicom/ | head -30 >> diagnostic.txt

cat diagnostic.txt
```

---

**Última revisão:** 22/01/2026
