import json
import boto3
import os
import joblib
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
import numpy as np
import logging
from encoder_decimal import CustomEncoder

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
model = load_model_from_s3(bucket_name, model_key)


getMethod = 'GET' #O método GET /sobreviventes deve retornar um JSON com a lista de passageiros que já foram avaliados (fica a critério do candidato implementar paginação ou não);
#O método GET /sobreviventes/{id} deve retornar um JSON com a probabilidade de sobrevivência do passageiro com o ID informado;
postMethod = 'POST' #O método POST deve receber um JSON no body com um array de características e retornar um JSON com a probabilidade de sobrevivência do passageiro, junto com o ID do passageiro
deleteMethod = 'DELETE' #O método DELETE deve deletar o passageiro com o ID informado;
healthPath = '/health'
endpointPath= '/sobreviventes'

def lambda_handler(event, context):
    logger.info(event)
    httpMethod = event['httpMethod']
    path = event['path']
    path_parameters = event.get('pathParameters', {})

    if httpMethod == getMethod and path == healthPath:
        response = buildResponse(200)

    elif httpMethod == getMethod and path == endpointPath:
        if 'id' in path_parameters:
            response = getId(id)
        else: 
            response = getPassengers()
    
    elif httpMethod == postMethod and path == endpointPath:
        response = scoreModel(event)
    
    elif httpMethod == deleteMethod and path == endpointPath:
        requestBody = json.loads(event['body'])
        response = deleteId(requestBody['id'])
    else:
        response = buildResponse(404, 'Not Found')
    
    return response
        



def scoreModel(event):
    
    try:
        data = json.loads(event['body'])

        ordered_features = [
            data['Embarked_Q'],
            data['Age'],
            data['Sex_male'],
            data['Fare'],
            data['SibSp'],
            data['Parch'],
            data['Pclass'],
            data['Embarked_S']
        ]

        features = np.array(ordered_features).reshape(1, -1)
        prediction = model.predict_proba(features)[0][1]
        
        # Store result in DynamoDB
        item = {
            'id': data['id'],
            'features': data['features'],
            'prediction': prediction
        }
        table.put_item(Item=item)
        
        return buildResponse(200, json.dumps({'id': data['id'], 'prediction': prediction}))

    except Exception as e:
        logger.exception(str(e))







#Oficiais
def buildResponse(status_code, body=None):
    response = {
        'statusCode': status_code,
        'headers' : {
            'Content-Type': 'application/json'
        }
    }
    if body is not None:
        response['body'] = json.dumps(body, cls=CustomEncoder)

    return response


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
            return buildResponse(404, {'Message': 'ID: %s not found' %passengerId})
    except Exception as e:
        logger.exception(str(e))
    

def getPassengers():
    try:
        response = table.scan()
        items = response['Item']

        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response['Item'])
        
        body = {
            'passangers' : response
        }

        return buildResponse(200, body)
    except Exception as e:
        logger.exception(str(e))


def deleteId(passenger_id):
    try:
        response = table.delete_item(
            Key={
                 'id': passenger_id
                },
                ReturnValues= 'All_OLD'
            )
        body = {
            'Operation': 'DELETE',
            'Message': 'SUCCESS',
            'deletedItem': response
        }
        return buildResponse(200, body)
    except Exception as e:
        logger.exception(str(e))

def load_model_from_s3(bucket_name, model_key):
    try:
        s3.download_file(bucket_name, model_key, '/tmp/model.pkl')
        model = joblib.load('/tmp/model.pkl')
        return model
    except (NoCredentialsError, PartialCredentialsError) as e:
        print(f"Error loading model from S3: {str(e)}")
        raise