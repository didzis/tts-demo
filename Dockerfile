FROM ubuntu:20.04

RUN apt update && apt install -y python3 python3-pip

RUN pip install -U pip

RUN pip install TTS==0.13.3

COPY tts_download_models.py /opt/app/

# download all models
RUN python3 /opt/app/tts_download_models.py --all

COPY requirements.txt /opt/app/
RUN pip install -r /opt/app/requirements.txt
# RUN pip install fastapi python-multipart uvicorn[standard]

RUN apt install -y espeak

WORKDIR /opt/app

COPY tts_wrapper.py /opt/app/
COPY server.py /opt/app/
COPY static/index.html /opt/app/static/

EXPOSE 8000

ENTRYPOINT ["/usr/bin/env", "python3", "/opt/app/server.py", "--host", "0.0.0.0"]
# ENTRYPOINT ["/usr/bin/env", "python3", "/opt/app/server.py", "--host", "0.0.0.0", "--port", "8000"]
# ENTRYPOINT ["/usr/bin/env", "uvicorn", "server:app", "--host", "0.0.0.0"]
# ENTRYPOINT ["/usr/bin/env", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
