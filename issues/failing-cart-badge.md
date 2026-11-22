# Bug check: cart badge count (deliberately wrong AC)

This ticket contains an intentionally incorrect expectation, to demonstrate that the agent reports a FAIL
with an actionable reason rather than forcing a pass.

Target URL: https://www.saucedemo.com

## Acceptance Criteria

- AC1: Logging in with username `standard_user` and password `secret_sauce` shows the Products page.
- AC2: After clicking "Add to cart" once on the "Sauce Labs Backpack", the cart badge shows 2.
