# UI/UX Design

## Overview

The Music Visualizer application has a single-page layout with three primary zones: the media area (preview + video player), the timeline/waveform editor, and the chat interface. The design prioritizes a seamless flow from upload → analysis → refinement → render → edit.

---

## Layout

### Desktop Layout (Primary)

```
┌──────────────────────────────────────────────────────────────────┐
│  ┌─ Header ────────────────────────────────────────────────────┐ │
│  │  Logo    [Upload Audio]   [Export ▾]   [Settings ⚙]        │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─ Preview / Video Player ─────────────┬─ Chat ──────────────┐ │
│  │                                      │                     │ │
│  │   ┌──────────────────────────┐       │  [Analysis results] │ │
│  │   │                          │       │                     │ │
│  │   │   Real-time preview      │       │  [LLM suggestions]  │ │
│  │   │   or rendered video      │       │                     │ │
│  │   │                          │       │  [User messages]    │ │
│  │   │   16:9 / 9:16 / 1:1     │       │                     │ │
│  │   │   (matches export)       │       │  [LLM responses]    │ │
│  │   │                          │       │                     │ │
│  │   └──────────────────────────┘       │                     │ │
│  │   [▶ Play] [⏸ Pause] [🔊 Vol]       │                     │ │
│  │                                      │ ┌─────────────────┐ │ │
│  │   Template: [Nebula ▾]              │ │ Type a message  │ │ │
│  │   Style overrides...                 │ │ or edit request │ │ │
│  │                                      │ └─────────────────┘ │ │
│  └──────────────────────────────────────┴─────────────────────┘ │
│                                                                  │
│  ┌─ Timeline / Waveform Editor ────────────────────────────────┐ │
│  │  [Zoom: ─────●─────]  [Snap to beats: ✓]                   │ │
│  │                                                             │ │
│  │  ┌─ Waveform ──────────────────────────────────────────┐    │ │
│  │  │ ▁▂▃▅▇▅▃▂▁▂▃▅▇█▇▅▃▁▂▃▅▇▅▃▂▁▂▅▇█▇▅▃▂▁▁▂▃▅▇▅▃▂▁   │    │ │
│  │  │ |intro  |  verse 1   | chorus 1  | verse 2  |cho2| │    │ │
│  │  │ ● ● ● ● ● ● ● ● ● ● ● ● ● ● ● ● ● ● ● ● ● ●  │    │ │
│  │  │ ^ beats                                             │    │ │
│  │  └─────────────────────────────────────────────────────┘    │ │
│  │                                                             │ │
│  │  ┌─ Lyrics Track ─────────────────────────────────────┐     │ │
│  │  │ "Is this the real life" ... "easy come easy go" ... │     │ │
│  │  └─────────────────────────────────────────────────────┘    │ │
│  │                                                             │ │
│  │  ┌─ Visual Keyframes ─────────────────────────────────┐     │ │
│  │  │ [🖼️]        [🖼️]      [🖼️]      [🖼️]      [🖼️]   │     │ │
│  │  │ intro      verse     chorus    bridge    outro     │     │ │
│  │  └─────────────────────────────────────────────────────┘    │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

### Mobile Layout (Responsive)

On mobile, the layout stacks vertically:
1. Preview (top, 50vh max)
2. Chat (expandable, takes remaining space)
3. Timeline (accessible via tab/swipe, simplified)

---

## User Flow

### Happy Path

```
1. Land on page → See upload prompt with example visualizations

2. Upload audio file
   → Drag-and-drop zone or file picker
   → Accepts: MP3, WAV, FLAC, OGG, M4A, AAC
   → Max file size: 50 MB
   → Optional: Enter initial prompt ("dark and moody cyberpunk theme")

3. Analysis in progress
   → Waveform appears immediately (client-side)
   → Beat markers populate in real-time
   → Progress indicators for server-side analysis
   → Real-time procedural preview starts playing

4. Analysis complete → Chat populated with thematic breakdown
   → User reads suggestions
   → User responds with feedback
   → LLM refines suggestions
   → Repeat until satisfied

5. User confirms → Render begins
   → Progress bar with frame count
   → Preview continues to play during render
   → Estimated time remaining shown

6. Render complete → Video player shows rendered video
   → Download button active
   → User can request edits in chat

7. Optional: Edit loop
   → User describes changes
   → Affected sections re-rendered
   → Updated video shown

8. Export
   → Choose preset (YouTube, TikTok, etc.) or custom
   → Download MP4
