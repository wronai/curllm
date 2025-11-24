#!/usr/bin/env python3
import asyncio
from typing import Dict, Any, Optional, List

class WordPressAutomation:
    """Automatyzacja WordPressa: login, tworzenie postów, upload mediów"""

    def __init__(self, page, run_logger=None):
        self.page = page
        self.run_logger = run_logger

    async def login(self, url: str, username: str, password: str) -> bool:
        """Logowanie do WordPress."""
        try:
            if not url:
                return False
            login_url = f"{url.rstrip('/')}/wp-admin"
            await self.page.goto(login_url)
            try:
                await self.page.wait_for_load_state("networkidle")
            except Exception:
                pass
            # Jeśli już zalogowany
            try:
                cur = self.page.url
                if ("/wp-admin" in cur) and ("wp-login" not in cur):
                    if self.run_logger:
                        self.run_logger.log_text("Already logged in to WordPress")
                    return True
            except Exception:
                pass

            # Wypełnij formularz logowania - kilka selektorów na wszelki wypadek
            async def _fill(sel: str, val: str) -> bool:
                try:
                    await self.page.fill(sel, val)
                    return True
                except Exception:
                    return False

            filled_user = (
                await _fill("#user_login", username)
                or await _fill("#username", username)
                or await _fill("input[name='log']", username)
            )
            filled_pass = (
                await _fill("#user_pass", password)
                or await _fill("#password", password)
                or await _fill("input[name='pwd']", password)
            )
            if not (filled_user and filled_pass):
                if self.run_logger:
                    self.run_logger.log_text("WordPress login form not found")
                return False

            # Zapamiętaj mnie
            try:
                remember = self.page.locator("#rememberme, input[name='rememberme']")
                if await remember.count() > 0:
                    await remember.first.check()
            except Exception:
                pass

            # Klik przycisku logowania
            try:
                await self.page.click("#wp-submit, input[type='submit'][value*='Log']")
            except Exception:
                # Fallback: submit form przez Enter
                try:
                    await self.page.keyboard.press("Enter")
                except Exception:
                    pass

            try:
                await self.page.wait_for_load_state("networkidle")
                await asyncio.sleep(2)
            except Exception:
                pass

            # Weryfikacja zalogowania
            try:
                cur = self.page.url
                if ("/wp-admin" in cur) and ("wp-login" not in cur):
                    if self.run_logger:
                        self.run_logger.log_text(f"Successfully logged in to WordPress as {username}")
                    return True
            except Exception:
                pass

            if self.run_logger:
                self.run_logger.log_text("WordPress login failed")
            return False
        except Exception as e:
            if self.run_logger:
                self.run_logger.log_text(f"WordPress login error: {e}")
            return False

    async def create_post(
        self,
        title: str,
        content: str,
        status: str = "draft",
        categories: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        featured_image_path: Optional[str] = None,
    ) -> Optional[str]:
        """Tworzy nowy post w WordPress."""
        try:
            # Przejdź do nowego posta
            base = self.page.url.split("/wp-admin")[0]
            await self.page.goto(f"{base}/wp-admin/post-new.php")
            try:
                await self.page.wait_for_load_state("networkidle")
            except Exception:
                pass

            is_gutenberg = False
            try:
                is_gutenberg = (await self.page.locator(".block-editor").count()) > 0
            except Exception:
                is_gutenberg = False

            if is_gutenberg:
                return await self._create_gutenberg_post(title, content, status, categories or [], tags or [], featured_image_path)
            else:
                return await self._create_classic_post(title, content, status, categories or [], tags or [], featured_image_path)
        except Exception as e:
            if self.run_logger:
                self.run_logger.log_text(f"Error creating WordPress post: {e}")
            return None

    async def _create_gutenberg_post(
        self, title: str, content: str, status: str,
        categories: List[str], tags: List[str], featured_image_path: Optional[str]
    ) -> Optional[str]:
        # Tytuł
        title_input = self.page.locator(".editor-post-title__input, .wp-block-post-title")
        await title_input.first.click()
        await title_input.first.fill(title)

        # Treść (prosty mapping markdown->bloki)
        await self.page.keyboard.press("Tab")
        for paragraph in content.split("\n\n"):
            if paragraph.strip():
                if paragraph.startswith("#"):
                    level = len(paragraph.split()[0])
                    await self.page.keyboard.type(f"/{level}")
                    await self.page.keyboard.press("Enter")
                    await self.page.keyboard.type(paragraph.lstrip("#").strip())
                else:
                    await self.page.keyboard.type(paragraph)
                await self.page.keyboard.press("Enter")

        # Kategorię/tagi (best-effort)
        if categories:
            try:
                cat = self.page.locator("button:has-text('Categories')")
                if await cat.count() > 0:
                    await cat.click()
                    await asyncio.sleep(1)
                    for category in categories:
                        cb = self.page.locator(f"label:has-text('{category}') input[type='checkbox']")
                        if await cb.count() > 0:
                            await cb.check()
            except Exception:
                pass
        if tags:
            try:
                tag_input = self.page.locator("input[placeholder*='Add new tag']")
                if await tag_input.count() > 0:
                    for tag in tags:
                        await tag_input.fill(tag)
                        await self.page.keyboard.press("Enter")
                        await asyncio.sleep(0.2)
            except Exception:
                pass

        # Publikuj / Zapisz
        if status == "publish":
            try:
                await self.page.click("button:has-text('Publish'):visible")
                await asyncio.sleep(1)
                confirm_button = self.page.locator("button:has-text('Publish'):visible").last
                if await confirm_button.count() > 0:
                    await confirm_button.click()
            except Exception:
                pass
        else:
            try:
                await self.page.click("button:has-text('Save draft'):visible")
            except Exception:
                pass

        try:
            await self.page.wait_for_load_state("networkidle")
        except Exception:
            pass

        # URL posta
        post_url = None
        try:
            view_button = self.page.locator("a:has-text('View Post'), a:has-text('Preview')")
            if await view_button.count() > 0:
                post_url = await view_button.first.get_attribute("href")
        except Exception:
            pass
        if self.run_logger:
            self.run_logger.log_text(f"WordPress post created: {title} (status: {status})")
            if post_url:
                self.run_logger.log_text(f"Post URL: {post_url}")
        return post_url

    async def _create_classic_post(
        self, title: str, content: str, status: str,
        categories: List[str], tags: List[str], featured_image_path: Optional[str]
    ) -> Optional[str]:
        try:
            await self.page.fill("#title", title)
        except Exception:
            pass
        try:
            text_tab = self.page.locator("#content-text, #content-html")
            if await text_tab.count() > 0:
                await text_tab.click()
        except Exception:
            pass
        try:
            content_area = self.page.locator("#content")
            await content_area.fill(content)
        except Exception:
            pass
        if categories:
            for category in categories:
                try:
                    cb = self.page.locator(f"#categorychecklist label:has-text('{category}') input")
                    if await cb.count() > 0:
                        await cb.check()
                except Exception:
                    pass
        if tags:
            try:
                tag_input = self.page.locator("#new-tag-post_tag")
                if await tag_input.count() > 0:
                    await tag_input.fill(", ".join(tags))
                    await self.page.click(".tagadd")
            except Exception:
                pass
        if status == "publish":
            try:
                await self.page.click("#publish")
            except Exception:
                pass
        else:
            try:
                await self.page.click("#save-post")
            except Exception:
                pass
        try:
            await self.page.wait_for_load_state("networkidle")
        except Exception:
            pass
        post_url = None
        try:
            view_link = self.page.locator("#sample-permalink a, #view-post-btn a")
            if await view_link.count() > 0:
                post_url = await view_link.first.get_attribute("href")
        except Exception:
            pass
        return post_url

    async def upload_media(self, file_path: str) -> Optional[str]:
        try:
            base = self.page.url.split("/wp-admin")[0]
            await self.page.goto(f"{base}/wp-admin/media-new.php")
            file_input = self.page.locator("input[type='file']")
            await file_input.set_input_files(file_path)
            try:
                await self.page.wait_for_selector(".media-item .pinkynail", timeout=30000)
            except Exception:
                pass
            try:
                url_input = self.page.locator(".url").first
                if await url_input.count() > 0:
                    return await url_input.get_attribute("value")
            except Exception:
                pass
            return None
        except Exception as e:
            if self.run_logger:
                self.run_logger.log_text(f"Media upload error: {e}")
            return None
