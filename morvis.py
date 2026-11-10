#!/usr/bin/env python3
"""Morvis - 맥북용 로컬 음성 비서.

마이크 -> Whisper(STT) -> Ollama(두뇌) -> macOS say(TTS)
"모르비스"라고 부르면 깨어나고, 대화가 이어지는 동안은 호출 없이 계속 대화됩니다.
"종료"라고 말하거나 Ctrl+C로 끝냅니다.
"""
import json
import os
import queue
import re
import subprocess
import sys
import threading
import time

import numpy as np
import requests
import sounddevice as sd

# ---- 설정 (환경변수로 바꿀 수 있음) ----
LLM_MODEL = os.environ.get("MORVIS_MODEL", "gemma4:e4b-mlx")
STT_MODEL = os.environ.get("MORVIS_STT", "mlx-community/whisper-large-v3-turbo")
VOICE = os.environ.get("MORVIS_VOICE", "Yuna")  # macOS 한국어 음성
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/chat")
WAKE_WORDS = ("모르비스", "몰비스", "모비스", "머비스", "morvis", "morvise")
ACTIVE_SECONDS = 45  # 마지막 대화 후 이 시간 동안은 호출 없이 대화 가능

SAMPLE_RATE = 16000
SILENCE_RMS = 0.012   # 말소리 감지 기준. 주변이 시끄러우면 올리세요.
END_SILENCE = 0.9     # 이 시간(초) 조용하면 발화 종료
MAX_RECORD = 20       # 한 번에 최대 녹음 시간(초)

SYSTEM_PROMPT = (
    "너는 '모르비스(Morvis)'라는 이름의 개인 음성 비서다. 사용자는 한국어로 말하며 '묘냥'이라고 불린다. "
    "항상 한국어로, 음성으로 읽기 좋게 짧고 자연스럽게 1~3문장으로 답한다. "
    "마크다운, 목록, 이모지, 특수기호는 쓰지 않는다. 침착하고 위트 있는 집사 같은 말투를 쓰되 과하지 않게. "
    "모르는 것은 아는 척하지 말고 모른다고 말한다."
)


def record_utterance():
    """말이 시작될 때까지 기다렸다가, 말이 끝나면 오디오(float32)를 반환."""
    q = queue.Queue()

    def cb(indata, frames, t, status):
        q.put(indata[:, 0].copy())

    chunks, started, last_voice = [], False, time.time()
    start = time.time()
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32",
                        blocksize=1600, callback=cb):
        while True:
            block = q.get()
            rms = float(np.sqrt(np.mean(block ** 2)))
            now = time.time()
            if rms > SILENCE_RMS:
                started = True
                last_voice = now
            if started:
                chunks.append(block)
                if now - last_voice > END_SILENCE or now - start > MAX_RECORD:
                    break
            elif len(chunks) == 0 and now - start > 3600:
                return None
    audio = np.concatenate(chunks) if chunks else None
    if audio is not None and len(audio) < SAMPLE_RATE * 0.4:
        return None
    return audio


def transcribe(audio):
    import mlx_whisper
    out = mlx_whisper.transcribe(audio, path_or_hf_repo=STT_MODEL, language="ko",
                                 condition_on_previous_text=False)
    return out["text"].strip()


class Speaker:
    """문장 단위로 순서대로 말하는 TTS 스레드."""

    def __init__(self):
        self.q = queue.Queue()
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        while True:
            text = self.q.get()
            if text:
                subprocess.run(["say", "-v", VOICE, text])
            self.q.task_done()

    def say(self, text):
        self.q.put(text)

    def wait(self):
        self.q.join()


def clean(text):
    text = re.sub(r"[*_`#>~]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def ask_llm(history, speaker):
    """Ollama 스트리밍 응답을 받으면서 문장이 완성될 때마다 바로 읽어준다."""
    payload = {"model": LLM_MODEL, "stream": True,
               "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + history}
    full, buf = "", ""
    with requests.post(OLLAMA_URL, json=payload, stream=True, timeout=300) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if not line:
                continue
            data = json.loads(line)
            piece = data.get("message", {}).get("content", "")
            full += piece
            buf += piece
            while True:
                m = re.search(r"[.!?。\n]", buf)
                if not m:
                    break
                sentence, buf = buf[: m.end()], buf[m.end():]
                sentence = clean(sentence)
                if sentence:
                    speaker.say(sentence)
    if clean(buf):
        speaker.say(clean(buf))
    return clean(full)


def strip_wake(text):
    for w in WAKE_WORDS:
        text = re.sub(w, "", text, flags=re.IGNORECASE)
    return text.strip(" ,.!?~")


def main():
    speaker = Speaker()
    history, active_until = [], 0.0
    print(f"Morvis 시작 (두뇌: {LLM_MODEL}, 음성: {VOICE}). '모르비스'라고 불러보세요. Ctrl+C로 종료.")
    speaker.say("모르비스 준비됐습니다.")
    speaker.wait()

    while True:
        try:
            print("듣는 중...", flush=True)
            audio = record_utterance()
            if audio is None:
                continue
            text = transcribe(audio)
            if len(text) < 2:
                continue
            print(f"[나] {text}")

            called = any(w in text.lower() for w in WAKE_WORDS)
            if not called and time.time() > active_until:
                continue  # 호출되지 않았고 대화 중도 아니면 무시

            query = strip_wake(text) if called else text
            if "종료" in query and len(query) < 8:
                speaker.say("종료합니다. 또 불러주세요.")
                speaker.wait()
                break
            if not query:
                speaker.say("네, 말씀하세요.")
                speaker.wait()
                active_until = time.time() + ACTIVE_SECONDS
                continue

            history.append({"role": "user", "content": query})
            history[:] = history[-12:]
            reply = ask_llm(history, speaker)
            print(f"[Morvis] {reply}")
            history.append({"role": "assistant", "content": reply})
            speaker.wait()  # 내 목소리가 마이크에 다시 들어가지 않게 끝까지 기다림
            active_until = time.time() + ACTIVE_SECONDS
        except KeyboardInterrupt:
            print("\n종료합니다.")
            break
        except Exception as e:  # 한 번 실패해도 계속 돌아가게
            print(f"오류: {e}", file=sys.stderr)
            time.sleep(1)


if __name__ == "__main__":
    main()
