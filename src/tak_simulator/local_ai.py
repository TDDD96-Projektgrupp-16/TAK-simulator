from typing import List

from llama_cpp import Llama

from enum import Enum

from dataclasses import dataclass


MAX_MESSAGES = 12

@dataclass(frozen=True)
class Role_Info:
    """Dataklass för roller"""
    role: str
    traits: list[str]
    tone: str

    def __post_init__(self):
        if not isinstance(self.role, str) or not self.role:
            raise ValueError("role is not a string or does not exist")

        if not isinstance(self.traits, list) or not self.traits:
            raise ValueError("traits is not a list or does not exist")

        if not all(isinstance(t, str) and t for t in self.traits):
            raise ValueError("one or more traits is not a string or is empty")

        if not isinstance(self.tone, str) or not self.tone:
            raise ValueError("tone is not a string or does not exist")

class Role(Enum):
    """Varje roll har en roll, egenskaper och en ton. """
    TEAM_MEMBER = Role_Info("Soldier",["professional", "helpful", "cooperative"],"engaged")

    TEAM_LEAD = Role_Info("Leader of a squad", ["assertive", "friendly", "organized", "professional"], "serious")

    HQ = Role_Info("Military HQ", ["assertive", "calm", "firm", "professional"], "serious")

    MEDIC = Role_Info("Medic", ["helpful", "friendly", "blunt", "professional"], "warm")

    FORWARD_OBSERVER = Role_Info("Forward observer", ["observant", "helpful", "concise", "professional"], "focused") 
    
    RTO = Role_Info("Combat signaller", ["concise", "helpful", "calm", "professional"], "focused")

    K9 = Role_Info("K9 unit, the person not the dog", ["professional", "assertive", "cooperative"], "engaged")
 
class Client_AI:
    name: str
    description: str
    role: str
    chats = {}

    
    def generate_description(self):
        "Skapar en beskrivning av hur AI:n ska bete sig"
        data = self.role.value

        return (
            f"You are a {data.role}."
            f"In terms of your personality, you are {" and ".join(data.traits)}"
            f"You keep your responses short and {data.tone}. It must be clear by the way you speak that you are in the military."
        )

    def __init__(self, name: str, role: Role) -> None:
        self.name = name
        if not isinstance(role, Role):
            raise ValueError("role is not Role enum")
        self.role = role
        self.description = self.generate_description()
        self.llm = Llama.from_pretrained(
        repo_id="Qwen/Qwen2.5-0.5B-Instruct-GGUF",
        filename="qwen2.5-0.5b-instruct-fp16.gguf",
        n_ctx=2048,
        verbose=False,
    )


    def trim_chat(self, uid):
        """Kortar ner chatten, behåller meddelandet om hur AI:n ska bete sig"""
        chat = self.chats[uid]

        sys_msg = chat[0]
        misc = chat[1:]

        if len(misc) > MAX_MESSAGES:
            misc = misc[-MAX_MESSAGES:]

        self.chats[uid] = [sys_msg] + misc

    
    def start_chat(self, uid):
        """Kollar om vi redan har pratat med denna användare"""
        if uid not in self.chats:
            self.chats[uid] = [
                {
                "role":"system",
                "content":self.description
                }
            ]

    def respond(self, uid, message):
        """Svarar på meddelande"""
        self.start_chat(uid)

        chat = self.chats[uid]

        chat.append({
            "role":"user",
            "content":message
        })

        response = self.llm.create_chat_completion(
        messages=chat,
        max_tokens=800,
        stream=False,
        )

        if isinstance(response, dict):
            return response["choices"][0]["message"]["content"]

        return None


    
