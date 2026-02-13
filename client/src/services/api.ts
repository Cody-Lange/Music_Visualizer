/**
 * REST API client for the Music Visualizer backend.
 */

const BASE_URL = "/api";

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    throw new ApiError(response.status, body.detail ?? "Request failed");
  }

  return response.json() as Promise<T>;
}

// --- Audio ---

export interface UploadResponse {
  job_id: string;
  status: string;
}

export async function uploadAudio(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  return request<UploadResponse>("/audio/upload", {
    method: "POST",
    body: formData,
  });
}

export async function getAnalysis(jobId: string): Promise<{ job_id: string; analysis: unknown }> {
  return request(`/audio/${jobId}/analysis`);
}

export async function getWaveform(
  jobId: string,
): Promise<{ job_id: string; times: number[]; rms: number[] }> {
  return request(`/audio/${jobId}/waveform`);
}

// --- Lyrics ---

export async function fetchLyrics(
  title: string,
  artist: string,
  jobId?: string,
): Promise<{ lyrics: unknown }> {
  return request("/lyrics/fetch", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, artist, job_id: jobId }),
  });
}

export async function getLyrics(jobId: string): Promise<{ lyrics: unknown }> {
  return request(`/lyrics/${jobId}`);
}

// --- Render ---

export async function startRender(
  jobId: string,
  renderSpec: unknown,
): Promise<{ render_id: string; status: string }> {
  return request("/render/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ job_id: jobId, render_spec: renderSpec }),
  });
}

export async function getRenderStatus(
  renderId: string,
): Promise<{
  render_id: string;
  status: string;
  percentage: number;
  download_url?: string;
  error?: string;
}> {
  return request(`/render/${renderId}/status`);
}

export async function submitRenderEdit(
  renderId: string,
  editDescription: string,
): Promise<{ render_id: string; status: string }> {
  return request(`/render/${renderId}/edit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ edit_description: editDescription }),
  });
}

// --- Health ---

export async function healthCheck(): Promise<{ status: string }> {
  return request("/health");
}
