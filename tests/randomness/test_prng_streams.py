"""PRNG reproducibility tests."""

from revive.rng import PRNGStreamRegistry


def test_same_seed_same_sequence():
    a = PRNGStreamRegistry(42).stream("predictor")
    b = PRNGStreamRegistry(42).stream("predictor")
    assert [a.randint(0, 1000) for _ in range(5)] == [b.randint(0, 1000) for _ in range(5)]


def test_different_labels_different_sequences():
    reg = PRNGStreamRegistry(99)
    assert reg.stream("predictor").random() != reg.stream("allocator").random()


def test_different_seeds_different_sequences():
    a = PRNGStreamRegistry(1).stream("dataset")
    b = PRNGStreamRegistry(2).stream("dataset")
    assert a.random() != b.random()
