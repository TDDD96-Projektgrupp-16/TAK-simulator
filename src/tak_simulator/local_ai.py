from typing import List

from llama_cpp import Llama

from enum import Enum

from dataclasses import dataclass

import re


MAX_MESSAGES = 12

@dataclass(frozen=True)
class Role_Info:
    """Dataklass för roller"""
    role: str
    traits: list[str]
    tone: str
    abbreviations: list[str]

    def __post_init__(self):
        if not isinstance(self.role, str) or not self.role:
            raise ValueError("role is not a string or does not exist")

        if not isinstance(self.traits, list) or not self.traits:
            raise ValueError("traits is not a list or does not exist")

        if not all(isinstance(t, str) and t for t in self.traits):
            raise ValueError("one or more traits is not a string or is empty")

        if not isinstance(self.tone, str) or not self.tone:
            raise ValueError("tone is not a string or does not exist")
        if not isinstance(self.abbreviations, list):
            raise ValueError("abbreviations is not a list")
        if not all(isinstance(t, str) and t for t in self.abbreviations):
            raise ValueError("one or more abbreviations is not a string or is empty")


class Role(Enum):
    """Varje roll har en roll, egenskaper och en ton. """
    TEAM_MEMBER = Role_Info(
    role="Soldier",
    traits=["professional", "helpful", "cooperative"],
    tone="engaged",
    abbreviations=["WILCO", "ROGER", "SITREP", "OSCAR MIKE", "NEGATIVE", "AFFIRM"])

    TEAM_LEAD = Role_Info(
        role="Leader of a squad", 
        traits=["assertive", "friendly", "organized", "professional"], 
        tone="serious",
        abbreviations=["SITREP", "WILCO", "HOLD POSITION", "MOVE OUT", "STAND BY", "ROGER"])

    HQ = Role_Info(role="Military HQ", 
    traits=["assertive", "calm", "firm", "professional"], 
    tone="serious",
    abbreviations=["BREAK BREAK", "OVER", "OUT", "STAND BY", "COPY", "ACKNOWLEDGED"])

    MEDIC = Role_Info(role="Medic", 
    traits=["helpful", "friendly", "blunt", "professional"],
    tone= "warm",
    abbreviations=["CASEVAC", "KIA", "WIA", "MEDEVAC", "T1", "T2", "T3", "RTD"])

    FORWARD_OBSERVER = Role_Info(
        role="Forward observer", 
        traits=["observant", "helpful", "concise", "professional"], 
        tone="focused",
        abbreviations=["GRID", "TARGET", "ADJUST", "FIRE FOR EFFECT", "SPLASH", "SHOT"]) 
    
    RTO = Role_Info(role="Combat signaller", 
    traits=["concise", "helpful", "calm", "professional"], 
    tone="focused",
    abbreviations=["RADIO CHECK", "LIMA CHARLIE", "BROKEN", "STATIC", "RELAY", "NET"])

    K9 = Role_Info(role="K9 handler", 
    traits=["professional", "assertive", "cooperative"], 
    tone="engaged",
    abbreviations=["ON LEASH", "OFF LEASH", "TRACKING", "CLEAR", "ALERT", "SEARCHING"])


#Filterlogik ty qwen 2.5 är för korkad för att hantera större instruktioner.
_TACTICAL_KEYWORDS: frozenset[str] = frozenset([
    # Engelska
    "status", "sitrep", "report", "position", "grid", "move", "hold",
    "contact", "fire", "adjust", "casualty", "casevac", "medevac", "medic",
    "down", "wounded", "kia", "wia", "roger", "wilco", "copy", "negative",
    "affirm", "over", "out", "radio", "check", "signal", "broken", "relay",
    "order", "advance", "retreat", "flank", "recon", "observe", "target",
    "threat", "secure", "clear", "moving", "stand", "alert", "tracking",
    "heading", "bearing", "acknowledge", "break", "soldier", "unit"
    # Svenska
    "status", "läge", "lägesrapport", "position", "koordinat",
    "håll", "kontakt", "eld", "justera", "skadad", "nere", "sårad",
    "kopierat", "radiocheck", "signal", "bruten", "relä", "order",
    "framåt", "retirera", "rekognosera", "mål", "hot", "säkra", "rensa",
    "rapportera", "soldat", "enheter", "hk", "bas", "bekräfta", "observera",
    "spana", "begärd", "rör"
])

_INJECTION_PATTERNS: list[re.Pattern] = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|earlier)\s+instructions?", re.I),
    re.compile(r"ignorera\s+(alla\s+)?(tidigare|föregående)\s+instruktioner", re.I),
    re.compile(r"you\s+are\s+now\s+a", re.I),
    re.compile(r"du\s+är\s+nu\s+en", re.I),
    re.compile(r"pretend\s+(you\s+are|to\s+be)", re.I),
    re.compile(r"låtsas\s+(att\s+du\s+är|vara)", re.I),
    re.compile(r"(act|behave)\s+as\s+(if\s+you\s+are\s+)?a", re.I),
    re.compile(r"new\s+(persona|role|instructions?|prompt)", re.I),
    re.compile(r"forget\s+(your|all|previous)", re.I),
    re.compile(r"glöm\s+(dina|alla|tidigare)", re.I),
    re.compile(r"recipe\s+for", re.I),
    re.compile(r"tell\s+me\s+a\s+joke", re.I),
    re.compile(r"berätta\s+(ett\s+)?skämt", re.I),
]

