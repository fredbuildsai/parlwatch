from typing import Literal

from pydantic import BaseModel, Field

Stance = Literal["supportive", "critical", "concerned", "neutral", "mixed", "calls_for_action"]


class QA(BaseModel):
    asker: str = Field(description="who asks: a name from the participant list, or 'Unknown deputy'")
    asker_role: Literal["deputy", "chair", "rapporteur", "witness", "other"] = "deputy"
    question: str = Field(description="the question(s) in 1-3 sentences, in French")
    answerer: str
    answer: str = Field(default="", description="what the answerer said to THIS question, paraphrased in at most 60 words, in French; empty if unanswered here")
    answered: bool = True
    time: str = Field(description="hh:mm:ss of the sentence where the question starts, copied from the transcript")
    answer_time: str = Field(default="", description="hh:mm:ss where the answer to this question starts")
    subtopics: list[str] = Field(default_factory=list)
    ai_relevant: bool = False


class Position(BaseModel):
    speaker: str
    subtopic: str = Field(description="short snake_case label, e.g. regulation, sovereignty, compute_infrastructure")
    target: str = Field(description="what the position is about, e.g. 'Cloud Act', 'public procurement rules', 'open-source AI models'")
    stance: Stance = Field(description="the speaker's attitude towards `target`")
    claim: str = Field(description="the position in one sentence, in French, in your own words (not a copy of the quote)")
    quote: str = Field(description="VERBATIM excerpt of at most 35 words copied exactly from the transcript")
    time: str


class WindowOut(BaseModel):
    qa: list[QA] = Field(default_factory=list)
    positions: list[Position] = Field(default_factory=list)
    window_summary: str = ""


class Overall(BaseModel):
    summary: str = Field(description="150-250 words, in French")
    key_takeaways: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    ai_stance_overview: str = Field(default="", description="how the witness and the deputies position themselves on AI")
