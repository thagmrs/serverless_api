FROM public.ecr.aws/lambda/python:3.8


# Install the required packages
COPY /../lambda_function/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the function code
COPY /../lambda_function/lambda_function.py ${LAMBDA_TASK_ROOT}
COPY /../lambda_function/encoder_decimal.py ${LAMBDA_TASK_ROOT}

# Set the CMD to your handler
CMD [ "lambda_function.lambda_handler" ]

ENV AWS_REGION=us-west-2