```

---

## Key UI Components

### Audio Upload Zone

- Large drag-and-drop area (centered on empty state)
- File type validation with friendly error messages
- Upload progress bar
- Audio metadata display after upload (title, artist, duration, format)
- Optional text input for initial prompt

### Preview Player

- Standard video player controls (play, pause, seek, volume)
- Aspect ratio toggle (preview how it looks in 16:9, 9:16, 1:1)
- Fullscreen mode
- Toggle between real-time preview and rendered video (after render)
- Visual quality indicator (Preview / Rendered)

### Chat Interface

- Message bubbles (user on right, assistant on left)
- Streamed LLM responses (text appears word-by-word)
- Collapsible sections in LLM responses (track overview, per-section analysis)
- Inline color swatches next to hex codes
- Clickable section references (clicking "Chorus 1" in chat highlights that section in timeline)
- "Accept suggestion" buttons inline with each section suggestion
- Typing indicator while LLM is generating

### Timeline / Waveform Editor

- Zoomable waveform (mouse wheel / pinch)
- Scrollable (click and drag)
- Playhead indicator synced to audio playback
- Beat markers (auto-detected, draggable for manual correction)
- Section boundaries (labeled, draggable)
- Section color coding (matches visualization color palette)
- Lyrics track (word-level blocks, clickable to seek)
- Visual keyframes track (thumbnail previews of AI-generated images)
- Click anywhere to seek audio to that point

### Export Settings Panel

- Preset selector (YouTube, TikTok, Instagram, Twitter, 4K, Custom)
- Resolution display
- FPS selector (24, 30, 60)
- Quality slider (file size vs. quality tradeoff)
- Estimated file size
- Render button (prominent, disabled until visualization is confirmed)

---

## Visual Design System

### Color Palette (Application UI — Not Visualization)

| Token | Color | Usage |
|-------|-------|-------|
| `--bg-primary` | `#0A0A0F` | Main background |
| `--bg-secondary` | `#12121A` | Card/panel backgrounds |
| `--bg-tertiary` | `#1A1A28` | Elevated surfaces |
| `--border` | `#2A2A3A` | Borders and dividers |
| `--text-primary` | `#F0F0F5` | Primary text |
| `--text-secondary` | `#8888AA` | Secondary/muted text |
| `--accent` | `#7C5CFC` | Primary accent (buttons, highlights) |
| `--accent-hover` | `#9B7FFF` | Accent hover state |
| `--success` | `#34D399` | Success states, completed indicators |
| `--warning` | `#FBBF24` | Warning states |
| `--error` | `#F87171` | Error states |

The application uses a dark theme by default — appropriate for a media creation tool and ensures the visualization preview is the visual focal point.

### Typography

| Element | Font | Size | Weight |
|---------|------|------|--------|
| Headings | Inter | 18-24px | 600 |
| Body | Inter | 14px | 400 |
| Chat messages | Inter | 14px | 400 |
| Code/technical | JetBrains Mono | 13px | 400 |
| Timeline labels | Inter | 11px | 500 |
| Buttons | Inter | 14px | 500 |

### Spacing

- Base unit: 4px
- Component padding: 12-16px
- Section gaps: 16-24px
- Timeline track height: 40px

---

## Empty States & Onboarding

### First Visit

```
┌──────────────────────────────────────────┐
│                                          │
│         🎵  Music Visualizer             │
│                                          │
│   Upload a track and describe your       │
│   vision. AI will analyze the music      │
│   and help create a beat-synced          │
│   visualization video.                   │
│                                          │
│   ┌──────────────────────────────┐       │
│   │                              │       │
│   │   Drop your audio file here  │       │
│   │   or click to browse         │       │
│   │                              │       │
│   │   MP3, WAV, FLAC, OGG, M4A  │       │
│   │   Up to 50 MB               │       │
│   │                              │       │
│   └──────────────────────────────┘       │
│                                          │
│   Optionally describe your vision:       │
│   ┌──────────────────────────────┐       │
│   │ "dark cinematic with gothic  │       │
│   │  imagery..."                 │       │
│   └──────────────────────────────┘       │
│                                          │
│           [ Start Visualizing ]          │
│                                          │
│   ── Example Visualizations ──           │
│   [Preview 1] [Preview 2] [Preview 3]   │
│                                          │
└──────────────────────────────────────────┘
```

### Analysis In Progress

- Skeleton loaders for timeline and chat
- Animated progress indicators with step labels
- Real-time preview starts as soon as client-side analysis completes (before server analysis finishes)

---

## Accessibility

- All interactive elements are keyboard navigable
- ARIA labels on timeline controls, beat markers, and section boundaries
- Color contrast ratios meet WCAG AA standards
- Screen reader announcements for analysis progress and render status
- Reduced motion mode: disable beat-reactive UI animations
- Focus management: chat input receives focus after LLM response completes

---

## Responsive Breakpoints

| Breakpoint | Layout |
|-----------|--------|
| >= 1280px | Full layout: preview + chat side by side, timeline below |
| 768-1279px | Preview stacks above chat, timeline below (narrower) |
| < 768px | Single column: preview → chat → timeline (tabs) |

---

## Loading & Progress States

| State | UI Treatment |
|-------|-------------|
| Audio uploading | Progress bar in upload zone |
| Client-side analysis | Waveform drawing progressively, beat markers appearing |
| Server-side analysis | Checklist with steps (each gets a checkmark on completion) |
| LLM generating | Streaming text in chat bubble + typing indicator |
| AI keyframes generating | Thumbnail placeholders in timeline, filled as each completes |
| Video rendering | Progress bar with frame count, percentage, and ETA |
| Re-rendering (edit) | Minimal progress indicator, section-specific |

---

## Error States

| Error | UI Treatment |
|-------|-------------|
| Invalid file format | Inline error below upload zone with supported formats |
| File too large | Inline error with size limit |
| Analysis failure | Error message in chat with retry button |
| LLM rate limited | "Please wait a moment..." with auto-retry countdown |
| Render failure | Error details in chat with "Retry" and "Simplify" options |
| Network error | Toast notification with retry |
