#!/bin/bash

# Script de Instalação Automática para Servidores Debian/Ubuntu
# Instala Docker, Docker Compose (Plugin) e Git

set -e # Para o script se houver erro

echo ">> [1/4] Atualizando o sistema..."
sudo apt-get update && sudo apt-get upgrade -y

echo ">> [2/4] Instalando dependências (curl, git, ca-certificates)..."
sudo apt-get install -y ca-certificates curl gnupg git

echo ">> [3/4] Configurando repositório oficial do Docker..."
# Cria diretório de chaves se não existir
sudo install -m 0755 -d /etc/apt/keyrings
# Baixa a chave GPG oficial do Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Adiciona o repositório nas fontes do apt
echo \
  "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

echo ">> [4/4] Instalando Docker Engine e Docker Compose..."
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Adiciona usuário ao grupo docker
if ! groups $USER | grep &>/dev/null '\bdocker\b'; then
    echo ">> Adicionando usuário $USER ao grupo docker..."
    sudo usermod -aG docker $USER
fi

echo "-------------------------------------------------------"
echo "Instalação concluída com sucesso!"
echo "IMPORTANTE: É necessário fazer Logout e Login (ou reiniciar) para atualizar as permissões do usuário."
echo "-------------------------------------------------------"
echo "Para verificar a instalação após o login, execute:"
echo "docker compose version"
