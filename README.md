# Dictaria

Dictaria is a small local desktop tool for multi-language speech-to-text.  
It uses [faster-whisper](https://github.com/SYSTRAN/faster-whisper), `sounddevice`, and a minimalist Tkinter GUI.

You select up to five favorite languages, pick one flag, and then use a global hotkey to start and stop recording from your microphone. Transcription is done locally on your machine.

---

## Features

- Local speech-to-text using `faster-whisper`
- Multiple languages selectable from a menu
- Up to 5 favorite languages with flag icons
- Clickable favorites row above the record button
- Global hotkey: `Cmd + Shift + J` (on macOS, or Win + Shift + J on a PC keyboard)
- Dark mode and light mode toggle (☾ / ☀︎)
- Minimal, distraction-free GUI in Tkinter
- System messages in English, transcribed text in the selected language
- Simple JSON config file to remember favorites, last language, theme and help panel visibility

---

## How it works

Dictaria is a single Python script that:

1. Loads a `faster-whisper` model (by default `medium`) on CPU.
2. Opens a Tkinter window with:
   - Top bar with app name, instructions, theme toggle and language menu
   - A favorites row showing up to five language flags
   - A round red record button
   - A scrollable text area for transcription output
3. Listens to your microphone using `sounddevice` and records audio chunks.
4. After you stop recording, it writes the audio to a temporary `.wav` file.
5. Uses `WhisperModel.transcribe()` from `faster-whisper` with the selected language code.
6. Appends the recognized text to the text box.

All speech-to-text processing happens locally.

---

## Installation (macOS)

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USER/dictaria.git
cd dictaria
