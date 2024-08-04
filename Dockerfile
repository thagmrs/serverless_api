FROM public.ecr.aws/lambda/python:3.8

# Install the required packages
RUN pip install numpy scikit-learn==1.1.3 pandas==1.5.3 joblib

# Copy the function code
COPY /../lambda_function/lambda_function.py ${LAMBDA_TASK_ROOT}
COPY /../lambda_function/encoder_decimal.py ${LAMBDA_TASK_ROOT}

# Set the CMD to your handler
CMD [ "lambda_function.lambda_handler" ]
