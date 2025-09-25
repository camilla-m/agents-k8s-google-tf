# Scripts para Deploy do ADK Travel Agents

Este conjunto de scripts facilita o deploy, monitoramento e gestão dos agentes ADK Travel no Google Kubernetes Engine (GKE) usando Terraform.

## 📋 Pré-requisitos

Antes de executar os scripts, certifique-se de ter instalado:

- [Google Cloud SDK (gcloud)](https://cloud.google.com/sdk/docs/install)
- [kubectl](https://kubernetes.io/docs/tasks/tools/)
- [Terraform](https://terraform.io/downloads)
- [Docker](https://docs.docker.com/get-docker/)
- [Python 3](https://python.org/downloads/) (para testes)

## 🚀 Scripts Disponíveis

### 1. `quick_setup.sh` - Configuração Rápida
**Uso:** `./scripts/quick_setup.sh PROJECT_ID [REGION]`

Script de configuração inicial que:
- Autentica com o gcloud
- Configura o projeto
- Habilita APIs necessárias
- Executa o deploy principal

**Exemplo:**
```bash
./scripts/quick_setup.sh meu-projeto-gcp us-central1
```

### 2. `deploy.sh` - Deploy Principal
**Uso:** `./scripts/deploy.sh PROJECT_ID [REGION]`

Script principal de deploy que:
- Cria conta de serviço e chaves
- Aplica infraestrutura Terraform
- Constrói e publica imagens Docker
- Deploya recursos Kubernetes
- Configura secrets e configmaps

**Exemplo:**
```bash
./scripts/deploy.sh meu-projeto-gcp us-west1
```

### 3. `test_adk_demo.py` - Testes Automatizados
**Uso:** `python3 scripts/test_adk_demo.py [OPTIONS]`

Script de testes que verifica:
- Conectividade dos serviços
- Endpoints de saúde
- Funcionalidade dos agentes
- Performance do sistema

**Opções:**
- `--url URL`: URL base do serviço (padrão: http://localhost:8080)
- `--namespace NS`: Namespace Kubernetes (padrão: adk-travel)
- `--port PORT`: Porta local para port-forward (padrão: 8080)
- `--skip-port-forward`: Pula configuração automática de port-forward
- `--quick`: Executa apenas testes básicos
- `--verbose`: Saída detalhada

**Exemplos:**
```bash
# Testes completos com port-forward automático
python3 scripts/test_adk_demo.py

# Testes rápidos
python3 scripts/test_adk_demo.py --quick

# Testes contra serviço externo
python3 scripts/test_adk_demo.py --skip-port-forward --url http://external-ip

# Testes com configuração customizada
python3 scripts/test_adk_demo.py --namespace meu-namespace --port 9090
```

### 4. `status.sh` - Monitoramento
**Uso:** `./scripts/status.sh [PROJECT_ID] [REGION] [OPTIONS]`

Script de monitoramento que mostra:
- Status do cluster GKE
- Status dos nodes
- Status dos pods e deployments
- Status dos serviços
- Logs recentes
- Teste de conectividade

**Opções:**
- `--watch`: Modo de monitoramento contínuo (atualiza a cada 10s)
- `--logs`: Mostra logs recentes dos pods

**Exemplos:**
```bash
# Status único
./scripts/status.sh meu-projeto-gcp

# Monitoramento contínuo
./scripts/status.sh meu-projeto-gcp us-central1 --watch

# Status com logs
./scripts/status.sh --logs
```

### 5. `cleanup.sh` - Limpeza de Recursos
**Uso:** `./scripts/cleanup.sh PROJECT_ID [REGION] [--force]`

Script de limpeza que remove:
- Recursos Kubernetes
- Infraestrutura Terraform
- Imagens do Artifact Registry
- Contas de serviço
- Arquivos locais

**Opções:**
- `--force`: Pula confirmações de segurança

**Exemplo:**
```bash
# Limpeza interativa
./scripts/cleanup.sh meu-projeto-gcp

# Limpeza forçada (sem confirmações)
./scripts/cleanup.sh meu-projeto-gcp us-central1 --force
```

## 🔧 Estrutura do Projeto

Os scripts esperam a seguinte estrutura de diretórios:

```
projeto/
├── scripts/
│   ├── deploy.sh
│   ├── quick_setup.sh
│   ├── test_adk_demo.py
│   ├── status.sh
│   └── cleanup.sh
├── terraform/
│   ├── main.tf
│   ├── variables.tf
│   └── outputs.tf
├── k8s/
│   ├── namespace.yaml
│   ├── deployments.yaml
│   ├── services.yaml
│   └── ingress.yaml
└── docker/
    ├── flight-agent/
    │   └── Dockerfile
    ├── hotel-agent/
    │   └── Dockerfile
    └── coordinator/
        └── Dockerfile
```

## 🚀 Fluxo de Deploy Completo

1. **Configuração inicial:**
   ```bash
   ./scripts/quick_setup.sh seu-projeto-id
   ```

2. **Verificar o status:**
   ```bash
   ./scripts/status.sh
   ```

3. **Executar testes:**
   ```bash
   python3 scripts/test_adk_demo.py
   ```

4. **Para fazer port-forward manual:**
   ```bash
   kubectl port-forward service/travel-adk-coordinator 8080:80 -n adk-travel
   ```

## 🧪 Testando os Serviços

Após o deploy, você pode testar os endpoints:

### Health Check
```bash
curl http://localhost:8080/health
```

### Agente de Voos
```bash
curl -X POST http://localhost:8080/agent/flight/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "I need flights to Tokyo next month"}'
```

### Coordenador de Viagem
```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Plan a complete Tokyo trip with flights, hotels, and cultural activities"}'
```

### Planejador de Viagem
```bash
curl -X POST http://localhost:8080/plan \
  -H "Content-Type: application/json" \
  -d '{
    "destination": "Tokyo",
    "days": 4,
    "budget": 3000,
    "interests": ["cultural", "food", "technology"],
    "travel_style": "mid-range"
  }'
```

## 🔍 Monitoramento e Logs

### Ver logs em tempo real
```bash
kubectl logs -f deployment/travel-coordinator -n adk-travel --tail=20
```

### Escalar deployments
```bash
kubectl scale deployment flight-agent --replicas=5 -n adk-travel
```

### Ver métricas de recursos
```bash
kubectl top pods -n adk-travel
kubectl top nodes
```

### Monitorar HPA (se configurado)
```bash
kubectl get hpa -n adk-travel -w
```

## ⚠️ Troubleshooting

### Problemas Comuns

1. **Erro de autenticação:**
   ```bash
   gcloud auth login
   gcloud auth application-default login
   ```

2. **APIs não habilitadas:**
   ```bash
   gcloud services enable container.googleapis.com compute.googleapis.com
   ```

3. **Cluster não encontrado:**
   ```bash
   gcloud container clusters get-credentials adk-travel-cluster --region=us-central1
   ```

4. **Pods não inicializando:**
   ```bash
   kubectl describe pod <pod-name> -n adk-travel
   kubectl logs <pod-name> -n adk-travel
   ```

5. **Problemas de network:**
   ```bash
   kubectl get networkpolicies -n adk-travel
   kubectl get ingress -n adk-travel
   ```

### Comandos Úteis de Debug

```bash
# Ver eventos do cluster
kubectl get events --sort-by='.lastTimestamp' -n adk-travel

# Debug de um pod específico
kubectl describe pod <pod-name> -n adk-travel

# Executar shell em um pod
kubectl exec -it <pod-name> -n adk-travel -- /bin/bash

# Ver configuração de um deployment
kubectl get deployment <deployment-name> -n adk-travel -o yaml

# Verificar secrets
kubectl get secrets -n adk-travel
kubectl describe secret adk-credentials -n adk-travel
```

## 🔐 Segurança

### Boas Práticas

1. **Rotação de chaves:** Rotacione as chaves da conta de serviço regularmente
2. **Princípio do menor privilégio:** Use apenas as permissões IAM necessárias
3. **Network policies:** Configure políticas de rede para restringir tráfego
4. **Secrets management:** Use Google Secret Manager para dados sensíveis
5. **Image scanning:** Escaneie imagens Docker por vulnerabilidades

### Comandos de Segurança

```bash
# Verificar permissões da conta de serviço
gcloud projects get-iam-policy seu-projeto-id

# Listar chaves da conta de serviço
gcloud iam service-accounts keys list --iam-account=adk-travel-sa@seu-projeto-id.iam.gserviceaccount.com

# Rotacionar chave
gcloud iam service-accounts keys create nova-chave.json --iam-account=adk-travel-sa@seu-projeto-id.iam.gserviceaccount.com
```

## 📊 Monitoramento de Produção

Para um ambiente de produção, considere:

1. **Google Cloud Monitoring:** Configure alertas e dashboards
2. **Logging:** Centralize logs com Cloud Logging
3. **Health checks:** Configure health checks mais robustos
4. **Backup:** Configure backup regular dos dados
5. **CI/CD:** Integre com pipelines de CI/CD

## 🆘 Suporte

Para problemas ou dúvidas:
1. Verifique os logs dos scripts
2. Consulte a documentação do GKE e Terraform
3. Verifique o status dos recursos no Google Cloud Console
4. Use o script `status.sh` para diagnóstico

## 📝 Notas

- Os scripts foram testados no Linux e macOS
- Para Windows, use WSL ou Git Bash
- Certifique-se de ter as permissões adequadas no projeto GCP
- O billing deve estar habilitado no projeto
- Alguns recursos podem incorrer em custos no Google Cloud