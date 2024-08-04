# Construa a imagem Docker
docker build -t lambda-image ../Dockerfile .. 

# Tag a imagem Docker
docker tag lambda-image:latest 740374395395.dkr.ecr.us-west-2.amazonaws.com/img_docker:latest

# Push da imagem para o ECR
docker push 740374395395.dkr.ecr.us-west-2.amazonaws.com/img_docker:latest
