#!/usr/bin/env python3

from collections import namedtuple, defaultdict
import struct
import os, json
import io

from TTS.api import TTS
from TTS.utils.manage import get_user_data_dir

data_dir = get_user_data_dir('tts')

model_languages = {}
model_speakers = {}
models_by_language = defaultdict(list)
model_sep = '--'
# default_model_type = 'tts_models'
default_model_type = None

def tts_model_components(model_name):
    model_type = default_model_type
    lang, dataset, model = model_name.split(model_sep, 2)
    # model_type, lang, dataset, model = model_name.split(model_sep, 3)
    return model_type, lang, dataset, model

def tts_list_all_models():
    global default_model_type
    for model_name in TTS.list_models():
        model_type, lang, dataset, model = model_name.split('/')
        if not default_model_type:
            default_model_type = model_type
        elif model_type != default_model_type:
            raise f'unexpected model type: got {model_type}, expected {default_model_type}'

    return [model_sep.join(model_name.split('/')[1:]) for model_name in TTS.list_models()]
    # return [model_sep.join(model_name.split('/')[1:]) for model_name in TTS.list_models()]
    # return [model_name.replace('/', model_sep) for model_name in TTS.list_models()]

def tts_list_models():
    available_models = []
    for model_name in tts_list_all_models():
        model_path = tts_model_path(model_name)
        if not os.path.exists(model_path):
            continue
        available_models.append(model_name)
    return available_models

def tts_model_path(model_name):
    # Name format: type/language/dataset/model
    # model_type, lang, dataset, model = model_name.split(model_sep)
    model_type, lang, dataset, model = tts_model_components(model_name)
    model_full_name = f'{model_type}--{lang}--{dataset}--{model}'
    return os.path.join(data_dir, model_full_name)


def tts_list_model_languages():
    global model_languages
    if model_languages:
        return model_languages
    for model_name in tts_list_models():
        # Name format: type/language/dataset/model
        # _, lang, _, _ = model_name.split(model_sep)
        _, lang, _, _ = tts_model_components(model_name)
        # model_type, lang, dataset, model = model_name.split(model_sep)
        # model_full_name = f'{model_type}--{lang}--{dataset}--{model}'
        # model_path = os.path.join(data_dir, model_full_name)
        model_path = tts_model_path(model_name)
        # if not os.path.exists(model_path):
        #     # print(f'model {model_name} NOT present at {model_path}')
        #     continue

        # print(f'model {model_name} downloaded at {model_path}')

        languages = set() if lang == 'multilingual' else set([lang])
        lang_ids_path = os.path.join(model_path, 'language_ids.json')
        if os.path.exists(lang_ids_path):
            with open(lang_ids_path, 'r') as f:
                data = json.load(f)
            languages |= data.keys()

        # print(f'model {model_name} languages: {", ".join(languages)}')

        model_languages[model_name] = list(languages)

    return model_languages

def tts_list_model_speakers():
    global model_speakers
    if model_speakers:
        return model_speakers
    for model_name in tts_list_models():
        model_path = tts_model_path(model_name)
        speakers = []
        speaker_ids_path = os.path.join(model_path, 'speaker_ids.json')
        if os.path.exists(speaker_ids_path):
            with open(speaker_ids_path, 'r') as f:
                data = json.load(f)
            speakers = list(data.keys())
        if not speakers:
            speakers_path = os.path.join(model_path, 'speakers.json')
            if os.path.exists(speakers_path):
                with open(speakers_path, 'r') as f:
                    data = json.load(f)
                speakers = list(sorted(set(sample.get('name').strip() for fn,sample in data.items())))
        if not speakers:
            speaker_ids_path = os.path.join(model_path, 'speaker_ids.pth')
            if os.path.exists(speaker_ids_path):
                import zipfile, pickle
                with zipfile.ZipFile(speaker_ids_path, 'r') as zf:
                    with zf.open('archive/data.pkl') as f:
                        data = pickle.load(f)
                speakers = list(data.keys())

        # print(f'model {model_name} speakers: {", ".join(speakers)}')

        model_speakers[model_name] = list(speakers)

    return model_speakers

