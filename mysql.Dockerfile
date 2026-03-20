FROM mysql:8.0

# Environment variables will be overridden by render.yaml
ENV MYSQL_DATABASE=leopoldina
ENV MYSQL_ROOT_PASSWORD=rootpassword

EXPOSE 3306
