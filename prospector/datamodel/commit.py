import re
from typing import Dict, List, Optional, Tuple
import requests

from pydantic import BaseModel, Field
from psycopg2.extras import DictRow

from datamodel.nlp import (
    extract_cve_references,
    extract_ghissue_references,
    extract_jira_references,
)
from git.git import Commit as RawCommit


class Commit(BaseModel):
    """
    Remember to propagate any changes you make here to the DB schema and
    to the save() and lookup() functions of the database module.
    """

    commit_id: str = ""
    repository: str = ""
    timestamp: Optional[int] = 0
    hunks: List[Tuple[int, int]] = Field(default_factory=list)
    message: Optional[str] = ""
    diff: List[str] = Field(default_factory=list)
    changed_files: List[str] = Field(default_factory=list)
    message_reference_content: List[str] = Field(default_factory=list)
    jira_refs: Dict[str, str] = Field(default_factory=dict)
    ghissue_refs: Dict[str, str] = Field(default_factory=dict)
    cve_refs: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    annotations: Dict[str, str] = Field(default_factory=dict)
    weight: Optional[int] = 0

    @property
    def hunk_count(self):
        return len(self.hunks)

    # Re-implement these two methods to allow sorting by weight
    def __lt__(self, other) -> bool:
        return self.weight < other.weight

    def __eq__(self, other) -> bool:
        return self.weight == other.weight

    # def format(self):
    #     out = "Commit: {} {}".format(self.repository.get_url(), self.commit_id)
    #     out += "\nhunk_count: %d   diff_size: %d" % (self.hunk_count, len(self.diff))
    #     return out
    def toJSON(self):
        return self.json()

    def print(self):
        out = f"Commit: {self.commit_id}\nRepository: {self.repository}\nMessage: {self.message}\nTags: {self.tags}\n"
        print(out)


def parse_commit(raw_commit_data: DictRow) -> Commit:
    """
    This function is responsible of parsing a preprocessed commit from the database
    """
    commit = Commit(
        commit_id=raw_commit_data["commit_id"],
        repository=raw_commit_data["repository"],
        timestamp=int(raw_commit_data["timestamp"]),
        hunks=get_hunks(raw_commit_data["hunks"]),
        message=raw_commit_data["message"],
        diff=raw_commit_data["diff"],
        changed_files=raw_commit_data["changed_files"],
        message_reference_content=raw_commit_data["message_reference_content"],
        jira_refs=dict(
            zip(raw_commit_data["jira_refs_id"], raw_commit_data["jira_refs_content"])
        ),
        ghissue_refs=dict(
            zip(
                raw_commit_data["ghissue_refs_id"],
                raw_commit_data["ghissue_refs_content"],
            )
        ),
        cve_refs=raw_commit_data["cve_refs"],
        tags=raw_commit_data["tags"],
    )
    return commit


def get_hunks(raw_hunks: List[str]) -> List[Tuple[int, int]]:
    """
    This function is responsible of extracting the hunks from a commit
    """
    hunks = [int(x) for x in re.findall("[0-9]+", "".join(raw_hunks))]
    # They are always pairs so no problem
    return list(zip(hunks, hunks[2:]))


def make_from_raw_commit(git_commit: RawCommit) -> Commit:
    """
    This function is responsible of translating a raw (git)Commit
    into a preprocessed-Commit, that can be saved to the DB
    and later used by the ranking/ML module.


    NOTE: don't be confused by the fact that we have two classes
    both named Commit: the one from the git module represents
    a commit as extracted directly from Git, with only minimal post-processing.
    The datamodel.Commit class instead maps one-to-one onto the
    rows of the backend database, and its instances are the input
    to the ranking module (together with an Advisory Record with
    which they must be matched)
    """

    commit_id = git_commit.get_id()
    repository_url = git_commit._repository._url

    commit = Commit(commit_id=commit_id, repository=repository_url)

    # This is where all the attributes of the preprocessed commit
    # are computed and assigned.
    #
    # Note: all attributes that do not depend on a particular query
    # (that is, that do not depend on a particular Advisory Record)
    # should be computed here so that they can be stored in the db.
    # Space-efficiency is important.

    commit.diff = git_commit.get_diff()
    commit.hunks = git_commit.get_hunks()
    commit.message = git_commit.get_msg()
    commit.timestamp = int(git_commit.get_timestamp())
    commit.changed_files = git_commit.get_changed_files()
    commit.tags = git_commit.get_tags()
    commit.jira_refs = extract_jira_references(commit.repository, commit.message)
    commit.ghissue_refs = extract_ghissue_references(commit.repository, commit.message)
    commit.cve_refs = extract_cve_references(commit.repository, commit.message)

    return commit


if __name__ == "__main__":
    from git.git import Git

    repo = Git("https://github.com/apache/struts")
    raw = repo.get_commit("93f378809cc73c65c1d689a0e32ec440c52e7ce2")
    repo.clone()
    commit = make_from_raw_commit(raw)
