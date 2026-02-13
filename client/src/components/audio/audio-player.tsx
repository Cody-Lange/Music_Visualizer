import { useRef, useEffect, useCallback } from "react";
import { Play, Pause, Volume2, VolumeX } from "lucide-react";
import { useAudioStore } from "@/stores/audio-store";

export function AudioPlayer() {
  const audioRef = useRef<HTMLAudioElement>(null);
  const audioUrl = useAudioStore((s) => s.audioUrl);
  const isPlaying = useAudioStore((s) => s.isPlaying);
  const currentTime = useAudioStore((s) => s.currentTime);
  const duration = useAudioStore((s) => s.duration);
  const volume = useAudioStore((s) => s.volume);
  const setIsPlaying = useAudioStore((s) => s.setIsPlaying);
  const setCurrentTime = useAudioStore((s) => s.setCurrentTime);
  const setAudioBuffer = useAudioStore((s) => s.setAudioBuffer);
  const setVolume = useAudioStore((s) => s.setVolume);

  // Decode audio buffer for analysis
  useEffect(() => {
    if (!audioUrl) return;
    const audio = audioRef.current;
    if (!audio) return;

    audio.src = audioUrl;
    audio.volume = volume;

    // Also decode AudioBuffer for client-side analysis
    fetch(audioUrl)
      .then((r) => r.arrayBuffer())
      .then((buf) => new AudioContext().decodeAudioData(buf))
      .then(setAudioBuffer)
      .catch(() => {
        // Non-critical — visualization will work without pre-decoded buffer
      });
  }, [audioUrl, setAudioBuffer, volume]);

  // Sync playback state
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    if (isPlaying) {
      audio.play().catch(() => setIsPlaying(false));
    } else {
      audio.pause();
    }
  }, [isPlaying, setIsPlaying]);

  // Update current time during playback
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const onTimeUpdate = () => setCurrentTime(audio.currentTime);
    const onEnded = () => setIsPlaying(false);
    const onLoadedMetadata = () => {
      // Duration may come from here too
    };

    audio.addEventListener("timeupdate", onTimeUpdate);
    audio.addEventListener("ended", onEnded);
    audio.addEventListener("loadedmetadata", onLoadedMetadata);

    return () => {
      audio.removeEventListener("timeupdate", onTimeUpdate);
      audio.removeEventListener("ended", onEnded);
      audio.removeEventListener("loadedmetadata", onLoadedMetadata);
    };
  }, [setCurrentTime, setIsPlaying]);

  const togglePlay = useCallback(() => {
    setIsPlaying(!isPlaying);
  }, [isPlaying, setIsPlaying]);

  const seek = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const time = parseFloat(e.target.value);
      setCurrentTime(time);
      if (audioRef.current) {
        audioRef.current.currentTime = time;
      }
    },
    [setCurrentTime],
  );

  const formatTime = (seconds: number): string => {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, "0")}`;
  };

  return (
    <div className="flex items-center gap-3 px-4 py-2">
      <audio ref={audioRef} preload="auto" />

      <button
        onClick={togglePlay}
        className="flex h-8 w-8 items-center justify-center rounded-full bg-accent text-white hover:bg-accent-hover"
      >
        {isPlaying ? <Pause size={14} /> : <Play size={14} className="ml-0.5" />}
      </button>

      <span className="w-12 text-right text-xs text-text-secondary tabular-nums">
        {formatTime(currentTime)}
      </span>

      <input
        type="range"
        min={0}
        max={duration || 0}
        step={0.1}
        value={currentTime}
        onChange={seek}
        className="h-1 flex-1 cursor-pointer appearance-none rounded-full bg-border accent-accent"
      />

      <span className="w-12 text-xs text-text-secondary tabular-nums">
        {formatTime(duration)}
      </span>

      <div className="flex items-center gap-1">
        <button
          onClick={() => setVolume(volume > 0 ? 0 : 0.8)}
          className="p-1 text-text-secondary hover:text-text-primary"
        >
          {volume > 0 ? <Volume2 size={14} /> : <VolumeX size={14} />}
        </button>
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={volume}
          onChange={(e) => setVolume(parseFloat(e.target.value))}
          className="h-1 w-16 cursor-pointer appearance-none rounded-full bg-border accent-accent"
        />
      </div>
    </div>
  );
}
