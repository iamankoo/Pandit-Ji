import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import AdminHomePage from "../app/page";

describe("AdminHomePage", () => {
  it("renders the foundation placeholder", () => {
    render(<AdminHomePage />);
    expect(screen.getByRole("heading", { name: "Pandit Ji Admin" })).toBeDefined();
  });
});
