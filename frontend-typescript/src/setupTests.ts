import "@testing-library/jest-dom";

if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => {};
}