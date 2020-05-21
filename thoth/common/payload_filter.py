#!/usr/bin/env python3
# thoth-common
# Copyright(C) 2020 Sai Sankar Gochhayat
#
# This program is free software: you can redistribute it and / or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

"""
Payload Filter.

Payload filter handles installation and remove events for a Kebechet workflow.
And also filters the webhooks that Kebechet doesn't support to prevent unnecessary workflows.
"""

import logging
from thoth.storages import GraphDatabase
from typing import Dict
from typing import List

_LOGGER = logging.getLogger(__name__)

_SUPPORTED_ACTIONS = ["opened", "edited"]
_EVENT_TYPES = ["issues", "pull_request", "installation"]


class PayloadProcess:
    """Helper methods that handle incoming payloads."""

    def __init__(self):
        """Init Method."""
        pass

    def process(self, webhook_payload: dict) -> dict:
        """
        Initialize the payload and check if we need to process it.

        If we cannot process the payload we return it back to the workflow.
        """
        # We only check github webhook payloads.
        if webhook_payload.get("service") == "github":
            event, payload = (
                webhook_payload.get("event"),
                webhook_payload.get("payload"),
            )
            if event == "integration_installation_repositories":
                if payload.get("action") == "added":
                    self._install_event(payload.get("repositories_added"))
                    return None
                elif payload.get("action") == "removed":
                    self._remove_event(payload.get("repositories_removed"))
                    return None
            if event in _EVENT_TYPES:
                # We ignore issues, PR actions like reopened, closed.
                action = payload.get("action")
                # This is needed for advanced usage like change of application permission.
                if event == "installation":
                    _LOGGER.info(
                        f"For event type - {event}, we don't support action - {action}"
                    )
                    return None
                if action not in _SUPPORTED_ACTIONS:
                    _LOGGER.info(
                        f"For event type - {event}, we don't support action - {action}"
                    )
                    return None
        return webhook_payload

    def _install_event(self, install_repos: List[dict]) -> None:
        """Handle Github App install webhooks."""
        graph = GraphDatabase()
        graph.connect()
        repos_not_installed = []
        for repo in install_repos:
            try:
                status = graph.create_github_app_installation(slug=repo.get("full_name"), repo_name=repo.get(
                    "name"), private=repo.get("private"), installation_id=repo.get("id"))
                if not status:
                    repos_not_installed.add(repo)
            except Exception as exc:
                _LOGGER.error(f"The repo couldn't be added to the database. Repo details - {repo}")
        if len(repos_not_installed):
            _LOGGER.error(
                f"Installed repo's were not added to the database. The complete list - {repos_not_installed}")
        else:
            _LOGGER.info(
                f"Installed repositories have been sucessfully added. Count - {len(install_repos)}")

    def _remove_event(self, uninstall_repos: List[dict]) -> None:
        """Handle Github App remove webhooks."""
        graph = GraphDatabase()
        graph.connect()
        for repo in uninstall_repos:
            status = graph.update_kebechet_github_installations_on_is_active(
                slug=repo.get("full_name"))
            if not status:
                _LOGGER.error(f"Failed to deactivate repo - {repo}")
