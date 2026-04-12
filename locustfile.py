"""
Load test configuration for Antar FastAPI backend.
Run with: locust -f locustfile.py --host=https://antar-fastapi-production.up.railway.app
"""

from locust import HttpUser, task, between
import random


class AntarUser(HttpUser):
    """Simulates typical user behavior on Antar backend."""

    wait_time = between(1, 3)

    def on_start(self):
        """Initialize test with a valid chart ID."""
        self.chart_id = "de02bb52-d43a-4b09-be25-b45a07bfbf8a"
        self.languages = ["en", "es", "hi", "pt"]

    @task(5)
    def get_dashboard(self):
        """Heavy endpoint: full dashboard with all sections."""
        lang = random.choice(self.languages)
        self.client.get(
            f"/api/v1/dashboard/{self.chart_id}?language={lang}",
            name="/api/v1/dashboard/[chart_id]"
        )

    @task(4)
    def get_daily_week(self):
        """Daily 7-day signal array (includes WOW hints)."""
        lang = random.choice(self.languages)
        tz = random.choice([-5, -3, 0, 5])
        self.client.get(
            f"/api/v1/daily-week/{self.chart_id}?tz_offset={tz}&language={lang}",
            name="/api/v1/daily-week/[chart_id]"
        )

    @task(3)
    def get_practices(self):
        """Practice schedule for the week."""
        lang = random.choice(self.languages)
        self.client.get(
            f"/api/v1/practices/{self.chart_id}/schedule?language={lang}",
            name="/api/v1/practices/[chart_id]/schedule"
        )

    @task(2)
    def get_welcome(self):
        """Welcome signal (one-time generation)."""
        lang = random.choice(self.languages)
        self.client.get(
            f"/api/v1/welcome/{self.chart_id}?language={lang}",
            name="/api/v1/welcome/[chart_id]"
        )

    @task(2)
    def get_astrocartography(self):
        """Astrocartography power lines."""
        self.client.get(
            f"/api/v1/astrocartography/{self.chart_id}",
            name="/api/v1/astrocartography/[chart_id]"
        )

    @task(1)
    def get_practice_streak(self):
        """User's practice streak counter."""
        self.client.get(
            f"/api/v1/practices/{self.chart_id}/streak",
            name="/api/v1/practices/[chart_id]/streak"
        )

    @task(1)
    def get_daily_signal(self):
        """Single daily signal for today."""
        self.client.get(
            f"/api/v1/daily-signal/{self.chart_id}",
            name="/api/v1/daily-signal/[chart_id]"
        )
