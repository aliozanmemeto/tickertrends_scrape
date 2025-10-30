from playwright.sync_api import Page, Locator, expect


class HomePage:
    """Page Object for the TickerTrends Home page."""

    def __init__(self, page: Page) -> None:
        self.page = page
        # Locator for the 'Exploding Trends' card
        self.exploding_card: Locator = page.locator('div[title="Exploding Trends"]').first

    def wait_for_exploding_card(self, timeout: int = 20_000) -> None:
        """Waits until the Exploding Trends card is visible on the page."""
        self.exploding_card.wait_for(state="visible", timeout=timeout)
        expect(self.exploding_card).to_be_enabled()

    def click_exploding_card(self) -> None:
        """Clicks the Exploding Trends card."""
        self.exploding_card.click()

    def open_exploding_trends(self) -> None:
        """Waits for and opens the Exploding Trends card."""
        self.wait_for_exploding_card()
        self.click_exploding_card()
