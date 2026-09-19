from __future__ import annotations

from .types import (PromptBinding, PromptVersion, RenderedPrompt, sha256_obj)


def render_template(prompt: PromptVersion, binding: PromptBinding) -> RenderedPrompt:
    values = binding.values()
    missing = [name for name in prompt.required_variables if name not in values]
    if missing:
        raise ValueError(f"missing prompt variables: {', '.join(missing)}")
    values = {**{name: "" for name in prompt.optional_variables}, **values}

    rendered_messages = []
    for msg in prompt.messages:
        content = msg["content"]
        if prompt.engine == "format":
            content = content.format(**values)
        elif prompt.engine != "plain":
            raise ValueError(f"unsupported prompt engine {prompt.engine!r}")
        rendered_messages.append({"role": msg["role"], "content": content.strip()})

    binding_hash = sha256_obj(binding.hash_payload())
    rendered_hash = sha256_obj(rendered_messages)
    rendered_text = "\n\n".join(
        f"{m['role'].upper()}:\n{m['content']}" for m in rendered_messages)
    return RenderedPrompt(
        prompt_id=prompt.prompt_id,
        version=prompt.version,
        rendered_text=rendered_text,
        rendered_hash=rendered_hash,
        messages=rendered_messages,
        binding_hash=binding_hash,
        template_hash=prompt.source_hash,
    )

