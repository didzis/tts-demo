# Text-To-Speech demo interface powered by Coqui TTS

## Dependencies

- Python 3
- Coqui TTS
- FastAPI

## Dependency setup

```
pip install -r requirements.txt
```

## Run

```
./server.py
```

Open [http://localhost:8000](http://localhost:8000) in your browser for demo interface
or [http://localhost:8000/docs](http://localhost:8000/docs) for OpenAPI.

## Models

The demo interface lists only downloaded models. To download a model either select model to download in all models list and click download
or use the API `/models/{model_name}/download`,
where `{model_name}` must be one returned from [/models/all](http://localhost:8000/models/all).

List all models using `curl`:

```
curl http://localhost:8000/models/all
```

For example, to download YourTTS model, open API endpoint
[/models/multilingual--multi-dataset--your_tts/download](http://localhost:8000/models/multilingual--multi-dataset--your_tts/download)
either in browser or using `curl`:

```
curl http://localhost:8000/models/multilingual--multi-dataset--your_tts/download
```

