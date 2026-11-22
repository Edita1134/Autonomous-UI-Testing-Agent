# Test Scenarios

Source: mock GitHub issue [issues/checkout-flow.md](issues/checkout-flow.md), moved to "Ready for QA" by adding the
`RFQA` label. Target application: https://www.saucedemo.com (public demo shop).

## Acceptance Criteria (from the issue)

| ID | Acceptance Criterion |
|----|----------------------|
| AC1 | Logging in with username `standard_user` and password `secret_sauce` shows the Products page. |
| AC2 | Clicking "Add to cart" on the "Sauce Labs Backpack" changes its button to "Remove" and shows a cart badge of 1. |
| AC3 | Opening the cart lists the "Sauce Labs Backpack". |
| AC4 | Checking out with first name "Ada", last name "Lovelace" and zip "12345" ends on a page saying "Thank you for your order!". |

## Functional scenarios

The agent generates the exact steps itself at run time (the plan is logged in `agent.log` as `PLAN ACn: ...`).
Intended coverage:

| Scenario | AC | Expected agent behaviour | Expected verdict |
|----------|----|--------------------------|------------------|
| Valid login | AC1 | Fill username and password, click Login, see the Products page | PASS |
| Add to cart | AC2 | Pick the Backpack's button among 6 identical "Add to cart" buttons (needs disambiguation), see "Remove" and badge 1 | PASS |
| Cart contents | AC3 | Open the cart, see the Backpack listed | PASS |
| Checkout | AC4 | Checkout, fill the 3-field form, continue, finish, see the confirmation | PASS |

## Negative scenario (demonstrates failure reporting)

[issues/failing-cart-badge.md](issues/failing-cart-badge.md) states a deliberately wrong expectation
("cart badge shows 2" after one add). The agent should log in, add the item, observe a badge of 1 and report
**FAIL** with a reason like "expected 2, observed 1", quoting the page.

## Why these scenarios exercise autonomy

- Six identical "Add to cart" buttons force element disambiguation without selectors.
- Multi-page flow means later criteria depend on earlier state (session carries over between criteria).
- A wrong AC proves the agent will not rubber-stamp a pass.
