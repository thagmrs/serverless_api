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

model = None

def load_model_from_s3(bucket_name, model_key):
    try:
        logger.info(f"Downloading model from bucket: {bucket_name}, key: {model_key}")
        s3.download_file(bucket_name, model_key, '/tmp/model.pkl')
        with open('/tmp/model.pkl', 'rb') as f:
            model = joblib.load(f)
        logger.info("Model loaded successfully from S3")
        return model
    except (NoCredentialsError, PartialCredentialsError) as e:
        logger.error(f"Error loading model from S3: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error loading model from S3: {str(e)}")
        raise

try:
    model = load_model_from_s3(bucket_name, model_key)
except Exception as e:
    logger.error(f"Failed to load model: {str(e)}")

getMethod = 'GET'
postMethod = 'POST'
deleteMethod = 'DELETE'
healthPath = '/health'
endpointPath = '/sobreviventes'

def lambda_handler(event, context):
    logger.info(event)
    httpMethod = event['httpMethod']
    path = event['path']
    path_parameters = event.get('pathParameters', {})

    try:
        if httpMethod == getMethod and path == healthPath:
            response = buildResponse(200)
        elif httpMethod == getMethod and path == endpointPath:
            if 'id' in path_parameters:
                passenger_id = path_parameters['id']
                response = getId(passenger_id)
            else:
                response = getPassengers()
        elif httpMethod == postMethod and path == endpointPath:
            response = scoreModel(event)
        elif httpMethod == deleteMethod and path == endpointPath:
            requestBody = json.loads(event['body'])
            response = deleteId(requestBody['id'])
        else:
            response = buildResponse(404, 'Not Found')
    except Exception as e:
        logger.exception(f"Error handling request: {str(e)}")
        response = buildResponse(500, 'Internal Server Error')

    return response

def scoreModel(event):
    try:
        logger.info("Scoring model...")
        data = json.loads(event['body'])
        logger.info(f"Data received for scoring: {data}")

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
        logger.info(f"Features for model: {features}")

        # Verifique se o modelo está carregado corretamente
        if model is None:
            raise ValueError("Model is not loaded properly")

        prediction = model.predict_proba(features)[0][1]
        logger.info(f"Prediction: {prediction}")

        # Store result in DynamoDB
        item = {
            'id': str(data['id']),  # Ensure ID is a string
            'features': data,  # Store the original data received
            'prediction': prediction
        }
        table.put_item(Item=item)
        logger.info(f"Item stored in DynamoDB: {item}")

        return buildResponse(200, {'id': data['id'], 'prediction': prediction})

    except KeyError as e:
        logger.exception(f"Key error: Missing key {str(e)}")
        return buildResponse(400, {'message': f"Missing key: {str(e)}"})
    except ValueError as e:
        logger.exception(f"Value error: {str(e)}")
        return buildResponse(500, {'message': f"Value error: {str(e)}"})
    except Exception as e:
        logger.exception(f"Error scoring model: {str(e)}")
        return buildResponse(500, {'message': 'Error scoring model'})

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
