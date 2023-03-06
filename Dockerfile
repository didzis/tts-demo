FROM ubuntu

RUN apt update && apt install -y python3 python3-pip

RUN pip install TTS

COPY tts_download_models.py /opt/app/

RUN python3 /opt/app/tts_download_models.py --all

RUN pip install fastapi python-multipart uvicorn[standard]

WORKDIR /opt/app

COPY tts_wrapper.py /opt/app/
COPY server.py /opt/app/

EXPOSE 8000

ENTRYPOINT ["/usr/bin/env", "python3", "/opt/app/server.py", "--host", "0.0.0.0"]
# ENTRYPOINT ["/usr/bin/env", "python3", "/opt/app/server.py", "--host", "0.0.0.0", "--port", "8000"]
# ENTRYPOINT ["/usr/bin/env", "uvicorn", "server:app", "--host", "0.0.0.0"]
# ENTRYPOINT ["/usr/bin/env", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
