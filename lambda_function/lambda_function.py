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
        if httpMethod == getMethod and path == healthPath:
            response = buildResponse(200)
        elif httpMethod == getMethod and path == endpointPath:
            if path_parameters is None:
                response = getPassengers()
            else:
                passenger_id = path_parameters['id']
                response = getId(passenger_id)

        elif httpMethod == postMethod and path == endpointPath:
            response = scoreModel(event)
        elif httpMethod == deleteMethod and path == endpointPath:
            passenger_id = path_parameters['id']
            response = deleteId(passenger_id)
        else:
            response = buildResponse(404, 'Not Found')
    except Exception as e:
        logger.exception(f"Error handling request: {str(e)}")
        response = buildResponse(500, f'Internal Server Error: {str(e)}')

    return response

def scoreModel(event):
    print('ENTROU NA v0.4')
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
        # Store result in DynamoDB
        item = {
            "id": str(data["id"]),  # Ensure ID is a string
            "features": data_string,  # Store the original data received
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
