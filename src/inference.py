"""Load the checkpoint once. Each generation or judge call uses a new user message."""
import json
from rubric import BRIEF_PROMPT, judge_message


class Llama:
    def __init__(self, model, revision):
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
        if not torch.cuda.is_available():
            raise RuntimeError("Enable a Kaggle CUDA GPU before starting the Llama run.")
        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(model, revision=revision)
        quant = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                                   bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.float16)
        self.model = AutoModelForCausalLM.from_pretrained(model, revision=revision,
                    quantization_config=quant, torch_dtype=torch.float16, device_map={"": 0}).eval()

    def _generate(self, message, limit):
        tokens = self.tokenizer.apply_chat_template([{"role": "user", "content": message}],
                tokenize=True, add_generation_prompt=True, return_tensors="pt", return_dict=True).to("cuda:0")
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
