import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import LegalPage from "./Legal";

describe("LegalPage", () => {
  it("renders both the privacy policy and terms of service", () => {
    render(
      <MemoryRouter>
        <LegalPage />
      </MemoryRouter>,
    );

    expect(
      screen.getByRole("heading", { name: "Privacy Policy" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Terms of Service" }),
    ).toBeInTheDocument();
  });
});
