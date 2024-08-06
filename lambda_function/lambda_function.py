import json
import boto3
import os
import joblib
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
import pandas as pd
import logging
from encoder_decimal import CustomEncoder
import sklearn
import sys
from decimal import Decimal

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Inicialize o cliente DynamoDB e s3
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')

# Obtenha o nome da tabela a partir das variáveis de ambiente
table_name = os.environ.get('DYNAMODB_TABLE')
table = dynamodb.Table(table_name)

bucket_name = os.environ.get('S3_BUCKET_NAME')
model_key = os.environ.get('S3_MODEL_KEY')


#Função para carregar o modelo
def load_model_from_s3(bucket_name, model_key):
    try:
        logger.info(f"loading model from bucket: {bucket_name}, key: {model_key}")
        s3.download_file(bucket_name, model_key, '/tmp/model.pkl')
        with open('/tmp/model.pkl', 'rb') as f:
            model = joblib.load(f)
        logger.info(f"model loaded: {model}")
        return model
    except Exception as e:
        logger.error(f"ERROR loading model:  {str(e)}")
        raise

#metodos a serem definidos
getMethod = 'GET'
postMethod = 'POST'
deleteMethod = 'DELETE'
healthPath = '/health'
endpointPath = '/sobreviventes'

def lambda_handler(event, context):
    logger.info(event)
    httpMethod = event['httpMethod']
    path = event['path']
    path_parameters = event.get('queryStringParameters')

    try:
        #metodo que verifica a saude da API
        if httpMethod == getMethod and path == healthPath:
            response = buildResponse(200)

        elif httpMethod == getMethod and path == endpointPath:
        #metodo para retornar a lista de todos os passageiros analisados
            if path_parameters is None:
                response = getPassengers()
        #metodo para retornar o passageiro com o id especificado
            else:
                passenger_id = path_parameters['id']
                response = getId(passenger_id)
        #metodo para escorar o modelo para o passageiro com as informações enviadas
        elif httpMethod == postMethod and path == endpointPath:
            response = scoreModel(event)
        #metodo para deletar o passageiro
        elif httpMethod == deleteMethod and path == endpointPath:
            passenger_id = path_parameters['id']
            response = deleteId(passenger_id)
        else:
            response = buildResponse(404, 'Not Found')
    except Exception as e:
        logger.exception(f"Error handling request: {str(e)}")
        response = buildResponse(500, f'Internal Server Error: {str(e)}')

    return response

#escora o modelo
def scoreModel(event):
    model = load_model_from_s3(bucket_name, model_key)

    try:
        logger.info("scoring model")
        data = json.loads(event['body'])
        logger.info(f"data received: {data}")

        model_features = model.feature_names_in_
        data_df = pd.DataFrame([data])

        features_df = data_df[list(model_features)]
        prediction = model.predict_proba(features_df)[0][1]
        logger.info(f"prediction: {prediction}")
    
        data_string = json.dumps(event, cls=CustomEncoder)
        # Armazena o resultado no DynamoDB
        item = {
            "id": str(data["id"]),  
            "features": data_string,  
            "prediction": Decimal(str(prediction))
        }
        try:
            table.put_item(Item=item)
            logger.info(f"item saved in dynamo: {item}")
        except Exception as e:
            logger.error(f"ERROR saving item to dynamo: {str(e)}")

        return buildResponse(200, {'id': data['id'], 'prediction': prediction})

    except Exception as e:
        logger.exception(f"ERROR to score model: {str(e)}")
        return buildResponse(501, {'message': 'ERROR to score model'})

#função para construir as respostas
def buildResponse(status_code, body=None):
    response = {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json'
        }
    }
    if body is not None:
        response['body'] = json.dumps(body, cls=CustomEncoder)
    else:
        response['body'] = json.dumps({
            'message': 'Health check successful'
        })
    return response

#funçao para trazer as informações do passageiro especificado
def getId(passengerId):
    try:
        response = table.get_item(
            Key={
                'id': passengerId
            }
        )
        if 'Item' in response:
            return buildResponse(200, response['Item'])
        else:
            return buildResponse(404, {'Message': f'ID: {passengerId} not found'})
    except Exception as e:
        logger.exception(f"Error getting passenger by ID: {str(e)}")
        return buildResponse(500, 'Error getting passenger by ID')

#funcao para listar todos os passageiros
def getPassengers():
    try:
        response = table.scan()
        items = response['Items']

        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response['Items'])

        body = {
            'passengers': items
        }

        return buildResponse(200, body)
    except Exception as e:
        logger.exception(f"Error getting passengers: {str(e)}")
        return buildResponse(500, 'Error getting passengers')

#funcao para deleter as informacoes do passageiro
def deleteId(passenger_id):
    try:
        response = table.delete_item(
            Key={
                'id': passenger_id
            },
            ReturnValues='ALL_OLD'
        )
        body = {
            'Operation': 'DELETE',
            'Message': 'SUCCESS',
            'deletedItem': response
        }
        return buildResponse(200, body)
    except Exception as e:
        logger.exception(f"Error deleting passenger: {str(e)}")
        return buildResponse(500, 'Error deleting passenger')
