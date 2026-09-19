from .model import ModelOutput


class PastedTextModel:
    """把人工从Claude/GPT聊天界面复制粘贴保存的文本文件，
    伪装成Model协议的一次"生成"。不调用任何API，零成本，
    用于在没有API Key的情况下验证整条pipeline。"""
    model_kind = "llm"

    def __init__(self, paste_file: str, model_id: str):
        self.paste_file = paste_file
        self.model_id = model_id

    def generate(self, prompt: str) -> ModelOutput:
        text = open(self.paste_file, encoding="utf-8").read().strip()
        return ModelOutput(text=text, model_id=self.model_id,
                           model_kind=self.model_kind)
