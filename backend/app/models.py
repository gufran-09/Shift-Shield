"""Validated API schemas. Anonymous rest submissions intentionally have no identity fields."""
from __future__ import annotations

from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Surface = Literal["bare_soil", "grass", "asphalt", "light_concrete", "dark_concrete", "mixed"]
Shade = Literal["none", "partial", "mostly", "indoor"]
WindExposure = Literal["open", "sheltered", "partial_or_unknown"]
Intensity = Literal["light", "moderate", "heavy", "very_heavy"]
Acclimatization = Literal["acclimatized", "unacclimatized", "unknown"]
PPE = Literal["normal", "heavy", "impermeable"]
Language = Literal["en", "hi"]


class Task(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=80)
    intensity: Intensity
    duration_minutes: int = Field(ge=15, le=720)


class SiteCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(min_length=2, max_length=100)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timezone: str = Field(default="Asia/Kolkata", min_length=2, max_length=60)
    surface: Surface = "light_concrete"
    shade: Shade = "none"
    wind_exposure: WindExposure = "partial_or_unknown"
    land_use: Literal["vegetated", "dense_built_up", "unknown"] = "unknown"
    enclosure: Literal["open", "metal_roof", "concrete_roof", "ventilated", "closed"] = "open"
    intensity: Intensity = "heavy"
    acclimatization: Acclimatization = "unknown"
    ppe: PPE = "normal"
    shift_start: str = Field(default="08:00", pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    shift_end: str = Field(default="17:00", pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    tasks: list[Task] = Field(default_factory=list, max_length=6)
    supervisor_email: str | None = Field(default=None, max_length=254)
    email_alert_opt_in: bool = False
    language: Language = "en"

    @field_validator("supervisor_email")
    @classmethod
    def validate_email_if_present(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        value = value.strip()
        if "@" not in value or len(value) > 254 or value.startswith("@") or value.endswith("@"):
            raise ValueError("Enter a valid supervisor email address")
        return value

    @field_validator("tasks")
    @classmethod
    def validate_task_count(cls, value: list[Task]) -> list[Task]:
        if value and not 3 <= len(value) <= 6:
            raise ValueError("Provide 3–6 tasks, or leave the task list empty")
        return value


class PublicCheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    surface: Surface = "light_concrete"
    shade: Shade = "none"
    wind_exposure: WindExposure = "partial_or_unknown"
    land_use: Literal["vegetated", "dense_built_up", "unknown"] = "unknown"
    enclosure: Literal["open", "metal_roof", "concrete_roof", "ventilated", "closed"] = "open"
    intensity: Intensity = "moderate"
    acclimatization: Acclimatization = "unknown"
    ppe: PPE = "normal"
    timezone: str = Field(default="auto", min_length=2, max_length=60)


class RestSubmission(BaseModel):
    """One aggregate vote. Never add account, name, contact or device keys here."""
    model_config = ConfigDict(extra="forbid")
    window_id: str = Field(min_length=8, max_length=128)
    break_received: bool
    water_available: bool | None = None
    shade_available: bool | None = None
    symptoms: list[Literal["dizzy", "headache", "cramps", "ok"]] = Field(default_factory=list, max_length=4)

    @field_validator("symptoms")
    @classmethod
    def no_duplicate_symptoms(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("Choose each symptom only once")
        return value


class RuleDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["approve", "reject", "edit"]
    requirement_text: str | None = Field(default=None, max_length=1200)
    applies_when: str | None = Field(default=None, max_length=500)
    reviewer_role: Literal["site_supervisor", "safety_officer"] = "site_supervisor"


class ReplayAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: str = Field(min_length=3, max_length=100)


class AckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(min_length=20, max_length=2000)


class HistoricalBacktestRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    start_date: date
    end_date: date
    baseline_threshold_c: float = Field(ge=10, le=60)
    baseline_source: str = Field(min_length=6, max_length=300)

    @model_validator(mode="after")
    def validate_range(self) -> "HistoricalBacktestRequest":
        if self.end_date < self.start_date:
            raise ValueError("End date must not precede start date")
        if (self.end_date - self.start_date).days > 6:
            raise ValueError("Choose a historical range of seven days or fewer")
        if self.end_date >= date.today():
            raise ValueError("Historical comparisons require completed dates")
        return self
