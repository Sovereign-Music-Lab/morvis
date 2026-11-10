# Morvis

맥북에서 인터넷 없이 돌아가는 로컬 음성 비서. 이름을 부르면 깨어나고, 말하는 대로 듣고, 생각하고, 목소리로 답합니다.

```
마이크 → Whisper (음성 인식) → Ollama (두뇌) → macOS say (음성 출력)
```

모든 처리가 내 맥에서 이뤄지기 때문에 대화 내용이 밖으로 나가지 않습니다.

## 요구 사항

- Apple Silicon 맥북 (macOS)
- [Ollama](https://ollama.com) 설치 및 실행 중
- 대화용 모델 하나 (기본값: `gemma4:e4b-mlx`)
- Python 3.10 이상

```bash
ollama pull gemma4:e4b-mlx
```

## 설치

```bash
git clone https://github.com/Sovereign-Music-Lab/morvis.git
cd morvis
bash setup.sh
```

`setup.sh`는 `.venv` 가상환경을 만들고 `sounddevice`, `numpy`, `requests`, `mlx-whisper`를 설치합니다.

## 실행

```bash
source .venv/bin/activate
python morvis.py
```

- 처음 실행하면 마이크 권한 요청이 뜹니다. 허용해 주세요.
- 처음 한 번은 Whisper 모델을 내려받느라 시간이 걸립니다.

## 사용법

| 하는 말 | 동작 |
| --- | --- |
| "모르비스, 오늘 뭐 하면 좋을까?" | 이름을 부르며 바로 질문 |
| "모르비스" (이름만) | "네, 말씀하세요."라고 대답하고 대기 |
| 대화 직후 이어서 말하기 | 마지막 대화 후 45초 동안은 이름 없이 계속 대화 |
| "종료" | 프로그램 종료 (Ctrl+C도 가능) |

Morvis가 말하는 동안에는 마이크를 듣지 않아서 자기 목소리를 다시 인식하지 않습니다.

## 설정

환경변수로 바꿉니다.

| 변수 | 기본값 | 설명 |
| --- | --- | --- |
| `MORVIS_MODEL` | `gemma4:e4b-mlx` | 대화에 쓰는 Ollama 모델 |
| `MORVIS_STT` | `mlx-community/whisper-large-v3-turbo` | 음성 인식 모델. 빠르게 쓰려면 `mlx-community/whisper-small-mlx` |
| `MORVIS_VOICE` | `Yuna` | macOS 음성 이름 (`say -v '?'`로 목록 확인) |
| `OLLAMA_URL` | `http://localhost:11434/api/chat` | Ollama 서버 주소 |

```bash
MORVIS_MODEL=gemma4:26b-mlx python morvis.py
```

코드 위쪽 상수로도 조정할 수 있습니다.

- `WAKE_WORDS`: 호출어. 음성 인식이 이름을 다르게 받아적는 경우 여기에 추가합니다.
- `SILENCE_RMS`: 말소리 감지 기준. 주변이 시끄러워 계속 듣는다면 올립니다.
- `END_SILENCE`: 말이 끝났다고 판단하는 침묵 시간(초). 말하는 중에 끊기면 키웁니다.
- `ACTIVE_SECONDS`: 호출 없이 대화가 이어지는 시간.

## 문제 해결

- **목소리가 안 나와요**: 시스템 설정 → 손쉬운 사용 → 말하기 콘텐츠에서 한국어 Yuna 음성을 내려받으세요.
- **오류: Connection refused**: Ollama가 꺼져 있습니다. Ollama 앱을 켜거나 `ollama serve`를 실행하세요.
- **이름을 불러도 반응이 없어요**: 화면에 찍히는 `[나]` 인식 결과를 보고, 다르게 인식된 철자를 `WAKE_WORDS`에 추가하세요.
- **답이 느려요**: 더 작은 STT 모델이나 작은 대화 모델로 바꿔 보세요.
