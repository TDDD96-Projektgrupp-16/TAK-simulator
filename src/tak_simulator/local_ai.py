from typing import List

from llama_cpp import Llama


def generate_conversation(user: List[LocalAiUser]):
    instructions = "You are a creative writer. Write a natural back-and-forth conversation between the following characters:\n\n"

    for u in user:
        instructions += f"{u.name}: {u.description}\n\n"

    instructions += "\nRules for the conversation:"
    instructions += "\n- Format the output exactly like a play script. Every single line MUST start with the character's actual name, followed by a colon."
    instructions += (
        "\n- The conversation must be exactly 5 to 6 messages long in total."
    )
    instructions += (
        "\n- Ensure their unique personalities shine through in the dialogue."
    )

    llm = Llama.from_pretrained(
        repo_id="Qwen/Qwen2.5-0.5B-Instruct-GGUF",
        filename="qwen2.5-0.5b-instruct-fp16.gguf",
        n_ctx=2048,
        verbose=False,
    )

    response = llm.create_chat_completion(
        messages=[
            {"role": "system", "content": instructions},
            {"role": "user", "content": "Please write the conversation now."},
        ],
        max_tokens=800,
        stream=False,
    )
    if isinstance(response, dict):
        return response["choices"][0]["message"]["content"]
    return None


class LocalAiUser:
    name: str
    description: str

    def __init__(self, name: str, description: str) -> None:
        self.name = name
        self.description = description