def tts_list_models_by_language():
    if models_by_language:
        return models_by_language
    model_languages = tts_list_model_languages()
    for model_name, languages in model_languages.items():
        for language in languages:
            models_by_language[language].append(model_name)
    return models_by_language


# https://stackoverflow.com/questions/67317366/how-to-add-header-info-to-a-wav-file-to-get-a-same-result-as-ffmpeg

def raw_audio_data_to_wav(data, sample_rate, sample_type=float):

    if type(data) == bytes and data.startswith("RIFF".encode()):
        return data

    if sample_type is None:
        sample_type = type(data[0])

    if sample_type == float:
        format_tag = 3      # WAVE_FORMAT_IEEE_FLOAT=3, WAVE_FORMAT_PCM=1
        bits_per_sample = 32
    elif sample_type == int:
        format_tag = 1
        bits_per_sample = 16

    bytes_per_sample = bits_per_sample // 8
    ch = 1

    sample_count = len(data)

    chunk1_size = 16
    chunk2_size = sample_count * ch * bytes_per_sample
    chunk_size = 4 + 8 + chunk1_size + 8 + chunk2_size

    header = [
        'RIFF'.encode(),
        struct.pack('i', chunk_size),
        'WAVEfmt '.encode(),
        struct.pack('i', chunk1_size),
        struct.pack('h', format_tag),
        struct.pack('h', ch),
        struct.pack('i', sample_rate),
        struct.pack('i', sample_rate * bytes_per_sample),
        struct.pack('h', bytes_per_sample), # block align
        struct.pack('h', bits_per_sample),
        'data'.encode(),
        struct.pack('i', chunk2_size),
    ]

    if type(data) == bytes:
        data_chunk = data
    elif type(data) == list:
        # https://stackoverflow.com/questions/16368263/python-struct-pack-for-individual-elements-in-a-list
        if sample_type is int:
            data_chunk = struct.pack('h' * sample_count * ch, *data)
        elif sample_type is float:
            data_chunk = struct.pack('f' * sample_count * ch, *data)

    return b''.join(header) + data_chunk

class InvalidInputException(Exception):
    pass

TTSResult = namedtuple('TTSResult', 'data, sample_rate, text, language, speaker')

class TTSWrapper:

    def __init__(self, model_name):
        self.model_type, self.lang, self.dataset, self.model = tts_model_components(model_name)
        self.model_name = '/'.join([self.model_type, self.lang, self.dataset, self.model])
        self.tts = TTS(self.model_name)

    @property
    def speakers(self):
        return [x.strip() for x in self.tts.speakers or []]

    @property
    def languages(self):
        return list(set(self.tts.languages or []) | set([lang]))

    def download(self):
        self.tts.download_model_by_name(self.model_name)

    def get_wav(self, data):
        if type(data) is TTSResult:
            data = data.data
        output = io.BytesIO()
        self.tts.synthesizer.save_wav(data, output)
        return output.getvalue()

    def __call__(self, text, language=None, speaker=None, speaker_wav=None):
        if not text:
            raise InvalidInputException('input text not specified')
        if not self.tts.is_multi_speaker:
            speaker = None
            speaker_wav = None
        elif not speaker_wav and not speaker:
            speaker = self.tts.speakers[0]
        if not self.tts.is_multi_lingual:
            language = None
        elif not language:
            raise InvalidInputException('language not specified for multi-lingual model')
        return TTSResult(self.tts.tts(text=text, language=language, speaker=speaker, speaker_wav=speaker_wav),
                         self.tts.synthesizer.tts_config.audio.sample_rate, text, language or self.lang, speaker)

# if __name__ == '__main__':
#     print(tts_list_model_speakers())
