import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { CropGlyph, DRAWN_CROPS } from "@/components/farm/crop-glyph";
import { CropRow } from "@/components/farm/crop-row";
import { Badge, STATUS_TONE } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { IconButton } from "@/components/ui/icon-button";
import { Segmented } from "@/components/ui/segmented";
import { Track } from "@/components/ui/track";
import { cn } from "@/lib/cn";

describe("cn", () => {
  it("lets the last Tailwind utility win", () => {
    expect(cn("px-2 px-4", "text-sm", false && "hidden")).toBe("px-4 text-sm");
  });
});

describe("Button", () => {
  it("renders its label as an accessible button and fires onClick", async () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Save</Button>);
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(onClick).toHaveBeenCalledOnce();
  });
  it("does not fire when disabled", async () => {
    const onClick = vi.fn();
    render(<Button disabled onClick={onClick}>Save</Button>);
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(onClick).not.toHaveBeenCalled();
  });
  it("a caller class overrides a default one", () => {
    render(<Button className="px-9">x</Button>);
    expect(screen.getByRole("button").className).toContain("px-9");
    expect(screen.getByRole("button").className).not.toContain("px-4");
  });
});

describe("IconButton", () => {
  it("always has an accessible name", () => {
    render(<IconButton label="Search"><svg /></IconButton>);
    expect(screen.getByRole("button", { name: "Search" })).toHaveAttribute("title", "Search");
  });
});

describe("Badge", () => {
  it("shows its words and the tone's colour classes", () => {
    render(<Badge tone={STATUS_TONE.attention}>Needs attention</Badge>);
    const el = screen.getByText("Needs attention");
    expect(el.className).toContain("text-coral-ink");
  });
  it("maps the three soil-health words to three tones", () => {
    expect(STATUS_TONE).toEqual({ good: "mint", moderate: "butter", attention: "coral" });
  });
});

describe("Track", () => {
  it("is a progressbar with the value and a name", () => {
    render(<Track value={90.2} label="ID3" />);
    const bar = screen.getByRole("progressbar", { name: "ID3" });
    expect(bar).toHaveAttribute("aria-valuenow", "90.2");
  });
  it("clamps values outside 0 to 100 and survives NaN", () => {
    render(<><Track value={140} label="high" /><Track value={-5} label="low" /><Track value={Number.NaN} label="nan" /></>);
    expect(screen.getByRole("progressbar", { name: "high" })).toHaveAttribute("aria-valuenow", "100");
    expect(screen.getByRole("progressbar", { name: "low" })).toHaveAttribute("aria-valuenow", "0");
    expect(screen.getByRole("progressbar", { name: "nan" })).toHaveAttribute("aria-valuenow", "0");
  });
});

describe("Segmented", () => {
  const options = [{ value: "en", label: "EN" }, { value: "mr", label: "मराठी" }];
  it("reports the new choice", async () => {
    const onChange = vi.fn();
    render(<Segmented value="en" onChange={onChange} options={options} label="Language" />);
    await userEvent.click(screen.getByRole("button", { name: "मराठी" }));
    expect(onChange).toHaveBeenCalledWith("mr");
  });
  it("never deselects: clicking the selected option does nothing", async () => {
    const onChange = vi.fn();
    render(<Segmented value="en" onChange={onChange} options={options} label="Language" />);
    await userEvent.click(screen.getByRole("button", { name: "EN" }));
    expect(onChange).not.toHaveBeenCalled();
  });
});

describe("CropGlyph", () => {
  it("draws all 22 crops, each differently, and falls back to a neutral leaf only for an unknown crop", () => {
    expect(DRAWN_CROPS).toHaveLength(22);
    const pictures = DRAWN_CROPS.map((crop) => render(<CropGlyph crop={crop} />).container.innerHTML);
    expect(new Set(pictures).size).toBe(22);                  // no two crops share a picture
    for (const html of pictures) expect(html).toMatch(/<(path|circle|ellipse)/);
    const { container: fallback } = render(<CropGlyph crop="not-a-crop" />);
    expect(fallback.querySelector("svg g")).toBeNull();      // the Lucide leaf is a different svg, not a crop's drawing
    expect(pictures).not.toContain(fallback.innerHTML);
  });
});

describe("CropRow", () => {
  it("shows the name, the rounded score twice (bar name and number) and the status word", () => {
    render(<CropRow crop="jute" name="Jute" score={44.6} tone="butter" tag="Moderate" color="var(--butter)" />);
    expect(screen.getByText("Jute")).toBeInTheDocument();
    expect(screen.getByText("45")).toBeInTheDocument();
    expect(screen.getByText("Moderate")).toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: "Jute: 45" })).toBeInTheDocument();
  });
});
