from note_growth.metrics import analyze_metrics, score_row


def test_score_row_weights_sales_more_than_views() -> None:
    row = {"views": 100, "likes": 10, "comments": 1, "sales": 2, "price": 980}
    assert score_row(row) == 39


def test_analyze_metrics_returns_recommendations() -> None:
    report = analyze_metrics(
        [
            {
                "published_at": "2026-01-01",
                "title": "A",
                "views": 100.0,
                "likes": 10.0,
                "comments": 1.0,
                "sales": 1.0,
                "price": 500.0,
            },
            {
                "published_at": "2026-01-02",
                "title": "B",
                "views": 200.0,
                "likes": 5.0,
                "comments": 0.0,
                "sales": 0.0,
                "price": 500.0,
            },
        ]
    )

    assert report["row_count"] == 2
    assert report["ranked"][0]["title"] == "A"
    assert report["recommendations"]
