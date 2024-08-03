# Serverless API para Previsão de Sobrevivência no Titanic

Este projeto implementa uma API serverless para prever a sobrevivência de passageiros do Titanic usando um modelo de Machine Learning. A API é implementada usando AWS Lambda, API Gateway e DynamoDB, com a infraestrutura provisionada via Terraform.  A API expõe endpoints para avaliar a sobrevivência dos passageiros, bem como para manipular dados de passageiros armazenados no DynamoDB.

## Estrutura do Projeto

- `main.tf`: Configuração principal do Terraform.
- `variables.tf`: Declaração de variáveis.
- `terraform.tfvars`: Valores das variáveis.
- `lambda_function.py`: Código da função Lambda que realiza a previsão.
- `lambda_function.zip`: Arquivo zip contendo a função Lambda.
- `model.pkl`: Arquivo do modelo de Machine Learning (que será armazenado no S3).
- `README.md`: Este arquivo.

## Pré-requisitos

- Conta na AWS.
- Terraform instalado.
- AWS CLI configurada localmente.

## Configuração

### Configuração do AWS CLI

Execute `aws configure` e forneça suas credenciais da AWS

## Peças do Projeto
- `Lambda Function:` Função AWS Lambda que carrega um modelo de Machine Learning e expõe endpoints para escorar o modelo e manipular dados no DynamoDB.
- `API Gateway`: Configurado para criar uma API REST que interage com a função Lambda.
- `DynamoDB`: Armazena as avaliações de sobrevivência dos passageiros.
- `S3 Bucket`: Armazena o modelo de Machine Learning.

## Funcionalidade da Lambda Function
A Lambda Function implementa os seguintes métodos HTTP:

- `GET /sobreviventes`: Retorna a lista de passageiros avaliados.
- `GET /sobreviventes/{id}`: Retorna a probabilidade de sobrevivência do passageiro com o ID especificado.
- `POST /sobreviventes`: Recebe um JSON com características do passageiro e retorna a probabilidade de sobrevivência.
- `DELETE /sobreviventes/{id}`: Remove o passageiro com o ID especificado.


## Executando o Projeto
** Configuração do Terraform: ** 

Atualize as variáveis no arquivo terraform.tfvars com as informações necessárias para seu ambiente AWS.
Execute terraform init para inicializar o Terraform.
Execute terraform apply para criar os recursos na AWS.


Certifique-se de que o código da Lambda Function está comprimido e disponível em ${path.module}/../lambda_function/lambda_function.zip.
A função Lambda será automaticamente implantada quando você executar o Terraform.

##Testando a API:

Após o deployment, você receberá um endpoint URL.
Use ferramentas como curl ou Postman para enviar requisições HTTP para o endpoint.

##Notas
Certifique-se de que o arquivo lambda_function.zip contém todos os pacotes e dependências necessários.
Ajuste o modelo e as variáveis de ambiente conforme necessário para seu caso de uso específico.

