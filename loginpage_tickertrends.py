from __future__ import annotations
from playwright.sync_api import Page, Locator, expect


class LoginPage:
    """Page Object for the Login modal/page."""

    def __init__(self, page: Page) -> None:
        self.page = page

        # Locators
        self.continue_with_email_btn: Locator = page.get_by_role("button", name="Continue with Email")
        self.login_modal: Locator = page.locator("div:has(button:has-text('Reset Password'))").first
        self.email_input: Locator = self.login_modal.locator("input[type='email']")
        self.password_input: Locator = self.login_modal.locator("input[type='password']")
        self.login_button: Locator = self.login_modal.get_by_role("button", name="Log In")


    def open_email_login(self) -> None:
        """Clicks 'Continue with Email' and waits for login modal to appear."""
        self.continue_with_email_btn.click()
        expect(self.login_modal).to_be_visible(timeout=10_000)

    def fill_username(self, username: str) -> None:
        """Fills the email/username field inside the modal."""
        self.email_input.fill(username)

    def fill_password(self, password: str) -> None:
        """Fills the password field inside the modal."""
        self.password_input.fill(password)

    def submit_login(self) -> None:
        """Clicks the 'Log In' button inside the modal."""
        self.login_button.click()
