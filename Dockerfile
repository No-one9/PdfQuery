#Use official python base image
FROM python:3.11-slim
#Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    poppler-utils \
    nodejs \
    npm \
    supervisor \
    && rm -rf /var/lib/apt/lists/*
#Set working directory
WORKDIR /app
#Copy package files
COPY package*.json ./
#install node.js dependencies
RUN npm install
#Copy python requirements
COPY requirements.txt .
#install python dependencies
RUN pip install --no-cache-dir -r requirements.txt
#Copy application files
COPY . .
#Copy supervisord config
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
#Expose port
EXPOSE 3000 8000
#start command
CMD ["supervisord", "-n"]
