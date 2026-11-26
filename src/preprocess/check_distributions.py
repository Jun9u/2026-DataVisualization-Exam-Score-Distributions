"""Validate selected July grade and LEET score-frequency records."""
import csv
from collections import defaultdict
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data/processed/distributions"


def read(name):
    with (DATA / name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main():
    groups = defaultdict(list)
    july = read("july_grades.csv")
    sources = {r["파일"] for r in read("july_sources.csv")}
    for r in july:
        assert r["원본"] in sources and r["월"] == "7"
        groups[(int(r["시행연도"]), r["과목"])].append(r)
    assert len(july) == 126 and len(groups) == 14
    assert {y for y, _ in groups} == {2017, 2019, 2020, 2022, 2023, 2024, 2025}
    for rs in groups.values():
        assert sorted(int(r["등급"]) for r in rs) == list(range(1, 10))
        n = int(rs[0]["과목응시자"])
        assert {int(r["과목응시자"]) for r in rs} == {n}
        counts = [int(r["인원"]) for r in rs]
        assert min(counts) >= 0 and sum(counts) == n > 0
    groups.clear()
    leet = read("leet.csv")
    sources = {r["파일"] for r in read("leet_sources.csv")}
    for r in leet:
        assert r["원본"] in sources
        groups[(int(r["시행연도"]), r["과목"])].append(r)
    assert len(leet) == 223 and len(groups) == 14
    assert {y for y, _ in groups} == {2018, 2019, 2020, 2022, 2023, 2024, 2025}
    for (y, _), rs in groups.items():
        rs.sort(key=lambda r: float(r["하한_포함"]))
        bounds = [(float(r["하한_포함"]), float(r["상한_미포함"])) for r in rs]
        assert all(lo < hi for lo, hi in bounds)
        assert all(a[1] <= b[0] for a, b in zip(bounds, bounds[1:]))
        n = int(rs[0]["과목유효성적자"])
        assert {int(r["과목유효성적자"]) for r in rs} == {n}
        counts = [int(r["인원"]) for r in rs]
        assert min(counts) >= 0 and sum(counts) == n > 0
        assert {r["점수체계"] for r in rs} == {"2018 이전체계(별도)" if y == 2018 else "2019 이후체계"}
    print("OK: 14 July and 14 LEET distributions (2018 separate)")


if __name__ == "__main__":
    main()
