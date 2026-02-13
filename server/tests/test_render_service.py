"""Tests for the RenderService — filter building and template colors."""

from app.models.render import ExportSettings, GlobalStyle, RenderSpec, SectionSpec
from app.services.render_service import RenderService


class TestBuildSectionFilters:
    def setup_method(self):
        self.service = RenderService()

    def test_no_sections_solid_color(self):
        spec = RenderSpec(global_style=GlobalStyle(template="nebula"))
        filt = self.service._build_section_filters(spec, 180.0, 1920, 1080)
        assert "drawbox" in filt
        assert "1B1464" in filt  # nebula color

    def test_single_section(self):
        spec = RenderSpec(
            sections=[
                SectionSpec(
                    label="intro",
                    start_time=0.0,
                    end_time=30.0,
                    color_palette=["#FF0000"],
                ),
            ]
        )
        filt = self.service._build_section_filters(spec, 180.0, 1920, 1080)
        assert "FF0000" in filt
        assert "between(t,0.0,30.0)" in filt

    def test_multiple_sections(self):
        spec = RenderSpec(
            sections=[
                SectionSpec(label="verse", start_time=0, end_time=60, color_palette=["#AA0000"]),
                SectionSpec(label="chorus", start_time=60, end_time=120, color_palette=["#00AA00"]),
                SectionSpec(label="outro", start_time=120, end_time=180, color_palette=["#0000AA"]),
            ]
        )
        filt = self.service._build_section_filters(spec, 180.0, 1920, 1080)
        assert "AA0000" in filt
        assert "00AA00" in filt
        assert "0000AA" in filt
        assert "[out]" in filt  # Final label

    def test_empty_color_palette_uses_default(self):
        spec = RenderSpec(
            sections=[SectionSpec(label="x", start_time=0, end_time=10, color_palette=[])]
        )
        filt = self.service._build_section_filters(spec, 10.0, 1920, 1080)
        assert "7C5CFC" in filt  # Default accent color


class TestTemplateBaseColor:
    def test_known_templates(self):
        assert RenderService._template_base_color("nebula") == "0x1B1464"
        assert RenderService._template_base_color("retro") == "0xFF00FF"
        assert RenderService._template_base_color("urban") == "0x333333"
        assert RenderService._template_base_color("glitchbreak") == "0xFF0066"
        assert RenderService._template_base_color("90s-anime") == "0xFF8844"

    def test_unknown_template_fallback(self):
        assert RenderService._template_base_color("unknown") == "0x0A0A0F"
        assert RenderService._template_base_color("") == "0x0A0A0F"
