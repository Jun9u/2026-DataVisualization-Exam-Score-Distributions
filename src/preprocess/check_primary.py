"""Check the published, already transcribed CSAT/CPA input tables."""
import csv
import re
from collections import defaultdict
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data/processed/primary"


def read(name):
    with (DATA / name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main():
    csat, cpa = read("csat.csv"), read("cpa.csv")
    refs = {(r["과목"], int(r["시행연도"])): int(r["대조값"])
            for r in read("denominators.csv")}
    csources = {r["출처ID"] for r in read("csat_sources.csv")}
    psources = {r["원자료"] for r in read("cpa_sources.csv")}
    groups = defaultdict(list)
    for r in csat:
        y = int(r["시행연도"])
        assert r["회차_학년도"] == f"{y+1}학년도"
        assert r["출처ID"] in csources
        groups[(r["과목_모집단"], y)].append(r)
    assert len(csat) == 171 and len(groups) == len(refs) == 19
    for key, rs in groups.items():
        rs.sort(key=lambda r: int(r["원표내_순서"]))
        assert [int(r["원표내_순서"]) for r in rs] == list(range(1, 10))
        assert {int(r["분모"]) for r in rs} == {refs[key]}
        counts = [int(r["구간인원"]) for r in rs]
        assert min(counts) >= 0 and sum(counts) == refs[key]
        bounds = sorted(tuple(map(int, re.fullmatch(r"\d등급 \((\d+)~(\d+)점\)", r["구간"]).groups())) for r in rs)
        assert bounds[0][0] == 0
        assert all(left[1] + 1 == right[0] for left, right in zip(bounds, bounds[1:]))
    groups.clear()
    for r in cpa:
        assert r["원자료"] in psources and r["시행연도"] != "2019"
        groups[(r["과목_평균"], int(r["시행연도"]))].append(r)
    assert len(cpa) == 540 and len(groups) == 54
    for rs in groups.values():
        rs.sort(key=lambda r: int(r["하한_이상"]))
        assert [int(r["하한_이상"]) for r in rs] == list(range(0, 100, 10))
        n = int(rs[0]["응시자"])
        counts = [int(r["구간인원"]) for r in rs]
        assert {int(r["응시자"]) for r in rs} == {n}
        assert min(counts) >= 0 and sum(counts) == n > 0
        assert all(sum(counts[i:]) == int(r["하한이상_누적인원"]) for i, r in enumerate(rs))
    print("OK: CSAT 19 distributions, CPA 54 distributions (2025 separate)")


if __name__ == "__main__":
    main()
