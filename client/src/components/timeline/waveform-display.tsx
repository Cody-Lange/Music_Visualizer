import { useRef, useEffect } from "react";

interface Props {
  rms: number[];
  times: number[];
  beats: number[];
  currentTime: number;
  duration: number;
  zoom: number;
}

export function WaveformDisplay({ rms, beats, currentTime, duration, zoom }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || rms.length === 0 || duration === 0) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const w = rect.width;
    const h = rect.height;
    const midY = h / 2;

    // Clear
    ctx.clearRect(0, 0, w, h);

    // Find max RMS for normalization
    const maxRms = Math.max(...rms, 0.01);

    // Draw waveform bars
    const barCount = Math.min(rms.length, Math.floor(w * zoom));
    const step = Math.max(1, Math.floor(rms.length / barCount));
    const barWidth = w / barCount;

    for (let i = 0; i < barCount; i++) {
      const idx = i * step;
      const value = (rms[idx] ?? 0) / maxRms;
      const barH = value * midY * 0.9;

      const x = i * barWidth;
      const timeAtBar = (i / barCount) * duration;
      const isPast = timeAtBar < currentTime;

      ctx.fillStyle = isPast ? "#7C5CFC" : "#2A2A3A";
      ctx.fillRect(x, midY - barH, Math.max(1, barWidth - 1), barH * 2);
    }

    // Draw beat markers
    ctx.strokeStyle = "#7C5CFC40";
    ctx.lineWidth = 1;
    for (const beat of beats) {
      const x = (beat / duration) * w;
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, h);
      ctx.stroke();
    }

    // Draw playhead
    const playheadX = (currentTime / duration) * w;
    ctx.strokeStyle = "#F0F0F5";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(playheadX, 0);
    ctx.lineTo(playheadX, h);
    ctx.stroke();
  }, [rms, beats, currentTime, duration, zoom]);

  return (
    <canvas
      ref={canvasRef}
      className="h-20 w-full"
      style={{ imageRendering: "pixelated" }}
    />
  );
}
