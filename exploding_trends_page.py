from playwright.sync_api import Page, Locator, expect
import re
from typing import List, Dict
from typing import Optional

class ExplodingTrendsPage:
    """Page Object for the Exploding Trends page."""

    def __init__(self, page: Page) -> None:
        self.page = page
        self.current_granularity: str = "Monthly"

        # ----- Type selector -----
        self.current_data_type = "Search Trend"

        # ----- View selector (Chart/List) -----
        self.current_view = "Chart View"


        self.category_button: Locator = page.get_by_role(
            "button", name=re.compile(r"(Select sectors|\d+\s+selected)", re.I)
        ).first
        self.apply_filter_btn: Locator = page.get_by_role("button", name="Apply Filter")

        # ----- Trend Cards -----
        self.trend_cards: Locator = page.locator("div.grid div.trend-ultra-compact")

        # ----- Next button -----
        # Last one is more robust
        self.next_button: Locator = page.locator("button:has-text('Next')").last

    # ---------- TYPE MENU ----------
    def choose_data_type(self, label: str, timeout: int = 5_000) -> None:
        """
        Switch Data Type (e.g., 'Search Trend', 'Tiktok', 'Wiki', etc.)
        Using simple visible text selectors.
        """
        if label.lower() == self.current_data_type.lower():
            print(f"Already using data type '{label}' — skipping.")
            return

        # Open dropdown by clicking current type (e.g. "Search Trend")
        self.page.get_by_text(re.compile(rf"^{re.escape(self.current_data_type)}$", re.I)).click()

        # Click the target option
        target = self.page.get_by_text(label, exact=True)
        expect(target, f"Data Type '{label}' not found").to_be_visible(timeout=timeout)
        target.click()

        # Update internal state
        self.current_data_type = label
        print(f"Switched data type → {self.current_data_type}")

    # ---------- VIEW SWITCH ----------
    def choose_view(self, label: str, timeout: int = 5_000) -> None:
        """
        Change the 'View' dropdown by text, e.g. 'List View' or 'Chart View'.
        Uses your pattern: click current text, then click target text.
        """
        if label.lower() == self.current_view.lower():
            return  # already set

        # Click the current view chip (e.g., "Chart View")
        self.page.get_by_text(re.compile(rf"^{re.escape(self.current_view)}$")).click()

        # Click the target item (e.g., "List View")
        target = self.page.get_by_text(re.compile(rf"^{re.escape(label)}$"))
        expect(target, f"View option '{label}' not found").to_be_visible(timeout=timeout)
        target.click()

        # Update local state
        self.current_view = label

    # ---------- TIME GRANULARITY ----------
    def choose_time_granularity(self, label: str, timeout: int = 5_000) -> None:
        """
        Switch to 'Daily', 'Weekly', or 'Monthly' using visible text.
        Avoid redundant clicks by tracking the current granularity.
        """
        if label.lower() == self.current_granularity.lower():
            print(f"Already in '{label}' granularity — skipping change.")
            return

        # Click the current selection (e.g., "Monthly|")
        self.page.get_by_text(re.compile(rf"^{self.current_granularity}\|?$", re.I)).click()

        # Click the new option by visible text
        target = self.page.get_by_text(re.compile(rf"^{re.escape(label)}", re.I))
        expect(target, f"Granularity option '{label}' not found").to_be_visible(timeout=timeout)
        target.click()

        # Update internal state
        self.current_granularity = label
        print(f"Switched to granularity: {self.current_granularity}")

    # ---------- CATEGORY ----------
    def open_category_dropdown(self, timeout: int = 5_000) -> None:
        """Open sectors menu and wait until it's actually open."""
        self.category_button.click()
        expect(self.apply_filter_btn).to_be_visible(timeout=timeout)  # menu is open

    def choose_category(self, label: str, timeout: int = 5_000) -> None:
        """Select one sector by its visible label and apply."""
        self.open_category_dropdown(timeout)
        option = self.page.locator("label").filter(has_text=label).first
        expect(option, f"Label '{label}' not found").to_be_visible(timeout=timeout)
        option.click()
        self.apply_filter_btn.click()
        expect(self.apply_filter_btn).to_be_hidden(timeout=timeout)


    def extract_page_trends(self, timeout: int = 20_000) -> List[Dict[str, str]]:
        """Extract current page trends + top associated ticker and its percent (robust, simple)."""
        expect(self.trend_cards.first, "No trend cards found").to_be_visible(timeout=timeout)
        self.page.wait_for_timeout(100)  # small paint debounce

        cards = self.trend_cards.element_handles()  # snapshot
        results: List[Dict[str, str]] = []
        growth_re = re.compile(r"^\s*([+\-]{1,2})\s*([\d,\.]+(?:e[+\-]?\d+)?)\s*%?\s*$", re.I)
        pct_re = re.compile(r"^\s*([\d\.]+)\s*%?\s*$")

        for c in cards:
            # --- trend name ---
            h3 = c.query_selector("h3")
            name = (h3.inner_text().strip() if h3 else "")

            # --- growth chip (e.g., +4454%) ---
            badge = c.query_selector("div.mb-2 > span")
            raw_growth = (badge.inner_text().strip() if badge else "")
            m = growth_re.match(raw_growth.replace("%", ""))
            if m:
                sign, val = m.groups()
                # There are not any commas but just in case
                val = val.replace(",", "")
            else:
                sign = val = ""

            # --- top ticker + percent (button with two spans) ---
            # Example element:
            # <button ...><span>AAPL</span><span>83%</span></button>
            ticker_btn = c.query_selector("button.flex.w-full.items-center.justify-between")
            ticker_symbol, ticker_percent = "", ""
            if ticker_btn:
                spans = ticker_btn.query_selector_all("span")
                if len(spans) >= 2:
                    ticker_symbol = (spans[0].inner_text() or "").strip()
                    pct_txt = (spans[1].inner_text() or "").strip()
                    pm = pct_re.match(pct_txt)
                    ticker_percent = pm.group(1) if pm else pct_txt  # '83' or fallback

            results.append({
                "name": name,
                "sign": sign,  # '+', '-', '+-'
                "value": val,  # numeric string (supports scientific notation)
                "raw_growth": raw_growth,  # original chip text
                "ticker_symbol": ticker_symbol,  # e.g., 'AAPL'
                "ticker_percent": ticker_percent,  # e.g., '83'
            })

        return results

    def has_next(self) -> bool:
        """True if the 'Next' button exists and is not disabled."""
        return self.next_button.count() > 0 and not self.next_button.is_disabled()

    def go_next_page(self, timeout: int = 10_000) -> bool:
        """Click 'Next' and wait for the URL (pageNo) to change."""
        if not self.has_next():
            return False

        old_url = self.page.url
        self.next_button.click()

        # Wait until URL changes (pageNo increments)
        self.page.wait_for_function(
            "prev => window.location.href !== prev",
            arg=old_url,
            timeout=timeout,
        )
        return True

    def extract_all_trends(self, max_pages: Optional[int] = None) -> List[Dict[str, str]]:
        """Extract all trend cards from all available pages."""
        all_data: List[Dict[str, str]] = []
        page_count = 0

        while True:
            all_data.extend(self.extract_page_trends())
            page_count += 1

            if max_pages and page_count >= max_pages:
                break
            if not self.go_next_page():
                break

        return all_data