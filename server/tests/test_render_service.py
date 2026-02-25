"""Tests for the RenderService — filter building and template colors."""

from app.models.render import ExportSettings, GlobalStyle, RenderSpec, SectionSpec
from app.services.render_service import RenderService


class TestSimpleSectionFilters:
    def setup_method(self):
        self.service = RenderService()

    def test_no_sections_solid_color(self):
        spec = RenderSpec(global_style=GlobalStyle(template="nebula"))
        filt = self.service._simple_section_filters(spec, 180.0, 1920, 1080)
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
        filt = self.service._simple_section_filters(spec, 180.0, 1920, 1080)
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
        filt = self.service._simple_section_filters(spec, 180.0, 1920, 1080)
        assert "AA0000" in filt
        assert "00AA00" in filt
        assert "0000AA" in filt
        assert "[out]" in filt  # Final label

    def test_empty_color_palette_uses_default(self):
        spec = RenderSpec(
            sections=[SectionSpec(label="x", start_time=0, end_time=10, color_palette=[])]
        )
        filt = self.service._simple_section_filters(spec, 10.0, 1920, 1080)
        assert "7C5CFC" in filt  # Default accent color


class TestFullFilterGraph:
    """Tests for the full filter graph builder."""

    def setup_method(self):
        self.service = RenderService()

    def test_no_sections_returns_solid(self):
        spec = RenderSpec(global_style=GlobalStyle(template="cinematic"))
        filt = self.service._build_full_filter_graph(
            spec, "cinematic", 60.0, 1920, 1080, 30, [], {}
        )
        assert "[vout]" in filt
        assert "1A1A28" in filt

    def test_sections_produce_concat(self):
        spec = RenderSpec(
            sections=[
                SectionSpec(label="intro", start_time=0, end_time=30, color_palette=["#FF0000"]),
                SectionSpec(label="verse", start_time=30, end_time=90, color_palette=["#00FF00"]),
            ]
        )
        filt = self.service._build_full_filter_graph(
            spec, "nebula", 90.0, 1920, 1080, 30, [], {}
        )
        assert "concat=n=2" in filt
        assert "[vout]" in filt

    def test_beats_add_flash_layer(self):
        spec = RenderSpec(
            sections=[
                SectionSpec(label="a", start_time=0, end_time=10, color_palette=["#AABBCC"]),
            ]
        )
        beats = [1.0, 2.0, 3.0]
        filt = self.service._build_full_filter_graph(
            spec, "geometric", 10.0, 1920, 1080, 30, beats, {}
        )
        assert "beat_fl" in filt
        assert "blend" in filt

    def test_beat_flash_uses_comparison_operators(self):
        """Beat flash must use (T>=a)*(T<=b) — no commas, uppercase T for geq."""
        result = self.service._beat_flash([1.0, 2.5], 10.0, 1920, 1080, 30)
        assert result is not None
        assert "geq" in result
        # Must use uppercase T (geq variable) not lowercase t (enable variable)
        assert "(T>=" in result
        assert "(T<=" in result
        # Must not contain between() — commas break FFmpeg filter parsing
        assert "between" not in result


class TestProceduralEffect:
    """Tests for template-specific procedural effects."""

    def setup_method(self):
        self.service = RenderService()

    def test_nebula_produces_geq(self):
        result = self.service._procedural_effect("nebula", "s0", 1920, 1080, 10, 30, 0.5)
        assert result is not None
        assert "geq" in result

    def test_geometric_produces_mandelbrot(self):
        result = self.service._procedural_effect("geometric", "s0", 1920, 1080, 10, 30, 0.5)
        assert result is not None
        assert "mandelbrot" in result

    def test_waveform_produces_cellauto(self):
        result = self.service._procedural_effect("waveform", "s0", 1920, 1080, 10, 30, 0.5)
        assert result is not None
        assert "cellauto" in result

    def test_retro_produces_life(self):
        result = self.service._procedural_effect("retro", "s0", 1920, 1080, 10, 30, 0.5)
        assert result is not None
        assert "life" in result

    def test_unknown_returns_none(self):
        result = self.service._procedural_effect("unknown_template", "s0", 1920, 1080, 10, 30, 0.5)
        assert result is None


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
