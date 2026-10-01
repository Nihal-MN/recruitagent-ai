import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MarkdownLite } from "@/components/MarkdownLite";

describe("MarkdownLite", () => {
  it("renders bold and inline code", () => {
    render(<MarkdownLite text="**Amira Haddad** scored `93.3/100`" />);
    expect(screen.getByText("Amira Haddad")).toBeInTheDocument();
    expect(screen.getByText("Amira Haddad").tagName).toBe("STRONG");
    expect(screen.getByText("93.3/100").tagName).toBe("CODE");
  });

  it("renders bullet and numbered lists", () => {
    render(
      <MarkdownLite
        text={"- first item\n- second item\n\n1. step one\n2. step two"}
      />,
    );
    expect(screen.getByText("first item").closest("ul")).toBeTruthy();
    expect(screen.getByText("step one").closest("ol")).toBeTruthy();
  });

  it("never renders raw HTML from model output (XSS-safe by construction)", () => {
    const hostile = 'Hello <img src=x onerror="alert(1)"> <script>alert(2)</script>';
    render(<MarkdownLite text={hostile} />);
    expect(document.querySelector("script")).toBeNull();
    expect(document.querySelector("img")).toBeNull();
    // The text is shown literally, as data.
    expect(screen.getByText(/onerror/)).toBeInTheDocument();
  });

  it("renders headings and plain paragraphs", () => {
    render(<MarkdownLite text={"## Match summary\n\nAmira is a strong fit."} />);
    expect(screen.getByText("Match summary")).toBeInTheDocument();
    expect(screen.getByText("Amira is a strong fit.").tagName).toBe("P");
  });
});
