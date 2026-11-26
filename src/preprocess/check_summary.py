"""Check selected professional and annual/round summary inputs."""
import csv
from math import isclose
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data/processed/summary"


def read(name):
    with (DATA / name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main():
    prof = read("professional.csv")
    sources = {r["원본"] for r in read("professional_sources.csv")}
    keys = {(r["시험"], r["차수"], r["시행연도"], r["구분"], r["과목"]) for r in prof}
    assert len(prof) == len(keys) == 176
    excluded = []
    for r in prof:
        assert r["원본"] in sources
        n, c = int(r["과목응시자"]), int(r["원표과락인원"])
        assert n > 0 and 0 <= c <= n and 0 <= float(r["응시자평균"]) <= 100
        if not r["분석_과락률_pct"]:
            excluded.append((r["시험"], r["차수"], r["시행연도"], r["과목"]))
        else:
            assert isclose(float(r["분석_과락률_pct"]), 100*c/n, abs_tol=0.000001)
    assert excluded == [("세무사", "1", "2019", "상법")]
    toeic = read("toeic_annual.csv")
    assert sorted(int(r["시행연도"]) for r in toeic) == list(range(2017, 2026))
    assert all(0 <= int(r["평균"]) <= 990 for r in toeic)
    assert next(r["평균"] for r in toeic if r["시행연도"] == "2024") == "683"
    dietitian = read("dietitian.csv")
    assert [int(r["회차"]) for r in dietitian] == list(range(40, 50))
    assert all(r["만점"] == "220" and 0 <= float(r["평균"]) <= 220 and float(r["표준편차"]) > 0 for r in dietitian)
    assert sum(r["표기연도"] == "2017" for r in dietitian) == 2
    print("OK: 176 professional subject records, 9 TOEIC annual means, 10 dietitian rounds")


if __name__ == "__main__":
    main()