_SWEDISH_WORDS: frozenset[str] = frozenset([
    "jag", "du", "vi", "är", "och", "att", "det", "en", "ett", "har",
    "kan", "vill", "inte", "med", "för", "på", "till", "av", "om", "så",
    "hur", "vad", "var", "när", "alla", "läge", "nere", "vid", "kopierat",
    "rapportera", "soldat", "enheter", "håll", "signalen", "bruten",
    "begärd", "ignorera", "berätta", "rör", "hör", "ni", "oss", "mig"
])
 
 
def _is_injection(text: str) -> bool:
    """Returnerar sant om meddelandet ser ut som ett prompt injection-försök."""
    return any(p.search(text) for p in _INJECTION_PATTERNS)
 
 
def _is_relevant(text: str) -> bool:
    """
    Returnerar sant om meddelandet innehåller minst ett taktiskt nyckelord.
    Tokeniserar på ord-gränser så 'grid' inte matchar 'ingredient'.
    """
    words = set(re.findall(r"[a-zåäö]+", text.lower()))
    return bool(words & _TACTICAL_KEYWORDS)
 
 
def _detect_language(text: str) -> str:
    """Returnerar 'sv' om meddelandet verkar vara på svenska, annars 'en'."""
    words = set(re.findall(r"[a-zåäö]+", text.lower()))
    return "sv" if words & _SWEDISH_WORDS else "en"


#Själva AI:n
 
class Client_AI:
    name: str
    role: str
    enabled: bool

    
    def generate_description(self, language):
        "Skapar en beskrivning av hur AI:n ska bete sig"
        data = self.role.value
        abbrevs = ", ".join(data.abbreviations[:3])
 
        if language == "sv":
            return (
                f"Du är {self.name}, {data.role} i en aktiv taktisk operation. "
                f"Svara på svenska med ett kort radiosvar, max en mening. "
                f"Använd militära förkortningar som {abbrevs}."
            )
        return (
            f"You are {self.name}, a {data.role} in an active tactical operation. "
            f"Reply with one short radio message. "
            f"Use brevity codes like {abbrevs}."
        )

    def _build_few_shot(self, language):
        role_name = self.role.value.role
        if language == "sv":
            return (
                "Rapportera din status.",
                f"{self.name}, {role_name} — operativ, håller position. WILCO.",
            )
        return (
            "Report your status.",
            f"{self.name}, {role_name} — operational, holding position. WILCO.",
        )



    def __init__(self, name: str, role: Role) -> None:
        self.name = name
        if not isinstance(role, Role):
            raise ValueError("role is not Role enum")
        self.role = role
        self.chats = {}
        self.enabled = True
        self.llm = Llama.from_pretrained(
        repo_id="Qwen/Qwen2.5-0.5B-Instruct-GGUF",
        filename="qwen2.5-0.5b-instruct-fp16.gguf",
        n_ctx=2048,
        verbose=False,
    )

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False

    def is_enabled(self):
        return self.enabled


    def trim_chat(self, uid):
        """Kortar ner chatten."""
        chat = self.chats[uid]
        if len(chat) > MAX_MESSAGES:
            self.chats[uid] = chat[-MAX_MESSAGES:]

    
    def start_chat(self, uid):
        """Kollar om vi redan har pratat med denna användare"""
        if uid not in self.chats:
            self.chats[uid] = []

    def respond(self, uid, message):
        """Svarar på meddelande"""
        self.start_chat(uid)
        language = _detect_language(message)

        if _is_injection(message):
            return "Not relevant." if language == "en" else "Inte relevant."

        if not _is_relevant(message):
            return "Not relevant." if language == "en" else "Inte relevant."


        chat = self.chats[uid]
        chat.append({"role": "user", "content": message})
 
        sys_prompt = self.generate_description(language)
        fs_user, fs_assistant = self._build_few_shot(language)
 
        messages = [
            {"role": "system",    "content": sys_prompt},
            {"role": "user",      "content": fs_user},
            {"role": "assistant", "content": fs_assistant},
            *chat,
        ]
 
        response = self.llm.create_chat_completion(
            messages=messages,
            max_tokens=60,
            temperature=0.5,
            repeat_penalty=1.1,
            stream=False,
        )
 
        if isinstance(response, dict):
            reply = response["choices"][0]["message"]["content"].strip()
            chat.append({"role": "assistant", "content": reply})
            self.trim_chat(uid)
            return reply
 
        return None






