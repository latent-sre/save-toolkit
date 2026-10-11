// Runs in the app: Vitest + Testing Library + jsdom. `npx vitest run error-panel`.
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ErrorCard, PanelErrorBoundary, problemCardProps } from "./error-panel";

describe("ErrorCard", () => {
  it("shows the title, the next step, the request id with its log link, and the time with a zone", () => {
    render(
      <ErrorCard
        title="Orders did not load"
        detail="Try again. If it keeps failing, page the order-management on-call with the request ID."
        requestId="req-0f3a"
        status={502}
        at={new Date("2026-10-11T14:05:00Z")}
        timeZone="UTC"
        links={{ logSearchUrlTemplate: "https://splunk.example.internal/search?q={request_id}" }}
      />,
    );
    const card = screen.getByRole("alert");
    expect(card).toHaveTextContent("Orders did not load");
    expect(card).toHaveTextContent("page the order-management on-call");
    expect(screen.getByText("req-0f3a")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Logs" })).toHaveAttribute("href", "https://splunk.example.internal/search?q=req-0f3a");
    expect(card).toHaveTextContent("UTC");
    expect(screen.queryByRole("button", { name: "Try again" })).not.toBeInTheDocument();
  });

  it("offers a retry only when asked, and copies the request id", async () => {
    const user = userEvent.setup();
    const onRetry = vi.fn();
    render(<ErrorCard title="Fills did not load" requestId="req-9" onRetry={onRetry} />);
    await user.click(screen.getByRole("button", { name: "Copy" }));
    expect(await navigator.clipboard.readText()).toBe("req-9");
    expect(screen.getByRole("button", { name: "Copied" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("captures the time once and survives an unknown time zone", () => {
    const { rerender } = render(<ErrorCard title="Fills did not load" timeZone="Mars/Olympus_Mons" />);
    const shown = screen.getByRole("alert").querySelector("time")?.getAttribute("datetime");
    expect(shown).toBeTruthy();
    expect(screen.getByRole("alert")).toHaveTextContent("UTC");
    rerender(<ErrorCard title="Fills did not load" timeZone="Mars/Olympus_Mons" />);
    expect(screen.getByRole("alert").querySelector("time")?.getAttribute("datetime")).toBe(shown);
  });

  it("maps a problem to card props with the title the view chose", () => {
    const props = problemCardProps(
      { type: "about:blank", title: "Bad gateway", status: 502, detail: "Upstream timed out", request_id: "r-1" },
      "Positions did not load",
    );
    expect(props).toMatchObject({ title: "Positions did not load", detail: "Upstream timed out", requestId: "r-1", status: 502 });
  });
});

describe("PanelErrorBoundary", () => {
  // The cause lives outside React, as a failing query or store would; onReset clears it.
  const world = { fail: true };
  function Boom() {
    if (world.fail) throw Object.assign(new Error("render failed"), { request_id: "req-b", status: 500 });
    return <p>Panel content</p>;
  }

  it("renders the card in place with the thrown error's request id, and recovers on retry once the cause is cleared", async () => {
    const user = userEvent.setup();
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    const onError = vi.fn();
    world.fail = true;
    render(
      <PanelErrorBoundary title="Positions did not render" onError={onError} onReset={() => { world.fail = false; }}>
        <Boom />
      </PanelErrorBoundary>,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Positions did not render");
    expect(screen.getByText("req-b")).toBeInTheDocument();
    expect(onError).toHaveBeenCalledOnce();
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(screen.getByText("Panel content")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    spy.mockRestore();
  });

  it("keeps a plain exception's message off the card and gives it to onError", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    const onError = vi.fn();
    function Leak(): never {
      throw new TypeError("Cannot read properties of undefined (reading 'accountNumber')");
    }
    render(
      <PanelErrorBoundary title="Ledger did not render" onError={onError}>
        <Leak />
      </PanelErrorBoundary>,
    );
    const card = screen.getByRole("alert");
    expect(card).toHaveTextContent("Ledger did not render");
    expect(card).toHaveTextContent("Reload this panel");
    expect(card).not.toHaveTextContent("accountNumber");
    expect(onError).toHaveBeenCalledWith(expect.any(TypeError));
    spy.mockRestore();
  });

  it("clears the card when its resetKey changes, as on navigation", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    world.fail = true;
    const { rerender } = render(
      <PanelErrorBoundary title="Route did not render" resetKey="/orders/1">
        <Boom />
      </PanelErrorBoundary>,
    );
    expect(screen.getByRole("alert")).toBeInTheDocument();
    world.fail = false;
    rerender(
      <PanelErrorBoundary title="Route did not render" resetKey="/orders/2">
        <Boom />
      </PanelErrorBoundary>,
    );
    expect(screen.getByText("Panel content")).toBeInTheDocument();
    spy.mockRestore();
  });
});
