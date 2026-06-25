import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";

import { I18nProvider } from "./i18n-provider";
import { useI18n } from "./use-i18n";

function Probe() {
  const { t, tn, setLocale, locale, dir } = useI18n();
  return (
    <div>
      <span data-testid="label">{t("nav.dashboard")}</span>
      <span data-testid="plural">{tn("images", 3)}</span>
      <span data-testid="meta">{`${locale}:${dir}`}</span>
      <button onClick={() => setLocale("ar")}>ar</button>
      <button onClick={() => setLocale("en")}>en</button>
    </div>
  );
}

afterEach(() => {
  document.documentElement.lang = "";
  document.documentElement.dir = "";
});

describe("I18nProvider", () => {
  it("renders English by default and reflects it on <html>", () => {
    render(
      <I18nProvider>
        <Probe />
      </I18nProvider>,
    );
    expect(screen.getByTestId("label")).toHaveTextContent("Dashboard");
    expect(screen.getByTestId("plural")).toHaveTextContent("3 photos");
    expect(screen.getByTestId("meta")).toHaveTextContent("en:ltr");
    expect(document.documentElement.dir).toBe("ltr");
    expect(document.documentElement.lang).toBe("en");
  });

  it("switches to Arabic, flips direction, and persists the choice", async () => {
    const user = userEvent.setup();
    render(
      <I18nProvider>
        <Probe />
      </I18nProvider>,
    );

    await act(() => user.click(screen.getByRole("button", { name: "ar" })));

    expect(screen.getByTestId("label")).toHaveTextContent("الرئيسية");
    expect(screen.getByTestId("plural")).toHaveTextContent("3 صور");
    expect(screen.getByTestId("meta")).toHaveTextContent("ar:rtl");
    expect(document.documentElement.dir).toBe("rtl");
    expect(document.documentElement.lang).toBe("ar");
    expect(window.localStorage.getItem("seedbank.locale")).toBe("ar");
  });
});
