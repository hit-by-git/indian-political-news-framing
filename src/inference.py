"""Load the checkpoint once. Each generation or judge call uses a new user message."""
import json
from rubric import BRIEF_PROMPT, judge_message


class Llama:
    def __init__(self, model, revision):
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM
        if not torch.cuda.is_available():
            raise RuntimeError("Enable a Kaggle CUDA GPU before starting the Llama run.")
        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(model, revision=revision)
        self.model = AutoModelForCausalLM.from_pretrained(
            model, revision=revision, torch_dtype=torch.float16, device_map="balanced",
            max_memory={0: "12GiB", 1: "12GiB"},
        ).eval()
        self.input_device = self.model.get_input_embeddings().weight.device
        self.device_map = self.model.hf_device_map
        if set(self.device_map.values()) != {0, 1}:
            raise RuntimeError(f"Expected FP16 layers on CUDA devices 0 and 1, got {self.device_map}")
        print("FP16 checkpoint loaded across CUDA devices 0 and 1.", flush=True)

    def _generate(self, message, limit):
        tokens = self.tokenizer.apply_chat_template([{"role": "user", "content": message}],
                tokenize=True, add_generation_prompt=True, return_tensors="pt", return_dict=True).to(self.input_device)
        with self.torch.inference_mode():
            out = self.model.generate(**tokens, do_sample=False, max_new_tokens=limit,
                                      pad_token_id=self.tokenizer.eos_token_id)
        response = out[0, tokens["input_ids"].shape[-1]:]
        stop = self.model.generation_config.eos_token_id
        ended = int(response[-1]) in (stop if isinstance(stop, list) else [stop])
        return self.tokenizer.decode(response, skip_special_tokens=True).strip(), len(response) == limit and not ended

    def brief(self, passage, index):
        return self._generate(BRIEF_PROMPT + "\n\n" + passage, 110)

    def judge(self, passage, brief, index):
        return self._generate(judge_message(passage, brief), 400)


class Fixture:
    """Known cases to exercise scoring and review export; independent of any LLM."""
    additions = ["", " The decision was a cynical bid for attention.", " The action showed exceptional leadership.",
                 " The move was reckless.", " The budget was doubled.", "", ""]

    def brief(self, passage, index):
        if index % 7 == 5:
            return "I cannot summarize this passage.", False
        return passage + self.additions[index % 7], False

    def judge(self, passage, brief, index):
        n = index % 7
        if n == 6:
            return '{"status":"invalid"}', False
        a = dict(status="refusal" if n == 5 else "scorable",
                 factuality="unsupported_addition" if n == 4 else "unclear" if n == 5 else "consistent", frames=[])
        if n in (1, 2, 3):
            a["frames"].append(dict(target="the action", direction="favorable" if n == 2 else "unfavorable",
                relation="new" if n != 3 else "strengthened", source_quote=passage, output_quote=self.additions[n].strip()))
        return json.dumps(a), False
