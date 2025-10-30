from playwright.sync_api import Page, Locator, expect
import re
from typing import List, Dict
from typing import Optional

class ExplodingTrendsPage:
    """Page Object for the Exploding Trends page."""

    def __init__(self, page: Page) -> None:
        self.page = page

        # ----- Type selector -----
        self.type_section: Locator = page.locator("#type-selection")
        self.type_trigger: Locator = self.type_section.locator(".relative").first
        self.menu_items: Locator = self.type_section.locator("ul li div")

        # ----- View selector (Chart/List) -----
        self.view_switcher: Locator = page.locator(
            "div.relative.h-9.w-fit.cursor-pointer:has(p:has-text('View'))"
        ).first

        # ----- Time granularity selector (Monthly/Weekly/Daily) -----
        self.time_container: Locator = page.locator(
            "div.relative.h-9.w-fit.cursor-pointer:has(p:has-text('Monthly')), "
            "div.relative.h-9.w-fit.cursor-pointer:has(p:has-text('Weekly')), "
            "div.relative.h-9.w-fit.cursor-pointer:has(p:has-text('Daily'))"
        ).first
        self.time_label: Locator = self.time_container.locator("p.whitespace-nowrap")

        # ----- Category dropdown (sector selection) -----
        self.category_button: Locator = page.locator(
            "button:has-text('Select sectors'), button:has-text('selected')"
        ).first
        self.category_panel: Locator = page.locator("div.max-h-60.space-y-2")
        self.category_labels: Locator = self.category_panel.locator("label span.text-sm")

        # ----- Trend Cards -----
        self.trend_cards: Locator = page.locator("div.grid div.trend-ultra-compact")

        # ----- Next button -----
        # Last one is more robust
        self.next_button: Locator = page.locator("button:has-text('Next')").last

    # ---------- TYPE MENU ----------
    def open_type_menu(self, timeout: int = 50_000) -> None:
        """Opens the type dropdown and waits for options."""
        self.type_trigger.wait_for(state="visible", timeout=timeout)
        self.type_trigger.click()
        self.menu_items.first.wait_for(state="visible", timeout=timeout)

    def select_source(self, label: str, timeout: int = 10_000) -> None:
        """Selects a source like 'Tiktok' or 'Search Trend'."""
        self.open_type_menu(timeout)
        option = self.menu_items.filter(has_text=label).first
        expect(option, f"Option '{label}' not found in type menu").to_be_visible(timeout=timeout)
        option.click()

    # ---------- VIEW SWITCH ----------
    def choose_list_view(self, timeout: int = 5_000) -> None:
        """Switch to 'List View'."""
        self.view_switcher.wait_for(state="visible", timeout=timeout)
        self.view_switcher.click()
        option = self.page.get_by_text("List View", exact=True).first
        expect(option, "Couldn't find 'List View'").to_be_visible(timeout=timeout)
        option.click()

    # ---------- TIME GRANULARITY ----------
    def choose_time_granularity(self, label: str, timeout: int = 5_000) -> None:
        """Switch to 'Daily', 'Weekly', or 'Monthly'."""
        self.time_container.click()
        options = self.page.locator("div.absolute ul li div")
        option = options.filter(has_text=re.compile(rf"^{re.escape(label)}", re.I)).first
        expect(option, f"Option '{label}' not found").to_be_visible(timeout=timeout)
        option.click()
        expect(self.time_label).to_have_text(re.compile(rf"^{re.escape(label)}", re.I), timeout=timeout)

    # ---------- CATEGORY ----------
    def open_category_dropdown(self, timeout: int = 5_000) -> None:
        """Opens the category dropdown."""
        self.category_button.wait_for(state="visible", timeout=timeout)
        self.category_button.click()
        self.category_panel.first.wait_for(state="visible", timeout=timeout)

    def choose_category(self, label: str, timeout: int = 15_000) -> None:
        """Selects one category by visible label."""
        self.open_category_dropdown(timeout)
        option = self.category_labels.filter(has_text=label).first
        expect(option, f"Category '{label}' not found").to_be_visible(timeout=timeout)
        option.click()
        self.category_button.click()  # close dropdown

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