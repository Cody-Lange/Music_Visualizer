from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


def _to_camel(string: str) -> str:
    """Convert snake_case to camelCase."""
    components = string.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


VisualTemplate = Literal[
    "shader", "nebula", "geometric", "waveform", "cinematic", "retro", "nature", "abstract", "urban",
    "glitchbreak", "90s-anime",
]
MotionStyle = Literal[
    "slow-drift", "pulse", "energetic", "chaotic", "breathing", "glitch", "smooth-flow", "staccato"
]
TransitionType = Literal[
    "fade-from-black",
    "fade-to-black",
    "cross-dissolve",
    "hard-cut",
    "morph",
    "flash-white",
    "wipe",
    "zoom-in",
    "zoom-out",
]
LyricsAnimation = Literal["fade-word", "typewriter", "karaoke", "float-up", "none"]
AspectRatio = Literal["16:9", "9:16", "1:1"]
VideoQuality = Literal["draft", "standard", "high"]


class LyricsDisplayConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=_to_camel)

    enabled: bool = True
    font: Literal["sans", "serif", "mono"] = "sans"
    size: Literal["small", "medium", "large"] = "medium"
    animation: LyricsAnimation = "fade-word"
    color: str = "#F0F0F5"
    shadow: bool = True


class SectionSpec(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=_to_camel)

    label: str
    start_time: float
    end_time: float
    color_palette: list[str] = Field(default_factory=lambda: ["#7C5CFC", "#1A1A28"])
    motion_style: MotionStyle = "slow-drift"
    intensity: float = Field(ge=0, le=1, default=0.5)
    ai_prompt: str = ""
    transition_in: TransitionType = "cross-dissolve"
    transition_out: TransitionType = "cross-dissolve"
    visual_elements: list[str] = Field(default_factory=list)
    keyframe_url: str | None = None


class GlobalStyle(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=_to_camel)

    template: VisualTemplate = "shader"
    shader_description: str = ""
    style_modifiers: list[str] = Field(default_factory=list)
    recurring_motifs: list[str] = Field(default_factory=list)
    lyrics_display: LyricsDisplayConfig = Field(default_factory=LyricsDisplayConfig)


class ExportSettings(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=_to_camel)

    resolution: tuple[int, int] = (1920, 1080)
    fps: Literal[24, 30, 60] = 30
    aspect_ratio: AspectRatio = "16:9"
    format: Literal["mp4"] = "mp4"
    quality: VideoQuality = "high"


class RenderSpec(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=_to_camel)

    global_style: GlobalStyle = Field(default_factory=GlobalStyle)
    sections: list[SectionSpec] = Field(default_factory=list)
    export_settings: ExportSettings = Field(default_factory=ExportSettings)


class RenderRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=_to_camel)

    job_id: str
    render_spec: RenderSpec


class RenderEditRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=_to_camel)

    edit_description: str
    render_spec: RenderSpec | None = None
