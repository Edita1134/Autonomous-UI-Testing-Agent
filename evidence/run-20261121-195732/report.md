# QA Report: Bug check: cart badge count (deliberately wrong AC)

**Overall result: FAIL**  
Target: https://www.saucedemo.com  
Model: `gemini-3.5-flash-lite`  Duration: 107s

| AC | Result | Reason |
|----|--------|--------|
| AC1: Logging in with username `standard_user` and password `secret_sauce` shows the Products page. | PASS | The user successfully logged in with standard_user and secret_sauce, and the final page displays the Products inventory list at /inventory.html. |
| AC2: After clicking "Add to cart" once on the "Sauce Labs Backpack", the cart badge shows 2. | FAIL | Expected the cart badge to show 2 after adding the Sauce Labs Backpack to the cart once, but the cart badge displays 1. |

## AC1: PASS
*Logging in with username `standard_user` and password `secret_sauce` shows the Products page.*

- **Reason:** The user successfully logged in with standard_user and secret_sauce, and the final page displays the Products inventory list at /inventory.html.
- **Evidence quoted from page:** `Products Name (A to Z)`
- **Final screenshot:** [screenshots/004_AC1_final.png](screenshots/004_AC1_final.png)
- **Steps:**
  - [done] Type standard_user into the Username field. - Typed standard_user into the Username field successfully.
  - [done] Type secret_sauce into the Password field. - Successfully typed secret_sauce into the Password field.
  - [done] Click the Login button. - The Login button was clicked and the user is now on the inventory page (Swag Labs products).
  - [done] Look at the Products page. - The Products page is displayed with a list of items.

## AC2: FAIL
*After clicking "Add to cart" once on the "Sauce Labs Backpack", the cart badge shows 2.*

- **Reason:** Expected the cart badge to show 2 after adding the Sauce Labs Backpack to the cart once, but the cart badge displays 1.
- **Evidence quoted from page:** `button "Cart, 1 items": "1"`
- **Final screenshot:** [screenshots/006_AC2_final.png](screenshots/006_AC2_final.png)
- **Steps:**
  - [done] Click the Add to cart button for the Sauce Labs Backpack. - The Sauce Labs Backpack Add to cart button was clicked, and the page now shows the Remove button and cart count 1.
  - [done] Look at the shopping cart badge. - I observed the shopping cart badge showing 1 item: button "Cart, 1 items": "1".

## Video
- [video/page@cf25e192df607e0e03353100d8c8236e.webm](video/page@cf25e192df607e0e03353100d8c8236e.webm)
