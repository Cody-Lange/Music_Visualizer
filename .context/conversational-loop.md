# Conversational Loop Design

## Overview

The conversational interface is the primary way users interact with the visualizer. Powered by Gemini Flash, it guides users from initial upload through thematic analysis, iterative refinement, rendering, and post-render editing. The LLM maintains full context of the audio analysis, lyrics, and all prior conversation turns.

---

## Conversation Phases

### Phase 1: Upload & Initial Analysis

**Trigger**: User uploads an audio file and optionally provides an initial prompt.

**System behavior**:
1. Client-side analysis runs immediately (Essentia.js)
2. Server-side deep analysis begins (Librosa, Demucs, Whisper, lyrics APIs)
3. Chat displays progress messages as each analysis step completes
4. Once all analysis is complete, the LLM generates the initial thematic breakdown

**Chat flow**:
```
USER: [Uploads "bohemian_rhapsody.mp3"]
      "I want a dark, cinematic visualizer with lots of dramatic imagery"

SYSTEM: Analyzing audio...
        ✓ BPM: 72 (variable tempo)
        ✓ Key: Bb major
        ✓ Sections detected: 6 (intro, ballad, operatic, rock, outro, coda)
        ✓ Lyrics extracted (merged from Genius + Whisper)

ASSISTANT: [Streams thematic analysis...]

Here's my analysis of "Bohemian Rhapsody":

**Track Overview**
A genre-defying rock opera that moves through distinct movements...

**Themes & Symbolism**
- Guilt and confession ("Mama, just killed a man")
- Fate vs. free will ("Bismillah! No, we will not let you go")
- ...

**Pop Culture References**
- The operatic section references commedia dell'arte characters...
- "Scaramouche" from Italian theater...

**Section-by-Section Visualization Suggestions**

1. **Intro (0:00-0:49)** — "Is this the real life?"
   - Mood: Ethereal, questioning
   - Colors: Deep indigo, silver mist (#1B1464, #C0C0C0)
   - Visuals: Floating in darkness, distant stars slowly appearing
   - Motion: Extremely slow, dreamlike
   ...

[continues for each section]

**Would you like to adjust any of these suggestions? I can modify
colors, visual themes, intensity, or the overall style for any section.**
```

### Phase 2: Iterative Refinement

**Trigger**: User responds with feedback.

**LLM system prompt context** (maintained across turns):
```
You are a creative director for music visualization. You have access to:
- Full audio analysis (BPM, key, sections, energy profile)
- Complete lyrics with timestamps
- Your previous suggestions and the user's feedback

Your role:
1. Respond to user feedback with specific, modified suggestions
2. Always ground suggestions in the actual audio data (reference specific
   sections, timestamps, energy levels)
3. When suggesting colors, provide hex codes
4. When suggesting motion, describe in terms the user can visualize
5. Ask clarifying follow-up questions when the user's intent is ambiguous
6. Keep track of all agreed-upon decisions
7. When the user seems satisfied, summarize the final plan and ask for
   confirmation to proceed with rendering
```

**Example refinement exchanges**:
```
USER: I like the operatic section ideas but the ballad section feels too
      calm. Can we make it more ominous? Also, I'd prefer a gothic
      aesthetic throughout.

ASSISTANT: Great call — the ballad section's lyrics are actually quite dark
("Mama, just killed a man"), so an ominous treatment fits perfectly.

**Updated: Ballad Section (0:49-2:37)**
- Mood: Ominous, confessional → gothic cathedral atmosphere
- Colors: Shifting from blood red to deep black (#8B0000 → #0D0D0D)
- Visuals: Gothic arches emerging from shadow, candlelight flickering
  with the piano notes, rain on stained glass
- Motion: Slow but with subtle unease — slight camera sway, shadows
  that move independently
- AI keyframe prompt: "Gothic cathedral interior, candlelit, blood red
  stained glass windows, dark shadows, rain, ominous atmosphere,
  cinematic lighting, 8k"

**Gothic aesthetic applied globally:**
- All sections now use gothic architectural elements as visual anchors
- Color palettes shifted darker across the board
- Added recurring motifs: stone textures, iron, candlelight, ravens

Would you like me to walk through how each other section looks with
the gothic treatment? Or shall we focus on any specific section?
```

### Phase 3: Render Confirmation

**Trigger**: LLM detects user satisfaction or user explicitly asks to render.

**Detection heuristics** (in LLM system prompt):
```
Detect when the user is satisfied. Signs include:
- "That's perfect", "Love it", "Let's go", "Looks good"
- "Render it", "Make the video", "Start rendering"
- Lack of further change requests after 2+ exchanges
- User asking about export settings or timeline

When you detect satisfaction, present a FINAL SUMMARY of all agreed-upon
decisions before triggering the render. Include:
- Global style
- Each section's visual plan (abbreviated)
- Export settings
- Estimated render time

Ask for explicit confirmation: "Ready to render?"
```

**Chat flow**:
```
USER: This is exactly what I had in mind. Let's do it.

ASSISTANT: Here's the final visualization plan:

**Global Style**: Gothic cinematic, dark atmospheric
**Resolution**: 1080p 16:9 (YouTube)
**AI Keyframes**: 14 images across 6 sections

| Section | Time | Theme | Key Visual |
|---------|------|-------|------------|
| Intro | 0:00-0:49 | Ethereal gothic | Misty cathedral exterior |
| Ballad | 0:49-2:37 | Ominous confessional | Candlelit cathedral interior |
| Operatic | 2:37-3:03 | Chaotic battle | Gargoyles and lightning |
| Rock | 3:03-4:07 | Explosive release | Shattered stained glass |
| Outro | 4:07-5:08 | Melancholic resolution | Ruins at dawn |
| Coda | 5:08-5:55 | Final stillness | Single candle in darkness |

Estimated render time: ~8-12 minutes

**Ready to render?**
```

