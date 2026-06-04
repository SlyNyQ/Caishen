import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { MessageInput } from "@/components/message-input";

describe("MessageInput", () => {
  it("prevents empty submissions", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<MessageInput value="" onChange={vi.fn()} onSubmit={onSubmit} />);

    const button = screen.getByRole("button", { name: "Analyze" });
    expect(button).toBeDisabled();
    await user.click(button);
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("invokes the submit handler for non-empty input", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<MessageInput value="Compare AAPL and MSFT" onChange={vi.fn()} onSubmit={onSubmit} />);

    await user.click(screen.getByRole("button", { name: "Analyze" }));
    expect(onSubmit).toHaveBeenCalledTimes(1);
  });

  it("submits with Enter and preserves Shift+Enter", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<MessageInput value="Explain volatility" onChange={vi.fn()} onSubmit={onSubmit} />);

    const textarea = screen.getByPlaceholderText(/Ask Caishen to analyze a ticker/);
    textarea.focus();
    await user.keyboard("{Shift>}{Enter}{/Shift}");
    expect(onSubmit).not.toHaveBeenCalled();
    await user.keyboard("{Enter}");
    expect(onSubmit).toHaveBeenCalledTimes(1);
  });

  it("disables input controls while loading", () => {
    render(<MessageInput value="Working..." onChange={vi.fn()} onSubmit={vi.fn()} disabled />);

    expect(screen.getByRole("button", { name: "Analyzing..." })).toBeDisabled();
    expect(screen.getByPlaceholderText(/Ask Caishen to analyze a ticker/)).toBeDisabled();
  });
});
