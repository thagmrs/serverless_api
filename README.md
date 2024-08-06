# Serverless API para Previsão de Sobrevivência no Titanic

Este projeto implementa uma API serverless para prever a sobrevivência de passageiros do Titanic usando um modelo de Machine Learning. A API é implementada usando AWS Lambda, API Gateway e DynamoDB, com a infraestrutura provisionada via Terraform.  A API expõe endpoints para avaliar a sobrevivência dos passageiros, bem como para manipular dados de passageiros armazenados no DynamoDB.

## Estrutura do Projeto

- `main.tf`: Configuração principal do Terraform.
- `variables.tf`: Declaração de variáveis.
- `lambda_function.py`: Código da função Lambda que realiza a previsão.
- `encoder_decinal.py`: Código contendo encoder para conversão de tipos aceitos pelo DynamoDB
- `model.pkl`: Arquivo do modelo de Machine Learning (que será armazenado no S3).
- `Dockerfile`: Arquivo Docker para criar a imagem da função Lambda.
- `README.md`: Este arquivo.

## Pré-requisitos

- Conta na AWS.
- Terraform instalado.
- AWS CLI configurada localmente.

## Configuração

### Configuração do AWS CLI

Execute `aws configure` e forneça suas credenciais da AWS

- **Lambda Function:** Função AWS Lambda que carrega um modelo de Machine Learning e expõe endpoints para escorar o modelo e manipular dados no DynamoDB.
- **API Gateway:** Configurado para criar uma API REST que interage com a função Lambda.
- **DynamoDB:** Armazena as avaliações de sobrevivência dos passageiros.
- **S3 Bucket:** Armazena o modelo de Machine Learning.
- **ECR (Elastic Container Registry):** Armazena a imagem Docker da função Lambda.

## Funcionalidade da Lambda Function
A Lambda Function implementa os seguintes métodos HTTP:

- `GET /sobreviventes`: Retorna a lista de passageiros avaliados.
- `GET /sobreviventes/{id}`: Retorna a probabilidade de sobrevivência do passageiro com o ID especificado.
- `POST /sobreviventes`: Recebe um JSON com características do passageiro e retorna a probabilidade de sobrevivência.
- `DELETE /sobreviventes/{id}`: Remove o passageiro com o ID especificado.
-`/health`: Verifica o status (saúde) da API


## Executando o Projeto
**Configuração do Terraform:** 

1. Criação da imagem Docker e upload para o ECR
2. Execute terraform init para inicializar o Terraform dentro da pasta /terraform
3. Execute terraform apply para criar os recursos na AWS

## Criação e Upload da Imagem Docker para ECR:

1. Login no ECR:

   ```sh 
   aws ecr get-login-password --region <region> | docker login --username AWS --password-stdin <client_id>.dkr.ecr.<region>.amazonaws.com 
   ```
2. Construir a Imagem Docker
   ```sh 
   docker build -t lambda-image . 
   ```
3. Tag da imagem docker
   ```sh 
   docker tag lambda-image <client_id>.dkr.ecr.<region>.amazonaws.com/{repository_name}:{version} 
   ```
4. Push da Imagem docker
   ```sh 
   docker push <client_id>.dkr.ecr.<region>.amazonaws.com/{repository_name}:{version}  
   ```
## Execução do Terraform

1. Na pasta /terraform execute:
terraform init

2. Aplique as configurações:
terraform apply

## Testando a API:

Após o deployment, você receberá um endpoint URL.
Use ferramentas como curl ou Postman para enviar requisições HTTP para o endpoint.

## Documentação:
Uma documentação swagger mockada está disponível em:
https://app.swaggerhub.com/apis-docs/THAGMRS_1/survivors/2.0.0