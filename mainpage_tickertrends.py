from playwright.sync_api import Page, Locator, expect

class MainPage:
    """Page object for shared UI on ticketrends pages."""
    def __init__(self, page: Page) -> None:
        self.page = page

        # Overlay (tailwind-styled modal)
        self.overlay: Locator = page.locator(
            "div.fixed:has(h3:has-text('Subscribe to TickerTrends Newsletter'))"
        ).first
        self.modal: Locator = self.overlay.locator("div.relative.mx-auto").first
        self.close_x: Locator = self.modal.locator("button.absolute.top-1.right-1").first

        # Top-right login button
        self.login_btn: Locator = page.get_by_role("button", name="Log In")

    def close_subscription_popup_if_present(self) -> None:
        """
        Closes the newsletter subscription popup if it is present/visible.
        Retries with force if needed, and never fails the test if missing.
        """
        try:
            # Fast existence check; returns 0 if overlay not in DOM
            if self.overlay.count() == 0:
                return

            # If it exists, try to close it gracefully
            if self.close_x.is_visible():
                self.close_x.click(timeout=1000)

            # If overlay still visible, try a forced click as fallback
            if self.overlay.is_visible():
                self.close_x.click(timeout=800, force=True)

            # Optional: wait until it’s gone (prevents flake)
            expect(self.overlay).to_be_hidden(timeout=1500)

            # For debug logs
            print("Subscription popup closed.")
        except Exception:
            # Swallow—popup should never fail the test flow
            pass

    def click_login(self) -> None:
        """Clicks the 'Log In' button."""
        self.login_btn.click()

    # Convenience flow
    def prepare_and_open_login(self) -> None:
        """Closes popup (if any) and then opens login."""
        self.close_subscription_popup_if_present()
        self.click_login()
