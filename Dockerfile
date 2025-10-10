FROM python:3.10-slim

WORKDIR /app
COPY . /app

# (Optional) faster, smaller wheels
ENV PIP_NO_CACHE_DIR=1
RUN pip install --upgrade pip \
 && pip install -r requirements.txt

# Streamlit must listen on 0.0.0.0:8080 in Cloud Run
EXPOSE 8080
CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]
