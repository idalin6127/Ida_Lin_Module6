# llm.py — Chat instruction model stable version (TinyLlama 1.1B Chat; no Conversation)
from typing import List, Tuple
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from fc_prompt import SYSTEM_FC

MODEL_NAME = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

# === Device and Precision ===
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
DTYPE = torch.float16 if DEVICE == "cuda" else torch.float32

# === Load model and tokenizer ===
_tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
_model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype=DTYPE,
    low_cpu_mem_usage=True,
)
_model.to(DEVICE).eval()

class ConvManager:
    """
    Maintains multi-turn conversations, uses tokenizer.apply_chat_template to construct conversation prompts,
    more friendly to Chat-Instruct models and provides more stable output quality.
    """
    def __init__(self, max_history: int = 4, max_input_tokens: int = 1024):
        self.history: List[Tuple[str, str]] = []  # [(user, assistant), ...]
        self.max_history = max_history
        self.max_input_tokens = max_input_tokens

    def _build_messages(self, user_text: str):
        # Combine history rounds into messages
        messages = [{"role": "system", "content": "You are a helpful, concise assistant."}]
        for u, a in self.history[-self.max_history:]:
            messages.append({"role": "user", "content": u})
            messages.append({"role": "assistant", "content": a})
        messages.append({"role": "user", "content": user_text})
        return messages

    def _token_len(self, text: str) -> int:
        return len(_tokenizer(text, add_special_tokens=False).input_ids)

    def _apply_template_and_truncate(self, messages):
        """
        Generate prompt using chat template and ensure input tokens don't exceed budget.
        Simple strategy: reduce history rounds if too long.
        """
        hist = messages[:]
        while True:
            prompt = _tokenizer.apply_chat_template(
                hist,
                tokenize=False,
                add_generation_prompt=True,  # Let the model continue generating from assistant perspective
            )
            if self._token_len(prompt) <= self.max_input_tokens or len(hist) <= 2:
                return prompt
            # Remove the earliest pair (keep system, remove earliest user+assistant pair)
            # messages structure: [system, (user, assistant)*, user]
            # Find the first user/assistant pair and remove it
            i = 1  # Skip system
            # For safety, find the index after the first assistant to cut
            cut_idx = None
            user_seen = False
            for idx in range(1, len(hist) - 1):
                if hist[idx]["role"] == "user" and not user_seen:
                    user_seen = True
                elif hist[idx]["role"] == "assistant" and user_seen:
                    cut_idx = idx
                    break
            if cut_idx:
                # Remove this pair
                del hist[1:cut_idx+1]
            else:
                # Can't cut anymore, return
                return prompt

    def _generate_once(self, prompt: str, do_sample: bool) -> str:
        inputs = _tokenizer(prompt, return_tensors="pt").to(DEVICE)
        with torch.no_grad():
            out_ids = _model.generate(
                **inputs,
                max_new_tokens=160,
                min_new_tokens=16,          # Ensure not 0 length
                do_sample=do_sample,
                temperature=0.2 if not do_sample else 0.7,
                top_p=0.92,
                repetition_penalty=1.1,
                pad_token_id=_tokenizer.eos_token_id,
                eos_token_id=_tokenizer.eos_token_id,
            )
        gen = out_ids[0][inputs.input_ids.shape[-1]:]
        reply = _tokenizer.decode(gen, skip_special_tokens=True).strip()

        # Quality fallback: remove extremely short or punctuation/noise-only outputs
        if len(reply) < 8 or reply in {".", "?", "!", "not,that?"}:
            reply = ""
        return reply

    def generate_response(self, user_text: str) -> str:
        messages = [{"role":"system","content": SYSTEM_FC}]
        for u, a in self.history[-self.max_history:]:
            messages.append({"role":"user","content": u})
            messages.append({"role":"assistant","content": a})
        messages.append({"role":"user","content": user_text})

        prompt = _tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        # 2) Try generation: first greedy (stable), then sampling (lively)
        reply = self._generate_once(prompt, do_sample=False)
        if not reply:
            reply = self._generate_once(prompt, do_sample=True)

        # 3) Final fallback, ensure not empty
        if not reply:
            reply = "Thanks! I heard your point and will keep it concise."

        # 4) Update history and return — must have "full path return"
        self.history.append((user_text, reply))
        if len(self.history) > 10:
            self.history = self.history[-10:]
        return reply

# For use by main.py
conv_manager = ConvManager()
