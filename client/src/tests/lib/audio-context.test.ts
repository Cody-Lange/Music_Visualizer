import { describe, it, expect, beforeEach, vi } from "vitest";
import { getEnergyBands } from "@/lib/audio-context";

describe("getEnergyBands", () => {
  it("returns all zero for empty data", () => {
    const data = new Uint8Array(0);
    const bands = getEnergyBands(data);
    expect(bands.bass).toBe(0);
    expect(bands.lowMid).toBe(0);
    expect(bands.mid).toBe(0);
    expect(bands.highMid).toBe(0);
    expect(bands.treble).toBe(0);
  });

  it("returns normalized values between 0 and 1", () => {
    const data = new Uint8Array(1024);
    data.fill(128);
    const bands = getEnergyBands(data);

    expect(bands.bass).toBeGreaterThanOrEqual(0);
    expect(bands.bass).toBeLessThanOrEqual(1);
    expect(bands.lowMid).toBeGreaterThanOrEqual(0);
    expect(bands.lowMid).toBeLessThanOrEqual(1);
    expect(bands.mid).toBeGreaterThanOrEqual(0);
    expect(bands.mid).toBeLessThanOrEqual(1);
    expect(bands.highMid).toBeGreaterThanOrEqual(0);
    expect(bands.highMid).toBeLessThanOrEqual(1);
    expect(bands.treble).toBeGreaterThanOrEqual(0);
    expect(bands.treble).toBeLessThanOrEqual(1);
  });

  it("all bands ~0.5 for constant 128 data", () => {
    const data = new Uint8Array(1024);
    data.fill(128);
    const bands = getEnergyBands(data);

    // 128/255 ≈ 0.502
    expect(bands.bass).toBeCloseTo(128 / 255, 2);
    expect(bands.mid).toBeCloseTo(128 / 255, 2);
    expect(bands.treble).toBeCloseTo(128 / 255, 2);
  });

  it("returns 1.0 for max (255) data", () => {
    const data = new Uint8Array(1024);
    data.fill(255);
    const bands = getEnergyBands(data);

    expect(bands.bass).toBeCloseTo(1.0, 2);
    expect(bands.treble).toBeCloseTo(1.0, 2);
  });

  it("returns 0.0 for silent (0) data", () => {
    const data = new Uint8Array(1024);
    data.fill(0);
    const bands = getEnergyBands(data);

    expect(bands.bass).toBe(0);
    expect(bands.lowMid).toBe(0);
    expect(bands.mid).toBe(0);
    expect(bands.highMid).toBe(0);
    expect(bands.treble).toBe(0);
  });

  it("bass-heavy data shows higher bass", () => {
    const data = new Uint8Array(1024);
    data.fill(0);
    // Fill bass bins (first 4% = ~41 bins) with high values
    const bassEnd = Math.floor(1024 * 0.04);
    for (let i = 0; i < bassEnd; i++) {
      data[i] = 200;
    }

    const bands = getEnergyBands(data);
    expect(bands.bass).toBeGreaterThan(0.5);
    expect(bands.treble).toBe(0);
  });

  it("treble-heavy data shows higher treble", () => {
    const data = new Uint8Array(1024);
    data.fill(0);
    // Fill treble bins (last 50% = 512 bins) with high values
    const highMidEnd = Math.floor(1024 * 0.5);
    for (let i = highMidEnd; i < 1024; i++) {
      data[i] = 200;
    }

    const bands = getEnergyBands(data);
    expect(bands.treble).toBeGreaterThan(0.5);
    expect(bands.bass).toBe(0);
  });
});
