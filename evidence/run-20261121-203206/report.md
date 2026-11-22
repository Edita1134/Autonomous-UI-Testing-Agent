# QA Report: Feature: Add item to cart and complete checkout

**Overall result: PASS**  
Target: https://www.saucedemo.com  
Model: `gemini-3.5-flash-lite`  Duration: 209s

| AC | Result | Reason |
|----|--------|--------|
| AC1: Logging in with username `standard_user` and password `secret_sauce` shows the Products page. | PASS | Expected the Products page to be displayed after logging in with standard_user and secret_sauce, and the final snapshot confirms successful navigation to the inventory page showing the Products header. |
| AC2: Clicking "Add to cart" on the "Sauce Labs Backpack" changes its button to "Remove" and shows a cart badge of 1. | PASS | The Sauce Labs Backpack button successfully changed to 'Remove' and the shopping cart badge shows 1 item. |
| AC3: Opening the cart lists the "Sauce Labs Backpack". | PASS | The cart page is successfully opened and lists the Sauce Labs Backpack as expected. |
| AC4: Checking out with first name "Ada", last name "Lovelace" and zip "12345" ends on a page saying "Thank you for your order!". | PASS | The user checked out with first name 'Ada', last name 'Lovelace', and zip '12345', and the final page successfully displays the message 'Thank you for your order!'. |

## AC1: PASS
*Logging in with username `standard_user` and password `secret_sauce` shows the Products page.*

- **Reason:** Expected the Products page to be displayed after logging in with standard_user and secret_sauce, and the final snapshot confirms successful navigation to the inventory page showing the Products header.
- **Evidence quoted from page:** `Products`
- **Final screenshot:** [screenshots/004_AC1_final.png](screenshots/004_AC1_final.png)
- **Steps:**
  - [done] Type standard_user into the Username field. - Typed standard_user into the Username field successfully.
  - [done] Type secret_sauce into the Password field. - Typed secret_sauce into the Password field successfully.
  - [done] Click the Login button. - Clicked the Login button, and the page successfully navigated to the inventory page (Swag Labs).
  - [done] Look at the Products page. - Currently on the Products page showing Swag Labs inventory items.

## AC2: PASS
*Clicking "Add to cart" on the "Sauce Labs Backpack" changes its button to "Remove" and shows a cart badge of 1.*

- **Reason:** The Sauce Labs Backpack button successfully changed to 'Remove' and the shopping cart badge shows 1 item.
- **Evidence quoted from page:** `button "Remove"`
- **Final screenshot:** [screenshots/006_AC2_final.png](screenshots/006_AC2_final.png)
- **Steps:**
  - [done] Click the Add to cart button for the Sauce Labs Backpack. - Clicked the Add to cart button for the Sauce Labs Backpack, and the cart now shows 1 item with the button changed to Remove.
  - [done] Look at the Sauce Labs Backpack button showing Remove. - The Sauce Labs Backpack button showing Remove is visible on the page.
  - [done] Look at the shopping cart badge showing 1. - The shopping cart badge showing 1 is visible on the page.

## AC3: PASS
*Opening the cart lists the "Sauce Labs Backpack".*

- **Reason:** The cart page is successfully opened and lists the Sauce Labs Backpack as expected.
- **Evidence quoted from page:** `Sauce Labs Backpack`
- **Final screenshot:** [screenshots/008_AC3_final.png](screenshots/008_AC3_final.png)
- **Steps:**
  - [done] Click the shopping cart icon. - Clicked the shopping cart icon and successfully navigated to the cart page (cart.html).
  - [done] Look at the cart page listing the Sauce Labs Backpack. - The cart page is displayed, listing the Sauce Labs Backpack under Your Cart.

## AC4: PASS
*Checking out with first name "Ada", last name "Lovelace" and zip "12345" ends on a page saying "Thank you for your order!".*

- **Reason:** The user checked out with first name 'Ada', last name 'Lovelace', and zip '12345', and the final page successfully displays the message 'Thank you for your order!'.
- **Evidence quoted from page:** `Thank you for your order!`
- **Final screenshot:** [screenshots/015_AC4_final.png](screenshots/015_AC4_final.png)
- **Steps:**
  - [done] Click the Checkout button. - Clicked the Checkout button, and the page successfully navigated to the checkout information form (checkout-step-one.html).
  - [done] Type Ada into the First Name field. - Typed Ada into the First Name field successfully.
  - [done] Type Lovelace into the Last Name field. - Typed Lovelace into the Last Name field successfully.
  - [done] Type 12345 into the Zip/Postal Code field. - Successfully typed 12345 into the Zip/Postal Code field.
  - [done] Click the Continue button. - Clicked the Continue button and successfully navigated to the checkout overview page.
  - [done] Click the Finish button. - The Finish button was clicked and the order complete page is displayed with the success message.
  - [done] Look at the page saying Thank you for your order!. - The page successfully shows the heading 'Thank you for your order!' and the checkout complete message.

## Video
- [video/page@701dd46566d1636f7aabb92e1482b90e.webm](video/page@701dd46566d1636f7aabb92e1482b90e.webm)
