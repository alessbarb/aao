from aao.capability_evaluation import recommend


def test_equal_weighted_assessment_selects_unique_best_and_leaves_ties_open():
    options = [
        {"choice": "reuse", "fit": 5, "security": 5, "cost": 5, "time": 5,
         "tokens": 5, "maintenance": 5},
        {"choice": "adapt", "fit": 4, "security": 4, "cost": 4, "time": 4,
         "tokens": 4, "maintenance": 4},
        {"choice": "build", "fit": 3, "security": 3, "cost": 3, "time": 3,
         "tokens": 3, "maintenance": 3},
    ]
    recommendation, scores = recommend(options)
    assert recommendation == "reuse"
    assert scores == {"reuse": 5.0, "adapt": 4.0, "build": 3.0}

    options[1] = {**options[1], "fit": 5, "security": 5, "cost": 5,
                  "time": 5, "tokens": 5, "maintenance": 5}
    recommendation, _ = recommend(options)
    assert recommendation is None
