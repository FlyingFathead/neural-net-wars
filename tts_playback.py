# tts_playback.py

import pyttsx3
import tempfile
import logging
from pydub import AudioSegment
import simpleaudio as sa
import sys

# Initialize logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def apply_dsp(audio):
    logging.debug("Applying DSP to audio.")
    audio += 50
    audio = audio.compress_dynamic_range(threshold=-20.0, ratio=4.0)
    audio = audio.low_pass_filter(3000)
    new_frame_rate = int(audio.frame_rate * 0.6)
    shifted_audio = audio._spawn(audio.raw_data, overrides={'frame_rate': new_frame_rate})
    shifted_audio = shifted_audio.set_frame_rate(audio.frame_rate)
    logging.debug("DSP applied.")
    return shifted_audio

def play_audio(filename):
    try:
        audio = AudioSegment.from_wav(filename)
        playback = sa.play_buffer(audio.raw_data, num_channels=audio.channels, bytes_per_sample=audio.sample_width, sample_rate=audio.frame_rate)
        logging.debug(f"Playing audio: {filename}")
        playback.wait_done()
        logging.debug("Audio playback completed.")
    except Exception as e:
        logging.error(f"Error in play_audio: {e}")

def speak_with_dsp(text):
    logging.debug(f"Starting TTS for: {text}")
    try:
        tts_engine = pyttsx3.init()
        with tempfile.NamedTemporaryFile(delete=True, suffix=".wav") as tts_file:
            tts_engine.save_to_file(text, tts_file.name)
            tts_engine.runAndWait()
            logging.debug(f"TTS generated for: {text}")

            audio = AudioSegment.from_wav(tts_file.name)
            processed_audio = apply_dsp(audio)
            with tempfile.NamedTemporaryFile(delete=True, suffix=".wav") as dsp_file:
                processed_audio.export(dsp_file.name, format='wav')
                logging.debug(f"Processing and playing DSP audio: {dsp_file.name}")
                play_audio(dsp_file.name)
    except Exception as e:
        logging.error(f"Error in speak_with_dsp: {e}")

if __name__ == "__main__":
    taunt = sys.argv[1]  # Get the taunt text from command-line arguments
    speak_with_dsp(taunt)