### Phase 4: Rendering

**During render**: Chat shows real-time progress.

```
SYSTEM: Rendering your visualization...
        ⏳ Generating AI keyframes... (3/14)
        ⏳ Generating AI keyframes... (14/14) ✓
        ⏳ Rendering video... Frame 1,200 / 10,800 (11%)
        ⏳ Rendering video... Frame 5,400 / 10,800 (50%)
        ⏳ Rendering video... Frame 10,800 / 10,800 (100%) ✓
        ⏳ Encoding final video...
        ✓ Render complete!

ASSISTANT: Your visualization is ready! You can preview it above or download
the MP4. Here are some things you can do next:

- **Edit specific sections**: "Make the rock section more intense"
- **Adjust timing**: "The transition at 2:37 feels too abrupt"
- **Change lyrics style**: "Make the lyrics larger and add a glow effect"
- **Re-render at different resolution**: "Export for TikTok (9:16)"
- **Start over**: "Let's try a completely different concept"
```

### Phase 5: Post-Render Editing

**Trigger**: User requests changes after seeing the rendered video.

```
USER: The rock section is great but the transition from operatic to rock
      at 3:03 feels too smooth. I want a hard cut with a flash of white.

ASSISTANT: That'll create a great dramatic impact — the abrupt shift from
the operatic chaos to the hard rock mirrors the musical transition
perfectly.

**Edit applied:**
- Transition at 3:03: Cross-dissolve → hard cut with white flash (2 frames)
- Added: Screen shake on the first beat of the rock section (frame 5,490)

This only requires re-rendering 2 seconds around the transition point.
Re-rendering now...

SYSTEM: ⏳ Re-rendering section boundary (3:01-3:05)... ✓
        ✓ Video updated!

ASSISTANT: Done! The transition now hits hard with the white flash.
Take a look — want to adjust anything else?
```

---

## LLM Context Management

### Context Window Structure

Each LLM call includes:

```json
{
  "system": "[System prompt with role, capabilities, guidelines]",
  "messages": [
    {
      "role": "user",
      "content": "[AUDIO ANALYSIS]\n{compressed analysis summary}\n\n[LYRICS]\n{full lyrics}\n\n[USER PROMPT]\n{initial user prompt}"
    },
    {
      "role": "assistant",
      "content": "{initial thematic analysis and suggestions}"
    },
    {
      "role": "user",
      "content": "{user feedback}"
    },
    {
      "role": "assistant",
      "content": "{refined suggestions}"
    },
    // ... conversation continues
    {
      "role": "user",
      "content": "{latest user message}"
    }
  ]
}
```

### Context Compression

For long conversations, compress earlier turns while preserving key decisions:

```
1. Keep the full system prompt (always)
2. Keep the audio analysis summary (always, compressed format)
3. Keep full lyrics (always)
4. For conversation history beyond 10 turns:
   - Summarize into a "decisions so far" block
   - Keep the last 6 turns in full
   - This prevents context window overflow while maintaining coherence
```

### Structured Output

When the user confirms the render, the LLM outputs a structured render spec:

```json
{
  "globalStyle": {
    "template": "cinematic",
    "styleModifiers": ["gothic", "dark", "atmospheric"],
    "recurringMotifs": ["gothic arches", "candlelight", "ravens", "stained glass"],
    "lyricsDisplay": {
      "enabled": true,
      "font": "serif",
      "size": "medium",
      "animation": "fade-word",
      "color": "#C0C0C0",
      "shadow": true
    }
  },
  "sections": [
    {
      "label": "intro",
      "startTime": 0.0,
      "endTime": 49.0,
      "colorPalette": ["#1B1464", "#C0C0C0", "#2D1B69", "#0D0D0D"],
      "motionStyle": "slow-drift",
      "intensity": 0.3,
      "aiPrompt": "Misty gothic cathedral exterior at twilight, fog...",
      "transitionIn": "fade-from-black",
      "transitionOut": "cross-dissolve",
      "visualElements": ["fog", "distant-stars", "stone-texture"]
    }
    // ... more sections
  ],
  "exportSettings": {
    "resolution": [1920, 1080],
    "fps": 30,
    "aspectRatio": "16:9",
    "format": "mp4",
    "quality": "high"
  }
}
```

---

## Follow-Up Question Strategy

The LLM is instructed to ask targeted follow-up questions to refine the visualization:

### Question Categories

| Category | Example Questions |
|----------|------------------|
| **Style preference** | "Do you prefer abstract geometric visuals or more realistic/cinematic imagery?" |
| **Color** | "The chorus has a triumphant feel — would you prefer warm golds and reds, or cool electric blues?" |
| **Intensity** | "How reactive should the visuals be to the beat? Subtle and smooth, or aggressive with hard hits?" |
| **Lyrics** | "Would you like lyrics displayed? If so, full karaoke-style word highlighting or subtle text fading in?" |
| **Specific sections** | "The bridge has a very different energy. Should it contrast sharply with the verses or maintain visual continuity?" |
| **References** | "I noticed references to [topic] in the lyrics. Would you like visual nods to this, or keep it more abstract?" |
| **Technical** | "What platform is this for? I'll optimize the aspect ratio and resolution." |

### Question Flow Rules

1. **Never ask more than 2 questions at once** — prevents overwhelming the user
2. **Always provide options** — "Would you prefer A or B?" is better than open-ended
3. **Include a default** — "I'd suggest X based on the song's mood. Would that work, or do you have something else in mind?"
4. **Respect explicit choices** — if the user said "dark and gothic" in the initial prompt, don't ask "light or dark?"
5. **Know when to stop** — after 3-4 exchanges without new change requests, offer to proceed to render
