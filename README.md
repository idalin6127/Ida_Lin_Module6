<p align="center">
  <img src="logo/logo.png" alt="Project Logo" width="500"/>
</p>


# Week 6 — Voice Agent with Function Calling

## Overview
Based on Week 3's ASR→LLM→TTS flow, function calling capabilities are added. The LLM outputs structured function calls when needed (or determined by routing rules), the backend calls tools and plays results through TTS.

## Architecture
- ASR: Whisper (small or small.en), FastAPI uploads audio then transcribes
- LLM: TinyLlama-1.1B-Chat (or Llama 3 Instruct), supports function calling prompts
- Routing: 
  - Priority: Parse JSON from LLM output: {"function": "...", "arguments": {...}}
  - Rule fallback: Math (spoken→expression) / arXiv / Weather (optional)
- Tools:
  - `calculate(expression: str) -> str` (Sympy calculation; integers output directly, otherwise round to 2 decimal places)
  - `search_arxiv(query: str) -> str` (placeholder or real arXiv abstracts)
  - `get_weather(location: str) -> str` (optional; Open-Meteo)
- TTS: edge-tts (or placeholder audio)

## Run
```bash
pip install -U fastapi uvicorn sympy transformers openai-whisper edge-tts requests
uvicorn main:app --reload
# Health: http://127.0.0.1:8000/health
# Swagger: http://127.0.0.1:8000/docs


Test (via /chat_debug)

Log 1 — Math (calculate)
{
  "request_text": "Open parenthesis 12.5 plus 7.5 close parenthesis divided by 4.",
  "llm_raw": "(12.5 + 7.5) / 4 = 0.8333333333333333\n\nThe answer to the question is 0.8333333333333333.",
  "final_text": "5",
  "audio_url": "http://127.0.0.1:8000/audio?path=C%3A%5CUsers%5Cidali%5CAppData%5CLocal%5CTemp%5Ctmpvgn26xsn.wav"
}

Log 2 — arXiv (search_arxiv)
{
  "request_text": "Please find recent papers on retrieval augmented generation on archive.",
  "llm_raw": "I don't have access to real-time data or the latest papers. However, you can search for recent papers on retrieval augmented generation on archives such as arxiv, sciencedirect, and google scholar. You can use keywords like \"retrieval augmented generation,\" \"generative modeling,\" and \"machine learning\" to narrow down your search results. Some popular papers in this field include:\n\n1. \"Generating Text from Images: A Survey\" by jianwei zhang et al. (arxiv: 2009.06229)\n2. \"Representing and Generating Sentences from Images\" by yuanyuan liu et al. (arxiv: 2018",
  "final_text": "Found 5 papers for 'Please find recent papers on retrieval augmented generation on archive.':\n\n1. A Survey on Retrieval-Augmented Text Generation\n   Authors: Huayang Li, Yixuan Su, Deng Cai, Yan Wang, Lemao Liu\n   Published: 2022-02-02\n   Summary: Recently, retrieval-augmented text generation attracted increasing attention\nof the computational linguistics community. Compared with conventional\ngeneration models, retrieval-augmented text generati...\n\n2. Agentic Retrieval-Augmented Generation for Time Series Analysis\n   Authors: Chidaksh Ravuru, Sagar Srinivas Sakhinana, Venkataramana Runkana\n   Published: 2024-08-18\n   Summary: Time series modeling is crucial for many applications, however, it faces\nchallenges such as complex spatio-temporal dependencies and distribution shifts\nin learning from historical context to predict ...\n\n3. Tune My Adam, Please!\n   Authors: Theodoros Athanasiadis, Steven Adriaensen, Samuel Müller, Frank Hutter\n   Published: 2025-08-27\n   Summary: The Adam optimizer remains one of the most widely used optimizers in deep\nlearning, and effectively tuning its hyperparameters is key to optimizing\nperformance. However, tuning can be tedious and cost...\n\n4. Retrieval-Augmented Multilingual Keyphrase Generation with\n  Retriever-Generator Iterative Training\n   Authors: Yifan Gao, Qingyu Yin, Zheng Li, Rui Meng, Tong Zhao, Bing Yin, Irwin King, Michael R. Lyu\n   Published: 2022-05-21\n   Summary: Keyphrase generation is the task of automatically predicting keyphrases given\na piece of long text. Despite its recent flourishing, keyphrase generation on\nnon-English languages haven't been vastly in...\n\n5. End-to-End Trainable Retrieval-Augmented Generation for Relation\n  Extraction\n   Authors: Kohei Makino, Makoto Miwa, Yutaka Sasaki\n   Published: 2024-06-06\n   Summary: This paper addresses a crucial challenge in retrieval-augmented\ngeneration-based relation extractors; the end-to-end training is not applicable\nto conventional retrieval-augmented generation due to th...",
  "audio_url": "http://127.0.0.1:8000/audio?path=C%3A%5CUsers%5Cidali%5CAppData%5CLocal%5CTemp%5Ctmp5pnl69ei.wav"
}

Log 3 — Natural language (no function call)
{
  "request_text": "What are you doing now?",
  "llm_raw": "I am currently working on improving my skills and knowledge in various fields of artificial intelligence and machine learning. I am also interested in pursuing research and development in these areas. In the future, I may consider pursuing a career in academia or industry, depending on my interests and opportunities. Thank you for asking!",
  "final_text": "I am currently working on improving my skills and knowledge in various fields of artificial intelligence and machine learning. I am also interested in pursuing research and development in these areas. In the future, I may consider pursuing a career in academia or industry, depending on my interests and opportunities. Thank you for asking!",
  "audio_url": "http://127.0.0.1:8000/audio?path=C%3A%5CUsers%5Cidali%5CAppData%5CLocal%5CTemp%5Ctmpeqfrdv28.wav"
}

Log 4 — Weather (get_weather)

  "request_text": "What's the weather in Toronto today?",
  "llm_raw": "I do not have access to real-time weather information. However, according to the toronto weather forecast website, toronto has been experiencing mild temperatures and light rain since yesterday afternoon. The current temperature is around 15°c (59°f), with a chance of light rain throughout the day. The wind speed is 10 km/h (6 mph), and the humidity is 60%.",
  "final_text": "Toronto, Canada: 23.3°C, feels like 21.3°C, clear sky, wind 11.4 km/h, precip 0.0 mm (current).",
  "audio_url": "http://127.0.0.1:8000/audio?path=C%3A%5CUsers%5Cidali%5CAppData%5CLocal%5CTemp%5Ctmpbkrjy2se.wav"
}
