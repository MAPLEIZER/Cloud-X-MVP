#!/usr/bin/env python3
"""Synchronize Cloud-X issue/PR labels into repository-linked GitHub Projects.

Labels remain the durable, repository-local source of truth. This script discovers
Projects V2 linked to the repository, ensures the issue/PR is present, and maps
label dimensions into compatible Project fields. No project, field, option, or
item IDs are committed to the repository.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

GRAPHQL_URL = "https://api.github.com/graphql"
REST_ROOT = "https://api.github.com"
API_VERSION = "2022-11-28"


class ProjectSyncError(RuntimeError):
    pass


@dataclass(frozen=True)
class Entity:
    node_id: str
    number: int
    title: str
    state: str
    labels: tuple[str, ...]
    kind: str


def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def titleize(slug: str) -> str:
    if re.fullmatch(r"p\d+", slug, re.IGNORECASE):
        return slug.upper()
    words = [part for part in re.split(r"[-_/]+", slug) if part]
    return " ".join(word.upper() if word.lower() in {"ci", "api", "rbac", "dfir"} else word.title() for word in words)


def load_config(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("version") != 1:
        raise ProjectSyncError("Unsupported project-sync configuration version")
    dimensions = data.get("dimensions")
    if not isinstance(dimensions, dict) or not dimensions:
        raise ProjectSyncError("project-sync configuration requires dimensions")
    for name, mapping in dimensions.items():
        if not isinstance(mapping, dict):
            raise ProjectSyncError(f"Invalid mapping for dimension {name}")
        if not mapping.get("label_prefix") or not mapping.get("field_names"):
            raise ProjectSyncError(f"Dimension {name} requires label_prefix and field_names")
        if mapping.get("cardinality") not in {"one", "many"}:
            raise ProjectSyncError(f"Dimension {name} has invalid cardinality")
    return data


def extract_dimensions(labels: Iterable[str], state: str, config: dict[str, Any]) -> dict[str, list[str]]:
    labels = list(labels)
    result: dict[str, list[str]] = {}
    for name, mapping in config["dimensions"].items():
        prefix = mapping["label_prefix"]
        values = [label[len(prefix) :] for label in labels if label.startswith(prefix) and label[len(prefix) :]]
        # Preserve label order while removing accidental duplicates.
        values = list(dict.fromkeys(values))
        if mapping["cardinality"] == "one" and len(values) > 1:
            raise ProjectSyncError(
                f"Conflicting {name} labels: " + ", ".join(f"{prefix}{value}" for value in values)
            )
        result[name] = values

    override = config.get("state_overrides", {}).get(state, {})
    for name, values in override.items():
        if name in result and isinstance(values, list):
            result[name] = list(values)
    return result


def option_candidates(dimension: str, value: str, config: dict[str, Any]) -> list[str]:
    mapping = config["dimensions"][dimension]
    aliases = mapping.get("aliases", {}).get(value, [])
    candidates = [*aliases, titleize(value), value]
    return list(dict.fromkeys(candidate for candidate in candidates if candidate))


def find_field(project: dict[str, Any], field_names: Iterable[str]) -> dict[str, Any] | None:
    fields = [field for field in project.get("fields", {}).get("nodes", []) if isinstance(field, dict)]
    normalized = {normalize(field.get("name", "")): field for field in fields if field.get("name")}
    for name in field_names:
        field = normalized.get(normalize(name))
        if field:
            return field
    return None


def _field_options(field: dict[str, Any]) -> list[dict[str, Any]]:
    if field.get("__typename") == "ProjectV2SingleSelectField":
        return field.get("options", []) or []
    if field.get("__typename") == "ProjectV2MultiSelectField":
        return field.get("multiSelectOptions", []) or []
    return []


def find_option(field: dict[str, Any], candidates: Iterable[str]) -> dict[str, Any] | None:
    options = _field_options(field)
    by_name = {normalize(option.get("name", "")): option for option in options if option.get("name")}
    for candidate in candidates:
        option = by_name.get(normalize(candidate))
        if option:
            return option
    return None


def desired_field_value(
    field: dict[str, Any],
    dimension: str,
    values: list[str],
    config: dict[str, Any],
) -> tuple[dict[str, Any] | None, list[str]]:
    """Return GraphQL ProjectV2FieldValue plus any unmatched option values."""

    typename = field.get("__typename")
    if not values:
        return None, []

    if typename == "ProjectV2SingleSelectField":
        option = find_option(field, option_candidates(dimension, values[0], config))
        if not option:
            return None, list(values)
        return {"singleSelectOptionId": option["id"]}, []

    if typename == "ProjectV2MultiSelectField":
        option_ids: list[str] = []
        unmatched: list[str] = []
        for value in values:
            option = find_option(field, option_candidates(dimension, value, config))
            if option:
                option_ids.append(option["id"])
            else:
                unmatched.append(value)
        if not option_ids:
            return None, unmatched
        return {"multiSelectOptionIds": option_ids}, unmatched

    if typename == "ProjectV2Field" and field.get("dataType") == "TEXT":
        rendered = [option_candidates(dimension, value, config)[0] for value in values]
        return {"text": ", ".join(rendered)}, []

    return None, list(values)


class GitHubClient:
    def __init__(self, token: str):
        if not token:
            raise ProjectSyncError("PROJECTS_TOKEN is required")
        self.token = token

    def _request(self, url: str, *, body: dict[str, Any] | None = None) -> tuple[Any, dict[str, str]]:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(
            url,
            data=data,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": API_VERSION,
                "Content-Type": "application/json",
                "User-Agent": "cloudx-project-sync/1",
            },
            method="POST" if body is not None else "GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
                return payload, dict(response.headers.items())
        except urllib.error.HTTPError as exc:
            message = exc.read().decode("utf-8", errors="replace")
            raise ProjectSyncError(f"GitHub API returned HTTP {exc.code}: {message[:500]}") from exc
        except urllib.error.URLError as exc:
            raise ProjectSyncError(f"GitHub API request failed: {exc.reason}") from exc

    def graphql(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        payload, _ = self._request(GRAPHQL_URL, body={"query": query, "variables": variables})
        errors = payload.get("errors")
        if errors:
            rendered = "; ".join(error.get("message", "GraphQL error") for error in errors)
            raise ProjectSyncError(rendered)
        return payload.get("data") or {}

    def list_issues_and_prs(self, repository: str, state: str) -> list[Entity]:
        entities: list[Entity] = []
        page = 1
        while True:
            url = f"{REST_ROOT}/repos/{repository}/issues?state={state}&per_page=100&page={page}"
            payload, _ = self._request(url)
            if not isinstance(payload, list):
                raise ProjectSyncError("Unexpected response while listing repository issues")
            for item in payload:
                entities.append(
                    Entity(
                        node_id=item["node_id"],
                        number=int(item["number"]),
                        title=item.get("title", ""),
                        state=item.get("state", "open"),
                        labels=tuple(
                            label["name"] if isinstance(label, dict) else str(label)
                            for label in item.get("labels", [])
                        ),
                        kind="pull_request" if item.get("pull_request") else "issue",
                    )
                )
            if len(payload) < 100:
                break
            page += 1
        return entities


DISCOVER_QUERY = r"""
query($owner: String!, $repo: String!, $content: ID!) {
  repository(owner: $owner, name: $repo) {
    projectsV2(first: 50, minPermissionLevel: WRITE) {
      nodes {
        id
        number
        title
        closed
        fields(first: 100) {
          nodes {
            __typename
            ... on ProjectV2Field {
              id
              name
              dataType
            }
            ... on ProjectV2SingleSelectField {
              id
              name
              dataType
              options { id name }
            }
            ... on ProjectV2MultiSelectField {
              id
              name
              dataType
              multiSelectOptions { id name }
            }
          }
        }
      }
      pageInfo { hasNextPage }
    }
  }
  node(id: $content) {
    __typename
    ... on Issue {
      projectItems(first: 50, includeArchived: false) {
        nodes { id project { id } }
        pageInfo { hasNextPage }
      }
    }
    ... on PullRequest {
      projectItems(first: 50, includeArchived: false) {
        nodes { id project { id } }
        pageInfo { hasNextPage }
      }
    }
  }
}
"""

ADD_ITEM_MUTATION = r"""
mutation($project: ID!, $content: ID!) {
  addProjectV2ItemById(input: {projectId: $project, contentId: $content}) {
    item { id }
  }
}
"""

UPDATE_FIELD_MUTATION = r"""
mutation($project: ID!, $item: ID!, $field: ID!, $value: ProjectV2FieldValue!) {
  updateProjectV2ItemFieldValue(
    input: {projectId: $project, itemId: $item, fieldId: $field, value: $value}
  ) {
    projectV2Item { id }
  }
}
"""

CLEAR_FIELD_MUTATION = r"""
mutation($project: ID!, $item: ID!, $field: ID!) {
  clearProjectV2ItemFieldValue(
    input: {projectId: $project, itemId: $item, fieldId: $field}
  ) {
    projectV2Item { id }
  }
}
"""


def entity_from_event(path: str | Path) -> Entity:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    content = payload.get("issue")
    kind = "issue"
    if not content:
        content = payload.get("pull_request")
        kind = "pull_request"
    if not isinstance(content, dict):
        raise ProjectSyncError("Event does not contain an issue or pull request")
    return Entity(
        node_id=content["node_id"],
        number=int(content["number"]),
        title=content.get("title", ""),
        state=content.get("state", "open"),
        labels=tuple(
            label["name"] if isinstance(label, dict) else str(label)
            for label in content.get("labels", [])
        ),
        kind=kind,
    )


def sync_entity(
    client: GitHubClient,
    repository: str,
    entity: Entity,
    config: dict[str, Any],
) -> list[str]:
    owner, repo = repository.split("/", 1)
    dimensions = extract_dimensions(entity.labels, entity.state, config)
    data = client.graphql(
        DISCOVER_QUERY,
        {"owner": owner, "repo": repo, "content": entity.node_id},
    )

    repository_data = data.get("repository") or {}
    projects_connection = repository_data.get("projectsV2") or {}
    if projects_connection.get("pageInfo", {}).get("hasNextPage"):
        raise ProjectSyncError("More than 50 writable linked Projects found; pagination support is required")

    content = data.get("node") or {}
    project_items = content.get("projectItems") or {}
    if project_items.get("pageInfo", {}).get("hasNextPage"):
        raise ProjectSyncError("Issue/PR belongs to more than 50 Projects; pagination support is required")
    existing = {
        item["project"]["id"]: item["id"]
        for item in project_items.get("nodes", [])
        if isinstance(item, dict) and item.get("project")
    }

    summaries: list[str] = []
    projects = [
        project
        for project in projects_connection.get("nodes", [])
        if isinstance(project, dict) and not project.get("closed")
    ]
    if not projects:
        return [f"#{entity.number}: no writable repository-linked Projects found"]

    for project in projects:
        project_id = project["id"]
        item_id = existing.get(project_id)
        if not item_id:
            result = client.graphql(
                ADD_ITEM_MUTATION,
                {"project": project_id, "content": entity.node_id},
            )
            item_id = result["addProjectV2ItemById"]["item"]["id"]
            summaries.append(f"#{entity.number}: added to {project['title']}")

        for dimension, mapping in config["dimensions"].items():
            field = find_field(project, mapping["field_names"])
            if not field:
                summaries.append(
                    f"#{entity.number}: {project['title']} has no field matching "
                    + "/".join(mapping["field_names"])
                )
                continue

            values = dimensions.get(dimension, [])
            if not values:
                client.graphql(
                    CLEAR_FIELD_MUTATION,
                    {"project": project_id, "item": item_id, "field": field["id"]},
                )
                continue

            value, unmatched = desired_field_value(field, dimension, values, config)
            if value is not None:
                client.graphql(
                    UPDATE_FIELD_MUTATION,
                    {
                        "project": project_id,
                        "item": item_id,
                        "field": field["id"],
                        "value": value,
                    },
                )
            if unmatched:
                summaries.append(
                    f"#{entity.number}: {project['title']} field {field.get('name')} has no matching option "
                    + ", ".join(unmatched)
                )

        summaries.append(f"#{entity.number}: synchronized {project['title']}")
    return summaries


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=os.getenv("GITHUB_REPOSITORY"))
    parser.add_argument("--config", default=".missionkit/project-sync.json")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--event", help="Path to a GitHub issue/pull_request event payload")
    mode.add_argument("--backfill", choices=["open", "all"], help="Synchronize repository issues/PRs")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.repo or "/" not in args.repo:
        raise ProjectSyncError("--repo or GITHUB_REPOSITORY must be owner/name")

    token = os.getenv("PROJECTS_TOKEN", "").strip()
    client = GitHubClient(token)
    config = load_config(args.config)

    if args.event:
        entities = [entity_from_event(args.event)]
    else:
        entities = client.list_issues_and_prs(args.repo, args.backfill)

    total = 0
    for entity in entities:
        summaries = sync_entity(client, args.repo, entity, config)
        total += 1
        for line in summaries:
            print(f"- {line}")
    print(f"Synchronized {total} issue/pull-request item(s).")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ProjectSyncError as exc:
        print(f"project-sync error: {exc}", file=sys.stderr)
        raise SystemExit(2)
