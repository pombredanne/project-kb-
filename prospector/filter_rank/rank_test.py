import os

import pandas as pd
import pytest

from datamodel.commit import Commit
from datamodel.commit_features import CommitWithFeatures
from filter_rank.filter import filter_commits
from filter_rank.rank import make_dataframe, predict, rank, train


@pytest.fixture
def candidates():
    return [
        CommitWithFeatures(
            commit=Commit(repository="repo1", commit_id="1", ghissue_refs=["example"]),
            references_vuln_id=True,
            # TODO: https://github.com/SAP/project-kb/issues/201
            # references_ghissue=True,
            changes_relevant_path={"foo/bar/thing.xml"},
        ),
        CommitWithFeatures(
            commit=Commit(repository="repo2", commit_id="2"),
            references_vuln_id=True,
            # TODO: https://github.com/SAP/project-kb/issues/201
            # references_ghissue=False,
            changes_relevant_path=set(),
        ),
        CommitWithFeatures(
            commit=Commit(repository="repo3", commit_id="3", ghissue_refs=["example"]),
            references_vuln_id=False,
            # TODO: https://github.com/SAP/project-kb/issues/201
            # references_ghissue=True,
            changes_relevant_path=set(),
        ),
        CommitWithFeatures(
            commit=Commit(repository="repo4", commit_id="4"),
            references_vuln_id=False,
            # TODO: https://github.com/SAP/project-kb/issues/201
            # references_ghissue=False,
            changes_relevant_path={"foo/bar/otherthing.xml", "pom.xml"},
        ),
        CommitWithFeatures(
            commit=Commit(repository="repo5", commit_id="5"),
            references_vuln_id=False,
            # TODO: https://github.com/SAP/project-kb/issues/201
            # references_ghissue=False,
            changes_relevant_path=set(),
        ),
    ]


def test_filter(candidates):
    result = filter_commits(candidates)
    assert isinstance(result, list)


def test_rank(candidates):
    model_name = "LR_15_components"
    result = rank(candidates, model_name)
    assert isinstance(result, list)


def test_train():
    path = train("test123")
    assert os.path.exists(path)

    if os.path.exists(path):
        os.remove(path)


def test_get_training_dataframe():
    df = make_dataframe()
    assert isinstance(df, pd.DataFrame)


def test_predict(candidates):
    model_name = "LR_15_components"
    commit = candidates[0]
    score = predict(model_name, commit)
    assert isinstance(score, float)
