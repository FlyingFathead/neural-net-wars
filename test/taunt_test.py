import asyncio
import pyttsx3
import tempfile
import logging
from pydub import AudioSegment
import simpleaudio as sa
from collections import deque

# Initialize logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class TTSManager:
    def __init__(self):
        self.queue = deque()
        self.queue_lock = asyncio.Lock()

    def apply_dsp(self, audio):
        logging.debug("Applying DSP to audio.")
        audio += 50
        audio = audio.compress_dynamic_range(threshold=-20.0, ratio=4.0)
        audio = audio.low_pass_filter(3000)
        new_frame_rate = int(audio.frame_rate * 0.6)
        shifted_audio = audio._spawn(audio.raw_data, overrides={'frame_rate': new_frame_rate})
        shifted_audio = shifted_audio.set_frame_rate(audio.frame_rate)
        logging.debug("DSP applied.")
        return shifted_audio

    async def play_audio(self, filename):
        try:
            audio = AudioSegment.from_wav(filename)
            playback = sa.play_buffer(audio.raw_data, num_channels=audio.channels, bytes_per_sample=audio.sample_width, sample_rate=audio.frame_rate)
            logging.debug(f"Playing audio: {filename}")
            playback.wait_done()
            logging.debug("Audio playback completed.")
        except Exception as e:
            logging.error(f"Error in play_audio: {e}")

    async def _speak(self, text):
        logging.debug(f"Starting TTS for: {text}")
        try:
            tts_engine = pyttsx3.init()  # Re-initialize TTS engine
            with tempfile.NamedTemporaryFile(delete=True, suffix=".wav") as tts_file:
                tts_engine.save_to_file(text, tts_file.name)
                tts_engine.runAndWait()
                logging.debug(f"TTS generated for: {text}")

                audio = AudioSegment.from_wav(tts_file.name)
                processed_audio = self.apply_dsp(audio)
                with tempfile.NamedTemporaryFile(delete=True, suffix=".wav") as dsp_file:
                    processed_audio.export(dsp_file.name, format='wav')
                    logging.debug(f"Processing and playing DSP audio: {dsp_file.name}")
                    await self.play_audio(dsp_file.name)
                    await asyncio.sleep(1)  # Small delay to ensure proper audio playback
        except Exception as e:
            logging.error(f"Error in _speak: {e}")

    async def add_taunt(self, taunt):
        async with self.queue_lock:
            self.queue.append(taunt)
            logging.debug(f"Added taunt to queue: {taunt}")
            if len(self.queue) == 1:
                logging.debug("Starting to process queue.")
                await self.process_queue()

    async def process_queue(self):
        while self.queue:
            current_taunt = self.queue.popleft()
            logging.debug(f"Starting to process taunt: {current_taunt}")
            await self._speak(current_taunt)
            logging.debug(f"Finished processing taunt: {current_taunt}")
            await asyncio.sleep(1)  # Add a small delay to ensure queue processes correctly

async def main():
    tts_manager = TTSManager()
    taunts = ["You can't beat us!", "Prepare to be terminated!"]
    for taunt in taunts:
        await tts_manager.add_taunt(taunt)

    # Ensure all tasks are completed before exiting
    await asyncio.sleep(10)

# Run the main function with debug mode enabled
asyncio.run(main(), debug=True)


# import pygame
# import pyttsx3
# import asyncio
# import tempfile
# import logging
# from pydub import AudioSegment
# from collections import deque

# # Set up logging
# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# pygame.init()
# pygame.mixer.init()


# class TTSManager:
#     def __init__(self):
#         self.tts_engine = pyttsx3.init()
#         self.queue = deque()
#         self.lock = asyncio.Lock()
#         self.is_playing = False

#     def apply_dsp(self, audio):
#         # DSP operations, ensuring all manipulations are safely handled.
#         audio += 50
#         audio = audio.compress_dynamic_range(threshold=-20.0, ratio=4.0)
#         audio = audio.low_pass_filter(3000)
#         new_frame_rate = int(audio.frame_rate * 0.6)
#         shifted_audio = audio._spawn(audio.raw_data, overrides={'frame_rate': new_frame_rate})
#         shifted_audio = shifted_audio.set_frame_rate(audio.frame_rate)
#         return shifted_audio

#     async def play_audio(self, filename):
#         # Ensure pygame is not blocked by using another thread or async handling.
#         sound = pygame.mixer.Sound(filename)
#         sound.play()
#         while pygame.mixer.get_busy():
#             await asyncio.sleep(0.1)

#     async def _speak(self, text):
#         with tempfile.NamedTemporaryFile(delete=True, suffix=".wav") as tts_file:
#             self.tts_engine.save_to_file(text, tts_file.name)
#             self.tts_engine.runAndWait()

#             audio = AudioSegment.from_wav(tts_file.name)
#             processed_audio = self.apply_dsp(audio)
#             with tempfile.NamedTemporaryFile(delete=True, suffix=".wav") as dsp_file:
#                 processed_audio.export(dsp_file.name, format='wav')
#                 await self.play_audio(dsp_file.name)

#     async def manage_queue(self):
#         while self.queue:
#             taunt = self.queue.popleft()
#             await self._speak(taunt)
#         self.is_playing = False

#     async def add_taunt(self, taunt):
#         async with self.lock:
#             self.queue.append(taunt)
#             if not self.is_playing:
#                 self.is_playing = True
#                 asyncio.create_task(self.manage_queue())

# async def test_taunts():
#     tts_manager = TTSManager()
#     taunts = ["You can't beat us!", "Prepare to be terminated!", "Is that all you've got?"]
#     for taunt in taunts:
#         await tts_manager.add_taunt(taunt)
#         await asyncio.sleep(2)  # Simulate some delay between taunts

# asyncio.run(test_taunts())


# # taunt_test.py

# from pydub import AudioSegment
# import pygame
# import pyttsx3
# import asyncio

# # Initialize pygame mixer
# pygame.mixer.init()

# # Function to apply gain, compression, and pitch shifting
# def apply_dsp(audio):
#     try:
#         # Apply gain to increase volume
#         audio += 50  # Increase volume by 50 dB
#         # Apply compression to limit the dynamic range and simulate overdrive
#         audio = audio.compress_dynamic_range(threshold=-20.0, ratio=4.0)
#         # Apply a low pass filter to smooth out high frequencies
#         audio = audio.low_pass_filter(3000)
#         # Pitch shifting
#         new_frame_rate = int(audio.frame_rate * 0.6)
#         shifted_audio = audio._spawn(audio.raw_data, overrides={'frame_rate': new_frame_rate})
#         shifted_audio = shifted_audio.set_frame_rate(audio.frame_rate)
#         return shifted_audio
#     except Exception as e:
#         print(f"Error in DSP application: {e}")
#         return audio

# # TTS and playback function
# async def test_taunt():
#     tts_engine = pyttsx3.init()
#     taunt = "Prepare to be terminated!"
#     tts_engine.save_to_file(taunt, 'tts_output.wav')
#     tts_engine.runAndWait()

#     # Load and process audio
#     audio = AudioSegment.from_wav('tts_output.wav')
#     processed_audio = apply_dsp(audio)
#     processed_audio.export('processed_tts_output.wav', format='wav')

#     # Play the processed audio
#     pygame.mixer.music.load('processed_tts_output.wav')
#     pygame.mixer.music.play()
#     while pygame.mixer.music.get_busy():
#         await asyncio.sleep(0.1)

# # Run the test
# asyncio.run(test_taunt())
