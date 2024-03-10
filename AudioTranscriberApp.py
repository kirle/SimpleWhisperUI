from pydub import AudioSegment
from pydub.silence import split_on_silence
import os
import whisper
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from threading import Thread


class AudioProcessor:
    def __init__(self, filepath):
        self.filepath = filepath
        self.audio = AudioSegment.from_file(filepath)

    def mp3_to_wav(self, output_dir):
        wav_path = os.path.join(output_dir, os.path.splitext(os.path.basename(self.filepath))[0] + '.wav')
        self.audio.export(wav_path, format="wav")
        return wav_path

    def wav_to_mp3(self, output_dir):
        mp3_path = os.path.join(output_dir, os.path.splitext(os.path.basename(self.filepath))[0] + '.mp3')
        self.audio.export(mp3_path, format="mp3")
        return mp3_path

    def chop_audio(self, output_dir, min_length = 10*60*1000, max_length = 15*60*1000): # default min_length is 10 minutes, max_length is 15 minutes
        chunks = split_on_silence(self.audio, min_silence_len=2000, silence_thresh=-32, keep_silence=500)
        
        # ensuring chunks between interval
        refined_chunks = []
        temp_chunk = chunks[0]
        for chunk in chunks[1:]:
            if len(temp_chunk) + len(chunk) <= max_length:
                temp_chunk += chunk  # 
            else:
                if len(temp_chunk) >= min_length:
                    refined_chunks.append(temp_chunk)
                    temp_chunk = chunk  
                else:
                    temp_chunk += chunk  

        if len(temp_chunk) <= max_length:
            refined_chunks.append(temp_chunk)
        output_files = []
        for i, chunk in enumerate(refined_chunks):
            chunk_path = os.path.join(output_dir, f"chunk{i}.wav")
            chunk.export(chunk_path, format="wav")
            output_files.append(chunk_path)
            
        return output_files
    
class Transcriber:
    def __init__(self, model_name="base"):
        self.model = whisper.load_model(model_name)

    def transcribe(self, audio_file_path):
        return self.model.transcribe(audio_file_path)

    def transcribe_multiple(self, audio_files, output_txt):
        # reverse audio files
        audio_files = audio_files[::-1]
        
        with open(output_txt, 'a') as f:
            for audio_file in audio_files:
                result = self.transcribe(audio_file)
                f.write(result["text"])
                f.write('\n\n\n\n')  # separating transcriptions of different chunks by newlines
        print(f'Transcription completed and saved to {output_txt}')

    def transcribe_directory(self, directory, output_txt):
        audio_files = [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith('.wav')]
        self.transcribe_multiple(audio_files, output_txt)

class Application(tk.Tk):
    def __init__(self, audio_processor, transcriber):
        super().__init__()

        self.audio_processor = audio_processor
        self.transcriber = transcriber

        self.title("Audio Transcriber")
        self.geometry("600x400")

        style = ttk.Style()
        style.configure('TButton', font=('calibri', 10, 'bold', 'underline'),
                        foreground='red')

        # top titple
        title_label = tk.Label(self, text="Welcome to Audio Transcriber", font=("Arial", 16))
        title_label.pack(pady=10)

        # model selection box
        self.model_var = tk.StringVar()
        self.model_var.set("base")  # set default model
        model_label = tk.Label(self, text="Choose model:")
        model_label.pack()
        model_options = ttk.Combobox(self, textvariable=self.model_var, values=("tiny", "base", "small", "medium", "large"))
        model_options.pack()

        # btns
        process_button = ttk.Button(self, text="Process Audio", command=self.process_audio)
        process_button.pack(pady=10)
        transcribe_button = ttk.Button(self, text="Transcribe", command=self.transcribe)
        transcribe_button.pack(pady=10)

        # status and instruction labels
        self.status_label = tk.Label(self, text="")
        self.status_label.pack(pady=20)
        instruction_label = tk.Label(self, text="Instructions: \n1. Click 'Process Audio' and select an audio file. \n2. Select the output directory. \n3. Click 'Transcribe' and select the directory with the audio files. \n4. Select the location for the output text file.")
        instruction_label.pack(pady=20)

    def process_audio(self):
        filepath = filedialog.askopenfilename()
        try:
            self.audio_processor = AudioProcessor(filepath)
        except Exception as e:
            self.status_label.config(text=f"Failed to process audio: {str(e)}")
            return
        self.output_dir = filedialog.askdirectory()

        self.status_label.config(text="Processing audio...")

        process_thread = Thread(target=self.audio_processor.chop_audio, args=(self.output_dir,))
        process_thread.start()
        self.after(100, self.check_process, process_thread)

    def check_process(self, process_thread):
        if process_thread.is_alive():
            self.after(100, self.check_process, process_thread)  # Check again after 100ms
        else:
            self.status_label.config(text="Audio processing done!")
            messagebox.showinfo("Done", f"Audio processing completed!\nFiles saved to {self.output_dir}")

    def transcribe(self):
        try:
            self.transcriber = Transcriber(self.model_var.get())
        except Exception as e:
            self.status_label.config(text=f"Failed to load model: {str(e)}")
            return
        directory = filedialog.askdirectory()
        self.output_txt = filedialog.asksaveasfilename(defaultextension=".txt")

        self.status_label.config(text="Transcribing...")

        transcribe_thread = Thread(target=self.transcriber.transcribe_directory, args=(directory, self.output_txt))
        transcribe_thread.start()
        self.after(100, self.check_transcribe, transcribe_thread)

    def check_transcribe(self, transcribe_thread):
        if transcribe_thread.is_alive():
            self.after(100, self.check_transcribe, transcribe_thread)  # Check again after 100ms
        else:
            self.status_label.config(text="Transcription done!")
            messagebox.showinfo("Done", f"Transcription completed!\nTranscript saved to {self.output_txt}")


if __name__ == "__main__":
    audio_processor = None  # initially, no audio file to process
    transcriber = None  # initially, no model selected for transcription
    app = Application(audio_processor, transcriber)
    app.mainloop()





