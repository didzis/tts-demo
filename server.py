#!/usr/bin/env python3

debug = True

if __name__ == '__main__':

    import argparse

    parser = argparse.ArgumentParser(description='TTS Server', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--port', '-p', metavar='PORT', type=int, default=8000, help='port')
    parser.add_argument('--host', '-H', metavar='HOST', type=str, default='0.0.0.0', help='listen host, 0.0.0.0 for any (interface), 127.0.0.1 for localhost only')
    parser.add_argument('--reload', '-r', action='store_true', help='auto reload')
    parser.add_argument('--cors', '-c', action='store_true', help='enable CORS')
    parser.add_argument('--debug', '-d', action='store_true', help='debug mode')

    args = parser.parse_args()

    debug = args.debug  # TODO: this does not work for processes forked by uvicorn


from typing import Union
from enum import Enum
from collections import defaultdict
import traceback

from fastapi import FastAPI, File, UploadFile, Form, Response, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.utils import get_openapi

from TTS.api import TTS

from tts_wrapper import (tts_list_models, tts_list_all_models, tts_list_model_languages, tts_list_models_by_language,
                         TTSWrapper, raw_audio_data_to_wav, InvalidInputException, tts_model_components, tts_list_model_speakers, tts_download, tts_async_download)


# model_names = {}
# for model_name in tts_list_models():
#     # model_type, lang, dataset, model = model_name.split('/')
#     model_type, lang, dataset, model = tts_model_components(model_name)
#     model_names[f'{model_type}_{lang}_{dataset}_{model}'.replace('-', '_')] = model_name
#
# ModelName = Enum('ModelName', model_names)

AllModelName = Enum('AllModelName', [(model_name, model_name) for model_name in tts_list_all_models()])

def refresh_models():
    global models_by_language
    global model_languages
    global language_priority
    global model_priority

    global model_names
    global ModelName
    global languages
    global Languages

    models_by_language = tts_list_models_by_language()
    model_langauges = tts_list_model_languages()
    language_priority = defaultdict(int)
    model_priority = defaultdict(int)

    for language, models in models_by_language.items():
        for model in models:
            model_priority[model] += len(models_by_language[language])

    model_names = list(sorted(model_priority.keys(), key=lambda model: '%02d%s' % (len(model_priority) + 1 - model_priority[model], model), reverse=False))

    ModelName = Enum('ModelName', [(model_name, model_name) for model_name in model_names])

    for language, models in models_by_language.items():
        for model in models:
            language_priority[language] += len(model_langauges[model])

    languages = list(sorted(language_priority.keys(), key=lambda lang: '%02d%s' % (100-language_priority[lang], lang), reverse=False))

    Languages = Enum('Languages', [(lang, lang) for lang in languages])

refresh_models()


app = FastAPI(debug=debug)

def enable_cors():
    app.add_middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# https://stackoverflow.com/questions/70446584/how-does-fastapi-uvicorn-parallelize-requests
# https://github.com/tiangolo/fastapi/discussions/4358

# https://stackoverflow.com/questions/63169865/how-to-do-multiprocessing-in-fastapi

# https://stackoverflow.com/questions/63048825/how-to-upload-file-using-fastapi
# https://fastapi.tiangolo.com/tutorial/query-params/#__tabbed_1_2
# https://stackoverflow.com/questions/65627453/how-to-set-the-file-multiple-file-upload-field-as-an-optional-field-in-fastapi

# https://fastapi.tiangolo.com/tutorial/path-params/#working-with-python-enumerations
# https://codereview.stackexchange.com/questions/247505/fast-api-path-parameters-from-enum-class
# https://code-maven.com/slides/python/fastapi-path-parameters-specific-values-with-enum

def get_tts(model_name):
    return TTSWrapper(model_name)

def generate(model_name: ModelName,
                   text: str,
                   language: Union[Languages, None],
                   # language: Union[str, None],
                   speaker: Union[str, None],
                   speaker_wav: UploadFile,
                   download: bool):

    # return dict(model_name=model_name, text=text, language=language, speaker=speaker, speaker_wav=bool(speaker_wav))

    try:
        model_name = model_name.value
        if language:
            language = language.value

        tts = get_tts(model_name)

        if speaker_wav:
            speaker_wav = speaker_wav.file

        result = tts(text=text, language=language, speaker=speaker, speaker_wav=speaker_wav)

        # data = [int(0x7fff * sample * 0.4) for sample in result.data]
        # wav_data = raw_audio_data_to_wav(data, result.sample_rate, int)
        # wav_data = raw_audio_data_to_wav(result.data, result.sample_rate)
        wav_data = tts.get_wav(result)

        if download:
             headers = { 'Content-Disposition': 'attachment; filename=output.wav' }
        else:
             headers = {}

        return Response(wav_data, media_type='audio/wav', headers=headers)

    except InvalidInputException as e:
        if debug:
            traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        if debug:
            traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
        # return JSONResponse(status_code=500, content=dict(error=str(e)))


# @app.get("/reset")
# def reset():
#     print(app.router.routes)
#     app.router.routes = app.router.routes[0:4]
#     load_routes('y')
#     print(app.router.routes)
#     return ''

# def load_routes(x='x'):
#     from typing import Literal
#     @app.get("/test/{some}")
#     def download_model(some: Literal["a","b", x]):
#         return some

def load_routes(app):

    @app.get("/languages")
    def list_languages():
        return tts_list_models_by_language()

    @app.get("/languages/{language}/models")
    def list_language_models(language: Union[Languages]):
        return tts_list_models_by_language()[language.value]

    @app.get("/models")
    def list_models():
        return tts_list_models()

    @app.get("/models/all")
    def list_all_models():
        return tts_list_all_models()

    @app.get("/models/languages")
    def list_model_languages():
        return tts_list_model_languages()

    @app.get("/models/speakers")
    def list_model_speakers():
        return tts_list_model_speakers()

    @app.get("/models/{model_name}/download")
    def download_model(model_name: AllModelName):
        model_name = model_name.value
        model_name = '/'.join(tts_model_components(model_name))
        return StreamingResponse(tts_download(model_name, reload), media_type='text/plain')
        # return get_tts(model_name).download()

    # This blocks the main thread, use threaded version above
    # @app.get("/models/{model_name}/download-async")
    # async def async_download_model(model_name: AllModelName):
    #     model_name = model_name.value
    #     model_name = '/'.join(tts_model_components(model_name))
    #     return StreamingResponse(tts_async_download(model_name, reload), media_type='text/plain')
    #     # return get_tts(model_name).download()

    @app.get("/models/{model_name}/languages")
    def model_languages(model_name: ModelName):
        model_name = model_name.value
        return tts_list_model_languages()[model_name]

    @app.get("/models/{model_name}/speakers")
    def model_speakers(model_name: ModelName):
        model_name = model_name.value
        speakers = tts_list_model_speakers()
        return speakers.get(model_name)
        # tts = get_tts(model_name)
        # return tts.speakers

    @app.post('/models/{model_name}/generate')
    def model_generate_post(model_name: ModelName,
                            text: str = Form(),
                            language: Union[Languages, None] = Form(None),
                            # language: Union[str, None] = Form(None),
                            speaker: Union[str, None] = Form(None),
                            speaker_wav: UploadFile = File(None),
                            download: bool = Form(False)):

        return generate(model_name, text, language, speaker, speaker_wav, download)


    @app.get('/models/{model_name}/generate')
    def model_generate_get(model_name: ModelName,
                           text: str,
                           language: Union[Languages, None] = None,
                           # language: Union[str, None] = None,
                           speaker: Union[str, None] = None,
                           download: bool = False):

        return generate(model_name, text, language, speaker, None, download)


    @app.post('/generate')
    def generate_post(model_name: ModelName = Form(),
                            text: str = Form(),
                            language: Union[Languages, None] = Form(None),
                            # language: Union[str, None] = Form(None),
                            speaker: Union[str, None] = Form(None),
                            speaker_wav: UploadFile = File(None),
                            download: bool = Form(False)):

        return generate(model_name, text, language, speaker, speaker_wav, download)


    @app.get('/generate')
    def generate_get(model_name: ModelName,
                           text: str,
                           language: Union[Languages, None] = None,
                           # language: Union[str, None] = None,
                           speaker: Union[str, None] = None,
                           download: bool = False):

        return generate(model_name, text, language, speaker, None, download)


    app.mount("/", StaticFiles(directory="static", html=True), name="static")



def reload():
    refresh_models()
    app.router.routes = app.router.routes[0:4]  # reset app routes, leave only swaggger rotues, e.g., /docs, /redoc etc.
    load_routes(app)
    app.openapi_schema = create_openapi_schema(app)

load_routes(app)

def create_openapi_schema(app):
    return get_openapi(
        title="TTS Demo",
        version="0.0.1",
        description="Text-To-Speech API",
        routes=app.routes,
    )

def openapi():
    if app.openapi_schema:
        return app.openapi_schema
    app.openapi_schema = create_openapi_schema(app)
    return app.openapi_schema

app.openapi = openapi

enable_cors()   # TODO: make use of fork instead of spawn

if __name__ == '__main__':

    import uvicorn

    # TODO: make us of fork instead of spawn
    # if args.cors or True:
    if True:
        enable_cors()

    uvicorn.run("server:app", host=args.host, port=args.port, log_level='info', reload=args.reload)

    # or $ uvicorn server:app --host 0.0.0.0 --port 8000
