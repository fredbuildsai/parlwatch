"""Core schema. Portable column types only (SQLite now, PostgreSQL later)."""

from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Person(Base):
    __tablename__ = "person"
    id: Mapped[int] = mapped_column(primary_key=True)
    country: Mapped[str] = mapped_column(String(2))
    external_id: Mapped[str | None] = mapped_column(String(64))  # e.g. AN acteur uid PA...
    name: Mapped[str] = mapped_column(String(200))
    party: Mapped[str | None] = mapped_column(String(100))
    role: Mapped[str | None] = mapped_column(String(200))
    __table_args__ = (UniqueConstraint("country", "external_id"),)


class Meeting(Base):
    __tablename__ = "meeting"
    id: Mapped[int] = mapped_column(primary_key=True)
    country: Mapped[str] = mapped_column(String(2), index=True)
    source: Mapped[str] = mapped_column(String(50))
    external_id: Mapped[str] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(Text)
    organ: Mapped[str | None] = mapped_column(String(200))
    kind: Mapped[str | None] = mapped_column(String(50))  # audition | commission | plenary
    held_on: Mapped[date | None] = mapped_column(Date, index=True)
    agenda_text: Mapped[str | None] = mapped_column(Text)
    video_page_url: Mapped[str | None] = mapped_column(Text)
    raw: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    __table_args__ = (UniqueConstraint("country", "source", "external_id"),)

    topics: Mapped[list["MeetingTopic"]] = relationship(back_populates="meeting")


class MeetingTopic(Base):
    """Screening result for (meeting, topic). Negatives are stored too so recall can be audited."""

    __tablename__ = "meeting_topic"
    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meeting.id"), index=True)
    topic: Mapped[str] = mapped_column(String(50))
    keyword_score: Mapped[float] = mapped_column(Float, default=0.0)
    label: Mapped[str] = mapped_column(String(20))  # core | partial | mention | none
    rationale: Mapped[str | None] = mapped_column(Text)
    generator: Mapped[str | None] = mapped_column(String(100))
    meeting: Mapped[Meeting] = relationship(back_populates="topics")
    __table_args__ = (UniqueConstraint("meeting_id", "topic"),)


class ExistingTranscript(Base):
    """A transcript found before any media work (stage 3)."""

    __tablename__ = "existing_transcript"
    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meeting.id"), index=True)
    source: Mapped[str] = mapped_column(String(50))  # official_record | portal_subtitles | youtube_captions | own_db
    format: Mapped[str] = mapped_column(String(20))
    has_timestamps: Mapped[bool] = mapped_column(default=False)
    has_speakers: Mapped[bool] = mapped_column(default=False)
    coverage: Mapped[float] = mapped_column(Float, default=0.0)  # 0..1 of meeting duration/agenda covered
    language: Mapped[str | None] = mapped_column(String(8))
    quality: Mapped[float | None] = mapped_column(Float)
    url: Mapped[str | None] = mapped_column(Text)
    text: Mapped[str | None] = mapped_column(Text)


class Media(Base):
    __tablename__ = "media"
    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meeting.id"), index=True)
    stream_url: Mapped[str] = mapped_column(Text)
    audio_path: Mapped[str | None] = mapped_column(Text)
    duration_s: Mapped[float | None] = mapped_column(Float)
    sha256: Mapped[str | None] = mapped_column(String(64))


class Segment(Base):
    __tablename__ = "segment"
    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meeting.id"), index=True)
    start_s: Mapped[float | None] = mapped_column(Float)
    end_s: Mapped[float | None] = mapped_column(Float)
    speaker_label: Mapped[str | None] = mapped_column(String(100))
    person_id: Mapped[int | None] = mapped_column(ForeignKey("person.id"))
    text: Mapped[str] = mapped_column(Text)
    words: Mapped[list | None] = mapped_column(JSON)
    origin: Mapped[str] = mapped_column(String(50))  # asr:<model> | existing:<source>


class QAPair(Base):
    __tablename__ = "qa_pair"
    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meeting.id"), index=True)
    asker_id: Mapped[int | None] = mapped_column(ForeignKey("person.id"))
    answerer_id: Mapped[int | None] = mapped_column(ForeignKey("person.id"))
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    start_s: Mapped[float | None] = mapped_column(Float)
    end_s: Mapped[float | None] = mapped_column(Float)
    generator: Mapped[str] = mapped_column(String(100))


class Position(Base):
    __tablename__ = "position"
    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meeting.id"), index=True)
    person_id: Mapped[int | None] = mapped_column(ForeignKey("person.id"))
    subtopic: Mapped[str] = mapped_column(String(100))
    stance: Mapped[str] = mapped_column(String(30))
    quote: Mapped[str] = mapped_column(Text)
    start_s: Mapped[float | None] = mapped_column(Float)
    generator: Mapped[str] = mapped_column(String(100))


class Summary(Base):
    __tablename__ = "summary"
    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meeting.id"), unique=True)
    summary: Mapped[str] = mapped_column(Text)
    takeaways: Mapped[list] = mapped_column(JSON, default=list)
    open_questions: Mapped[list] = mapped_column(JSON, default=list)
    generator: Mapped[str] = mapped_column(String(100))
    pipeline_version: Mapped[str] = mapped_column(String(20))


class Task(Base):
    """Resumable queue: one row per `<stage>:<id>`."""

    __tablename__ = "tasks"
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    stage: Mapped[str] = mapped_column(String(50), index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)  # pending|done|failed|skipped
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
