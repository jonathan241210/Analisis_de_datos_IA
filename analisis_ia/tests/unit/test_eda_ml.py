import pandas as pd

from app.services.eda import boxplot_spec, build_eda_report, histogram_spec
from app.services.ml import train_supervised


def test_eda_shape_and_nulls():
    df = pd.DataFrame({"a": [1, None, 3], "b": ["x", "y", "x"]})
    report = build_eda_report(df)
    assert report["metrics"]["rows"] == 3
    assert report["metrics"]["columns"] == 2
    nulls = {row["columna"]: row["nulos"] for row in report["quality"]["columns"]}
    assert nulls["a"] == 1


def test_histogram_several_columns():
    df = pd.DataFrame({"a": [1, 2, 3, 4], "b": [4, 3, 2, 1]})
    one = histogram_spec(df, ["a"])
    many = histogram_spec(df, ["a", "b"])
    assert one["data"]
    assert len(many["data"]) == 2
    assert many["layout"]["height"] >= 700


def test_histogram_padded_and_question_names():
    col = "  4. ¿Asistes regularmente a clases?  "
    df = pd.DataFrame({col: [1, 2, 3, 4], "b": [4, 3, 2, 1]})
    trimmed = histogram_spec(df, ["4. ¿Asistes regularmente a clases?"])
    padded = histogram_spec(df, [col])
    joined = histogram_spec(df, ["4. ¿Asistes regularmente a clases?,b"])
    assert trimmed["data"]
    assert padded["data"]
    assert len(joined["data"]) == 2


def test_boxplot_several_columns_stacked():
    df = pd.DataFrame({"a": [1, 2, 3, 4, 10], "b": [4, 3, 2, 1, 0]})
    one = boxplot_spec(df, ["a"])
    many = boxplot_spec(df, ["a", "b"])
    assert one["data"]
    assert len(many["data"]) == 2
    assert many["layout"]["height"] >= 700


def test_supervised_smoke():
    df = pd.DataFrame({
        "x": [0, 1, 0, 1, 0, 1, 0, 1],
        "y": [0, 1, 0, 1, 0, 1, 0, 1],
    })
    result = train_supervised(df, "y", ["x"], "Clasificación", "Decision Tree", test_size=0.25)
    assert "accuracy" in result
    assert result["figures"]
