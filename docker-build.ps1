#login
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 740374395395.dkr.ecr.us-west-2.amazonaws.com
# Construa a imagem Docker
docker build -t lambda-image .

# Tag a imagem Docker
docker tag lambda-image 740374395395.dkr.ecr.us-west-2.amazonaws.com/img_docker:v3

# Push da imagem para o ECR
docker push 740374395395.dkr.ecr.us-west-2.amazonaws.com/img_docker:v3
