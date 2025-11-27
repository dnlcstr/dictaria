<p align="center">
  <img src="icon.png" alt="Dictaria icon" width="180">
</p>

# Dictaria 🎤 - Local Speech-to-Text Powered by Faster Whisper

Dictaria is a small, cross-platform desktop tool designed for multi-language speech-to-text transcription. It runs entirely **locally** on your machine, ensuring privacy and speed.

It leverages the power of **`faster-whisper`** for high-performance transcription and provides a minimalist, distraction-free GUI built with Tkinter.

## ✨ Features

- **Local Processing:** All speech-to-text processing happens instantly on your machine (CPU or GPU).
- **High Performance:** Uses `faster-whisper` for efficient transcription.
- **Multi-Language Support:** Supports all languages available in Whisper.
- **Favorites:** Select up to **5 favorite languages** displayed as clickable flag icons.
- **Global Hotkey:** Use a convenient hotkey (`Ctrl/Cmd + Shift + J`) to toggle recording from any application.
- **Minimalist GUI:** Dark-themed, distraction-free interface built with native Tkinter.
- **Configuration Persistence:** Remembers your favorite languages, active language, and theme using a simple JSON config file.

## 🛠️ Installation and Setup

Dictaria requires **Python 3.8+**. The core dependency for audio handling is `sounddevice`, which requires the **PortAudio** library to be installed on your system.

### 1. Clone the Repository

bash
git clone [https://github.com/YOUR_USER/dictaria.git](https://github.com/YOUR_USER/dictaria.git)
cd dictaria
`

### 2\. Create a Virtual Environment (Recommended)

This step isolates Dictaria's dependencies from your system Python.

bash
python3 -m venv .venv
# Activate on macOS/Linux
source .venv/bin/activate
# Activate on Windows (Command Prompt)
# .venv\Scripts\activate.bat


### 3\. Install System Audio Dependencies (PortAudio)

You must install the system library **PortAudio** before installing the Python dependencies.

#### 🍏 macOS

Use Homebrew to install PortAudio:

bash
brew install portaudio


#### 💻 Windows

No specific system-level installation is typically required. The Python package installer (`pip`) usually handles necessary DLLs for `sounddevice` on Windows.

#### 🐧 Linux (Debian/Ubuntu)

Use your distribution's package manager (e.g., `apt`) to install PortAudio development headers:

bash
sudo apt update
sudo apt install libportaudio2 libportaudio-dev


### 4\. Install Python Dependencies

Install the required Python libraries using the provided `requirements.txt`:

bash
pip install -r requirements.txt


**Requirements:**

  - `faster-whisper`
  - `sounddevice`
  - `soundfile`
  - `numpy`
  - `pynput` (for the global hotkey)

-----

## ▶️ Running Dictaria

From the project folder, with your virtual environment activated:

bash
python dictaria.py


### Initial Use and Setup

1.  **Model Download:** The first time you run the script, it will display `[Initializing AI Model... please wait]` while downloading the `medium` Whisper model to your machine. This may take a few minutes.
2.  **Select Language:** Once the model is loaded, use the **Languages ▾** menu to select your desired languages (up to 5 favorites are recommended).
3.  **Start Dictation:** Click the round button or press the **Global Hotkey** to start recording.

## ⌨️ Global Hotkey

The global hotkey toggles recording on and off from any running application.

| OS | Key Combination | Hotkey Label |
| :--- | :--- | :--- |
| **macOS** | `Command + Shift + J` | `Cmd + Shift + J` |
| **Windows/Linux** | `Control + Shift + J` | `Ctrl + Shift + J` |

> **Note on Hotkeys:** Global hotkey functionality relies on the `pynput` library. On some systems (especially Linux Wayland or certain macOS security settings), the global hotkey may only work reliably when the Dictaria window is focused.

## 🌎 Languages and Favorites

Dictaria supports an extensive list of languages.

  - **Favorites Row:** A row of up to 5 flag icons appears above the record button.
  - **Active Language:** Clicking a flag sets it as the **Active Language**. The active language determines the code passed to the Whisper model and enables the record button.
  - **No Active Language:** If no language is selected, the record button remains grey and a system message prompts you to choose one.

## ⚙️ Configuration File

Dictaria automatically creates and updates a small JSON file in your home directory (`~/.dictaria_config.json`). This file saves your last settings, ensuring your environment is ready immediately upon next launch.

**Example `~/.dictaria_config.json`:**

json
{
 "favorites": ["en", "es", "ja"],
 "active_language": "en"
}


-----

## 📝 How it Works Internally

Dictaria is a single Python script that manages the entire workflow:

1.  **Initialization:** Loads the selected `faster-whisper` model in a **background thread** to ensure the GUI opens instantly.
2.  **Recording:** Uses `sounddevice` to stream microphone audio into a buffer (`numpy` array) in real-time.
3.  **Transcription:** When recording stops, the audio is saved to a temporary `.wav` file.
4.  **Inference:** `WhisperModel.transcribe()` is called using the **Active Language** code.
5.  **Output:** The resulting text is appended to the scrollable text box using a **thread-safe mechanism** (`root.after`) to prevent the Tkinter GUI from freezing.

## 📄 Credits and License

  - Vibe-coded with ChatGPT (GPT-5.1 Thinking).
  - Core transcription technology provided by [faster-whisper](https://github.com/SYSTRAN/faster-whisper).

This project is licensed under the **MIT License**.


